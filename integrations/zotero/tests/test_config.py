from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from paios_zotero.config import ZoteroConfig, load_config
from paios_zotero.errors import IntegrationError


class ConfigTests(unittest.TestCase):
    def test_example_config_is_valid_and_read_only(self) -> None:
        config = load_config(Path(__file__).parents[2] / "config.example.toml")
        self.assertEqual(config.read_backend, "local")
        self.assertFalse(config.write_enabled)
        self.assertEqual(config.write_scope, "disabled")

    def test_unknown_field_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "integrations.toml"
            path.write_text("[zotero]\nunknown = true\n", encoding="utf-8")
            with self.assertRaisesRegex(IntegrationError, "Unknown Zotero"):
                load_config(path)

    def test_local_api_must_remain_loopback(self) -> None:
        config = ZoteroConfig(local_api_url="http://192.0.2.1:23119/api")
        with self.assertRaisesRegex(IntegrationError, "loopback"):
                config.validate()

    def test_local_transport_is_closed_enum(self) -> None:
        config = ZoteroConfig(local_transport="port-forward")
        with self.assertRaisesRegex(IntegrationError, "local_transport"):
            config.validate()

    def test_enabled_writes_require_scope(self) -> None:
        config = ZoteroConfig(write_enabled=True)
        with self.assertRaisesRegex(IntegrationError, "write_scope"):
            config.validate()

    def test_write_readiness_never_returns_secret(self) -> None:
        config = ZoteroConfig(
            web_library_id="123456",
            write_enabled=True,
            write_scope="library",
        )
        config.validate_write_ready({"ZOTERO_API_KEY": "super-secret"})
        self.assertNotIn("super-secret", str(config.public_summary({"ZOTERO_API_KEY": "super-secret"})))

    def test_collection_scope_accepts_an_exact_collection_name(self) -> None:
        ZoteroConfig(
            write_enabled=True,
            write_scope="collections",
            allowed_write_collection_names=("临时工作区",),
        ).validate_write_ready()

    def test_local_authorization_timeout_allows_human_response_time(self) -> None:
        self.assertEqual(ZoteroConfig().local_authorization_timeout_seconds, 120.0)
        with self.assertRaisesRegex(IntegrationError, "local_authorization_timeout_seconds"):
            ZoteroConfig(local_authorization_timeout_seconds=5).validate()


if __name__ == "__main__":
    unittest.main()
