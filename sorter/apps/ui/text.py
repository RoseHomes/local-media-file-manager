from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from sorter.apps.ui.services import DEFAULT_MENU_CONFIG, get_safe_menu_config

DEFAULT_LANGUAGE_MODE = "en"
DEFAULT_THEME_NAME = "mystic-violet"

MENU_KEY_ALIASES = {
    "fanart_file": "fanart_file",
    "fanart_album": "fanart_album",
    "fanart_setting": "fanart_setting",
    "games_setting": "games_setting",
    "character_setting": "character_setting",
    "album_setting": "album_setting",
    "interface_text_setting": "interface_text_setting",
    "filemanage:rename-files": "filemanage_rename_files",
    "filemanage:change-file-extension": "filemanage_change_file_extension",
    "filemanage:extract-zip": "filemanage_extract_zip",
    "filemanage:images-to-pdf": "filemanage_images_to_pdf",
    "filemanage:pdf-to-images": "filemanage_pdf_to_images",
    "filemanage:webp-to-mp4": "filemanage_webp_to_mp4",
}

GROUP_KEYS = (
    "fanart_filemanage",
    "setting_fanart_filemanage",
    "filemanage",
)
SORT_KEYS = ("date_desc", "date_asc", "name_asc", "name_desc")
LANGUAGE_MODE_KEYS = ("en", "th", "mixed")
THEME_KEYS = ("cocoa-brown", "mystic-violet", "cotton-candy-cloud", "lunar-cloud", "electric-violet")
BUTTON_KEYS = ("open_admin", "interface_text_settings")

MENU_ITEM_METADATA = {
    "fanart_file": {"url": "workspace", "icon": "workspace"},
    "fanart_album": {"url": "fanart_album", "icon": "album"},
    "fanart_setting": {"url": "fanart_setting", "icon": "fanart-setting"},
    "games_setting": {"url": "games_setting", "icon": "games"},
    "character_setting": {"url": "character_setting", "icon": "character"},
    "album_setting": {"url": "album_setting", "icon": "album-setting"},
    "filemanage:rename-files": {"url": "filemanage_rename_files", "icon": "rename"},
    "filemanage:change-file-extension": {"url": "filemanage_change_file_extension", "icon": "extension"},
    "filemanage:extract-zip": {"url": "filemanage_extract_zip", "icon": "zip"},
    "filemanage:images-to-pdf": {"url": "filemanage_images_to_pdf", "icon": "img-pdf"},
    "filemanage:pdf-to-images": {"url": "filemanage_pdf_to_images", "icon": "pdf-img"},
    "filemanage:webp-to-mp4": {"url": "filemanage_webp_to_mp4", "icon": "webp-mp4"},
}


PRIMARY_PAGE_UI_KEYS = {
    "select_game_first",
}

SUPPORTING_PAGE_UI_KEYS = {
    "reference_appears_here",
    "pick_from_list",
    "select_character_for_preview",
    "select_game_before_character",
    "folder_name_character_not_required",
    "folder_name_no_reference_needed",
    "folder_name_optional",
    "add_characters_in_admin",
    "queue_remove_failed",
    "help_text",
    "run_disabled_title",
    "starting_job",
    "waiting_first_file",
    "preview_capped_middle",
    "preview_capped_end",
    "delete_confirm_copy",
}

SUPPORTING_PAGE_UI_SUFFIXES = (
    "_intro",
    "_placeholder",
    "_empty",
    "_prefix",
    "_suffix",
    "_description",
    "_singular",
    "_plural",
)

SUPPORTING_PAGE_UI_COLLECTION_KEYS = {
    "messages",
    "error_messages",
    "steps",
    "workflow_steps",
}

SUPPORTING_PAGE_UI_ITEM_KEYS = {
    "body",
}

PAGE_UI_THAI_ONLY_PREFIXES = (
    "no_",
    "empty_",
)


def _is_list_index(part: str) -> bool:
    return part.isdigit()


def _last_named_key(path: tuple[str, ...]) -> str:
    for part in reversed(path):
        if not _is_list_index(part):
            return part
    return ""


def _locale_data_paths(locale: str) -> list[Path]:
    data_root = Path(__file__).resolve().parents[2] / "ui_text_data"
    locale_dir = data_root / locale
    if locale_dir.is_dir():
        return sorted(locale_dir.rglob("*.json"))
    return [data_root / f"{locale}.json"]


@lru_cache(maxsize=2)
def _locale_revision(locale: str) -> int:
    return max((path.stat().st_mtime_ns for path in _locale_data_paths(locale)), default=0)


@lru_cache(maxsize=8)
def _load_locale(locale: str, revision: int) -> dict:
    del revision
    merged: dict[str, Any] = {}
    paths = _locale_data_paths(locale)
    if len(paths) == 1 and paths[0].name == f"{locale}.json":
        return json.loads(paths[0].read_text(encoding="utf-8-sig"))
    for data_path in paths:
        payload = json.loads(data_path.read_text(encoding="utf-8-sig"))
        merged = _deep_merge(merged, payload)
    return merged


def _deep_merge(base: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in extra.items():
        current = merged.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            merged[key] = _deep_merge(current, value)
        else:
            merged[key] = value
    return merged


@lru_cache(maxsize=8)
def _catalogs(en_revision: int, th_revision: int) -> tuple[dict, dict]:
    return _load_locale("en", en_revision), _load_locale("th", th_revision)


def _current_catalogs() -> tuple[dict, dict]:
    return _catalogs(_locale_revision("en"), _locale_revision("th"))


def _safe_mode() -> str:
    try:
        from .models import InterfaceTextSetting
        mode = InterfaceTextSetting.load().language_mode
    except Exception:
        return DEFAULT_LANGUAGE_MODE
    return mode if mode in {"en", "th", "mixed"} else DEFAULT_LANGUAGE_MODE


def _locale_for(mode: str, *, description: bool = False) -> str:
    if mode == "th":
        return "th"
    if mode == "mixed":
        return "th" if description else "en"
    return "en"


def _get_value(section: str, key: str, locale: str, fallback=None):
    en_catalog, th_catalog = _current_catalogs()
    catalog = en_catalog if locale == "en" else th_catalog
    if section == "brand_title":
        return catalog.get("brand_title", fallback if fallback is not None else key)
    value = catalog.get(section, {}).get(key)
    if value is None:
        fallback_catalog = en_catalog if locale != "en" else th_catalog
        value = fallback_catalog.get(section, {}).get(key, fallback if fallback is not None else key)
    return value


def _get_page_value(page_key: str, field: str, locale: str, fallback: str = "") -> str:
    en_catalog, th_catalog = _current_catalogs()
    catalog = en_catalog if locale == "en" else th_catalog
    page = catalog.get("pages", {}).get(page_key, {})
    if field in page:
        return page[field]
    fallback_catalog = en_catalog if locale != "en" else th_catalog
    return fallback_catalog.get("pages", {}).get(page_key, {}).get(field, fallback)


def _should_use_thai_for_page_ui(path: tuple[str, ...]) -> bool:
    named_path = tuple(part for part in path if not _is_list_index(part))
    current_key = named_path[-1] if named_path else ""

    if current_key in PRIMARY_PAGE_UI_KEYS:
        return False
    if any(part in SUPPORTING_PAGE_UI_COLLECTION_KEYS for part in named_path):
        return True
    if current_key in SUPPORTING_PAGE_UI_ITEM_KEYS:
        return True
    if current_key in SUPPORTING_PAGE_UI_KEYS:
        return True
    if current_key.startswith(PAGE_UI_THAI_ONLY_PREFIXES):
        return True
    if current_key.endswith(SUPPORTING_PAGE_UI_SUFFIXES):
        return True
    return False


def _merge_mixed_page_ui(en_value: Any, th_value: Any, path: tuple[str, ...] = ()) -> Any:
    if en_value is None:
        return th_value
    if th_value is None:
        return en_value

    if isinstance(en_value, dict) and isinstance(th_value, dict):
        merged: dict[str, Any] = {}
        for key in en_value.keys() | th_value.keys():
            merged[key] = _merge_mixed_page_ui(en_value.get(key), th_value.get(key), path + (key,))
        return merged

    if isinstance(en_value, list) and isinstance(th_value, list):
        current_key = _last_named_key(path)
        if current_key in SUPPORTING_PAGE_UI_COLLECTION_KEYS:
            return th_value

        if current_key in {"display_modes", "themes", "rename_cards"}:
            merged_items: list[Any] = []
            max_len = max(len(en_value), len(th_value))
            for index in range(max_len):
                en_item = en_value[index] if index < len(en_value) else None
                th_item = th_value[index] if index < len(th_value) else None
                merged_items.append(_merge_mixed_page_ui(en_item, th_item, path + (str(index),)))
            return merged_items

        return en_value

    if _should_use_thai_for_page_ui(path):
        return th_value
    return en_value


def get_current_language_mode() -> str:
    return _safe_mode()


def get_current_theme_name() -> str:
    try:
        from .models import InterfaceTextSetting
        theme_name = InterfaceTextSetting.load().theme_name
    except Exception:
        return DEFAULT_THEME_NAME
    if theme_name == "warm-sand":
        return DEFAULT_THEME_NAME
    return theme_name if theme_name in THEME_KEYS else DEFAULT_THEME_NAME


def get_brand_title(mode: str | None = None) -> str:
    mode = mode or _safe_mode()
    return _get_value("brand_title", "brand_title", _locale_for(mode), fallback="Local Media File Manager")


def get_group_label(key: str, mode: str | None = None) -> str:
    mode = mode or _safe_mode()
    return _get_value("groups", key, _locale_for(mode), fallback=key)


def get_button_text(key: str, mode: str | None = None) -> str:
    mode = mode or _safe_mode()
    return _get_value("buttons", key, _locale_for(mode), fallback=key)


def get_shared_js_text(key: str, mode: str | None = None, *, description: bool = False, fallback: str | None = None) -> str:
    mode = mode or _safe_mode()
    return _get_value("shared_js", key, _locale_for(mode, description=description), fallback=fallback or key)


def get_sort_label(key: str, mode: str | None = None) -> str:
    mode = mode or _safe_mode()
    return _get_value("sorts", key, _locale_for(mode, description=True), fallback=key)


def get_sort_choices(mode: str | None = None) -> list[tuple[str, str]]:
    mode = mode or _safe_mode()
    return [(key, get_sort_label(key, mode)) for key in SORT_KEYS]


def get_language_mode_label(key: str, mode: str | None = None) -> str:
    mode = mode or _safe_mode()
    return _get_value("language_modes", key, _locale_for(mode, description=True), fallback=key)


def get_language_mode_choices(mode: str | None = None) -> list[tuple[str, str]]:
    mode = mode or _safe_mode()
    return [(key, get_language_mode_label(key, mode)) for key in LANGUAGE_MODE_KEYS]


def get_theme_label(key: str, mode: str | None = None) -> str:
    mode = mode or _safe_mode()
    return _get_value("themes", key, _locale_for(mode, description=True), fallback=key)


def get_theme_choices(mode: str | None = None) -> list[tuple[str, str]]:
    mode = mode or _safe_mode()
    return [(key, get_theme_label(key, mode)) for key in THEME_KEYS]


def get_page_text(key: str, mode: str | None = None) -> dict[str, str]:
    mode = mode or _safe_mode()
    title_locale = _locale_for(mode)
    intro_locale = _locale_for(mode, description=True)
    return {
        "kicker": _get_page_value(key, "kicker", title_locale, fallback=key),
        "title": _get_page_value(key, "title", title_locale, fallback=key),
        "intro": _get_page_value(key, "intro", intro_locale, fallback=""),
    }


def get_filemanage_run_button_label(slug: str, mode: str | None = None, fallback: str | None = None) -> str:
    mode = mode or _safe_mode()
    return _get_value("filemanage_run_buttons", slug, _locale_for(mode), fallback=fallback or slug)


def get_filemanage_setting_helper(slug: str, mode: str | None = None) -> dict[str, object]:
    mode = mode or _safe_mode()
    title_locale = _locale_for(mode)
    description_locale = _locale_for(mode, description=True)

    title_data = _get_value("filemanage_setting_helpers", slug, title_locale, fallback={})
    title = title_data.get("title") if isinstance(title_data, dict) else None
    if title is None:
        fallback_title_data = _get_value("filemanage_setting_helpers", slug, "en", fallback={})
        title = fallback_title_data.get("title", slug) if isinstance(fallback_title_data, dict) else slug

    helper_data = _get_value("filemanage_setting_helpers", slug, description_locale, fallback={})
    lines = helper_data.get("lines") if isinstance(helper_data, dict) else None
    if lines is None:
        fallback_helper = _get_value("filemanage_setting_helpers", slug, "en", fallback={})
        lines = fallback_helper.get("lines", []) if isinstance(fallback_helper, dict) else []

    return {"title": title, "lines": lines}


def get_page_ui_text(key: str, mode: str | None = None, fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    mode = mode or _safe_mode()
    fallback = dict(fallback or {})
    if mode == "mixed":
        en_text = _get_value("page_ui", key, "en", fallback=fallback)
        th_text = _get_value("page_ui", key, "th", fallback=fallback)
        if isinstance(en_text, dict) and isinstance(th_text, dict):
            return _merge_mixed_page_ui(en_text, th_text)
        if isinstance(en_text, dict):
            return en_text
        if isinstance(th_text, dict):
            return th_text
        return fallback

    text = _get_value("page_ui", key, _locale_for(mode), fallback=fallback)
    if isinstance(text, dict):
        return text
    return fallback


def build_ui_bundle() -> dict[str, object]:
    try:
        from .models import InterfaceTextSetting
        settings = InterfaceTextSetting.load()
        mode = settings.language_mode
        theme_name = settings.theme_name
        menu_config = get_safe_menu_config(settings.menu_config)
    except Exception:
        mode = DEFAULT_LANGUAGE_MODE
        theme_name = DEFAULT_THEME_NAME
        menu_config = DEFAULT_MENU_CONFIG

    menu_labels = {}
    for page_key, alias in MENU_KEY_ALIASES.items():
        menu_labels[alias] = get_page_text(page_key, mode)["title"]

    prepared_menu = []
    for group in menu_config:
        group_id = group["id"]
        group_label = get_group_label(group_id, mode)

        items = []
        for item_id in group["items"]:
            metadata = MENU_ITEM_METADATA.get(item_id, {})
            items.append({
                "id": item_id,
                "label": menu_labels.get(MENU_KEY_ALIASES.get(item_id, item_id), item_id),
                "url_name": metadata.get("url"),
                "icon": metadata.get("icon"),
            })

        prepared_menu.append({
            "id": group_id,
            "label": group_label,
            "items": items
        })

    return {
        "language_mode": mode,
        "theme_name": theme_name,
        "brand_title": get_brand_title(mode),
        "groups": {key: get_group_label(key, mode) for key in GROUP_KEYS},
        "menu": menu_labels,
        "menu_config": prepared_menu,
        "buttons": {key: get_button_text(key, mode) for key in BUTTON_KEYS},
        "shared_js": {
            "search_placeholder": get_shared_js_text("search_placeholder", mode, description=True),
            "empty_label": get_shared_js_text("empty_label", mode, description=True),
            "select_label": get_shared_js_text("select_label", mode),
            "clear_selection": get_shared_js_text("clear_selection", mode),
            "close_notification": get_shared_js_text("close_notification", mode),
        },
    }

