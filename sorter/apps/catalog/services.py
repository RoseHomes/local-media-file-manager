import base64
import io
import re
from pathlib import Path

from django.core.files.base import File
from PIL import Image, ImageOps, UnidentifiedImageError

from sorter.apps.catalog.models import Character, Game
from sorter.apps.fanart.services import is_supported_image, safe_name_component
def compact_title(value: str) -> str:
    cleaned = re.sub(r"\s+", "", value.strip())
    return cleaned or value.strip() or "Game"


def normalized_lookup_key(value: str) -> str:
    return re.sub(r"[\s_-]+", "", value.strip()).casefold()


def inline_preview_data_url(source_path: Path) -> str:
    try:
        with Image.open(source_path) as image:
            prepared = ImageOps.exif_transpose(image)
            if prepared.mode not in ("RGB", "L"):
                prepared = prepared.convert("RGB")
            elif prepared.mode == "L":
                prepared = prepared.convert("RGB")

            prepared.thumbnail((160, 160), Image.Resampling.LANCZOS)
            buffer = io.BytesIO()
            prepared.save(buffer, format="JPEG", quality=76, optimize=True)
    except (UnidentifiedImageError, OSError):
        return ""

    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def first_supported_image(folder: Path) -> Path | None:
    for child in sorted(folder.iterdir(), key=lambda item: item.name.lower()):
        if is_supported_image(child):
            return child
    return None


def find_matching_root_game(folder_name: str) -> Game | None:
    token = normalized_lookup_key(folder_name)
    for game in Game.objects.filter(main_folder__isnull=True).order_by("title"):
        candidates = {
            normalized_lookup_key(game.title),
            normalized_lookup_key(game.folder_name or ""),
            normalized_lookup_key(game.resolved_folder_name),
        }
        if token in candidates:
            return game
    return None


def split_character_name_and_description(filename_stem: str) -> tuple[str, str]:
    raw_value = filename_stem.strip()
    if "_" not in raw_value:
        return raw_value, ""

    short_name, description = raw_value.split("_", 1)
    return short_name.strip(), description.strip()


def scan_game_import_candidates(root_folder: str | Path, skip_existing: bool = False) -> dict[str, object]:
    root_path = Path(root_folder).expanduser()
    if not root_path.exists():
        raise FileNotFoundError(f"Folder not found: {root_path}")
    if not root_path.is_dir():
        raise NotADirectoryError(f"Path is not a folder: {root_path}")

    rows: list[dict[str, object]] = []
    root_game_count = 0
    subfolder_count = 0

    for game_dir in sorted((item for item in root_path.iterdir() if item.is_dir()), key=lambda item: item.name.lower()):
        game_title = compact_title(game_dir.name)
        existing_root = find_matching_root_game(game_dir.name)
        root_index = ""
        if not (skip_existing and existing_root is not None):
            root_index = len(rows)
            rows.append(
                {
                    "row_index": root_index,
                    "game_id": existing_root.id if existing_root is not None else "",
                    "display_path": game_title,
                    "title": game_title,
                    "folder_name": game_dir.name,
                    "parent_title": "",
                    "parent_index": "",
                    "parent_game_id": "",
                    "kind": "root",
                    "exists": existing_root is not None,
                    "status": "Existing" if existing_root else "New",
                    "active": True,
                    "use_folder_name_as_filename": existing_root.use_folder_name_as_filename if existing_root is not None else False,
                }
            )
            root_game_count += 1

        for child in sorted((item for item in game_dir.iterdir() if item.is_dir()), key=lambda item: item.name.lower()):
            child_title = compact_title(child.name)
            existing_child = None
            if existing_root is not None:
                existing_child = existing_root.subfolder_games.filter(folder_name__iexact=child.name).first()
                if existing_child is None:
                    existing_child = existing_root.subfolder_games.filter(title__iexact=child_title).first()
            if skip_existing and existing_child is not None:
                continue
            rows.append(
                {
                    "row_index": len(rows),
                    "game_id": existing_child.id if existing_child is not None else "",
                    "display_path": f"{game_title}/{child_title}",
                    "title": child_title,
                    "folder_name": child.name,
                    "parent_title": game_title,
                    "parent_index": root_index,
                    "parent_game_id": existing_root.id if existing_root is not None else "",
                    "kind": "subfolder",
                    "exists": existing_child is not None,
                    "status": "Existing" if existing_child else "New",
                    "active": True,
                    "use_folder_name_as_filename": existing_child.use_folder_name_as_filename if existing_child is not None else False,
                }
            )
            subfolder_count += 1

    return {
        "root_path": str(root_path),
        "skip_existing": skip_existing,
        "rows": rows,
        "root_game_count": root_game_count,
        "subfolder_count": subfolder_count,
    }


def normalize_game_import_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    normalized: list[dict[str, object]] = []

    for row in rows:
        row_index = str(row.get("row_index", row.get("index", ""))).strip()
        game_id = str(row.get("game_id", "")).strip()
        kind = str(row.get("kind", "root")).strip() or "root"
        title = str(row.get("title", "")).strip()
        folder_name = str(row.get("folder_name", "")).strip()
        parent_index = str(row.get("parent_index", "")).strip()
        parent_game_id = str(row.get("parent_game_id", "")).strip()
        active_value = row.get("active", "1")
        active = str(active_value).strip().casefold() not in {"0", "false", "off", ""}
        use_folder_value = row.get("use_folder_name_as_filename", "0")
        use_folder_name_as_filename = str(use_folder_value).strip().casefold() in {"1", "true", "on", "yes"}

        existing_game = Game.objects.select_related("main_folder").filter(pk=game_id).first() if game_id.isdigit() else None
        parent_title = ""
        if kind == "subfolder":
            parent_row = next((item for item in normalized if str(item.get("row_index")) == parent_index), None)
            parent_title = str(parent_row.get("title", "")).strip() if parent_row else str(row.get("parent_title", "")).strip()

        if not title:
            status = "Missing title"
        elif kind == "subfolder" and not (parent_index or parent_game_id):
            status = "Missing parent"
        else:
            status = "Existing" if existing_game is not None else "New"

        normalized.append(
            {
                "row_index": row_index,
                "game_id": game_id,
                "display_path": f"{parent_title}/{title}" if kind == "subfolder" and parent_title else title,
                "title": title,
                "folder_name": folder_name,
                "parent_title": parent_title,
                "parent_index": parent_index,
                "parent_game_id": parent_game_id,
                "kind": kind,
                "exists": existing_game is not None,
                "status": status,
                "active": active,
                "use_folder_name_as_filename": use_folder_name_as_filename,
            }
        )

    return normalized


def import_game_candidates(rows_or_root_folder: list[dict[str, object]] | str | Path) -> dict[str, object]:
    if isinstance(rows_or_root_folder, (str, Path)):
        preview = scan_game_import_candidates(rows_or_root_folder)
        rows = normalize_game_import_rows(preview["rows"])
    else:
        rows = normalize_game_import_rows(rows_or_root_folder)
        preview = {"rows": rows}

    created_roots = 0
    updated_roots = 0
    created_subfolders = 0
    updated_subfolders = 0
    skipped_count = 0
    row_game_map: dict[str, Game] = {}

    for row in rows:
        if not row.get("active", True):
            continue

        row_index = str(row.get("row_index", "")).strip()
        kind = str(row.get("kind", "root")).strip() or "root"
        title = str(row.get("title", "")).strip()
        folder_name = str(row.get("folder_name", "")).strip()
        use_folder_name_as_filename = bool(row.get("use_folder_name_as_filename"))
        game_id = str(row.get("game_id", "")).strip()

        if not title:
            skipped_count += 1
            continue

        if kind == "root":
            game = Game.objects.filter(pk=game_id).first() if game_id.isdigit() else find_matching_root_game(folder_name or title)
            if game is None:
                Game.objects.create(
                    title=title,
                    folder_name=folder_name,
                    use_folder_name_as_filename=use_folder_name_as_filename,
                )
                created_roots += 1
                game = Game.objects.get(title=title, main_folder__isnull=True)
            else:
                changed = False
                if game.title != title:
                    game.title = title
                    changed = True
                if game.folder_name != folder_name:
                    game.folder_name = folder_name
                    changed = True
                if game.use_folder_name_as_filename != use_folder_name_as_filename:
                    game.use_folder_name_as_filename = use_folder_name_as_filename
                    changed = True
                if changed:
                    game.save(update_fields=["title", "folder_name", "use_folder_name_as_filename", "updated_at"])
                    updated_roots += 1
            row_game_map[row_index] = game
            continue

        parent_index = str(row.get("parent_index", "")).strip()
        parent_game_id = str(row.get("parent_game_id", "")).strip()
        parent_game = row_game_map.get(parent_index)
        if parent_game is None and parent_game_id.isdigit():
            parent_game = Game.objects.filter(pk=int(parent_game_id)).first()
        if parent_game is None:
            skipped_count += 1
            continue

        game = Game.objects.filter(pk=game_id, main_folder=parent_game).first() if game_id.isdigit() else None
        if game is None:
            game = parent_game.subfolder_games.filter(folder_name__iexact=folder_name).first()
        if game is None:
            game = parent_game.subfolder_games.filter(title__iexact=title).first()

        if game is None:
            game = Game.objects.create(
                title=title,
                folder_name=folder_name,
                main_folder=parent_game,
                use_folder_name_as_filename=use_folder_name_as_filename,
            )
            created_subfolders += 1
        else:
            changed = False
            if game.title != title:
                game.title = title
                changed = True
            if game.folder_name != folder_name:
                game.folder_name = folder_name
                changed = True
            if game.use_folder_name_as_filename != use_folder_name_as_filename:
                game.use_folder_name_as_filename = use_folder_name_as_filename
                changed = True
            if changed:
                game.save(update_fields=["title", "folder_name", "use_folder_name_as_filename", "updated_at"])
                updated_subfolders += 1
        row_game_map[row_index] = game

    return {
        "created_roots": created_roots,
        "updated_roots": updated_roots,
        "created_subfolders": created_subfolders,
        "updated_subfolders": updated_subfolders,
        "skipped_count": skipped_count,
        "preview": preview,
    }


def scan_character_import_candidates(root_folder: str | Path, skip_existing: bool = False) -> dict[str, object]:
    root_path = Path(root_folder).expanduser()
    if not root_path.exists():
        raise FileNotFoundError(f"Folder not found: {root_path}")
    if not root_path.is_dir():
        raise NotADirectoryError(f"Path is not a folder: {root_path}")

    rows: list[dict[str, object]] = []
    matched_game_count = 0

    for game_dir in sorted((item for item in root_path.iterdir() if item.is_dir()), key=lambda item: item.name.lower()):
        matched_game = find_matching_root_game(game_dir.name)
        if matched_game is not None:
            matched_game_count += 1

        for image_path in sorted((item for item in game_dir.iterdir() if item.is_file() and is_supported_image(item)), key=lambda item: item.name.lower()):
            character_name, description = split_character_name_and_description(image_path.stem)
            existing_character = None
            if matched_game is not None:
                existing_character = matched_game.characters.filter(name__iexact=character_name).first()

            if matched_game is None:
                status = "Game not found"
            elif existing_character is not None:
                status = "Update"
            else:
                status = "New"

            if skip_existing and existing_character is not None:
                continue

            rows.append(
                {
                    "game_id": matched_game.id if matched_game is not None else "",
                    "game_title": matched_game.title if matched_game is not None else game_dir.name,
                    "game_folder": game_dir.name,
                    "character_name": character_name,
                    "character_description": description,
                    "source_dir": str(game_dir),
                    "source_image_path": str(image_path),
                    "preview_data_url": inline_preview_data_url(image_path),
                    "status": status,
                    "existing": existing_character is not None,
                }
            )

    return {
        "root_path": str(root_path),
        "skip_existing": skip_existing,
        "rows": rows,
        "matched_game_count": matched_game_count,
    }


def normalize_character_import_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    normalized: list[dict[str, object]] = []
    for row in rows:
        source_image_path = str(row.get("source_image_path", "")).strip()
        game_id = str(row.get("game_id", "")).strip()
        source_dir = str(row.get("source_dir", "")).strip()
        game_folder = str(row.get("game_folder", "")).strip()
        character_name = str(row.get("character_name", "")).strip()
        character_description = str(row.get("character_description", "")).strip()
        active = str(row.get("active", "1")).strip() != "0"

        matched_game = Game.objects.filter(pk=game_id).first() if game_id.isdigit() else None
        existing_character = None
        if matched_game is not None:
            existing_character = matched_game.characters.filter(name__iexact=character_name).first()

        if matched_game is None:
            status = "Game not found"
        elif not source_image_path:
            status = "No image"
        elif existing_character is not None:
            status = "Update"
        else:
            status = "New"

        normalized.append(
            {
                "game_id": game_id,
                "game_title": matched_game.title if matched_game is not None else (str(row.get("game_title", "")).strip() or game_folder),
                "game_folder": game_folder,
                "character_name": character_name,
                "character_description": character_description,
                "source_dir": source_dir,
                "source_image_path": source_image_path,
                "preview_data_url": inline_preview_data_url(Path(source_image_path)) if source_image_path and Path(source_image_path).exists() else "",
                "status": status,
                "existing": existing_character is not None,
                "active": active,
            }
        )
    return normalized


def import_character_candidates(rows: list[dict[str, object]]) -> dict[str, int]:
    created_count = 0
    updated_count = 0
    skipped_count = 0

    for row in rows:
        if not row.get("active", True):
            continue

        game_id = str(row.get("game_id", "")).strip()
        character_name = str(row.get("character_name", "")).strip()
        character_description = str(row.get("character_description", "")).strip()
        source_image_path = str(row.get("source_image_path", "")).strip()

        if not game_id.isdigit() or not character_name:
            skipped_count += 1
            continue

        game = Game.objects.filter(pk=int(game_id)).first()
        if game is None:
            skipped_count += 1
            continue

        character, created = Character.objects.get_or_create(game=game, name=character_name)
        character.description = character_description

        if source_image_path:
            source_path = Path(source_image_path)
            if source_path.exists() and is_supported_image(source_path):
                if character.reference_image:
                    character.reference_image.delete(save=False)
                import_name = f"references/imported/{safe_name_component(game.title)}_{safe_name_component(character_name)}{source_path.suffix.lower()}"
                with source_path.open("rb") as handle:
                    character.reference_image.save(import_name, File(handle), save=False)

        character.save()
        if created:
            created_count += 1
        else:
            updated_count += 1

    return {
        "created_count": created_count,
        "updated_count": updated_count,
        "skipped_count": skipped_count,
    }
