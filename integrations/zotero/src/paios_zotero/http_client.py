"""Small, dependency-free HTTP clients for Zotero API v3 and Better BibTeX."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Mapping

from .config import ZoteroConfig
from .errors import IntegrationError


@dataclass(frozen=True)
class JsonResponse:
    status: int
    headers: dict[str, str]
    data: Any


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001, ANN201
        return None


class JsonHttpClient:
    """Issue bounded JSON requests without following redirects."""

    def __init__(self, timeout: float, max_response_bytes: int) -> None:
        self.timeout = timeout
        self.max_response_bytes = max_response_bytes
        self.transport_name = "direct"
        self._opener = urllib.request.build_opener(_NoRedirect())

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        query: Mapping[str, object] | None = None,
        json_body: object | None = None,
    ) -> JsonResponse:
        if query:
            encoded = urllib.parse.urlencode(
                [(key, item) for key, value in query.items() for item in _query_values(value)],
                doseq=False,
            )
            url = f"{url}?{encoded}"
        request_headers = dict(headers or {})
        body = None
        if json_body is not None:
            body = json.dumps(json_body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            request_headers.setdefault("Content-Type", "application/json")
        request = urllib.request.Request(url, data=body, headers=request_headers, method=method)
        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                payload = self._bounded_read(response)
                return JsonResponse(
                    status=response.status,
                    headers={key.lower(): value for key, value in response.headers.items()},
                    data=_decode_json(payload, response.status),
                )
        except urllib.error.HTTPError as exc:
            payload = _bounded_error_read(exc, min(self.max_response_bytes, 4096))
            raise _http_error(exc.code, payload, exc.headers) from exc
        except (urllib.error.URLError, TimeoutError, socket.timeout, ConnectionError, OSError) as exc:
            reason = getattr(exc, "reason", exc)
            raise IntegrationError(
                "BACKEND_UNAVAILABLE",
                f"Cannot reach the configured Zotero backend: {reason}",
                retryable=True,
            ) from exc

    def _bounded_read(self, response) -> bytes:  # noqa: ANN001
        payload = response.read(self.max_response_bytes + 1)
        if len(payload) > self.max_response_bytes:
            raise IntegrationError(
                "RESPONSE_TOO_LARGE",
                "The Zotero backend response exceeds the configured byte limit",
                details={"max_bytes": self.max_response_bytes},
            )
        return payload


class WindowsCurlJsonHttpClient:
    """Reach a Windows-loopback service from WSL without exposing its port."""

    CURL_PATH = "/mnt/c/Windows/System32/curl.exe"
    STATUS_MARKER = b"\n__PAIOS_CURL_STATUS__:"

    def __init__(
        self,
        timeout: float,
        max_response_bytes: int,
        *,
        runner=subprocess.run,
        curl_path: str = CURL_PATH,
    ) -> None:
        if not os.path.isfile(curl_path):
            raise IntegrationError(
                "CONFIG_INVALID",
                f"Windows curl transport is unavailable at {curl_path}",
            )
        self.timeout = timeout
        self.max_response_bytes = max_response_bytes
        self.transport_name = "windows-curl"
        self.runner = runner
        self.curl_path = curl_path

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        query: Mapping[str, object] | None = None,
        json_body: object | None = None,
    ) -> JsonResponse:
        if query:
            encoded = urllib.parse.urlencode(
                [(key, item) for key, value in query.items() for item in _query_values(value)],
                doseq=False,
            )
            url = f"{url}?{encoded}"
        body = b""
        command = [
            self.curl_path,
            "--silent",
            "--show-error",
            "--noproxy",
            "*",
            "--proto",
            "=http",
            "--max-redirs",
            "0",
            "--max-time",
            str(self.timeout),
            "--max-filesize",
            str(self.max_response_bytes),
            "--request",
            method,
            "--dump-header",
            "-",
            "--write-out",
            "\n__PAIOS_CURL_STATUS__:%{http_code}",
        ]
        request_headers = dict(headers or {})
        if json_body is not None:
            body = json.dumps(json_body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            request_headers.setdefault("Content-Type", "application/json")
            command.extend(["--data-binary", "@-"])
        for key, value in request_headers.items():
            if "\r" in key or "\n" in key or "\r" in value or "\n" in value:
                raise IntegrationError(
                    "INVALID_ARGUMENT",
                    "HTTP header names and values cannot contain newlines",
                )
            command.extend(["--header", f"{key}: {value}"])
        command.append(url)
        try:
            completed = self.runner(
                command,
                input=body,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=self.timeout + 5,
            )
        except (subprocess.TimeoutExpired, OSError) as exc:
            raise IntegrationError(
                "BACKEND_UNAVAILABLE",
                f"Cannot run the Windows-loopback Zotero transport: {exc}",
                retryable=True,
            ) from exc
        if completed.returncode != 0:
            if completed.returncode == 63:
                raise IntegrationError(
                    "RESPONSE_TOO_LARGE",
                    "The Zotero backend response exceeds the configured byte limit",
                    details={"max_bytes": self.max_response_bytes},
                )
            message = completed.stderr.decode("utf-8", errors="replace").strip()[:500]
            raise IntegrationError(
                "BACKEND_UNAVAILABLE",
                f"Windows-loopback Zotero transport failed: {message or 'curl error'}",
                retryable=True,
                details={"transport_exit_code": completed.returncode},
            )
        response = _parse_curl_response(completed.stdout, self.STATUS_MARKER)
        if len(response[2]) > self.max_response_bytes:
            raise IntegrationError(
                "RESPONSE_TOO_LARGE",
                "The Zotero backend response exceeds the configured byte limit",
                details={"max_bytes": self.max_response_bytes},
            )
        status, response_headers, payload = response
        if status >= 400:
            raise _http_error(status, payload[:4096], response_headers)
        return JsonResponse(status, response_headers, _decode_json(payload, status))


def make_local_http_client(config: ZoteroConfig):  # noqa: ANN201
    transport = config.local_transport
    if transport == "auto":
        transport = "windows" if os.path.isfile(WindowsCurlJsonHttpClient.CURL_PATH) else "direct"
    if transport == "windows":
        return WindowsCurlJsonHttpClient(
            config.request_timeout_seconds,
            config.max_backend_response_bytes,
        )
    return JsonHttpClient(config.request_timeout_seconds, config.max_backend_response_bytes)


class ZoteroApiClient:
    """Backend-specific Zotero API v3 access."""

    def __init__(
        self,
        config: ZoteroConfig,
        backend: str,
        *,
        environ: Mapping[str, str] | None = None,
        http: JsonHttpClient | None = None,
    ) -> None:
        if backend not in {"local", "web"}:
            raise ValueError(f"Unsupported Zotero backend: {backend}")
        self.config = config
        self.backend = backend
        self.environ = environ
        self.http = http or (
            make_local_http_client(config)
            if backend == "local"
            else JsonHttpClient(config.request_timeout_seconds, config.max_backend_response_bytes)
        )
        self.transport_name = getattr(self.http, "transport_name", "injected")
        self.base_url = config.local_api_url if backend == "local" else config.web_api_url
        library_id = config.local_library_id if backend == "local" else config.web_library_id
        prefix = "users" if config.library_type == "user" else "groups"
        self.library_path = f"/{prefix}/{library_id}"

    def get(self, path: str, *, query: Mapping[str, object] | None = None) -> JsonResponse:
        return self._request("GET", path, query=query)

    def post(
        self,
        path: str,
        body: object,
        *,
        headers: Mapping[str, str] | None = None,
    ) -> JsonResponse:
        return self._request("POST", path, body=body, extra_headers=headers)

    def patch(
        self,
        path: str,
        body: object,
        *,
        headers: Mapping[str, str] | None = None,
    ) -> JsonResponse:
        return self._request("PATCH", path, body=body, extra_headers=headers)

    def _request(
        self,
        method: str,
        path: str,
        *,
        query: Mapping[str, object] | None = None,
        body: object | None = None,
        extra_headers: Mapping[str, str] | None = None,
    ) -> JsonResponse:
        if not path.startswith("/") or ".." in path:
            raise ValueError("Zotero API paths must be absolute and cannot contain '..'")
        headers = {
            "Accept": "application/json",
            "User-Agent": "personal-ai-os-zotero/1.0",
            "Zotero-API-Version": "3",
        }
        api_key = self.config.api_key(self.environ)
        if self.backend == "web" and api_key:
            headers["Zotero-API-Key"] = api_key
        if extra_headers:
            headers.update(extra_headers)
        return self.http.request(
            method,
            f"{self.base_url}{self.library_path}{path}",
            headers=headers,
            query=query,
            json_body=body,
        )


class BetterBibtexClient:
    """Narrow read-only Better BibTeX JSON-RPC client."""

    def __init__(self, config: ZoteroConfig, http: JsonHttpClient | None = None) -> None:
        self.config = config
        self.http = http or make_local_http_client(config)
        self.transport_name = getattr(self.http, "transport_name", "injected")
        self._request_id = 0

    def ready(self) -> dict[str, object]:
        result = self.call("api.ready", [])
        if not isinstance(result, dict):
            raise IntegrationError(
                "BACKEND_PROTOCOL_ERROR",
                "Better BibTeX api.ready returned an unexpected result",
            )
        return result

    def citation_keys(self, item_keys: list[str]) -> dict[str, str]:
        result = self.call("item.citationkey", [item_keys])
        if not isinstance(result, dict) or any(
            not isinstance(key, str) or not isinstance(value, str)
            for key, value in result.items()
        ):
            raise IntegrationError(
                "BACKEND_PROTOCOL_ERROR",
                "Better BibTeX item.citationkey returned an unexpected result",
            )
        return result

    def call(self, method: str, params: list[object]) -> object:
        self._request_id += 1
        response = self.http.request(
            "POST",
            self.config.better_bibtex_url,
            headers={"Accept": "application/json"},
            json_body={
                "jsonrpc": "2.0",
                "id": self._request_id,
                "method": method,
                "params": params,
            },
        )
        if not isinstance(response.data, dict):
            raise IntegrationError(
                "BACKEND_PROTOCOL_ERROR",
                "Better BibTeX returned a non-object JSON-RPC response",
            )
        if "error" in response.data:
            error = response.data.get("error")
            message = error.get("message") if isinstance(error, dict) else str(error)
            raise IntegrationError("OPTIONAL_BACKEND_ERROR", f"Better BibTeX error: {message}")
        if "result" not in response.data:
            raise IntegrationError(
                "BACKEND_PROTOCOL_ERROR",
                "Better BibTeX response does not contain a result",
            )
        return response.data["result"]


def _query_values(value: object) -> list[object]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    if isinstance(value, bool):
        return ["true" if value else "false"]
    return [value]


def _decode_json(payload: bytes, status: int) -> object:
    if not payload:
        return None
    try:
        return json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IntegrationError(
            "BACKEND_PROTOCOL_ERROR",
            f"Zotero backend returned invalid JSON with HTTP {status}",
        ) from exc


def _parse_curl_response(
    output: bytes,
    marker: bytes,
) -> tuple[int, dict[str, str], bytes]:
    marker_index = output.rfind(marker)
    if marker_index < 0:
        raise IntegrationError(
            "BACKEND_PROTOCOL_ERROR",
            "Windows-loopback transport did not return an HTTP status marker",
        )
    try:
        status = int(output[marker_index + len(marker) :].strip())
    except ValueError as exc:
        raise IntegrationError(
            "BACKEND_PROTOCOL_ERROR",
            "Windows-loopback transport returned an invalid HTTP status",
        ) from exc
    wire = output[:marker_index]
    while True:
        if not wire.startswith(b"HTTP/"):
            raise IntegrationError(
                "BACKEND_PROTOCOL_ERROR",
                "Windows-loopback transport did not return HTTP headers",
            )
        separator = b"\r\n\r\n" if b"\r\n\r\n" in wire else b"\n\n"
        boundary = wire.find(separator)
        if boundary < 0:
            raise IntegrationError(
                "BACKEND_PROTOCOL_ERROR",
                "Windows-loopback transport returned malformed HTTP headers",
            )
        header_block = wire[:boundary].decode("iso-8859-1")
        payload = wire[boundary + len(separator) :]
        first_line = header_block.splitlines()[0].split()
        block_status = int(first_line[1]) if len(first_line) >= 2 and first_line[1].isdigit() else 0
        if 100 <= block_status < 200 and payload.startswith(b"HTTP/"):
            wire = payload
            continue
        headers: dict[str, str] = {}
        for line in header_block.splitlines()[1:]:
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            headers[key.strip().lower()] = value.strip()
        return status, headers, payload


def _bounded_error_read(exc: urllib.error.HTTPError, limit: int) -> bytes:
    try:
        return exc.read(limit)
    except OSError:
        return b""


def _http_error(status: int, payload: bytes, headers) -> IntegrationError:  # noqa: ANN001
    mapping: dict[int, tuple[str, str, bool]] = {
        400: ("INVALID_REQUEST", "Zotero rejected the request", False),
        401: ("AUTHENTICATION_REQUIRED", "Zotero authentication failed", False),
        403: ("PERMISSION_DENIED", "Zotero denied the request", False),
        404: ("NOT_FOUND", "The requested Zotero object was not found", False),
        409: ("BACKEND_CONFLICT", "The Zotero library is locked or in conflict", True),
        412: ("VERSION_CONFLICT", "The Zotero object changed or the write token was reused", False),
        413: ("LIMIT_EXCEEDED", "Zotero rejected an oversized request", False),
        429: ("RATE_LIMITED", "Zotero rate-limited the request", True),
        501: ("UNSUPPORTED_CAPABILITY", "The configured Zotero backend does not support this request", False),
    }
    code, message, retryable = mapping.get(
        status,
        (
            "BACKEND_UNAVAILABLE" if status >= 500 else "BACKEND_PROTOCOL_ERROR",
            f"Zotero returned HTTP {status}",
            status >= 500,
        ),
    )
    details: dict[str, object] = {"http_status": status}
    retry_after = (headers.get("Retry-After") or headers.get("retry-after")) if headers else None
    if retry_after:
        details["retry_after"] = retry_after
    body = payload.decode("utf-8", errors="replace").strip()
    if body:
        details["backend_message"] = body[:500]
    return IntegrationError(code, message, retryable=retryable, details=details)
