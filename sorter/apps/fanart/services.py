import base64
import hashlib
import io
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import shutil
from urllib.parse import quote

from django.conf import settings
from django.core.files.base import File
from django.utils.text import slugify
from PIL import Image, ImageOps, UnidentifiedImageError

from sorter.apps.catalog.models import Character, Game
from sorter.apps.fanart.models import AlbumSetting, FanartSetting


@dataclass
class InboxImage:
    relative_path: str
    preview_url: str
    file_name: str
    created_at: datetime


@dataclass
class AlbumImage:
    relative_path: str
    preview_url: str
    file_url: str
    file_name: str
    full_path: str
    file_size_label: str
    created_at: datetime
    modified_at: datetime
    character_name: str = ""


@dataclass
class AlbumFolder:
    name: str
    relative_path: str
    folder_count: int
    image_count: int


@dataclass
class PlannedMove:
    entry: dict
    character: Character | None
    target_game: Game
    source_path: Path
    destination_dir: Path
    created_at: datetime
    date_token: str
    name_token: str
    destination_path: Path | None = None


class AlbumPathError(ValueError):
    pass


class AlbumRootNotConfigured(AlbumPathError):
    pass


class AlbumDirectoryNotFound(FileNotFoundError):
    pass


@dataclass
class AlbumCharacterFilterContext:
    is_visible: bool
    characters: list[str]
    game_label: str = ""



def is_supported_image(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in settings.SUPPORTED_IMAGE_EXTENSIONS



def normalize_filesystem_path(value: str) -> str:
    return str(Path(value.strip()).expanduser())



def format_file_size(num_bytes: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(num_bytes)
    unit_index = 0

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    return f"{size:.1f} {units[unit_index]}"



def get_fanart_paths() -> tuple[FanartSetting, Path, Path]:
    fanart_setting = FanartSetting.load()
    source_dir = fanart_setting.source_path
    destination_root = fanart_setting.destination_path
    source_dir.mkdir(parents=True, exist_ok=True)
    destination_root.mkdir(parents=True, exist_ok=True)
    settings.PREVIEW_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return fanart_setting, source_dir, destination_root



def get_album_root_paths() -> list[Path]:
    album_setting = AlbumSetting.load()
    return [Path(str(entry["path"])).expanduser() for entry in album_setting.normalized_entries]


def get_album_root_entries() -> list[dict[str, object]]:
    album_setting = AlbumSetting.load()
    return album_setting.normalized_entries



def clear_preview_cache() -> int:
    settings.PREVIEW_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    removed_count = 0

    for cached_file in settings.PREVIEW_CACHE_DIR.glob("*"):
        if not cached_file.is_file():
            continue
        cached_file.unlink(missing_ok=True)
        removed_count += 1

    return removed_count



def resolve_inbox_path(relative_path: str) -> Path:
    _, source_dir, _ = get_fanart_paths()
    resolved_path = (source_dir / Path(relative_path)).resolve()
    inbox_root = source_dir.resolve()
    resolved_path.relative_to(inbox_root)
    return resolved_path



def resolve_album_root(root_index: int) -> Path:
    root_entries = get_album_root_entries()
    if not root_entries:
        raise AlbumRootNotConfigured("No album paths have been configured yet.")
    if root_index < 0 or root_index >= len(root_entries):
        raise AlbumRootNotConfigured("Selected album path is invalid.")
    return Path(str(root_entries[root_index]["path"])).expanduser().resolve()


def resolve_album_root_entry(root_index: int) -> dict[str, object]:
    root_entries = get_album_root_entries()
    if not root_entries:
        raise AlbumRootNotConfigured("No album paths have been configured yet.")
    if root_index < 0 or root_index >= len(root_entries):
        raise AlbumRootNotConfigured("Selected album path is invalid.")
    return root_entries[root_index]



def resolve_album_path(root_index: int, relative_path: str = "") -> Path:
    album_root = resolve_album_root(root_index)
    resolved_path = (album_root / Path(relative_path)).resolve()
    resolved_path.relative_to(album_root)
    return resolved_path



def preview_cache_path(source_path: Path, cache_key: str) -> Path:
    stat = source_path.stat()
    digest_source = f"{cache_key}|{stat.st_mtime_ns}|{stat.st_size}|{settings.PREVIEW_MAX_SIZE}"
    digest = hashlib.sha256(digest_source.encode("utf-8")).hexdigest()
    return settings.PREVIEW_CACHE_DIR / f"{digest}.jpg"



def ensure_preview_for_path(source_path: Path, cache_key: str) -> Path:
    preview_path = preview_cache_path(source_path, cache_key)
    if preview_path.exists():
        return preview_path

    preview_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with Image.open(source_path) as image:
            prepared = ImageOps.exif_transpose(image)
            if prepared.mode not in ("RGB", "L"):
                prepared = prepared.convert("RGB")
            elif prepared.mode == "L":
                prepared = prepared.convert("RGB")

            prepared.thumbnail(settings.PREVIEW_MAX_SIZE, Image.Resampling.LANCZOS)
            prepared.save(preview_path, format="JPEG", quality=82, optimize=True)
    except (UnidentifiedImageError, OSError):
        return source_path

    return preview_path



def ensure_preview_image(relative_path: str) -> Path:
    source_path = resolve_inbox_path(relative_path)
    return ensure_preview_for_path(source_path, f"workspace:{relative_path}")



def ensure_album_preview_image(root_index: int, relative_path: str) -> Path:
    source_path = resolve_album_path(root_index, relative_path)
    return ensure_preview_for_path(source_path, f"album:{root_index}:{relative_path}")



def build_inbox_listing(staged_paths: set[str]) -> list[InboxImage]:
    images: list[InboxImage] = []
    fanart_setting, source_dir, _ = get_fanart_paths()
    iterator = source_dir.rglob("*") if fanart_setting.include_subfolders else source_dir.iterdir()

    for file_path in sorted(iterator):
        if not is_supported_image(file_path):
            continue

        relative_path = file_path.relative_to(source_dir).as_posix()
        if relative_path in staged_paths:
            continue

        stat = file_path.stat()
        created_at = datetime.fromtimestamp(stat.st_ctime)
        images.append(
            InboxImage(
                relative_path=relative_path,
                preview_url=f"/workspace-preview/{quote(relative_path, safe='/')}",
                file_name=file_path.name,
                created_at=created_at,
            )
        )

    return images



def build_album_listing(root_index: int, relative_dir: str = "") -> tuple[Path, Path, str, list[AlbumFolder], list[AlbumImage]]:
    album_root = resolve_album_root(root_index)
    current_dir = resolve_album_path(root_index, relative_dir)
    if not current_dir.exists() or not current_dir.is_dir():
        raise AlbumDirectoryNotFound("Album folder was not found.")

    normalized_relative = ""
    if current_dir != album_root:
        normalized_relative = current_dir.relative_to(album_root).as_posix()

    subfolders: list[AlbumFolder] = []
    images: list[AlbumImage] = []

    for child in sorted(current_dir.iterdir(), key=lambda item: item.name.lower()):
        if child.is_dir():
            nested_folders = 0
            nested_images = 0
            try:
                for nested in child.iterdir():
                    if nested.is_dir():
                        nested_folders += 1
                    elif is_supported_image(nested):
                        nested_images += 1
            except OSError:
                nested_folders = 0
                nested_images = 0

            relative_path = child.relative_to(album_root).as_posix()
            subfolders.append(
                AlbumFolder(
                    name=child.name,
                    relative_path=relative_path,
                    folder_count=nested_folders,
                    image_count=nested_images,
                )
            )
            continue

        if not is_supported_image(child):
            continue

        stat = child.stat()
        relative_path = child.relative_to(album_root).as_posix()
        images.append(
            AlbumImage(
                relative_path=relative_path,
                preview_url=f"/album-preview/{root_index}/{quote(relative_path, safe='/')}",
                file_url=f"/album-file/{root_index}/{quote(relative_path, safe='/')}",
                file_name=child.name,
                full_path=str(child),
                file_size_label=format_file_size(stat.st_size),
                created_at=datetime.fromtimestamp(stat.st_ctime),
                modified_at=datetime.fromtimestamp(stat.st_mtime),
            )
        )

    return album_root, current_dir, normalized_relative, subfolders, images


def _path_parts_lower(relative_dir: str) -> tuple[str, ...]:
    cleaned = relative_dir.strip().strip("/")
    if not cleaned:
        return ()
    return tuple(part.casefold() for part in Path(cleaned).parts)


def _game_path_candidates(game: Game) -> set[tuple[str, ...]]:
    candidates: set[tuple[str, ...]] = set()
    for raw_path in (game.output_path, game.display_path):
        parts = tuple(part.casefold() for part in Path(raw_path).parts if part)
        if parts:
            candidates.add(parts)
    return candidates


def _matches_path_prefix(current_parts: tuple[str, ...], candidate_parts: tuple[str, ...]) -> bool:
    return len(candidate_parts) <= len(current_parts) and current_parts[: len(candidate_parts)] == candidate_parts


def _matches_path_suffix(current_parts: tuple[str, ...], candidate_parts: tuple[str, ...]) -> bool:
    return len(candidate_parts) <= len(current_parts) and current_parts[-len(candidate_parts):] == candidate_parts


def find_album_game(relative_dir: str, album_root: Path | None = None) -> Game | None:
    current_parts = _path_parts_lower(relative_dir)
    root_parts = tuple(part.casefold() for part in album_root.parts) if album_root is not None else ()
    if not current_parts:
        current_parts = ()

    matched_game = None
    matched_depth = -1
    for game in Game.objects.select_related("main_folder").all():
        for game_parts in _game_path_candidates(game):
            matches_relative = bool(current_parts) and _matches_path_prefix(current_parts, game_parts)
            matches_root = bool(root_parts) and _matches_path_suffix(root_parts, game_parts)
            if not matches_relative and not matches_root:
                continue
            if len(game_parts) > matched_depth:
                matched_game = game
                matched_depth = len(game_parts)

    return matched_game


def _match_album_subfolder_game(root_game: Game, relative_dir: str) -> Game | None:
    relative_parts = Path(relative_dir).parts
    if not relative_parts:
        return None

    subfolder_token = relative_parts[0].casefold()
    for subfolder_game in root_game.subfolder_games.all():
        candidates = {
            subfolder_game.title.casefold(),
            subfolder_game.resolved_folder_name.casefold(),
        }
        if subfolder_game.folder_name:
            candidates.add(subfolder_game.folder_name.casefold())
        if subfolder_token in candidates:
            return subfolder_game

    return None


def resolve_album_game(root_index: int, relative_dir: str, album_root: Path | None = None) -> Game | None:
    album_entry = resolve_album_root_entry(root_index)
    root_game_id = album_entry.get("root_game_id")
    follow_subfolder_from_url = bool(album_entry.get("follow_subfolder_from_url", False))
    del album_root

    if root_game_id:
        root_game = (
            Game.objects.select_related("main_folder")
            .prefetch_related("subfolder_games")
            .filter(pk=root_game_id, main_folder__isnull=True)
            .first()
        )
        if root_game is not None:
            if follow_subfolder_from_url:
                matched_subfolder = _match_album_subfolder_game(root_game, relative_dir)
                if matched_subfolder is not None:
                    return matched_subfolder
            return root_game

    return None


def _looks_like_album_suffix(value: str) -> bool:
    if not value:
        return False
    compact = re.sub(r"[_\-\s]", "", value)
    return compact.isdigit()


def match_album_character_name(file_name: str, characters: list[Character]) -> str:
    stem = Path(file_name).stem.casefold()
    best_match = ""
    best_length = -1

    for character in characters:
        token = safe_name_component(character.name).casefold()
        if not token:
            continue

        if not stem.startswith(token):
            continue

        remainder = stem[len(token):]
        if not _looks_like_album_suffix(remainder):
            continue

        if len(token) > best_length:
            best_match = character.name
            best_length = len(token)

    return best_match


def prepare_album_character_filter(root_index: int, album_root: Path, relative_dir: str, images: list[AlbumImage]) -> AlbumCharacterFilterContext:
    matched_game = resolve_album_game(root_index, relative_dir, album_root)
    if matched_game is None:
        return AlbumCharacterFilterContext(is_visible=False, characters=[])

    if matched_game.use_folder_name_as_filename:
        return AlbumCharacterFilterContext(
            is_visible=False,
            characters=[],
            game_label=matched_game.display_path,
        )

    characters = list(Character.objects.filter(game_id=matched_game.character_owner_id).order_by("name"))
    if not characters:
        return AlbumCharacterFilterContext(
            is_visible=False,
            characters=[],
            game_label=matched_game.display_path,
        )

    for image in images:
        image.character_name = match_album_character_name(image.file_name, characters)

    return AlbumCharacterFilterContext(
        is_visible=True,
        characters=[character.name for character in characters],
        game_label=matched_game.display_path,
    )



def safe_name_component(value: str) -> str:
    compact = re.sub(r"\s+", "", value.strip())
    cleaned = re.sub(r"[^A-Za-z0-9_-]", "", compact)
    return cleaned or slugify(value).replace("-", "_") or "file"



def build_filename_prefix(character_name: str, date_token: str, separator: str) -> str:
    character_token = safe_name_component(character_name)
    return f"{character_token}{separator}{date_token}{separator}"



def next_sequence_number(destination_dir: Path, character_name: str, date_token: str, separator: str) -> int:
    prefix = build_filename_prefix(character_name, date_token, separator)
    max_number = 0

    for path in destination_dir.glob(f"{prefix}*"):
        stem = path.stem
        if not stem.startswith(prefix):
            continue

        suffix = stem[len(prefix):]
        if not suffix.isdigit():
            continue

        max_number = max(max_number, int(suffix))

    return max_number + 1



def process_staged_entries(staged_entries: list[dict]) -> list[dict]:
    processed: list[dict] = []
    planned_moves: list[PlannedMove] = []
    fanart_setting, _, destination_root = get_fanart_paths()

    for entry in staged_entries:
        try:
            target_game = Game.objects.select_related("main_folder").get(pk=entry["target_game_id"])
        except Game.DoesNotExist:
            processed.append(
                {
                    "status": "missing",
                    "source": entry["relative_path"],
                    "detail": "Target game was removed before processing.",
                }
            )
            continue

        character = None
        if entry.get("use_folder_name_as_filename"):
            name_token = target_game.resolved_folder_name
        else:
            try:
                character = Character.objects.select_related("game").get(pk=entry["character_id"])
            except Character.DoesNotExist:
                processed.append(
                    {
                        "status": "missing",
                        "source": entry["relative_path"],
                        "detail": "Character was removed from master data before processing.",
                    }
                )
                continue
            name_token = character.name

        try:
            source_path = resolve_inbox_path(entry["relative_path"])
        except ValueError:
            processed.append(
                {
                    "status": "missing",
                    "source": entry["relative_path"],
                    "detail": "File path is outside the inbox.",
                }
            )
            continue

        if not source_path.exists():
            processed.append(
                {
                    "status": "missing",
                    "source": entry["relative_path"],
                    "detail": "File was not found in the inbox.",
                }
            )
            continue

        destination_dir = destination_root / Path(target_game.output_path)
        created_at = datetime.fromtimestamp(source_path.stat().st_ctime)
        planned_moves.append(
            PlannedMove(
                entry=entry,
                character=character,
                target_game=target_game,
                source_path=source_path,
                destination_dir=destination_dir,
                created_at=created_at,
                date_token=fanart_setting.format_date_token(created_at),
                name_token=name_token,
            )
        )

    grouped_moves: dict[tuple[str, str], list[PlannedMove]] = defaultdict(list)
    for move in planned_moves:
        group_key = (str(move.destination_dir), safe_name_component(move.name_token))
        grouped_moves[group_key].append(move)

    for group in grouped_moves.values():
        group.sort(
            key=lambda move: (
                move.created_at,
                move.source_path.name.lower(),
                move.entry["relative_path"],
            )
        )

        moves_by_date: dict[str, list[PlannedMove]] = defaultdict(list)
        for move in group:
            moves_by_date[move.date_token].append(move)

        for date_token, date_moves in moves_by_date.items():
            destination_dir = date_moves[0].destination_dir
            destination_dir.mkdir(parents=True, exist_ok=True)
            sequence = next_sequence_number(
                destination_dir,
                date_moves[0].name_token,
                date_token,
                fanart_setting.filename_separator,
            )
            reserved_names: set[str] = set()
            filename_token = safe_name_component(date_moves[0].name_token)

            for move in date_moves:
                while True:
                    sequence_token = str(sequence).zfill(fanart_setting.sequence_padding)
                    destination_name = (
                        f"{filename_token}"
                        f"{fanart_setting.filename_separator}{date_token}"
                        f"{fanart_setting.filename_separator}{sequence_token}"
                        f"{move.source_path.suffix.lower()}"
                    )
                    destination_path = destination_dir / destination_name
                    if not destination_path.exists() and destination_name not in reserved_names:
                        move.destination_path = destination_path
                        reserved_names.add(destination_name)
                        sequence += 1
                        break
                    sequence += 1

    for move in planned_moves:
        if move.destination_path is None:
            processed.append(
                {
                    "status": "missing",
                    "source": move.entry["relative_path"],
                    "detail": "Could not build a destination filename.",
                }
            )
            continue

        move.destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(move.source_path), str(move.destination_path))
        processed.append(
            {
                "status": "moved",
                "source": move.entry["relative_path"],
                "destination": str(move.destination_path),
            }
        )

    return processed


