from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.contrib import messages
from django.db import IntegrityError
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET

from sorter.apps.catalog.forms import CharacterImportSettingForm, CharacterManualEntryForm, GameImportSettingForm, GameManualEntryForm
from sorter.apps.catalog.models import Character, Game
from sorter.apps.catalog.services import (
    find_matching_root_game,
    import_character_candidates,
    import_game_candidates,
    inline_preview_data_url,
    normalize_character_import_rows,
    normalize_game_import_rows,
    scan_character_import_candidates,
    scan_game_import_candidates,
)
from sorter.apps.ui.text import get_page_text, get_page_ui_text


GAME_STATUS_KEYS = {
    "Existing": "Existing",
    "New": "New",
    "Missing title": "Missing title",
    "Missing parent": "Missing parent",
}

CHARACTER_STATUS_KEYS = {
    "Game not found": "Game not found",
    "No image": "No image",
    "Update": "Update",
    "New": "New",
}


def localize_game_preview_payload(payload: dict[str, object] | None, games_text: dict[str, object]) -> dict[str, object] | None:
    if not payload:
        return payload

    localized = dict(payload)
    statuses = games_text.get("statuses", {}) if isinstance(games_text, dict) else {}
    rows = []
    for row in payload.get("rows") or []:
        localized_row = dict(row)
        status_code = str(localized_row.get("status", "")).strip()
        localized_row["status_code"] = status_code
        localized_row["status_label"] = statuses.get(status_code, status_code)
        rows.append(localized_row)
    localized["rows"] = rows
    if localized.get("root_path") == "Manual entry":
        localized["root_path"] = games_text.get("manual_entry_root", localized["root_path"])
    return localized


def localize_character_preview_payload(payload: dict[str, object] | None, character_text: dict[str, object]) -> dict[str, object] | None:
    if not payload:
        return payload

    localized = dict(payload)
    statuses = character_text.get("statuses", {}) if isinstance(character_text, dict) else {}
    rows = []
    for row in payload.get("rows") or []:
        localized_row = dict(row)
        status_code = str(localized_row.get("status", "")).strip()
        localized_row["status_code"] = status_code
        localized_row["status_label"] = statuses.get(status_code, status_code)
        if localized_row.get("source_dir") == "Manual upload":
            localized_row["source_dir"] = character_text.get("manual_upload", localized_row["source_dir"])
        rows.append(localized_row)
    localized["rows"] = rows
    if localized.get("root_path") == "Manual entry":
        localized["root_path"] = character_text.get("manual_entry_root", localized["root_path"])
    return localized


def parse_character_preview_rows(request: HttpRequest) -> list[dict]:
    rows: list[dict] = []
    for index in request.POST.getlist("row_index"):
        rows.append(
            {
                "active": request.POST.get(f"row_active_{index}", "1"),
                "game_id": request.POST.get(f"row_game_id_{index}", ""),
                "game_title": request.POST.get(f"row_game_title_{index}", ""),
                "game_folder": request.POST.get(f"row_game_folder_{index}", ""),
                "character_name": request.POST.get(f"row_character_name_{index}", ""),
                "character_description": request.POST.get(f"row_character_description_{index}", ""),
                "source_dir": request.POST.get(f"row_source_dir_{index}", ""),
                "source_image_path": request.POST.get(f"row_source_image_path_{index}", ""),
            }
        )
    return normalize_character_import_rows(rows)

def parse_game_preview_rows(request: HttpRequest) -> list[dict]:
    rows: list[dict] = []
    for index in request.POST.getlist("row_index"):
        rows.append(
            {
                "row_index": index,
                "active": request.POST.get(f"row_active_{index}", "1"),
                "game_id": request.POST.get(f"row_game_id_{index}", ""),
                "title": request.POST.get(f"row_title_{index}", ""),
                "folder_name": request.POST.get(f"row_folder_name_{index}", ""),
                "parent_index": request.POST.get(f"row_parent_index_{index}", ""),
                "parent_game_id": request.POST.get(f"row_parent_game_id_{index}", ""),
                "kind": request.POST.get(f"row_kind_{index}", "root"),
                "use_folder_name_as_filename": request.POST.get(f"row_use_folder_name_{index}", "0"),
            }
        )
    return normalize_game_import_rows(rows)

def build_manual_game_preview_payload(cleaned_data: dict[str, object]) -> dict[str, object]:
    kind = str(cleaned_data.get("manual_kind", "root")).strip() or "root"
    title = str(cleaned_data.get("manual_title", "")).strip()
    folder_name = str(cleaned_data.get("manual_folder_name", "")).strip()
    use_folder_name_as_filename = bool(cleaned_data.get("manual_use_folder_name_as_filename"))
    parent_game = cleaned_data.get("manual_parent_game")

    parent_title = ""
    parent_game_id = ""
    existing_game = None

    if kind == "subfolder" and isinstance(parent_game, Game):
        parent_title = parent_game.title
        parent_game_id = str(parent_game.id)
        if folder_name:
            existing_game = parent_game.subfolder_games.filter(folder_name__iexact=folder_name).first()
        if existing_game is None:
            existing_game = parent_game.subfolder_games.filter(title__iexact=title).first()
    else:
        existing_game = find_matching_root_game(folder_name or title)

    row = {
        "row_index": "0",
        "game_id": existing_game.id if existing_game is not None else "",
        "display_path": f"{parent_title}/{title}" if kind == "subfolder" and parent_title else title,
        "title": title,
        "folder_name": folder_name,
        "parent_title": parent_title,
        "parent_index": "",
        "parent_game_id": parent_game_id,
        "kind": kind,
        "exists": existing_game is not None,
        "status": "Existing" if existing_game is not None else "New",
        "active": True,
        "use_folder_name_as_filename": use_folder_name_as_filename,
    }

    return {
        "import_mode": "manual",
        "root_path": "Manual entry",
        "skip_existing": False,
        "rows": [row],
        "root_game_count": 1 if kind == "root" else 0,
        "subfolder_count": 1 if kind == "subfolder" else 0,
    }

def games_setting(request: HttpRequest) -> HttpResponse:
    page_text = get_page_text("games_setting")
    games_text = get_page_ui_text("catalog_games_setting_page")
    preview_payload: dict[str, object] | None = request.session.pop("games_setting_preview", None)
    open_saved_group_id = request.session.pop("games_setting_open_group_id", None)
    preview_payload = localize_game_preview_payload(preview_payload, games_text)
    saved_import_mode = str(request.session.get("games_setting_import_mode", "")).strip()

    import_mode = "scan"
    if preview_payload and preview_payload.get("import_mode") in {"scan", "manual"}:
        import_mode = str(preview_payload["import_mode"])
    elif saved_import_mode in {"scan", "manual"}:
        import_mode = saved_import_mode

    scan_initial: dict[str, object] = {}
    manual_initial: dict[str, object] = {"manual_kind": "root"}

    if preview_payload:
        if import_mode == "scan" and preview_payload.get("root_path"):
            scan_initial = {
                "root_folder": preview_payload["root_path"],
                "skip_existing": preview_payload.get("skip_existing", False),
            }
        elif import_mode == "manual":
            preview_rows = preview_payload.get("rows") or []
            first_row = preview_rows[0] if preview_rows else {}
            manual_initial = {
                "manual_kind": first_row.get("kind", "root"),
                "manual_title": first_row.get("title", ""),
                "manual_folder_name": first_row.get("folder_name", ""),
                "manual_parent_game": first_row.get("parent_game_id", "") or None,
                "manual_use_folder_name_as_filename": first_row.get("use_folder_name_as_filename", False),
            }

    scan_form = GameImportSettingForm(initial=scan_initial) if scan_initial else GameImportSettingForm()
    manual_form = GameManualEntryForm(initial=manual_initial)

    if request.method == "POST":
        action = request.POST.get("action", "preview")
        import_mode = request.POST.get("import_mode", import_mode).strip() or "scan"
        if import_mode not in {"scan", "manual"}:
            import_mode = "scan"
        request.session["games_setting_import_mode"] = import_mode

        if action == "clear":
            request.session.pop("games_setting_preview", None)
            messages.info(request, games_text["messages"]["cleared_preview"])
            return redirect("games_setting")

        if action == "delete_saved":
            request.session.pop("games_setting_preview", None)
            game = get_object_or_404(Game.objects.select_related("main_folder"), pk=request.POST.get("game_id"))
            label = game.display_path
            if game.main_folder_id:
                request.session["games_setting_open_group_id"] = game.main_folder_id
            if game.main_folder_id is None:
                game.subfolder_games.all().delete()
            game.delete()
            messages.success(request, games_text["messages"]["deleted"].format(label=label))
            return redirect("games_setting")

        if action == "update_saved":
            request.session.pop("games_setting_preview", None)
            game = get_object_or_404(Game.objects.select_related("main_folder"), pk=request.POST.get("game_id"))
            request.session["games_setting_open_group_id"] = game.main_folder_id or game.id
            game.title = request.POST.get("saved_title", "").strip() or game.title
            game.folder_name = request.POST.get("saved_folder_name", "").strip()
            game.use_folder_name_as_filename = request.POST.get("saved_use_folder_name_as_filename") == "1"
            try:
                game.save(update_fields=["title", "folder_name", "use_folder_name_as_filename", "updated_at"])
            except IntegrityError:
                messages.error(request, games_text["messages"]["duplicate_title"])
            else:
                messages.success(request, games_text["messages"]["updated"].format(label=game.display_path))
            return redirect("games_setting")

        if action == "save":
            request.session.pop("games_setting_preview", None)
            preview_rows = parse_game_preview_rows(request)
            preview_mode = request.POST.get("preview_import_mode", import_mode).strip() or "scan"
            preview_root_path = request.POST.get("preview_root_path", "").strip()
            preview_skip_existing = request.POST.get("preview_skip_existing", "0") == "1"
            preview_payload = {
                "import_mode": preview_mode,
                "root_path": preview_root_path or ("Manual entry" if preview_mode == "manual" else ""),
                "skip_existing": preview_skip_existing,
                "rows": preview_rows,
                "root_game_count": sum(1 for row in preview_rows if row.get("kind") == "root" and row.get("active", True)),
                "subfolder_count": sum(1 for row in preview_rows if row.get("kind") == "subfolder" and row.get("active", True)),
            }
            if not preview_rows:
                messages.warning(request, games_text["messages"]["preview_before_save"])
            else:
                result = import_game_candidates(preview_rows)
                messages.success(
                    request,
                    games_text["messages"]["saved_summary"].format(
                        root_count=result["created_roots"] + result["updated_roots"],
                        sub_count=result["created_subfolders"] + result["updated_subfolders"],
                    ),
                )
                if result["skipped_count"]:
                    messages.warning(request, games_text["messages"]["skipped_rows"].format(count=result["skipped_count"]))
                request.session["games_setting_import_mode"] = preview_mode
                return redirect("games_setting")

        elif import_mode == "manual":
            manual_form = GameManualEntryForm(request.POST)
            scan_form = GameImportSettingForm(
                initial={
                    "root_folder": request.POST.get("root_folder", "").strip(),
                    "skip_existing": request.POST.get("skip_existing") in {"1", "true", "on", "yes"},
                }
            )
            if manual_form.is_valid():
                preview_payload = build_manual_game_preview_payload(manual_form.cleaned_data)
                request.session["games_setting_preview"] = preview_payload
                preview_payload = localize_game_preview_payload(preview_payload, games_text)
                return redirect("games_setting")

        else:
            scan_form = GameImportSettingForm(request.POST)
            manual_form = GameManualEntryForm(
                initial={
                    "manual_kind": request.POST.get("manual_kind", "root"),
                    "manual_title": request.POST.get("manual_title", "").strip(),
                    "manual_folder_name": request.POST.get("manual_folder_name", "").strip(),
                    "manual_parent_game": request.POST.get("manual_parent_game", "") or None,
                    "manual_use_folder_name_as_filename": request.POST.get("manual_use_folder_name_as_filename") in {"1", "true", "on", "yes"},
                }
            )
            if scan_form.is_valid():
                try:
                    preview_payload = scan_game_import_candidates(
                        scan_form.cleaned_data["root_folder"],
                        skip_existing=scan_form.cleaned_data.get("skip_existing", False),
                    )
                except (FileNotFoundError, NotADirectoryError) as exc:
                    scan_form.add_error("root_folder", str(exc))
                else:
                    preview_payload["import_mode"] = "scan"
                    request.session["games_setting_preview"] = preview_payload
                    preview_payload = localize_game_preview_payload(preview_payload, games_text)
                    return redirect("games_setting")

    saved_games = list(Game.objects.select_related("main_folder").all())
    saved_games.sort(
        key=lambda game: (
            (game.main_folder.display_path if game.main_folder_id else game.display_path).lower(),
            1 if game.main_folder_id else 0,
            game.title.lower(),
        )
    )
    saved_root_count = sum(1 for game in saved_games if game.main_folder_id is None)
    saved_subfolder_count = len(saved_games) - saved_root_count
    saved_game_groups = []
    root_games = Game.objects.filter(main_folder__isnull=True).prefetch_related("subfolder_games").order_by("title")
    for game in root_games:
        subfolders = list(game.subfolder_games.all())
        saved_game_groups.append(
            {
                "game": game,
                "entries": [{"game": game, "is_root": True}] + [{"game": child, "is_root": False} for child in subfolders],
                "count": 1 + len(subfolders),
                "subfolder_count": len(subfolders),
            }
        )

    context = {
        "scan_form": scan_form,
        "manual_form": manual_form,
        "import_mode": import_mode,
        "preview_payload": preview_payload,
        "saved_games": saved_games,
        "saved_game_groups": saved_game_groups,
        "saved_root_count": saved_root_count,
        "saved_subfolder_count": saved_subfolder_count,
        "open_saved_group_id": open_saved_group_id,
        "active_nav": "games_setting",
        "page_title": page_text["title"],
        "page_heading": page_text["title"],
        "page_intro_text": page_text["intro"],
        "page_kicker": page_text["kicker"],
        "games_text": games_text,
    }
    return render(request, "catalog/games_setting.html", context)

def get_character_manual_upload_dir() -> Path:
    upload_dir = Path(settings.MEDIA_ROOT) / "references" / "_manual_preview"
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir

def is_character_manual_upload_path(source_image_path: str) -> bool:
    if not source_image_path:
        return False

    try:
        candidate = Path(source_image_path).resolve()
        candidate.relative_to(get_character_manual_upload_dir().resolve())
    except (OSError, ValueError):
        return False
    return True

def cleanup_character_preview_payload_files(preview_payload: dict[str, object] | None) -> None:
    if not preview_payload:
        return

    for row in preview_payload.get("rows") or []:
        source_image_path = str(row.get("source_image_path", "")).strip()
        if not is_character_manual_upload_path(source_image_path):
            continue
        try:
            Path(source_image_path).unlink(missing_ok=True)
        except OSError:
            continue

def cleanup_character_preview_request_files(request: HttpRequest) -> None:
    for index in request.POST.getlist("row_index"):
        source_image_path = request.POST.get(f"row_source_image_path_{index}", "")
        if not is_character_manual_upload_path(source_image_path):
            continue
        try:
            Path(source_image_path).unlink(missing_ok=True)
        except OSError:
            continue

def persist_manual_character_upload(uploaded_file) -> tuple[str, str]:
    suffix = Path(getattr(uploaded_file, "name", "") or "").suffix.lower()
    if suffix not in settings.SUPPORTED_IMAGE_EXTENSIONS:
        suffix = ".png"

    target_path = get_character_manual_upload_dir() / f"{uuid4().hex}{suffix}"
    with target_path.open("wb") as handle:
        for chunk in uploaded_file.chunks():
            handle.write(chunk)

    return str(target_path), inline_preview_data_url(target_path)

def build_manual_character_preview_payload(cleaned_data: dict[str, object], uploaded_reference=None) -> dict[str, object]:
    game = cleaned_data["manual_game"]
    character_name = str(cleaned_data.get("manual_name", "")).strip()
    character_description = str(cleaned_data.get("manual_description", "")).strip()
    existing_character = game.characters.filter(name__iexact=character_name).first()

    source_dir = ""
    source_image_path = ""
    preview_data_url = existing_character.reference_image.url if existing_character and existing_character.reference_image else ""

    if uploaded_reference is not None:
        source_image_path, preview_data_url = persist_manual_character_upload(uploaded_reference)
        source_dir = "Manual upload"

    return {
        "import_mode": "manual",
        "root_path": "Manual entry",
        "skip_existing": False,
        "rows": [
            {
                "game_id": game.id,
                "game_title": game.title,
                "game_folder": game.resolved_folder_name,
                "character_name": character_name,
                "character_description": character_description,
                "source_dir": source_dir,
                "source_image_path": source_image_path,
                "preview_data_url": preview_data_url,
                "status": "Update" if existing_character is not None else "New",
                "existing": existing_character is not None,
                "active": True,
            }
        ],
        "matched_game_count": 1,
    }

def character_setting(request: HttpRequest) -> HttpResponse:
    page_text = get_page_text("character_setting")
    character_text = get_page_ui_text("catalog_character_setting_page")
    preview_payload: dict[str, object] | None = request.session.pop("character_setting_preview", None)
    open_saved_group_id = request.session.pop("character_setting_open_group_id", None)
    preview_payload = localize_character_preview_payload(preview_payload, character_text)
    next_import_mode = str(request.session.pop("character_setting_next_import_mode", "")).strip()

    import_mode = "scan"
    if preview_payload and preview_payload.get("import_mode") in {"scan", "manual"}:
        import_mode = str(preview_payload["import_mode"])
    elif next_import_mode in {"scan", "manual"}:
        import_mode = next_import_mode

    scan_initial: dict[str, object] = {}
    manual_initial: dict[str, object] = {}

    if preview_payload:
        if import_mode == "scan" and preview_payload.get("root_path"):
            scan_initial = {
                "root_folder": preview_payload["root_path"],
                "skip_existing": preview_payload.get("skip_existing", False),
            }
        elif import_mode == "manual":
            preview_rows = preview_payload.get("rows") or []
            first_row = preview_rows[0] if preview_rows else {}
            manual_initial = {
                "manual_game": first_row.get("game_id", "") or None,
                "manual_name": first_row.get("character_name", ""),
                "manual_description": first_row.get("character_description", ""),
            }

    scan_form = CharacterImportSettingForm(initial=scan_initial) if scan_initial else CharacterImportSettingForm()
    manual_form = CharacterManualEntryForm(initial=manual_initial)

    if request.method == "POST":
        action = request.POST.get("action", "preview")
        import_mode = request.POST.get("import_mode", import_mode).strip() or "scan"
        if import_mode not in {"scan", "manual"}:
            import_mode = "scan"

        if action == "clear":
            cleanup_character_preview_request_files(request)
            request.session["character_setting_next_import_mode"] = import_mode
            request.session.pop("character_setting_preview", None)
            messages.info(request, character_text["messages"]["cleared_preview"])
            return redirect("character_setting")

        if action == "delete_saved":
            cleanup_character_preview_payload_files(preview_payload)
            request.session.pop("character_setting_preview", None)
            character = get_object_or_404(Character.objects.select_related("game"), pk=request.POST.get("character_id"))
            request.session["character_setting_open_group_id"] = character.game_id
            label = f"{character.game.display_path} / {character.name}"
            character.delete()
            messages.success(request, character_text["messages"]["deleted"].format(label=label))
            return redirect("character_setting")

        if action == "update_saved":
            cleanup_character_preview_payload_files(preview_payload)
            request.session.pop("character_setting_preview", None)
            character = get_object_or_404(Character.objects.select_related("game"), pk=request.POST.get("character_id"))
            request.session["character_setting_open_group_id"] = character.game_id
            new_name = request.POST.get("saved_character_name", "").strip()
            new_description = request.POST.get("saved_character_description", "").strip()
            uploaded_reference = request.FILES.get("saved_reference_image")
            if not new_name:
                messages.error(request, character_text["messages"]["blank_name"])
                return redirect("character_setting")
            character.name = new_name
            character.description = new_description
            if uploaded_reference is not None:
                character.reference_image = uploaded_reference
            try:
                character.save()
            except IntegrityError:
                messages.error(request, character_text["messages"]["duplicate_name"])
            else:
                suffix = character_text["messages"]["updated_with_image_suffix"] if uploaded_reference is not None else ""
                messages.success(request, character_text["messages"]["updated"].format(label=f"{character.game.display_path} / {character.name}", suffix=suffix))
            return redirect("character_setting")

        if action == "save":
            request.session.pop("character_setting_preview", None)
            preview_rows = parse_character_preview_rows(request)
            preview_mode = request.POST.get("preview_import_mode", import_mode).strip() or "scan"
            preview_root_path = request.POST.get("preview_root_path", "").strip()
            preview_skip_existing = request.POST.get("preview_skip_existing", "0") == "1"
            preview_payload = {
                "import_mode": preview_mode,
                "root_path": preview_root_path or ("Manual entry" if preview_mode == "manual" else ""),
                "skip_existing": preview_skip_existing,
                "rows": preview_rows,
                "matched_game_count": len({row["game_id"] for row in preview_rows if row.get("game_id")}),
            }
            if not preview_rows:
                cleanup_character_preview_payload_files(preview_payload)
                messages.warning(request, character_text["messages"]["preview_before_save"])
            else:
                result = import_character_candidates(preview_rows)
                cleanup_character_preview_payload_files(preview_payload)
                messages.success(request, character_text["messages"]["saved_summary"].format(created_count=result["created_count"], updated_count=result["updated_count"]))
                if result["skipped_count"]:
                    messages.warning(request, character_text["messages"]["skipped_rows"].format(count=result["skipped_count"]))
                return redirect("character_setting")

        elif import_mode == "manual":
            manual_form = CharacterManualEntryForm(request.POST, request.FILES)
            scan_form = CharacterImportSettingForm(
                initial={
                    "root_folder": request.POST.get("root_folder", "").strip(),
                    "skip_existing": request.POST.get("skip_existing") in {"1", "true", "on", "yes"},
                }
            )
            if manual_form.is_valid():
                cleanup_character_preview_request_files(request)
                preview_payload = build_manual_character_preview_payload(manual_form.cleaned_data, request.FILES.get("manual_reference_image"))
                request.session["character_setting_preview"] = preview_payload
                preview_payload = localize_character_preview_payload(preview_payload, character_text)
                return redirect("character_setting")

        else:
            scan_form = CharacterImportSettingForm(request.POST)
            manual_form = CharacterManualEntryForm(
                initial={
                    "manual_game": request.POST.get("manual_game", "") or None,
                    "manual_name": request.POST.get("manual_name", "").strip(),
                    "manual_description": request.POST.get("manual_description", "").strip(),
                }
            )
            if scan_form.is_valid():
                cleanup_character_preview_request_files(request)
                try:
                    preview_payload = scan_character_import_candidates(
                        scan_form.cleaned_data["root_folder"],
                        skip_existing=scan_form.cleaned_data.get("skip_existing", False),
                    )
                except (FileNotFoundError, NotADirectoryError) as exc:
                    scan_form.add_error("root_folder", str(exc))
                else:
                    preview_payload["import_mode"] = "scan"
                    request.session["character_setting_preview"] = preview_payload
                    preview_payload = localize_character_preview_payload(preview_payload, character_text)
                    return redirect("character_setting")

    saved_character_groups = []
    total_saved_characters = 0
    root_games = Game.objects.filter(main_folder__isnull=True).prefetch_related("characters").order_by("title")
    for game in root_games:
        characters = list(game.characters.all())
        if not characters:
            continue
        saved_character_groups.append(
            {
                "game": game,
                "characters": characters,
                "count": len(characters),
            }
        )
        total_saved_characters += len(characters)

    context = {
        "scan_form": scan_form,
        "manual_form": manual_form,
        "import_mode": import_mode,
        "preview_payload": preview_payload,
        "saved_character_groups": saved_character_groups,
        "saved_character_game_count": len(saved_character_groups),
        "saved_character_total": total_saved_characters,
        "open_saved_group_id": open_saved_group_id,
        "active_nav": "character_setting",
        "page_title": page_text["title"],
        "page_heading": page_text["title"],
        "page_intro_text": page_text["intro"],
        "page_kicker": page_text["kicker"],
        "character_text": character_text,
    }
    return render(request, "catalog/character_setting.html", context)

@require_GET
def characters_for_game(request: HttpRequest, game_id: int) -> JsonResponse:
    characters = Character.objects.filter(game_id=game_id).order_by("name")
    payload = [
        {
            "id": character.id,
            "name": character.name,
            "description": character.description,
            "reference_image_url": character.reference_image.url if character.reference_image else "",
        }
        for character in characters
    ]
    return JsonResponse({"characters": payload})

