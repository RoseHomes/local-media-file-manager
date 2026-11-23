from pathlib import Path
from urllib.parse import quote
import mimetypes

from django.contrib import messages
from django.http import FileResponse, Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from sorter.apps.catalog.models import Character, Game
from sorter.apps.fanart.forms import AlbumSettingForm, FanartSettingForm
from sorter.apps.fanart.models import AlbumSetting, FanartSetting
from sorter.apps.fanart.services import (
    AlbumDirectoryNotFound,
    AlbumRootNotConfigured,
    build_album_listing,
    build_inbox_listing,
    clear_preview_cache,
    ensure_album_preview_image,
    ensure_preview_image,
    prepare_album_character_filter,
    get_fanart_paths,
    process_staged_entries,
    resolve_album_path,
    resolve_inbox_path,
)
from sorter.apps.ui.text import get_page_text, get_page_ui_text


SESSION_KEY = "staged_assignments"


def build_album_query(root_index: int, relative_path: str = "") -> str:
    query = f"?library={root_index}"
    if relative_path:
        query += f"&path={relative_path}"
    return query

def get_staged_entries(request: HttpRequest) -> list[dict]:
    return request.session.get(SESSION_KEY, [])

def save_staged_entries(request: HttpRequest, entries: list[dict]) -> None:
    request.session[SESSION_KEY] = entries
    request.session.modified = True

def workspace(request: HttpRequest) -> HttpResponse:
    fanart_setting, source_dir, destination_root = get_fanart_paths()
    staged_entries = get_staged_entries(request)
    staged_paths = {entry["relative_path"] for entry in staged_entries}
    images = build_inbox_listing(staged_paths)
    games = list(Game.objects.select_related("main_folder").prefetch_related("characters").all())
    games.sort(key=lambda game: game.display_path.lower())
    characters = Character.objects.select_related("game").all()
    page_text = get_page_text("fanart_file")
    workspace_text = get_page_ui_text("fanart_workspace")
    character_map = {
        character.id: {
            "id": character.id,
            "name": character.name,
            "description": character.description,
            "game_id": character.game_id,
            "reference_image_url": character.reference_image.url if character.reference_image else "",
        }
        for character in characters
    }

    destination_payload = []
    for game in games:
        destination_payload.append(
            {
                "key": f"game:{game.id}",
                "label": game.display_path,
                "target_game_id": game.id,
                "character_game_id": game.character_owner_id,
                "use_folder_name_as_filename": game.use_folder_name_as_filename,
                "filename_label": game.resolved_folder_name,
            }
        )

    enriched_staged_entries = []
    for entry in staged_entries:
        character = character_map.get(entry.get("character_id")) if entry.get("character_id") else None
        target_label = entry.get("target_label") or entry.get("game_title") or workspace_text["unknown_game"]
        relative_path = entry.get("relative_path", "")
        filename_label = entry.get("filename_label") or (character["name"] if character else workspace_text["unknown_name"])
        enriched_staged_entries.append(
            {
                **entry,
                "character_name": filename_label,
                "target_label": target_label,
                "file_name": Path(relative_path).name if relative_path else workspace_text["unknown_file"],
                "preview_url": f"/workspace-preview/{quote(relative_path, safe='/')}" if relative_path else "",
                "uses_folder_name_as_filename": bool(entry.get("use_folder_name_as_filename")),
            }
        )

    context = {
        "games": games,
        "images": images,
        "staged_entries": enriched_staged_entries,
        "character_payload": list(character_map.values()),
        "workspace_text": workspace_text,
        "destination_payload": destination_payload,
        "inbox_dir": source_dir,
        "library_root": destination_root,
        "fanart_setting": fanart_setting,
        "default_sort": fanart_setting.default_sort,
        "active_nav": "fanart_file",
        "page_title": page_text["title"],
        "page_heading": page_text["title"],
        "page_intro_text": page_text["intro"],
        "page_kicker": page_text["kicker"],
    }
    return render(request, "fanart/workspace.html", context)

def fanart_album(request: HttpRequest) -> HttpResponse:
    album_setting = AlbumSetting.load()
    album_paths = album_setting.normalized_paths
    page_text = get_page_text("fanart_album")
    fanart_album_text = get_page_ui_text("fanart_album_page")
    root_index = 0
    requested_root = request.GET.get("library")
    if requested_root not in (None, ""):
        try:
            root_index = int(requested_root)
        except ValueError:
            root_index = 0

    requested_relative = request.GET.get("path", "").strip().strip("/")

    root_options = [
        {
            "index": index,
            "label": Path(path).name or path,
            "path": path,
            "url": build_album_query(index),
            "is_active": index == root_index,
        }
        for index, path in enumerate(album_paths)
    ]

    current_root = None
    current_relative = ""
    current_folder_name = fanart_album_text["viewer_title"]
    current_folder_path = ""
    parent_url = ""
    breadcrumbs = []
    subfolders = []
    images = []
    album_error = ""
    album_character_filter = {"is_visible": False, "characters": [], "game_label": ""}

    if album_paths:
        if root_index < 0 or root_index >= len(album_paths):
            root_index = 0
            root_options = [
                {
                    **option,
                    "is_active": option["index"] == root_index,
                }
                for option in root_options
            ]

        try:
            album_root, current_dir, current_relative, folder_items, images = build_album_listing(root_index, requested_relative)
        except (AlbumRootNotConfigured, AlbumDirectoryNotFound, ValueError):
            album_error = fanart_album_text["messages"]["album_open_error"]
        else:
            current_root = str(album_root)
            current_folder_name = current_dir.name if current_relative else (Path(current_root).name or current_root)
            current_folder_path = current_relative or "."

            if current_relative:
                parent_path = Path(current_relative).parent
                parent_relative = "" if str(parent_path) == "." else parent_path.as_posix()
                parent_url = build_album_query(root_index, parent_relative)

            breadcrumbs.append({"label": Path(current_root).name or current_root, "url": build_album_query(root_index)})
            if current_relative:
                running_parts: list[str] = []
                for part in Path(current_relative).parts:
                    running_parts.append(part)
                    breadcrumbs.append({
                        "label": part,
                        "url": build_album_query(root_index, "/".join(running_parts)),
                    })

            subfolders = [
                {
                    "name": folder.name,
                    "relative_path": folder.relative_path,
                    "url": build_album_query(root_index, folder.relative_path),
                    "folder_count": folder.folder_count,
                    "image_count": folder.image_count,
                }
                for folder in folder_items
            ]

            album_character_filter = prepare_album_character_filter(root_index, album_root, current_relative, images)

    context = {
        "album_paths": album_paths,
        "root_options": root_options,
        "root_index": root_index,
        "current_root": current_root,
        "current_relative": current_relative,
        "current_folder_name": current_folder_name,
        "current_folder_path": current_folder_path,
        "parent_url": parent_url,
        "breadcrumbs": breadcrumbs,
        "subfolders": subfolders,
        "images": images,
        "album_error": album_error,
        "album_character_filter": album_character_filter,
        "fanart_album_text": fanart_album_text,
        "default_sort": album_setting.default_sort,
        "active_nav": "fanart_album",
        "page_title": page_text["title"],
        "page_heading": page_text["title"],
        "page_intro_text": page_text["intro"],
        "page_kicker": page_text["kicker"],
    }
    return render(request, "fanart/fanart_album.html", context)

def fanart_setting(request: HttpRequest) -> HttpResponse:
    setting_instance = FanartSetting.load()
    page_text = get_page_text("fanart_setting")
    fanart_setting_text = get_page_ui_text("fanart_setting_page")
    fanart_messages = get_page_ui_text("fanart_messages")

    if request.method == "POST":
        form = FanartSettingForm(request.POST, instance=setting_instance)
        if form.is_valid():
            updated_setting = form.save(commit=False)
            try:
                updated_setting.source_path.mkdir(parents=True, exist_ok=True)
                updated_setting.destination_path.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                form.add_error(None, fanart_messages["folder_access_error"].format(error=exc))
            else:
                updated_setting.save()
                messages.success(request, fanart_messages["fanart_setting_saved"])
                return redirect("fanart_setting")
    else:
        form = FanartSettingForm(instance=setting_instance)

    context = {
        "form": form,
        "fanart_setting": setting_instance,
        "filename_preview": setting_instance.sample_filename(),
        "fanart_setting_text": fanart_setting_text,
        "active_nav": "fanart_setting",
        "page_title": page_text["title"],
        "page_heading": page_text["title"],
        "page_intro_text": page_text["intro"],
        "page_kicker": page_text["kicker"],
    }
    return render(request, "fanart/fanart_setting.html", context)

def album_setting(request: HttpRequest) -> HttpResponse:
    setting_instance = AlbumSetting.load()
    page_text = get_page_text("album_setting")
    album_setting_text = get_page_ui_text("album_setting_page")
    form = AlbumSettingForm(
        request.POST or None,
        initial={"default_sort": setting_instance.default_sort},
        initial_rows=setting_instance.normalized_entries,
    )

    if request.method == "POST" and form.is_valid():
        setting_instance.album_paths = form.cleaned_data["album_rows"]
        setting_instance.default_sort = form.cleaned_data["default_sort"]
        setting_instance.save(update_fields=["album_paths", "default_sort", "updated_at"])
        messages.success(request, album_setting_text["messages"]["saved"])
        return redirect("album_setting")

    root_game_lookup = {str(game.id): game for game in form.root_games}
    configured_rows = []
    for entry in setting_instance.normalized_entries:
        root_game_id = str(entry.get("root_game_id") or "")
        configured_rows.append(
            {
                **entry,
                "root_game_label": root_game_lookup[root_game_id].display_path if root_game_id in root_game_lookup else album_setting_text["unlinked_game"],
            }
        )

    context = {
        "form": form,
        "album_rows": form.rows_for_render,
        "configured_rows": configured_rows,
        "album_setting_text": album_setting_text,
        "active_nav": "album_setting",
        "page_title": page_text["title"],
        "page_heading": page_text["title"],
        "page_intro_text": page_text["intro"],
        "page_kicker": page_text["kicker"],
    }
    return render(request, "fanart/album_setting.html", context)

@require_POST
def stage_selection(request: HttpRequest) -> HttpResponse:
    fanart_messages = get_page_ui_text("fanart_messages")
    selected_images = request.POST.getlist("selected_images")
    target_game_id = request.POST.get("target_game", "").strip()
    character_game_id = request.POST.get("game", "").strip()
    character_id = request.POST.get("character", "").strip()

    if not selected_images:
        messages.warning(request, fanart_messages["select_image_before_queue"])
        return redirect("workspace")

    if not target_game_id or not target_game_id.isdigit():
        messages.warning(request, fanart_messages["select_valid_game"])
        return redirect("workspace")

    target_game = get_object_or_404(Game.objects.select_related("main_folder"), pk=int(target_game_id))

    character_game = None
    character = None
    if target_game.use_folder_name_as_filename:
        filename_label = target_game.resolved_folder_name
    else:
        if not character_game_id or not character_id:
            messages.warning(request, fanart_messages["select_game_and_character"])
            return redirect("workspace")

        if not character_game_id.isdigit() or not character_id.isdigit():
            messages.warning(request, fanart_messages["invalid_game_or_character"])
            return redirect("workspace")

        character_game = get_object_or_404(Game, pk=int(character_game_id))
        character = get_object_or_404(Character, pk=int(character_id), game=character_game)
        filename_label = character.name

    staged_entries = get_staged_entries(request)
    staged_paths = {entry["relative_path"] for entry in staged_entries}
    added_count = 0
    target_label = target_game.display_path

    for relative_path in selected_images:
        normalized = Path(relative_path).as_posix()
        try:
            source_path = resolve_inbox_path(normalized)
        except ValueError:
            continue

        if normalized in staged_paths or not source_path.exists():
            continue

        staged_entries.append(
            {
                "relative_path": normalized,
                "game_id": character_game.id if character_game is not None else "",
                "game_title": character_game.title if character_game is not None else target_game.title,
                "character_id": character.id if character is not None else "",
                "target_game_id": target_game.id,
                "target_label": target_label,
                "filename_label": filename_label,
                "use_folder_name_as_filename": target_game.use_folder_name_as_filename,
            }
        )
        staged_paths.add(normalized)
        added_count += 1

    save_staged_entries(request, staged_entries)

    if added_count:
        messages.success(request, fanart_messages["staged_count"].format(count=added_count, label=filename_label))
    else:
        messages.warning(request, fanart_messages["no_new_images_staged"])

    return redirect("workspace")

@require_POST
def unstage_selection(request: HttpRequest) -> HttpResponse:
    fanart_messages = get_page_ui_text("fanart_messages")
    requested_paths = request.POST.getlist("relative_paths")
    if not requested_paths:
        single_path = request.POST.get("relative_path", "")
        if single_path:
            requested_paths = [single_path]

    relative_paths = [Path(path).as_posix() for path in requested_paths if path]
    current_entries = get_staged_entries(request)
    removed_entries = [entry for entry in current_entries if entry["relative_path"] in relative_paths]
    staged_entries = [entry for entry in current_entries if entry["relative_path"] not in relative_paths]
    save_staged_entries(request, staged_entries)

    if len(relative_paths) == 1:
        message = fanart_messages["removed_single"].format(path=relative_paths[0])
    else:
        message = fanart_messages["removed_count"].format(count=len(removed_entries))

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        restored_images = []
        for entry in removed_entries:
            relative_path = entry["relative_path"]
            try:
                source_path = resolve_inbox_path(relative_path)
                stat = source_path.stat()
                restored_images.append(
                    {
                        "relative_path": relative_path,
                        "preview_url": f"/workspace-preview/{quote(relative_path, safe='/')}",
                        "file_name": Path(relative_path).name,
                        "created_at_timestamp": int(stat.st_ctime),
                    }
                )
            except (ValueError, FileNotFoundError):
                continue

        return JsonResponse(
            {
                "message": message,
                "relative_paths": relative_paths,
                "removed_count": len(removed_entries),
                "remaining_count": len(staged_entries),
                "restored_images": restored_images,
            }
        )

    messages.info(request, message)
    return redirect("workspace")

@require_POST
def clear_preview_cache_view(request: HttpRequest) -> HttpResponse:
    fanart_messages = get_page_ui_text("fanart_messages")
    removed_count = clear_preview_cache()
    if removed_count:
        messages.success(request, fanart_messages["cleared_preview_cache"].format(count=removed_count))
    else:
        messages.info(request, fanart_messages["preview_cache_empty"])
    return redirect("workspace")

@require_POST
def process_staging(request: HttpRequest) -> HttpResponse:
    fanart_messages = get_page_ui_text("fanart_messages")
    staged_entries = get_staged_entries(request)
    if not staged_entries:
        messages.warning(request, fanart_messages["queue_empty"])
        return redirect("workspace")

    results = process_staged_entries(staged_entries)
    moved_count = sum(1 for result in results if result["status"] == "moved")
    missing_count = sum(1 for result in results if result["status"] == "missing")
    cleared_preview_count = clear_preview_cache()

    save_staged_entries(request, [])

    if moved_count:
        messages.success(request, fanart_messages["processed_count"].format(count=moved_count))
    if missing_count:
        messages.warning(request, fanart_messages["skipped_missing"].format(count=missing_count))
    if cleared_preview_count:
        messages.info(request, fanart_messages["cleared_after_processing"].format(count=cleared_preview_count))

    return redirect("workspace")

@require_GET
def serve_workspace_file(request: HttpRequest, relative_path: str) -> FileResponse:
    try:
        resolved_path = resolve_inbox_path(relative_path)
    except ValueError as exc:
        raise Http404(get_page_ui_text("fanart_http_messages")["file_outside_inbox"]) from exc

    if not resolved_path.exists() or not resolved_path.is_file():
        raise Http404(get_page_ui_text("fanart_http_messages")["file_not_found"])

    content_type = mimetypes.guess_type(str(resolved_path))[0] or "application/octet-stream"
    return FileResponse(open(resolved_path, "rb"), content_type=content_type)

@require_GET
def serve_workspace_preview(request: HttpRequest, relative_path: str) -> FileResponse:
    try:
        preview_path = ensure_preview_image(relative_path)
    except ValueError as exc:
        raise Http404(get_page_ui_text("fanart_http_messages")["file_outside_inbox"]) from exc

    if not preview_path.exists() or not preview_path.is_file():
        raise Http404(get_page_ui_text("fanart_http_messages")["preview_not_found"])

    content_type = mimetypes.guess_type(str(preview_path))[0] or "image/jpeg"
    return FileResponse(open(preview_path, "rb"), content_type=content_type)

@require_GET
def serve_album_file(request: HttpRequest, root_index: int, relative_path: str) -> FileResponse:
    try:
        resolved_path = resolve_album_path(root_index, relative_path)
    except (AlbumRootNotConfigured, ValueError) as exc:
        raise Http404(get_page_ui_text("fanart_http_messages")["album_file_invalid"]) from exc

    if not resolved_path.exists() or not resolved_path.is_file():
        raise Http404(get_page_ui_text("fanart_http_messages")["album_file_not_found"])

    content_type = mimetypes.guess_type(str(resolved_path))[0] or "application/octet-stream"
    return FileResponse(open(resolved_path, "rb"), content_type=content_type)

@require_GET
def serve_album_preview(request: HttpRequest, root_index: int, relative_path: str) -> FileResponse:
    try:
        preview_path = ensure_album_preview_image(root_index, relative_path)
    except (AlbumRootNotConfigured, ValueError) as exc:
        raise Http404(get_page_ui_text("fanart_http_messages")["album_preview_invalid"]) from exc

    if not preview_path.exists() or not preview_path.is_file():
        raise Http404(get_page_ui_text("fanart_http_messages")["album_preview_not_found"])

    content_type = mimetypes.guess_type(str(preview_path))[0] or "image/jpeg"
    return FileResponse(open(preview_path, "rb"), content_type=content_type)

