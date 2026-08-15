"""Normalize Zotero-native JSON into the stable AI-OS contract."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from .config import ZoteroConfig
from .errors import IntegrationError


Clock = Callable[[], datetime]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def item_ref(
    config: ZoteroConfig,
    key: str,
    version: int | None,
) -> dict[str, object]:
    ref: dict[str, object] = {
        "id": f"zotero:{config.library_alias}:item:{key}",
        "system": "zotero",
        "kind": "item",
        "library": {
            "alias": config.library_alias,
            "type": config.library_type,
            "id": config.canonical_library_id,
        },
        "key": key,
    }
    if version is not None:
        ref["version"] = version
    return ref


def collection_ref(
    config: ZoteroConfig,
    key: str,
    version: int | None,
) -> dict[str, object]:
    ref: dict[str, object] = {
        "id": f"zotero:{config.library_alias}:collection:{key}",
        "system": "zotero",
        "kind": "collection",
        "library": {
            "alias": config.library_alias,
            "type": config.library_type,
            "id": config.canonical_library_id,
        },
        "key": key,
    }
    if version is not None:
        ref["version"] = version
    return ref


def normalize_item(
    raw: object,
    config: ZoteroConfig,
    backend: str,
    *,
    clock: Clock = utc_now,
) -> dict[str, object]:
    wrapper = _object(raw, "item")
    data = _object(wrapper.get("data"), "item.data")
    meta = wrapper.get("meta") if isinstance(wrapper.get("meta"), dict) else {}
    links = wrapper.get("links") if isinstance(wrapper.get("links"), dict) else {}
    key = _required_string(wrapper.get("key") or data.get("key"), "item key")
    version = _optional_int(wrapper.get("version", data.get("version")))
    item_type = _required_string(data.get("itemType"), "item type")

    normalized: dict[str, object] = {
        "ref": item_ref(config, key, version),
        "item_type": item_type,
        "title": _first_string(data, "title", "caseName", "nameOfAct", "subject"),
        "creators": _normalize_creators(data.get("creators")),
        "date": _optional_string(data.get("date")),
        "parsed_date": _optional_string(meta.get("parsedDate")),
        "abstract": _optional_string(data.get("abstractNote")),
        "publication": _normalize_publication(data),
        "identifiers": _normalize_identifiers(data),
        "url": _optional_string(data.get("url")),
        "language": _optional_string(data.get("language")),
        "pages": _optional_string(data.get("pages")),
        "volume": _optional_string(data.get("volume")),
        "issue": _optional_string(data.get("issue")),
        "tags": _normalize_tags(data.get("tags")),
        "collection_keys": _string_array(data.get("collections")),
        "parent_item_key": _false_or_string(data.get("parentItem")),
        "relations": data.get("relations") if isinstance(data.get("relations"), dict) else {},
        "dates": {
            "added": _optional_string(data.get("dateAdded")),
            "modified": _optional_string(data.get("dateModified")),
            "accessed": _optional_string(data.get("accessDate")),
        },
        "provenance": {
            "backend": backend,
            "retrieved_at": clock().isoformat(),
            "canonical_url": _link_href(links, "alternate"),
        },
    }

    if item_type == "attachment":
        normalized["attachment"] = {
            "link_mode": _optional_string(data.get("linkMode")),
            "content_type": _optional_string(data.get("contentType")),
            "filename": _optional_string(data.get("filename")),
            "path": _optional_string(data.get("path")),
            "charset": _optional_string(data.get("charset")),
        }
    elif item_type == "note":
        normalized["note_html"] = _optional_string(data.get("note"))
    elif item_type == "annotation":
        normalized["annotation"] = {
            "type": _optional_string(data.get("annotationType")),
            "text": _optional_string(data.get("annotationText")),
            "comment": _optional_string(data.get("annotationComment")),
            "color": _optional_string(data.get("annotationColor")),
            "page_label": _optional_string(data.get("annotationPageLabel")),
            "sort_index": _optional_string(data.get("annotationSortIndex")),
            "position": data.get("annotationPosition")
            if isinstance(data.get("annotationPosition"), dict)
            else {},
        }
    return normalized


def normalize_collection(
    raw: object,
    config: ZoteroConfig,
    backend: str,
    *,
    clock: Clock = utc_now,
) -> dict[str, object]:
    wrapper = _object(raw, "collection")
    data = _object(wrapper.get("data"), "collection.data")
    meta = wrapper.get("meta") if isinstance(wrapper.get("meta"), dict) else {}
    links = wrapper.get("links") if isinstance(wrapper.get("links"), dict) else {}
    key = _required_string(wrapper.get("key") or data.get("key"), "collection key")
    version = _optional_int(wrapper.get("version", data.get("version")))
    return {
        "ref": collection_ref(config, key, version),
        "name": _required_string(data.get("name"), "collection name"),
        "parent_collection_key": _false_or_string(data.get("parentCollection")),
        "counts": {
            "items": _optional_int(meta.get("numItems")),
            "collections": _optional_int(meta.get("numCollections")),
        },
        "provenance": {
            "backend": backend,
            "retrieved_at": clock().isoformat(),
            "canonical_url": _link_href(links, "alternate"),
        },
    }


def _normalize_creators(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    creators: list[dict[str, object]] = []
    for entry in value:
        if not isinstance(entry, dict):
            continue
        creator = {
            "creator_type": _optional_string(entry.get("creatorType")),
            "first_name": _optional_string(entry.get("firstName")),
            "last_name": _optional_string(entry.get("lastName")),
            "name": _optional_string(entry.get("name")),
        }
        creators.append(creator)
    return creators


def _normalize_tags(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    tags: list[dict[str, object]] = []
    for entry in value:
        if not isinstance(entry, dict) or not isinstance(entry.get("tag"), str):
            continue
        tags.append(
            {
                "name": entry["tag"],
                "type": entry.get("type") if isinstance(entry.get("type"), int) else 0,
            }
        )
    return tags


def _normalize_identifiers(data: dict[str, Any]) -> dict[str, str]:
    field_map = {
        "doi": "DOI",
        "isbn": "ISBN",
        "issn": "ISSN",
        "pmid": "PMID",
    }
    return {
        normalized: data[native]
        for normalized, native in field_map.items()
        if isinstance(data.get(native), str) and data[native]
    }


def _normalize_publication(data: dict[str, Any]) -> dict[str, str | None]:
    return {
        "title": _first_string(
            data,
            "publicationTitle",
            "bookTitle",
            "proceedingsTitle",
            "encyclopediaTitle",
            "dictionaryTitle",
            "websiteTitle",
            "blogTitle",
            "forumTitle",
            "programTitle",
        ),
        "publisher": _first_string(data, "publisher", "institution", "university"),
        "place": _optional_string(data.get("place")),
        "series": _optional_string(data.get("series")),
    }


def _object(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise IntegrationError(
            "BACKEND_PROTOCOL_ERROR",
            f"Zotero returned an invalid {label} object",
        )
    return value


def _required_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise IntegrationError(
            "BACKEND_PROTOCOL_ERROR",
            f"Zotero response is missing {label}",
        )
    return value


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _first_string(data: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = _optional_string(data.get(key))
        if value:
            return value
    return None


def _optional_int(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _string_array(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [entry for entry in value if isinstance(entry, str)]


def _false_or_string(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _link_href(links: dict[str, Any], name: str) -> str | None:
    link = links.get(name)
    if not isinstance(link, dict):
        return None
    return _optional_string(link.get("href"))
