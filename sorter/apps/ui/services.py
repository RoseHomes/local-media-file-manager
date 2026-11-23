from __future__ import annotations

import json
from copy import deepcopy
from typing import Any


DEFAULT_MENU_CONFIG = [
    {"id": "fanart_filemanage", "items": ["fanart_file", "fanart_album"]},
    {
        "id": "setting_fanart_filemanage",
        "items": ["fanart_setting", "games_setting", "character_setting", "album_setting"],
    },
    {
        "id": "filemanage",
        "items": [
            "filemanage:rename-files",
            "filemanage:change-file-extension",
            "filemanage:extract-zip",
            "filemanage:images-to-pdf",
            "filemanage:pdf-to-images",
            "filemanage:webp-to-mp4",
        ],
    },
]


class InvalidMenuConfig(ValueError):
    pass


def _clone_default_menu_config() -> list[dict[str, list[str]]]:
    return deepcopy(DEFAULT_MENU_CONFIG)


def parse_menu_config(value: Any) -> list[dict[str, list[str]]]:
    if value in (None, "", []):
        return _clone_default_menu_config()

    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as exc:
            raise InvalidMenuConfig("invalid_json") from exc

    if not isinstance(value, list):
        raise InvalidMenuConfig("invalid_shape")

    expected_groups = {group["id"]: tuple(group["items"]) for group in DEFAULT_MENU_CONFIG}
    normalized: list[dict[str, list[str]]] = []
    seen_groups: set[str] = set()

    for entry in value:
        if not isinstance(entry, dict):
            raise InvalidMenuConfig("invalid_shape")

        group_id = entry.get("id")
        items = entry.get("items")

        if not isinstance(group_id, str) or group_id not in expected_groups:
            raise InvalidMenuConfig("unknown_group")
        if group_id in seen_groups:
            raise InvalidMenuConfig("duplicate_group")
        if not isinstance(items, list) or not all(isinstance(item, str) for item in items):
            raise InvalidMenuConfig("invalid_items")
        if len(items) != len(set(items)):
            raise InvalidMenuConfig("duplicate_item")

        expected_items = expected_groups[group_id]
        if tuple(sorted(items)) != tuple(sorted(expected_items)):
            raise InvalidMenuConfig("invalid_items")

        normalized.append({"id": group_id, "items": items})
        seen_groups.add(group_id)

    if seen_groups != set(expected_groups):
        raise InvalidMenuConfig("missing_group")

    return normalized


def get_safe_menu_config(value: Any) -> list[dict[str, list[str]]]:
    try:
        return parse_menu_config(value)
    except InvalidMenuConfig:
        return _clone_default_menu_config()
