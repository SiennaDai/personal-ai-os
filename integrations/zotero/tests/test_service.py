from __future__ import annotations

import copy
import hashlib
import json
import tempfile
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


class FakePdfUploadClient(FakeApiClient):
    def __init__(self, *, fail_upload: bool = False, fail_create: bool = False) -> None:
        super().__init__({"/items/ABCD2345": fixture("item.json")})
        self.attachment = None
        self.pending = None
        self.uploaded = b""
        self.fail_upload = fail_upload
        self.fail_create = fail_create

    def get(self, path: str, *, query=None) -> JsonResponse:
        self.calls.append(("GET", path, query))
        if path == "/items/ABCD2345/children":
            rows = [self.attachment] if self.attachment else []
            return JsonResponse(200, {"total-results": str(len(rows))}, copy.deepcopy(rows))
        if path == "/items/ABCD2345":
            return JsonResponse(200, {}, fixture("item.json"))
        if self.attachment and path == f"/items/{self.attachment['key']}":
            return JsonResponse(200, {}, copy.deepcopy(self.attachment))
        raise IntegrationError("NOT_FOUND", "fake route not found")

    def post(self, path: str, body: object, *, headers=None) -> JsonResponse:
        self.calls.append(("POST", path, {"body": body, "headers": headers}))
        item = copy.deepcopy(body[0])
        item["version"] = 43
        self.attachment = {
            "key": item["key"],
            "version": 43,
            "links": {},
            "meta": {},
            "data": item,
        }
        if self.fail_create:
            raise IntegrationError("BACKEND_UNAVAILABLE", "simulated ambiguous create", retryable=True)
        return JsonResponse(200, {}, {"successful": {"0": item["key"]}, "failed": {}})

    def post_form(self, path: str, fields: object, *, headers=None) -> JsonResponse:
        self.calls.append(("POST_FORM", path, {"fields": fields, "headers": headers}))
        if "upload" not in fields:
            self.pending = dict(fields)
            return JsonResponse(
                200,
                {},
                {
                    "url": "http://127.0.0.1:23119/api/local/uploads/UPLOAD1",
                    "uploadKey": "UPLOAD1",
                    "contentType": "application/pdf",
                    "prefix": "",
                    "suffix": "",
                },
            )
        self.attachment["data"].update(
            {
                "md5": self.pending["md5"],
                "filename": self.pending["filename"],
                "mtime": str(self.pending["mtime"]),
            }
        )
        self.attachment["version"] = 44
        self.attachment["data"]["version"] = 44
        return JsonResponse(204, {"last-modified-version": "44"}, None)

    def post_upload(self, url: str, file_body, body_length: int, content_type: str) -> JsonResponse:  # noqa: ANN001
        self.calls.append(("POST_UPLOAD", url, {"length": body_length, "type": content_type}))
        if self.fail_upload:
            raise IntegrationError("BACKEND_UNAVAILABLE", "simulated upload failure", retryable=True)
        self.uploaded = file_body.read()
        return JsonResponse(201, {}, None)


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

    def test_create_bibliographic_item_in_exact_name_scope(self) -> None:
        created = fixture("item.json")
        created["key"] = "NPQR6789"
        created["data"]["key"] = "NPQR6789"
        write = FakeApiClient(
            {
                "/collections/RSTU2345": fixture("collection.json"),
                "/items/NPQR6789": created,
                ("POST", "/items"): {"successful": {"0": "NPQR6789"}, "failed": {}},
            }
        )
        config = self.config(
            write_enabled=True,
            write_scope="collections",
            allowed_write_collection_names=("Integration Test Sources",),
        )
        result = self.service(
            FakeApiClient(),
            config=config,
            write_client=write,
        ).create_bibliographic_item(
            "journalArticle",
            "A new paper",
            "RSTU2345",
            "0123456789abcdef0123456789abcdef",
            creators=[{"creator_type": "author", "first_name": "Ada", "last_name": "Lovelace"}],
            container_title="A Journal",
            fields={"doi": "10.1000/example", "date": "2026"},
        )
        self.assertEqual(result["effect"], "created_bibliographic_item")
        post_call = next(call for call in write.calls if call[0] == "POST")
        body = post_call[2]["body"][0]
        self.assertEqual(body["collections"], ["RSTU2345"])
        self.assertEqual(body["publicationTitle"], "A Journal")
        self.assertEqual(body["DOI"], "10.1000/example")

    def test_import_pdf_attachment_is_resumable_and_hash_verified(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pdf = root / "paper.pdf"
            content = b"%PDF-1.7\ncontrolled test\n%%EOF\n"
            pdf.write_bytes(content)
            client = FakePdfUploadClient()
            config = self.config(
                write_enabled=True,
                write_scope="collections",
                allowed_write_collection_keys=("RSTU2345",),
                attachment_upload_enabled=True,
                allowed_pdf_import_roots=(directory,),
            )
            service = self.service(FakeApiClient(), config=config, write_client=client)
            result = service.import_pdf_attachment(
                "ABCD2345",
                42,
                str(pdf),
                "0123456789abcdef0123456789abcdef",
                source_url="https://example.org/paper.pdf",
            )
            repeated = service.import_pdf_attachment(
                "ABCD2345",
                42,
                str(pdf),
                "0123456789abcdef0123456789abcdef",
                source_url="https://example.org/paper.pdf",
            )
        self.assertEqual(result["effect"], "imported_pdf_attachment")
        self.assertEqual(repeated["effect"], "pdf_already_attached")
        self.assertEqual(client.uploaded, content)
        self.assertEqual(result["file"]["md5"], hashlib.md5(content).hexdigest())
        self.assertEqual(result["file"]["sha256"], hashlib.sha256(content).hexdigest())
        self.assertNotIn(str(pdf), str(result))
        self.assertEqual(len([call for call in client.calls if call[0] == "POST_UPLOAD"]), 1)

    def test_import_pdf_rejects_out_of_scope_and_non_pdf_files(self) -> None:
        with tempfile.TemporaryDirectory() as allowed, tempfile.TemporaryDirectory() as outside:
            outside_pdf = Path(outside) / "paper.pdf"
            outside_pdf.write_bytes(b"%PDF-test")
            invalid = Path(allowed) / "paper.pdf"
            invalid.write_bytes(b"not a pdf")
            config = self.config(
                write_enabled=True,
                write_scope="collections",
                allowed_write_collection_keys=("RSTU2345",),
                attachment_upload_enabled=True,
                allowed_pdf_import_roots=(allowed,),
            )
            service = self.service(
                FakeApiClient(),
                config=config,
                write_client=FakePdfUploadClient(),
            )
            with self.assertRaises(IntegrationError) as outside_error:
                service.import_pdf_attachment(
                    "ABCD2345",
                    42,
                    str(outside_pdf),
                    "0123456789abcdef0123456789abcdef",
                )
            with self.assertRaises(IntegrationError) as invalid_error:
                service.import_pdf_attachment(
                    "ABCD2345",
                    42,
                    str(invalid),
                    "fedcba9876543210fedcba9876543210",
                )
        self.assertEqual(outside_error.exception.code, "FILE_SCOPE_DENIED")
        self.assertEqual(invalid_error.exception.code, "INVALID_PDF")

    def test_import_pdf_rejects_symlinks_and_a_different_existing_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target.pdf"
            target.write_bytes(b"%PDF-target")
            symlink = root / "linked.pdf"
            symlink.symlink_to(target)
            config = self.config(
                write_enabled=True,
                write_scope="collections",
                allowed_write_collection_keys=("RSTU2345",),
                attachment_upload_enabled=True,
                allowed_pdf_import_roots=(directory,),
            )
            client = FakePdfUploadClient()
            service = self.service(FakeApiClient(), config=config, write_client=client)
            with self.assertRaises(IntegrationError) as symlink_error:
                service.import_pdf_attachment(
                    "ABCD2345",
                    42,
                    str(symlink),
                    "0123456789abcdef0123456789abcdef",
                )
            existing = fixture("attachment.json")
            existing["data"]["md5"] = hashlib.md5(b"%PDF-other").hexdigest()
            client.attachment = existing
            with self.assertRaises(IntegrationError) as existing_error:
                service.import_pdf_attachment(
                    "ABCD2345",
                    42,
                    str(target),
                    "fedcba9876543210fedcba9876543210",
                )
        self.assertEqual(symlink_error.exception.code, "FILE_SCOPE_DENIED")
        self.assertEqual(existing_error.exception.code, "PDF_ATTACHMENT_EXISTS")

    def test_import_pdf_reports_recoverable_partial_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            pdf = Path(directory) / "paper.pdf"
            pdf.write_bytes(b"%PDF-test")
            client = FakePdfUploadClient(fail_upload=True)
            config = self.config(
                write_enabled=True,
                write_scope="collections",
                allowed_write_collection_keys=("RSTU2345",),
                attachment_upload_enabled=True,
                allowed_pdf_import_roots=(directory,),
            )
            with self.assertRaises(IntegrationError) as raised:
                self.service(FakeApiClient(), config=config, write_client=client).import_pdf_attachment(
                    "ABCD2345",
                    42,
                    str(pdf),
                    "0123456789abcdef0123456789abcdef",
                )
        self.assertEqual(raised.exception.code, "BACKEND_UNAVAILABLE")
        self.assertEqual(raised.exception.details["stage"], "upload_bytes")
        self.assertTrue(raised.exception.details["recoverable_with_same_operation_id"])

    def test_import_pdf_ambiguous_create_can_resume_with_same_operation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            pdf = Path(directory) / "paper.pdf"
            pdf.write_bytes(b"%PDF-test")
            client = FakePdfUploadClient(fail_create=True)
            config = self.config(
                write_enabled=True,
                write_scope="collections",
                allowed_write_collection_keys=("RSTU2345",),
                attachment_upload_enabled=True,
                allowed_pdf_import_roots=(directory,),
            )
            service = self.service(FakeApiClient(), config=config, write_client=client)
            with self.assertRaises(IntegrationError) as raised:
                service.import_pdf_attachment(
                    "ABCD2345",
                    42,
                    str(pdf),
                    "0123456789abcdef0123456789abcdef",
                )
            client.fail_create = False
            resumed = service.import_pdf_attachment(
                "ABCD2345",
                42,
                str(pdf),
                "0123456789ABCDEF0123456789ABCDEF",
            )
        self.assertEqual(raised.exception.details["stage"], "create_attachment")
        self.assertTrue(raised.exception.details["recoverable_with_same_operation_id"])
        self.assertEqual(resumed["effect"], "imported_pdf_attachment")

    def test_add_item_to_collection_is_append_only(self) -> None:
        current = fixture("item.json")
        current["data"]["collections"] = ["UVWX2345"]
        write = FakeApiClient(
            {
                "/collections/RSTU2345": fixture("collection.json"),
                "/items/ABCD2345": current,
            }
        )
        config = self.config(
            write_enabled=True,
            write_scope="collections",
            allowed_write_collection_keys=("RSTU2345",),
        )
        result = self.service(
            FakeApiClient(),
            config=config,
            write_client=write,
        ).add_item_to_collection("ABCD2345", 42, "RSTU2345")
        self.assertEqual(result["effect"], "added_to_collection")
        patch_call = next(call for call in write.calls if call[0] == "PATCH")
        self.assertEqual(
            patch_call[2]["body"]["collections"],
            ["UVWX2345", "RSTU2345"],
        )

    def test_add_item_to_collection_refuses_malformed_existing_membership(self) -> None:
        current = fixture("item.json")
        current["data"]["collections"] = ["malformed"]
        write = FakeApiClient(
            {
                "/collections/RSTU2345": fixture("collection.json"),
                "/items/ABCD2345": current,
            }
        )
        config = self.config(
            write_enabled=True,
            write_scope="collections",
            allowed_write_collection_keys=("RSTU2345",),
        )
        service = self.service(FakeApiClient(), config=config, write_client=write)
        with self.assertRaisesRegex(IntegrationError, "invalid collection membership"):
            service.add_item_to_collection("ABCD2345", 42, "RSTU2345")
        self.assertFalse(any(call[0] == "PATCH" for call in write.calls))

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
