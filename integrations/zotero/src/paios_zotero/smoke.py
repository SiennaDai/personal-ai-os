"""Privacy-preserving live read smoke checks."""

from __future__ import annotations

from typing import Callable

from .errors import IntegrationError
from .service import ZoteroService


def run_read_smoke(service: ZoteroService) -> dict[str, object]:
    """Exercise representative read paths without returning library content."""

    checks: dict[str, object] = {}
    page_limit = min(10, service.config.max_page_size)
    scan_limit = min(50, service.config.max_page_size)
    status = service.status()
    checks["status"] = {
        "passed": bool(status["read"]["available"]),
        "transport": status["read"].get("transport"),
        "better_bibtex_available": bool(status["better_bibtex"]["available"]),
        "writes_enabled": bool(status["write"]["enabled"]),
    }
    if not status["read"]["available"]:
        return {"overall_ok": False, "checks": checks}

    collection_result, collection_error = _probe(lambda: service.list_collections(limit=1))
    checks["collections"] = _check(collection_result, collection_error)

    top_response, top_error = _probe(
        lambda: service.read_client.get(
            "/items/top",
            query={"limit": page_limit, "sort": "dateModified", "direction": "desc"},
        )
    )
    if top_error:
        checks["top_items"] = _check(None, top_error)
        return {"overall_ok": False, "checks": checks}
    rows = top_response.data if isinstance(top_response.data, list) else None
    if rows is None or any(not isinstance(row, dict) for row in rows):
        error = IntegrationError(
            "BACKEND_PROTOCOL_ERROR",
            "Zotero returned an invalid top-item list during read smoke",
        )
        checks["top_items"] = _check(None, error)
        return {"overall_ok": False, "checks": checks}
    checks["top_items"] = {"passed": True, "library_has_items": bool(rows)}
    if not rows:
        empty_search, empty_search_error = _probe(
            lambda: service.search_items(
                "paios-integration-smoke-no-match-7f3c9b1e",
                limit=1,
            )
        )
        search_check = _check(empty_search, empty_search_error)
        if empty_search:
            search_check["response_shape_valid"] = isinstance(empty_search.get("items"), list)
            search_check["sentinel_query_returned_zero"] = len(empty_search.get("items", [])) == 0
        checks["search"] = search_check
        return {
            "overall_ok": bool(checks["collections"]["passed"] and checks["search"]["passed"]),
            "checks": checks,
            "warnings": ["The configured library is empty; item-level paths were not exercised"],
        }

    candidates = [row for row in rows if _item_type(row) not in {"note", "attachment", "annotation"}]
    primary = candidates[0] if candidates else rows[0]
    primary_key = _item_key(primary)
    primary_title = _item_title(primary)

    exact, exact_error = _probe(lambda: service.get_item(primary_key))
    exact_check = _check(exact, exact_error)
    if exact:
        ref = exact["item"].get("ref", {})
        exact_check["canonical_ref_valid"] = (
            isinstance(ref, dict)
            and ref.get("system") == "zotero"
            and ref.get("key") == primary_key
        )
        exact_check["version_present"] = isinstance(ref, dict) and isinstance(ref.get("version"), int)
    checks["exact_item"] = exact_check

    if primary_title:
        search, search_error = _probe(
            lambda: service.search_items(primary_title[:500], limit=page_limit)
        )
        search_check = _check(search, search_error)
        if search:
            search_check["exact_item_found"] = any(
                item.get("ref", {}).get("key") == primary_key
                for item in search.get("items", [])
                if isinstance(item, dict)
            )
        checks["search"] = search_check
    else:
        checks["search"] = {"passed": True, "not_exercised": "selected item has no title"}

    selected_pdf: tuple[str, str] | None = None
    primary_children = None
    primary_children_error = None
    for candidate in candidates or [primary]:
        candidate_key = _item_key(candidate)
        children, children_error = _probe(
            lambda key=candidate_key: service.get_item_children(key, limit=scan_limit)
        )
        if candidate_key == primary_key:
            primary_children, primary_children_error = children, children_error
        if not children:
            continue
        for child in children.get("items", []):
            if (
                isinstance(child, dict)
                and child.get("item_type") == "attachment"
                and child.get("attachment", {}).get("content_type") == "application/pdf"
            ):
                selected_pdf = (candidate_key, child["ref"]["key"])
                break
        if selected_pdf:
            break
    checks["children"] = _check(primary_children, primary_children_error)

    if selected_pdf:
        _, attachment_key = selected_pdf
        annotations, annotation_error = _probe(
            lambda: service.get_annotations(attachment_key, limit=1)
        )
        checks["annotations"] = _check(annotations, annotation_error)
        fulltext, fulltext_error = _probe(
            lambda: service.get_fulltext(attachment_key, offset=0, max_chars=64)
        )
        fulltext_check = _check(fulltext, fulltext_error)
        if fulltext:
            fulltext_check["bounded_slice_returned"] = fulltext.get("returned_chars", 0) <= 64
            fulltext_check["page_state_present"] = "indexed_pages" in fulltext and "total_pages" in fulltext
        checks["fulltext"] = fulltext_check
    else:
        checks["annotations"] = {"passed": True, "not_exercised": "no PDF in bounded sample"}
        checks["fulltext"] = {"passed": True, "not_exercised": "no PDF in bounded sample"}

    if service.config.better_bibtex_enabled:
        citekey, citekey_error = _probe(lambda: service.get_citation_key(primary_key))
        citekey_check = _check(citekey, citekey_error)
        if citekey:
            citekey_check["nonempty_key_returned"] = bool(citekey.get("citation_key"))
        checks["citation_key"] = citekey_check
    else:
        checks["citation_key"] = {"passed": True, "not_exercised": "Better BibTeX disabled"}

    required = ["status", "collections", "top_items", "exact_item", "search", "children"]
    overall_ok = all(bool(checks[name].get("passed")) for name in required)
    return {"overall_ok": overall_ok, "checks": checks}


def _probe(call: Callable[[], object]) -> tuple[object | None, IntegrationError | None]:
    try:
        return call(), None
    except IntegrationError as exc:
        return None, exc


def _check(result: object | None, error: IntegrationError | None) -> dict[str, object]:
    if error:
        return {
            "passed": False,
            "error_code": error.code,
            "retryable": error.retryable,
        }
    return {"passed": result is not None}


def _item_data(row: dict[str, object]) -> dict[str, object]:
    data = row.get("data")
    if not isinstance(data, dict):
        raise IntegrationError(
            "BACKEND_PROTOCOL_ERROR",
            "Zotero top item does not contain editable data",
        )
    return data


def _item_key(row: dict[str, object]) -> str:
    data = _item_data(row)
    key = row.get("key") or data.get("key")
    if not isinstance(key, str):
        raise IntegrationError("BACKEND_PROTOCOL_ERROR", "Zotero top item has no key")
    return key


def _item_type(row: dict[str, object]) -> str | None:
    value = _item_data(row).get("itemType")
    return value if isinstance(value, str) else None


def _item_title(row: dict[str, object]) -> str | None:
    value = _item_data(row).get("title")
    return value if isinstance(value, str) and value else None
