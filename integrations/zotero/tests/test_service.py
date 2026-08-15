from __future__ import annotations

import copy
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from paios_zotero.config import ZoteroConfig
from paios_zotero.errors import IntegrationError
from paios_zotero.http_client import JsonResponse
from paios_zotero.service import ZoteroService
from paios_zotero.smoke import run_read_smoke


FIXTURES = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 8, 15, 0, 0, tzinfo=timezone.utc)


def fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class FakeApiClient:
    def __init__(self, routes: dict[str, object] | None = None) -> None:
        self.routes = routes or {}
        self.calls: list[tuple[str, str, object]] = []

    def get(self, path: str, *, query=None) -> JsonResponse:
        self.calls.append(("GET", path, query))
        value = self.routes.get(path)
        if callable(value):
            value = value(query)
        if isinstance(value, JsonResponse):
            return value
        if value is None:
            raise IntegrationError("NOT_FOUND", "fake route not found")
        headers = {"total-results": str(len(value))} if isinstance(value, list) else {}
        return JsonResponse(200, headers, copy.deepcopy(value))

    def post(self, path: str, body: object, *, headers=None) -> JsonResponse:
        self.calls.append(("POST", path, {"body": body, "headers": headers}))
        value = self.routes.get(("POST", path))
        if isinstance(value, JsonResponse):
            return value
        return JsonResponse(200, {}, copy.deepcopy(value))

    def patch(self, path: str, body: object, *, headers=None) -> JsonResponse:
        self.calls.append(("PATCH", path, {"body": body, "headers": headers}))
        value = self.routes.get(path)
        if isinstance(value, dict) and isinstance(value.get("data"), dict):
            value["data"].update(body)
            value["version"] = int(value.get("version", 0)) + 1
            value["data"]["version"] = value["version"]
        return JsonResponse(204, {"last-modified-version": "99"}, None)


class FakeBbtClient:
    def ready(self) -> dict[str, object]:
        return {"betterbibtex": "9.0.55", "zotero": "9.0.6"}

    def citation_keys(self, keys: list[str]) -> dict[str, str]:
        return {keys[0]: "lovelaceNotes1843"}


class ServiceTests(unittest.TestCase):
    def config(self, **changes) -> ZoteroConfig:
        values = {
            "web_library_id": "123456",
            "max_fulltext_chars": 1000,
        }
        values.update(changes)
        return ZoteroConfig(**values)

    def service(self, read: FakeApiClient, **kwargs) -> ZoteroService:
        return ZoteroService(
            kwargs.pop("config", self.config()),
            read_client=read,
            clock=lambda: NOW,
            **kwargs,
        )

    def test_search_returns_normalized_items_and_page(self) -> None:
        read = FakeApiClient(
            {
                "/items/top": JsonResponse(
                    200,
                    {"total-results": "3"},
                    [fixture("item.json")],
                )
            }
        )
        result = self.service(read).search_items("Analytical Engine", limit=1)
        self.assertEqual(result["items"][0]["ref"]["key"], "ABCD2345")
        self.assertEqual(result["page"]["total"], 3)
        self.assertEqual(result["page"]["next_start"], 1)
        self.assertEqual(read.calls[0][2]["qmode"], "titleCreatorYear")

    def test_fulltext_is_bounded_and_provenanced(self) -> None:
        read = FakeApiClient(
            {
                "/items/ABCD2345": fixture("item.json"),
                "/items/ABCD2345/children": [fixture("attachment.json")],
                "/items/EFGH6789/fulltext": {
                    "content": "0123456789",
                    "indexedPages": 1,
                    "totalPages": 1,
                },
            }
        )
        result = self.service(read).get_fulltext("ABCD2345", offset=2, max_chars=4)
        self.assertEqual(result["content"], "2345")
        self.assertTrue(result["truncated"])
        self.assertEqual(result["next_offset"], 6)
        self.assertEqual(result["attachment_ref"]["key"], "EFGH6789")

    def test_multiple_pdf_attachments_require_explicit_selection(self) -> None:
        second = fixture("attachment.json")
        second["key"] = "NPQR6789"
        second["data"]["key"] = "NPQR6789"
        read = FakeApiClient(
            {
                "/items/ABCD2345": fixture("item.json"),
                "/items/ABCD2345/children": [fixture("attachment.json"), second],
            }
        )
        with self.assertRaisesRegex(IntegrationError, "multiple PDF"):
            self.service(read).get_fulltext("ABCD2345")

    def test_annotations_are_discovered_through_attachments(self) -> None:
        read = FakeApiClient(
            {
                "/items/ABCD2345": fixture("item.json"),
                "/items/ABCD2345/children": [fixture("attachment.json")],
                "/items/EFGH6789/children": [fixture("annotation.json")],
            }
        )
        result = self.service(read).get_annotations("ABCD2345")
        self.assertEqual(result["annotations"][0]["annotation"]["text"], "An important passage.")

    def test_citation_key_uses_only_better_bibtex_read_method(self) -> None:
        service = self.service(FakeApiClient(), bbt_client=FakeBbtClient())
        result = service.get_citation_key("ABCD2345")
        self.assertEqual(result["citation_key"], "lovelaceNotes1843")

    def test_disabled_writes_fail_before_network_access(self) -> None:
        write = FakeApiClient()
        service = self.service(FakeApiClient(), write_client=write)
        with self.assertRaisesRegex(IntegrationError, "disabled"):
            service.create_child_note(
                "ABCD2345",
                "<p>Test</p>",
                "0123456789abcdef0123456789abcdef",
            )
        self.assertEqual(write.calls, [])

    def test_update_requires_version_and_collection_scope(self) -> None:
        current = fixture("item.json")
        write = FakeApiClient({"/items/ABCD2345": current})
        config = self.config(
            write_enabled=True,
            write_scope="collections",
            allowed_write_collection_keys=("RSTU2345",),
        )
        service = self.service(
            FakeApiClient(),
            config=config,
            write_client=write,
            environ={"ZOTERO_API_KEY": "secret"},
        )
        with self.assertRaisesRegex(IntegrationError, "expected_version"):
            service.update_item_fields("ABCD2345", 41, {"title": "New title"})
        result = service.update_item_fields("ABCD2345", 42, {"title": "New title"})
        self.assertEqual(result["updated"]["ref"]["version"], 43)
        patch_call = next(call for call in write.calls if call[0] == "PATCH")
        self.assertEqual(patch_call[2]["headers"]["If-Unmodified-Since-Version"], "42")

    def test_create_child_note_uses_scope_and_idempotency_token(self) -> None:
        write = FakeApiClient(
            {
                "/items/ABCD2345": fixture("item.json"),
                "/items/MNPQ6789": fixture("note.json"),
                ("POST", "/items"): {"successful": {"0": "MNPQ6789"}, "failed": {}},
            }
        )
        config = self.config(
            write_enabled=True,
            write_scope="collections",
            allowed_write_collection_keys=("RSTU2345",),
        )
        service = self.service(
            FakeApiClient(),
            config=config,
            write_client=write,
            environ={"ZOTERO_API_KEY": "secret"},
        )
        result = service.create_child_note(
            "ABCD2345",
            "<p>Controlled test note.</p>",
            "0123456789abcdef0123456789abcdef",
            tags=["personal-ai-os-test"],
        )
        self.assertEqual(result["created"]["ref"]["key"], "MNPQ6789")
        post_call = next(call for call in write.calls if call[0] == "POST")
        self.assertEqual(
            post_call[2]["headers"]["Zotero-Write-Token"],
            "0123456789abcdef0123456789abcdef",
        )
        self.assertEqual(post_call[2]["body"][0]["parentItem"], "ABCD2345")

    def test_update_note_checks_parent_scope_and_version(self) -> None:
        write = FakeApiClient(
            {
                "/items/ABCD2345": fixture("item.json"),
                "/items/MNPQ6789": fixture("note.json"),
            }
        )
        config = self.config(
            write_enabled=True,
            write_scope="collections",
            allowed_write_collection_keys=("RSTU2345",),
        )
        service = self.service(
            FakeApiClient(),
            config=config,
            write_client=write,
            environ={"ZOTERO_API_KEY": "secret"},
        )
        result = service.update_note("MNPQ6789", 5, "<p>Updated note.</p>")
        self.assertEqual(result["updated"]["ref"]["version"], 6)
        patch_call = next(call for call in write.calls if call[0] == "PATCH")
        self.assertEqual(patch_call[2]["headers"]["If-Unmodified-Since-Version"], "5")

    def test_write_scope_denies_item_outside_allowed_collections(self) -> None:
        current = fixture("item.json")
        current["data"]["collections"] = []
        write = FakeApiClient({"/items/ABCD2345": current})
        config = self.config(
            write_enabled=True,
            write_scope="collections",
            allowed_write_collection_keys=("RSTU2345",),
        )
        service = self.service(
            FakeApiClient(),
            config=config,
            write_client=write,
            environ={"ZOTERO_API_KEY": "secret"},
        )
        with self.assertRaisesRegex(IntegrationError, "outside"):
            service.update_item_fields("ABCD2345", 42, {"title": "New title"})

    def test_active_note_html_is_rejected(self) -> None:
        config = self.config(write_enabled=True, write_scope="library")
        service = self.service(
            FakeApiClient(),
            config=config,
            write_client=FakeApiClient(),
            environ={"ZOTERO_API_KEY": "secret"},
        )
        with self.assertRaisesRegex(IntegrationError, "active content"):
            service.create_child_note(
                "ABCD2345",
                "<script>alert(1)</script>",
                "0123456789abcdef0123456789abcdef",
            )

    def test_read_smoke_returns_only_capability_evidence(self) -> None:
        read = FakeApiClient(
            {
                "/items": JsonResponse(200, {"last-modified-version": "9"}, {}),
                "/collections": [fixture("collection.json")],
                "/items/top": [fixture("item.json")],
                "/items/ABCD2345": fixture("item.json"),
                "/items/ABCD2345/children": [fixture("attachment.json")],
                "/items/EFGH6789": fixture("attachment.json"),
                "/items/EFGH6789/children": [fixture("annotation.json")],
                "/items/EFGH6789/fulltext": {
                    "content": "bounded source text",
                    "indexedPages": 1,
                    "totalPages": 1,
                },
            }
        )
        service = self.service(read, bbt_client=FakeBbtClient())
        result = run_read_smoke(service)
        self.assertTrue(result["overall_ok"])
        self.assertTrue(result["checks"]["fulltext"]["bounded_slice_returned"])
        serialized = json.dumps(result)
        self.assertNotIn("Analytical Engine", serialized)
        self.assertNotIn("lovelaceNotes1843", serialized)

    def test_read_smoke_exercises_search_for_an_empty_library(self) -> None:
        read = FakeApiClient(
            {
                "/items": JsonResponse(200, {"last-modified-version": "0"}, {}),
                "/collections": [],
                "/items/top": [],
            }
        )
        result = run_read_smoke(self.service(read, bbt_client=FakeBbtClient()))
        self.assertTrue(result["overall_ok"])
        self.assertTrue(result["checks"]["search"]["sentinel_query_returned_zero"])
        self.assertEqual(sum(call[1] == "/items/top" for call in read.calls), 2)


if __name__ == "__main__":
    unittest.main()
