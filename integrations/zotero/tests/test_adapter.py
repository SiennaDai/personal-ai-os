from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from paios_zotero.adapter import normalize_collection, normalize_item
from paios_zotero.config import ZoteroConfig


FIXTURES = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 8, 15, 0, 0, tzinfo=timezone.utc)


def fixture(name: str) -> object:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class AdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = ZoteroConfig(web_library_id="123456")

    def test_bibliographic_item_is_normalized_with_stable_identity(self) -> None:
        item = normalize_item(fixture("item.json"), self.config, "local", clock=lambda: NOW)
        self.assertEqual(item["ref"]["id"], "zotero:personal:item:ABCD2345")
        self.assertEqual(item["ref"]["version"], 42)
        self.assertEqual(item["creators"][0]["last_name"], "Lovelace")
        self.assertEqual(item["identifiers"]["doi"], "10.0000/example")
        self.assertEqual(item["provenance"]["backend"], "local")
        self.assertNotIn("raw", item)

    def test_attachment_and_annotation_preserve_native_details(self) -> None:
        attachment = normalize_item(
            fixture("attachment.json"), self.config, "local", clock=lambda: NOW
        )
        annotation = normalize_item(
            fixture("annotation.json"), self.config, "local", clock=lambda: NOW
        )
        self.assertEqual(attachment["attachment"]["content_type"], "application/pdf")
        self.assertEqual(annotation["annotation"]["page_label"], "4")
        self.assertEqual(annotation["parent_item_key"], "EFGH6789")

    def test_collection_is_normalized(self) -> None:
        collection = normalize_collection(
            fixture("collection.json"), self.config, "local", clock=lambda: NOW
        )
        self.assertEqual(collection["ref"]["id"], "zotero:personal:collection:RSTU2345")
        self.assertEqual(collection["counts"]["items"], 2)
        self.assertIsNone(collection["parent_collection_key"])


if __name__ == "__main__":
    unittest.main()
