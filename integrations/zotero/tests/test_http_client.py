from __future__ import annotations

import io
import json
import subprocess
import tempfile
import unittest
import urllib.error

from paios_zotero.config import ZoteroConfig
from paios_zotero.errors import IntegrationError
from paios_zotero.http_client import (
    JsonHttpClient,
    JsonResponse,
    WindowsCurlJsonHttpClient,
    ZoteroApiClient,
)


class FakeResponse:
    def __init__(self, payload: object, *, status: int = 200, headers=None) -> None:
        self.status = status
        self.headers = headers or {}
        self.payload = json.dumps(payload).encode()

    def read(self, limit: int = -1) -> bytes:
        return self.payload if limit < 0 else self.payload[:limit]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None


class FakeOpener:
    def __init__(self, response=None, error=None) -> None:
        self.response = response
        self.error = error

    def open(self, request, timeout):  # noqa: ANN001
        if self.error:
            raise self.error
        return self.response


class CapturingHttp:
    def __init__(self) -> None:
        self.request_data = None

    def request(self, method, url, **kwargs) -> JsonResponse:  # noqa: ANN001
        self.request_data = (method, url, kwargs)
        return JsonResponse(200, {}, {})


class LocalWriteHttp:
    def __init__(self) -> None:
        self.calls = []

    def request(self, method, url, **kwargs) -> JsonResponse:  # noqa: ANN001
        self.calls.append((method, url, kwargs))
        if "/api/users/0/items" in url:
            return JsonResponse(200, {"zotero-server-id": "server-A"}, {})
        if url.endswith("/api/local/authorize"):
            return JsonResponse(
                200,
                {"zotero-server-id": "server-A"},
                {"key": "A" * 32, "remember": True},
            )
        if method == "POST":
            return JsonResponse(200, {"zotero-server-id": "server-A"}, {"successful": {}})
        return JsonResponse(200, {"zotero-server-id": "server-A"}, {})


class HttpClientTests(unittest.TestCase):
    def test_json_http_client_decodes_json_and_headers(self) -> None:
        client = JsonHttpClient(2, 10_000)
        client._opener = FakeOpener(
            FakeResponse({"ok": True}, headers={"Last-Modified-Version": "9"})
        )
        response = client.request("GET", "http://127.0.0.1/ok")
        self.assertTrue(response.data["ok"])
        self.assertEqual(response.headers["last-modified-version"], "9")

    def test_http_conflict_maps_to_stable_error(self) -> None:
        client = JsonHttpClient(2, 10_000)
        client._opener = FakeOpener(
            error=urllib.error.HTTPError(
                "http://127.0.0.1/conflict",
                412,
                "Precondition Failed",
                {},
                io.BytesIO(b"version mismatch"),
            )
        )
        with self.assertRaises(IntegrationError) as raised:
            client.request("GET", "http://127.0.0.1/conflict")
        self.assertEqual(raised.exception.code, "VERSION_CONFLICT")
        self.assertEqual(raised.exception.details["http_status"], 412)

    def test_redirects_are_not_followed(self) -> None:
        client = JsonHttpClient(2, 10_000)
        client._opener = FakeOpener(
            error=urllib.error.HTTPError(
                "http://127.0.0.1/redirect",
                302,
                "Found",
                {"Location": "/ok"},
                io.BytesIO(b""),
            )
        )
        with self.assertRaises(IntegrationError) as raised:
            client.request("GET", "http://127.0.0.1/redirect")
        self.assertEqual(raised.exception.details["http_status"], 302)

    def test_backend_response_limit_is_enforced(self) -> None:
        client = JsonHttpClient(2, 100)
        client._opener = FakeOpener(FakeResponse({"value": "x" * 2000}))
        with self.assertRaisesRegex(IntegrationError, "byte limit"):
            client.request("GET", "http://127.0.0.1/large")

    def test_web_api_key_is_forwarded_only_as_header(self) -> None:
        capture = CapturingHttp()
        config = ZoteroConfig(web_library_id="123456")
        client = ZoteroApiClient(
            config,
            "web",
            environ={"ZOTERO_API_KEY": "secret-value"},
            http=capture,
        )
        client.get("/items", query={"limit": 1})
        method, url, kwargs = capture.request_data
        self.assertEqual(method, "GET")
        self.assertNotIn("secret-value", url)
        self.assertEqual(kwargs["headers"]["Zotero-API-Key"], "secret-value")
        self.assertEqual(kwargs["headers"]["Zotero-API-Version"], "3")

    def test_local_write_authorizes_with_server_id_and_keeps_key_out_of_url(self) -> None:
        http = LocalWriteHttp()
        client = ZoteroApiClient(ZoteroConfig(), "local", http=http)
        client.post("/items", [{"itemType": "note"}])

        self.assertEqual([call[0] for call in http.calls], ["GET", "POST", "POST"])
        authorize = http.calls[1]
        self.assertTrue(authorize[1].endswith("/api/local/authorize"))
        self.assertEqual(authorize[2]["headers"]["Zotero-Server-ID"], "server-A")
        self.assertEqual(authorize[2]["timeout"], 120.0)
        write = http.calls[2]
        self.assertEqual(write[2]["headers"]["Zotero-API-Key"], "A" * 32)
        self.assertEqual(write[2]["headers"]["Zotero-Server-ID"], "server-A")
        self.assertNotIn("A" * 32, write[1])

    def test_windows_curl_transport_parses_headers_and_body(self) -> None:
        captured = {}

        def runner(command, **kwargs):  # noqa: ANN001
            captured["command"] = command
            captured["kwargs"] = kwargs
            stdout = (
                b"HTTP/1.1 200 OK\r\nTotal-Results: 2\r\n\r\n"
                b'{"items":[]}\n__PAIOS_CURL_STATUS__:200'
            )
            return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr=b"")

        with tempfile.NamedTemporaryFile() as executable:
            client = WindowsCurlJsonHttpClient(
                2,
                10_000,
                runner=runner,
                curl_path=executable.name,
            )
            response = client.request(
                "GET",
                "http://127.0.0.1:23119/api/users/0/items",
                headers={"Zotero-API-Version": "3"},
                query={"limit": 1},
            )
        self.assertEqual(response.data, {"items": []})
        self.assertEqual(response.headers["total-results"], "2")
        self.assertIn("--noproxy", captured["command"])
        self.assertIn("http://127.0.0.1:23119/api/users/0/items?limit=1", captured["command"])
        self.assertEqual(captured["kwargs"]["input"], b"")

    def test_windows_curl_transport_maps_http_errors(self) -> None:
        def runner(command, **kwargs):  # noqa: ANN001
            stdout = (
                b"HTTP/1.0 403 Forbidden\r\nContent-Type: text/plain\r\n\r\n"
                b"Local API is not enabled\n__PAIOS_CURL_STATUS__:403"
            )
            return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr=b"")

        with tempfile.NamedTemporaryFile() as executable:
            client = WindowsCurlJsonHttpClient(
                2,
                10_000,
                runner=runner,
                curl_path=executable.name,
            )
            with self.assertRaises(IntegrationError) as raised:
                client.request("GET", "http://127.0.0.1:23119/api/")
        self.assertEqual(raised.exception.code, "PERMISSION_DENIED")
        self.assertEqual(raised.exception.details["http_status"], 403)


if __name__ == "__main__":
    unittest.main()
