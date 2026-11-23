from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid
import zipfile
from collections import defaultdict
from contextlib import closing
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Callable

from django.conf import settings
from django.db import OperationalError, close_old_connections, connection
from PIL import Image

from sorter.apps.ui.text import get_page_ui_text

from .models import (
    ExtensionSetting,
    FileManageOperationJob,
    FileManageWorkspaceSetting,
    ImagesToPdfSetting,
    PdfToImagesSetting,
    RenameSetting,
    WebpToMp4Setting,
    ZipSetting,
)

try:
    import pypdfium2 as pdfium
except ImportError:  # pragma: no cover - optional dependency
    pdfium = None


# PDFium calls must be serialized across FileManage worker threads.
PDFIUM_LOCK = threading.Lock()
PREVIEW_LIMIT = 400
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp', '.jfif'}
ProgressCallback = Callable[[str, dict[str, Any]], None]
FILEMANAGE_JOB_LIMIT = 20
FILEMANAGE_LOG_LIMIT = 240
FILEMANAGE_DB_RETRY_COUNT = 8
FILEMANAGE_DB_RETRY_DELAY = 0.03


def natural_sort_key(value: str) -> list[Any]:
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r'(\d+)', value)]


def normalize_extensions(raw_value: str) -> tuple[str, ...]:
    tokens: list[str] = []
    for token in (raw_value or '').split(','):
        cleaned = token.strip().lower()
        if not cleaned:
            continue
        if not cleaned.startswith('.'):
            cleaned = f'.{cleaned}'
        if cleaned not in tokens:
            tokens.append(cleaned)
    return tuple(tokens)


def file_created_at(path: Path) -> datetime:
    return datetime.fromtimestamp(path.stat().st_ctime)


def file_modified_at(path: Path) -> datetime:
    return datetime.fromtimestamp(path.stat().st_mtime)


def format_file_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if size < 1024 or unit == 'TB':
            if unit == 'B':
                return f'{int(size)} {unit}'
            return f'{size:.1f} {unit}'
        size /= 1024
    return f'{int(size)} B'


def letter_sequence(count: int, start_letter: str) -> list[str]:
    start = max(0, min(25, ord((start_letter or 'a')[0].lower()) - ord('a')))
    sequence: list[str] = []
    for index in range(count):
        sequence.append(chr(ord('a') + ((start + index) % 26)))
    return sequence


def safe_available_path(path: Path) -> Path:
    if not path.exists():
        return path
    counter = 1
    while True:
        candidate = path.with_name(f'{path.stem}_{counter}{path.suffix}')
        if not candidate.exists():
            return candidate
        counter += 1


def load_filemanage_workspace() -> tuple[FileManageWorkspaceSetting, Path]:
    setting = FileManageWorkspaceSetting.load()
    root = setting.root_path
    root.mkdir(parents=True, exist_ok=True)
    return setting, root


def _with_filemanage_job_db_retry(callback: Callable[[], Any]) -> Any:
    for attempt in range(FILEMANAGE_DB_RETRY_COUNT):
        try:
            return callback()
        except OperationalError as exc:
            if "locked" not in str(exc).lower() or attempt == FILEMANAGE_DB_RETRY_COUNT - 1:
                raise
            time.sleep(FILEMANAGE_DB_RETRY_DELAY)
    raise RuntimeError("FileManage job retry exhausted")


def should_run_filemanage_job_inline() -> bool:
    return connection.vendor == "sqlite" and "test" in sys.argv


def _trim_filemanage_jobs() -> None:
    overflow = _with_filemanage_job_db_retry(lambda: FileManageOperationJob.objects.count()) - FILEMANAGE_JOB_LIMIT
    if overflow <= 0:
        return
    stale_ids = _with_filemanage_job_db_retry(
        lambda: list(
            FileManageOperationJob.objects.exclude(status="running")
            .order_by("updated_at")
            .values_list("pk", flat=True)[:overflow]
        )
    )
    if stale_ids:
        _with_filemanage_job_db_retry(lambda: FileManageOperationJob.objects.filter(pk__in=stale_ids).delete())


def create_filemanage_operation_job(operation_slug: str, operation_label: str) -> FileManageOperationJob:
    job = _with_filemanage_job_db_retry(
        lambda: FileManageOperationJob.objects.create(
            id=uuid.uuid4().hex,
            operation_slug=operation_slug,
            operation_label=operation_label,
        )
    )
    _trim_filemanage_jobs()
    return job


def build_filemanage_operation_job_item(payload: dict[str, Any], kind: str) -> dict[str, Any]:
    return {
        "kind": kind,
        "index": int(payload.get("index") or 0),
        "total": int(payload.get("total") or 0),
        "action": str(payload.get("action") or "Process"),
        "source": str(payload.get("source") or ""),
        "target": str(payload.get("target") or ""),
    }


def get_filemanage_operation_job_snapshot(job_id: str) -> dict[str, Any] | None:
    job = _with_filemanage_job_db_retry(
        lambda: (
            FileManageOperationJob.objects.filter(pk=job_id)
            .values(
                "id",
                "operation_slug",
                "operation_label",
                "status",
                "total_count",
                "completed_count",
                "current_item",
                "completed_items",
                "failed_items",
                "message",
                "error_message",
            )
            .first()
        )
    )
    if job is None:
        return None
    job["current_item"] = dict(job["current_item"]) if job["current_item"] else None
    job["completed_items"] = [dict(item) for item in (job["completed_items"] or [])]
    job["failed_items"] = [dict(item) for item in (job["failed_items"] or [])]
    return job


def _make_filemanage_progress_callback(job_id: str) -> ProgressCallback:
    def callback(event: str, payload: dict[str, Any]) -> None:
        job = _with_filemanage_job_db_retry(lambda: FileManageOperationJob.objects.filter(pk=job_id).first())
        if job is None:
            return
        if event == "job_started":
            job.total_count = int(payload.get("total") or 0)
        elif event == "item_started":
            job.current_item = build_filemanage_operation_job_item(payload, "running")
        elif event == "item_completed":
            job.completed_count = int(job.completed_count or 0) + 1
            job.current_item = None
            completed_items = list(job.completed_items or [])
            completed_items.append(build_filemanage_operation_job_item(payload, "completed"))
            job.completed_items = completed_items[-FILEMANAGE_LOG_LIMIT:]
        elif event == "item_failed":
            job.current_item = None
            failed_items = list(job.failed_items or [])
            failed_items.append(build_filemanage_operation_job_item(payload, "failed"))
            job.failed_items = failed_items[-FILEMANAGE_LOG_LIMIT:]
        _with_filemanage_job_db_retry(
            lambda: job.save(
                update_fields=[
                    "total_count",
                    "completed_count",
                    "current_item",
                    "completed_items",
                    "failed_items",
                    "updated_at",
                ]
            )
        )

    return callback


def _finalize_filemanage_operation_job(
    *,
    job_id: str,
    operation_slug: str,
    operation_label: str,
    result: dict[str, Any] | None = None,
    error_message: str = "",
    mode: str,
) -> None:
    job = _with_filemanage_job_db_retry(lambda: FileManageOperationJob.objects.filter(pk=job_id).first())
    if job is None:
        return

    filemanage_messages = get_page_ui_text("filemanage_messages", mode)
    result = result or {}
    job.current_item = None

    if error_message:
        job.status = "error"
        job.error_message = error_message
    else:
        job.completed_count = int(result.get("completed", job.completed_count or 0))
        job.total_count = int(result.get("planned", job.total_count or 0))
        if result.get("dependency_missing"):
            job.status = "dependency_missing"
            if operation_slug == "pdf-to-images":
                job.message = filemanage_messages["dependency_missing_pdf_to_images"]
            elif operation_slug == "webp-to-mp4":
                job.message = filemanage_messages["dependency_missing_webp_to_mp4"]
            else:
                job.message = filemanage_messages["dependency_missing_generic"]
        elif result.get("planned", 0) == 0:
            job.status = "empty"
            job.message = filemanage_messages["no_matching_items"]
        else:
            job.status = "completed"
            job.message = filemanage_messages["operation_completed"].format(
                label=operation_label,
                count=result.get("completed", 0),
            )

    _with_filemanage_job_db_retry(
        lambda: job.save(
            update_fields=[
                "status",
                "total_count",
                "completed_count",
                "current_item",
                "message",
                "error_message",
                "updated_at",
            ]
        )
    )


def _run_filemanage_operation_job(
    *,
    job_id: str,
    operation_slug: str,
    operation_label: str,
    executor: Callable[[Path, Any, ProgressCallback | None], dict[str, Any]],
    root: Path,
    setting_instance: Any,
    mode: str,
) -> None:
    close_old_connections()
    callback = _make_filemanage_progress_callback(job_id)
    try:
        result = executor(root, setting_instance, callback=callback)
    except Exception as exc:  # pragma: no cover - background execution guard
        _finalize_filemanage_operation_job(
            job_id=job_id,
            operation_slug=operation_slug,
            operation_label=operation_label,
            error_message=str(exc),
            mode=mode,
        )
        close_old_connections()
        return

    _finalize_filemanage_operation_job(
        job_id=job_id,
        operation_slug=operation_slug,
        operation_label=operation_label,
        result=result,
        mode=mode,
    )
    close_old_connections()


def start_filemanage_operation_job(
    *,
    operation_slug: str,
    operation_label: str,
    executor: Callable[[Path, Any, ProgressCallback | None], dict[str, Any]],
    root: Path,
    setting_instance: Any,
    mode: str,
) -> FileManageOperationJob:
    job = create_filemanage_operation_job(operation_slug, operation_label)
    if should_run_filemanage_job_inline():
        _run_filemanage_operation_job(
            job_id=job.pk,
            operation_slug=operation_slug,
            operation_label=operation_label,
            executor=executor,
            root=root,
            setting_instance=setting_instance,
            mode=mode,
        )
        return job

    worker = threading.Thread(
        target=_run_filemanage_operation_job,
        kwargs={
            "job_id": job.pk,
            "operation_slug": operation_slug,
            "operation_label": operation_label,
            "executor": executor,
            "root": root,
            "setting_instance": setting_instance,
            "mode": mode,
        },
        daemon=True,
    )
    worker.start()
    return job


def build_workspace_snapshot(root: Path) -> dict[str, Any]:
    folder_count = 0
    file_count = 0
    image_count = 0
    for path in root.rglob('*'):
        if path.is_dir():
            folder_count += 1
        elif path.is_file():
            file_count += 1
            if path.suffix.lower() in IMAGE_EXTENSIONS:
                image_count += 1
    return {
        'folder_count': folder_count,
        'file_count': file_count,
        'image_count': image_count,
    }


def iter_directories(root: Path, include_subfolders: bool) -> list[Path]:
    directories = [root]
    if include_subfolders:
        directories.extend(path for path in root.rglob('*') if path.is_dir())
    return sorted(directories, key=lambda item: natural_sort_key(item.relative_to(root).as_posix() if item != root else item.name.lower()))


def list_folder_files(folder: Path) -> list[Path]:
    files = [path for path in folder.iterdir() if path.is_file() and path.name.lower() != 'desktop.ini']
    return files


def list_all_files(root: Path, include_subfolders: bool) -> list[Path]:
    files: list[Path] = []
    for folder in iter_directories(root, include_subfolders):
        files.extend(list_folder_files(folder))
    return files


def resolve_relative(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.name


def emit_progress(callback: ProgressCallback | None, event: str, **payload: Any) -> None:
    if callback is not None:
        callback(event, payload)


def progress_labels(root: Path, plan: dict[str, Any]) -> tuple[str, str]:
    source_path = plan.get('display_path')
    if not isinstance(source_path, Path):
        source_path = plan['source_path']

    target_path = plan.get('target_path')
    if isinstance(target_path, Path):
        try:
            target_label = resolve_relative(root, target_path)
        except Exception:
            target_label = str(target_path)
    else:
        target_label = str(target_path or '')

    return resolve_relative(root, source_path), target_label


def build_preview_from_plans(root: Path, plans: list[dict[str, Any]]) -> dict[str, Any]:
    items = []
    for plan in plans[:PREVIEW_LIMIT]:
        display_path = plan.get('display_path', plan.get('source_path'))
        stat_path = display_path if isinstance(display_path, Path) else plan['source_path']
        is_dir = stat_path.is_dir()
        created_at = file_created_at(stat_path)
        modified_at = file_modified_at(stat_path)
        size_label = '--' if is_dir else format_file_size(stat_path.stat().st_size)
        items.append(
            {
                'title': plan.get('title') or display_path.name,
                'source': resolve_relative(root, display_path),
                'target': resolve_relative(root, plan['target_path']) if isinstance(plan['target_path'], Path) and plan['target_path'].is_absolute() and str(plan['target_path']).startswith(str(root)) else str(plan['target_path']),
                'folder': resolve_relative(root, plan.get('folder_path', display_path.parent if isinstance(display_path, Path) else root)),
                'action': plan.get('action', 'Process'),
                'note': plan.get('note', ''),
                'created_at': created_at,
                'created_label': created_at.strftime('%d/%m/%Y %H:%M'),
                'modified_at': modified_at,
                'created_ts': int(created_at.timestamp()),
                'size_label': size_label,
                'kind': 'folder' if is_dir else 'file',
                'searchable': f"{display_path.name} {resolve_relative(root, display_path.parent if isinstance(display_path, Path) else root)} {plan.get('note', '')}".lower(),
            }
        )
    impacted_folders = {str(plan.get('folder_path', plan.get('source_path').parent)) for plan in plans}
    return {
        'items': items,
        'total_count': len(plans),
        'folder_count': len(impacted_folders),
        'truncated': len(plans) > PREVIEW_LIMIT,
    }


def allocate_unique_targets(plans: list[dict[str, Any]]) -> None:
    grouped: dict[Path, list[dict[str, Any]]] = defaultdict(list)
    for plan in plans:
        grouped[plan['target_dir']].append(plan)

    for target_dir, entries in grouped.items():
        target_dir.mkdir(parents=True, exist_ok=True)
        occupied = {path.name.lower() for path in target_dir.iterdir() if path.is_file()}
        source_names_in_same_dir = {
            plan['source_path'].name.lower()
            for plan in entries
            if plan['source_path'].parent == target_dir
        }
        occupied -= source_names_in_same_dir
        reserved: set[str] = set()

        for plan in entries:
            candidate = plan['candidate_name']
            stem = Path(candidate).stem
            suffix = Path(candidate).suffix
            unique_name = candidate
            counter = 1
            while unique_name.lower() in occupied or unique_name.lower() in reserved:
                unique_name = f'{stem}_{counter}{suffix}'
                counter += 1
            reserved.add(unique_name.lower())
            plan['target_path'] = target_dir / unique_name


def apply_rename_like_plans(root: Path, plans: list[dict[str, Any]], callback: ProgressCallback | None = None) -> int:
    temp_pairs: list[tuple[Path, Path, dict[str, Any]]] = []
    total = len(plans)
    for index, plan in enumerate(plans, start=1):
        source_path = plan['source_path']
        if not source_path.exists():
            continue
        source_label, target_label = progress_labels(root, plan)
        emit_progress(
            callback,
            'item_started',
            index=index,
            total=total,
            action=plan.get('action', 'Process'),
            source=source_label,
            target=target_label,
        )
        temp_path = source_path.with_name(f'__fm_tmp__{index - 1}_{source_path.name}')
        os.rename(source_path, temp_path)
        temp_pairs.append((temp_path, plan['target_path'], plan))

    completed = 0
    for index, (temp_path, target_path, plan) in enumerate(temp_pairs, start=1):
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(temp_path), str(target_path))
        completed += 1
        source_label, target_label = progress_labels(root, plan)
        emit_progress(
            callback,
            'item_completed',
            index=index,
            total=total,
            action=plan.get('action', 'Process'),
            source=source_label,
            target=target_label,
        )
    return completed


def replace_text_with_scope(name: str, search_text: str, replacement: str, scope: str, occurrence: str) -> str:
    if not search_text:
        return name

    target = Path(name).stem if scope == 'stem' else name
    suffix = '' if scope == 'full_name' else Path(name).suffix

    if occurrence == 'first':
        updated = target.replace(search_text, replacement, 1)
    elif occurrence == 'last':
        head, marker, tail = target.rpartition(search_text)
        updated = f'{head}{replacement}{tail}' if marker else target
    else:
        updated = target.replace(search_text, replacement)

    if scope == 'full_name':
        return updated
    return f'{updated}{suffix}'


def trim_name_by_delimiter(name: str, delimiter: str, action: str, occurrence: str, include_delimiter: bool) -> str:
    stem = Path(name).stem
    suffix = Path(name).suffix
    if not delimiter:
        return name

    index = stem.find(delimiter) if occurrence == 'first' else stem.rfind(delimiter)
    if index == -1:
        return name

    delimiter_end = index + len(delimiter)
    if action in {'keep_before', 'remove_after'}:
        new_stem = stem[:delimiter_end] if include_delimiter else stem[:index]
    else:
        new_stem = stem[index:] if include_delimiter else stem[delimiter_end:]
    return f'{new_stem}{suffix}'


def plan_text_transform_actions(setting: RenameSetting, directories: list[Path], extensions: tuple[str, ...]) -> list[dict[str, Any]]:
    plans: list[dict[str, Any]] = []
    files_by_folder: dict[Path, list[Path]] = {}
    active_directories: list[Path] = []
    for folder in directories:
        files = [path for path in list_folder_files(folder) if path_matches_extensions(path, extensions)]
        if not files:
            continue
        files_by_folder[folder] = files
        active_directories.append(folder)

    if setting.per_folder_alpha_mode and setting.text_action in {'replace', 'add_prefix', 'add_suffix'}:
        ordered_directories = active_directories if setting.order_ascending else list(reversed(active_directories))
        replacements = letter_sequence(len(ordered_directories), setting.start_letter)
        folder_replacements = {folder: replacements[index] for index, folder in enumerate(ordered_directories)}
    else:
        folder_replacements = {}

    for folder in active_directories:
        files = files_by_folder[folder]
        sorted_files = sorted(files, key=lambda item: natural_sort_key(item.name.lower()))
        if not setting.order_ascending:
            sorted_files = list(reversed(sorted_files))

        replacement = folder_replacements.get(folder, setting.replace_text)
        for file_path in sorted_files:
            if setting.text_action in {'replace', 'remove'}:
                scope_target = file_path.stem if setting.match_scope == 'stem' else file_path.name
                if setting.search_text and setting.search_text not in scope_target:
                    continue
                replace_with = replacement if setting.text_action == 'replace' else ''
                new_name = replace_text_with_scope(file_path.name, setting.search_text, replace_with, setting.match_scope, setting.match_occurrence)
                note = replace_with if replace_with else 'Remove matched text'
            elif setting.text_action == 'add_prefix':
                prefix_text = folder_replacements.get(folder, setting.added_text)
                new_name = f'{prefix_text}{file_path.name}'
                note = f'Prefix: {prefix_text}' if prefix_text else 'Add prefix'
            else:
                suffix_text = folder_replacements.get(folder, setting.added_text)
                new_name = f'{file_path.stem}{suffix_text}{file_path.suffix}'
                note = f'Suffix: {suffix_text}' if suffix_text else 'Add suffix'

            if new_name == file_path.name:
                continue
            plans.append(
                {
                    'source_path': file_path,
                    'display_path': file_path,
                    'folder_path': folder,
                    'candidate_name': new_name,
                    'target_dir': folder,
                    'action': 'Rename',
                    'note': note,
                }
            )
    return plans


def plan_trim_delimiter_actions(setting: RenameSetting, directories: list[Path], extensions: tuple[str, ...]) -> list[dict[str, Any]]:
    plans: list[dict[str, Any]] = []
    for folder in directories:
        files = [path for path in list_folder_files(folder) if path_matches_extensions(path, extensions)]
        if not files:
            continue

        sorted_files = sorted(files, key=lambda item: natural_sort_key(item.name.lower()))
        if not setting.order_ascending:
            sorted_files = list(reversed(sorted_files))

        for file_path in sorted_files:
            new_name = trim_name_by_delimiter(
                file_path.name,
                setting.trim_delimiter,
                setting.trim_action,
                setting.delimiter_occurrence,
                setting.include_delimiter,
            )
            if new_name == file_path.name:
                continue
            plans.append(
                {
                    'source_path': file_path,
                    'display_path': file_path,
                    'folder_path': folder,
                    'candidate_name': new_name,
                    'target_dir': folder,
                    'action': 'Trim',
                    'note': setting.trim_delimiter or 'Delimiter trim',
                }
            )
    return plans


def plan_numbering_actions(setting: RenameSetting, directories: list[Path], extensions: tuple[str, ...]) -> list[dict[str, Any]]:
    plans: list[dict[str, Any]] = []

    if setting.number_action == 'swap_numbers':
        for folder in directories:
            files = [path for path in list_folder_files(folder) if path_matches_extensions(path, extensions)]
            if not files:
                continue

            sorted_files = sorted(files, key=lambda item: natural_sort_key(item.name.lower()))
            if not setting.order_ascending:
                sorted_files = list(reversed(sorted_files))

            numbered_files: list[tuple[Path, int]] = []
            for file_path in sorted_files:
                extracted = extract_number_from_name(file_path.name, setting.number_width)
                if extracted is None:
                    continue
                numbered_files.append((file_path, extracted))
            if not numbered_files:
                continue
            max_number = max(number for _, number in numbered_files)
            for file_path, number in numbered_files:
                new_name = replace_number_in_name(file_path.name, setting.number_width, max_number - number)
                if new_name == file_path.name:
                    continue
                plans.append(
                    {
                        'source_path': file_path,
                        'display_path': file_path,
                        'folder_path': folder,
                        'candidate_name': new_name,
                        'target_dir': folder,
                        'action': 'Swap numbers',
                        'note': f'max {max_number:0{setting.number_width}d}',
                    }
                )
        return plans

    counter = setting.start_number
    for folder in directories:
        if setting.reset_per_folder:
            counter = setting.start_number

        files = [path for path in list_folder_files(folder) if path_matches_extensions(path, extensions)]
        if not files:
            continue
        sorted_files = sorted(files, key=lambda item: natural_sort_key(item.name.lower()))
        if not setting.order_ascending:
            sorted_files = list(reversed(sorted_files))

        for file_path in sorted_files:
            number_label = f'{counter:0{setting.number_width}d}'
            separator = setting.number_separator or ''
            if setting.number_action == 'add_prefix_sequence':
                new_name = f'{number_label}{separator}{file_path.name}'
                note = f'Prefix #{number_label}'
            elif setting.number_action == 'replace_with_sequence':
                new_name = f'{number_label}{file_path.suffix}'
                note = f'Replace with #{number_label}'
            else:
                new_name = f'{file_path.stem}{separator}{number_label}{file_path.suffix}'
                note = f'Suffix #{number_label}'
            if new_name != file_path.name:
                plans.append(
                    {
                        'source_path': file_path,
                        'display_path': file_path,
                        'folder_path': folder,
                        'candidate_name': new_name,
                        'target_dir': folder,
                        'action': 'Numbering',
                        'note': note,
                    }
                )
            counter += setting.increment
    return plans


def plan_rename_actions(root: Path, setting: RenameSetting) -> list[dict[str, Any]]:
    extensions = normalize_extensions(setting.target_extensions)
    directories = iter_directories(root, setting.include_subfolders)

    if setting.workflow == 'trim_delimiter':
        plans = plan_trim_delimiter_actions(setting, directories, extensions)
    elif setting.workflow == 'numbering':
        plans = plan_numbering_actions(setting, directories, extensions)
    else:
        plans = plan_text_transform_actions(setting, directories, extensions)

    allocate_unique_targets(plans)
    return plans


def execute_rename_actions(root: Path, setting: RenameSetting, callback: ProgressCallback | None = None) -> dict[str, Any]:
    plans = plan_rename_actions(root, setting)
    emit_progress(callback, 'job_started', total=len(plans), operation='rename-files')
    completed = apply_rename_like_plans(root, plans, callback)
    return {'completed': completed, 'planned': len(plans)}


def path_matches_extensions(path: Path, extensions: tuple[str, ...]) -> bool:
    return not extensions or path.suffix.lower() in extensions


def plan_extension_actions(root: Path, setting: ExtensionSetting) -> list[dict[str, Any]]:
    plans: list[dict[str, Any]] = []
    for file_path in list_all_files(root, setting.include_subfolders):
        if file_path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        if setting.old_extension != '.all' and file_path.suffix.lower() != setting.old_extension.lower():
            continue
        new_extension = setting.new_extension.lower()
        if not new_extension.startswith('.'):
            new_extension = f'.{new_extension}'
        if file_path.suffix.lower() == new_extension:
            continue
        candidate_name = f'{file_path.stem}{new_extension}'
        plans.append(
            {
                'source_path': file_path,
                'display_path': file_path,
                'folder_path': file_path.parent,
                'candidate_name': candidate_name,
                'target_dir': file_path.parent,
                'action': 'Convert extension',
                'note': f'{file_path.suffix.lower()} ? {new_extension}',
            }
        )
    allocate_unique_targets(plans)
    return plans


def execute_extension_actions(root: Path, setting: ExtensionSetting, callback: ProgressCallback | None = None) -> dict[str, Any]:
    plans = plan_extension_actions(root, setting)
    emit_progress(callback, 'job_started', total=len(plans), operation='change-file-extension')
    completed = 0
    total = len(plans)
    for index, plan in enumerate(plans, start=1):
        source_path = plan['source_path']
        target_path = plan['target_path']
        if not source_path.exists():
            continue
        source_label, target_label = progress_labels(root, plan)
        emit_progress(callback, 'item_started', index=index, total=total, action=plan.get('action', 'Process'), source=source_label, target=target_label)
        with Image.open(source_path) as image:
            if target_path.suffix.lower() in {'.jpg', '.jpeg'} and image.mode == 'RGBA':
                image = image.convert('RGB')
            elif target_path.suffix.lower() in {'.jpg', '.jpeg'}:
                image = image.convert('RGB')
            image.save(target_path)
        if target_path.resolve() != source_path.resolve():
            source_path.unlink(missing_ok=True)
        completed += 1
        emit_progress(callback, 'item_completed', index=index, total=total, action=plan.get('action', 'Process'), source=source_label, target=target_label)
    return {'completed': completed, 'planned': len(plans)}


def plan_zip_actions(root: Path, setting: ZipSetting) -> list[dict[str, Any]]:
    plans: list[dict[str, Any]] = []
    for file_path in list_all_files(root, setting.include_subfolders):
        if file_path.suffix.lower() != '.zip':
            continue
        target_path = safe_available_path(file_path.with_suffix(''))
        plans.append(
            {
                'source_path': file_path,
                'display_path': file_path,
                'folder_path': file_path.parent,
                'target_path': target_path,
                'action': 'Extract ZIP',
                'note': 'Archive extraction',
            }
        )
    return plans


def execute_zip_actions(root: Path, setting: ZipSetting, callback: ProgressCallback | None = None) -> dict[str, Any]:
    plans = plan_zip_actions(root, setting)
    emit_progress(callback, 'job_started', total=len(plans), operation='extract-zip')
    completed = 0
    total = len(plans)
    for index, plan in enumerate(plans, start=1):
        source_path = plan['source_path']
        target_path = plan['target_path']
        if not source_path.exists():
            continue
        source_label, target_label = progress_labels(root, plan)
        emit_progress(callback, 'item_started', index=index, total=total, action=plan.get('action', 'Process'), source=source_label, target=target_label)
        target_path.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(source_path, 'r') as archive:
            archive.extractall(target_path)
        if setting.delete_archives_after_extract:
            source_path.unlink(missing_ok=True)
        completed += 1
        emit_progress(callback, 'item_completed', index=index, total=total, action=plan.get('action', 'Process'), source=source_label, target=target_label)
    return {'completed': completed, 'planned': len(plans)}


def plan_images_to_pdf_actions(root: Path, setting: ImagesToPdfSetting) -> list[dict[str, Any]]:
    plans: list[dict[str, Any]] = []
    extensions = normalize_extensions(setting.image_extensions)
    for folder in iter_directories(root, setting.include_subfolders):
        image_files = [path for path in list_folder_files(folder) if path_matches_extensions(path, extensions)]
        if not image_files:
            continue
        output_path = folder / f'{folder.name}.pdf'
        plans.append(
            {
                'source_path': folder,
                'display_path': folder,
                'folder_path': folder,
                'target_path': output_path,
                'image_files': sorted(image_files, key=lambda item: natural_sort_key(item.name.lower())),
                'action': 'Merge images',
                'note': f'{len(image_files)} image(s)',
                'title': folder.name,
            }
        )
    return plans


def prepare_pdf_images(image_paths: list[Path], setting: ImagesToPdfSetting) -> list[Image.Image]:
    rgb_images: list[Image.Image] = []
    max_width = 0
    max_height = 0
    for path in image_paths:
        with Image.open(path) as image:
            converted = image.convert('RGB')
            rgb_images.append(converted.copy())
            max_width = max(max_width, converted.width)
            max_height = max(max_height, converted.height)

    if not setting.fit_to_largest or not rgb_images:
        return rgb_images

    fitted_images: list[Image.Image] = []
    for image in rgb_images:
        if image.size == (max_width, max_height):
            fitted_images.append(image)
            continue
        if setting.upscale_method == 'pad':
            canvas = Image.new('RGB', (max_width, max_height), 'white')
            left = (max_width - image.width) // 2
            top = (max_height - image.height) // 2
            canvas.paste(image, (left, top))
            image.close()
            fitted_images.append(canvas)
            continue
        scale = min(max_width / image.width, max_height / image.height)
        new_size = (max(1, int(image.width * scale)), max(1, int(image.height * scale)))
        resized = image.resize(new_size, Image.LANCZOS)
        canvas = Image.new('RGB', (max_width, max_height), 'white')
        left = (max_width - resized.width) // 2
        top = (max_height - resized.height) // 2
        canvas.paste(resized, (left, top))
        image.close()
        resized.close()
        fitted_images.append(canvas)
    return fitted_images


def reencode_images_for_pdf_quality(images: list[Image.Image], quality: int) -> list[Image.Image]:
    if quality >= 100:
        return images

    reencoded: list[Image.Image] = []
    for image in images:
        buffer = BytesIO()
        image.save(buffer, format='JPEG', quality=quality)
        buffer.seek(0)
        with Image.open(buffer) as compressed:
            reencoded.append(compressed.copy())
        buffer.close()
        image.close()
    return reencoded


def execute_images_to_pdf_actions(root: Path, setting: ImagesToPdfSetting, callback: ProgressCallback | None = None) -> dict[str, Any]:
    plans = plan_images_to_pdf_actions(root, setting)
    emit_progress(callback, 'job_started', total=len(plans), operation='images-to-pdf')
    completed = 0
    total = len(plans)
    for index, plan in enumerate(plans, start=1):
        image_paths = plan['image_files']
        prepared = prepare_pdf_images(image_paths, setting)
        if not prepared:
            continue
        source_label, target_label = progress_labels(root, plan)
        emit_progress(callback, 'item_started', index=index, total=total, action=plan.get('action', 'Process'), source=source_label, target=target_label)
        prepared = reencode_images_for_pdf_quality(prepared, setting.jpg_quality)
        output_path = plan['target_path']
        output_path.parent.mkdir(parents=True, exist_ok=True)
        first_image, remaining_images = prepared[0], prepared[1:]
        first_image.save(output_path, save_all=True, append_images=remaining_images)
        for image in prepared:
            image.close()
        if setting.delete_source_images:
            for source_path in image_paths:
                source_path.unlink(missing_ok=True)
        completed += 1
        emit_progress(callback, 'item_completed', index=index, total=total, action=plan.get('action', 'Process'), source=source_label, target=target_label)
    return {'completed': completed, 'planned': len(plans), 'dependency_missing': False}


def plan_pdf_to_images_actions(root: Path, setting: PdfToImagesSetting) -> list[dict[str, Any]]:
    plans: list[dict[str, Any]] = []
    for file_path in list_all_files(root, setting.include_subfolders):
        if file_path.suffix.lower() != '.pdf':
            continue
        target_path = safe_available_path(file_path.with_suffix(''))
        plans.append(
            {
                'source_path': file_path,
                'display_path': file_path,
                'folder_path': file_path.parent,
                'target_path': target_path,
                'action': 'Export pages',
                'note': 'PDF pages to images',
            }
        )
    return plans


def execute_pdf_to_images_actions(root: Path, setting: PdfToImagesSetting, callback: ProgressCallback | None = None) -> dict[str, Any]:
    if pdfium is None:
        return {'completed': 0, 'planned': 0, 'dependency_missing': True}
    plans = plan_pdf_to_images_actions(root, setting)
    emit_progress(callback, 'job_started', total=len(plans), operation='pdf-to-images')
    completed = 0
    total = len(plans)
    for index, plan in enumerate(plans, start=1):
        source_path = plan['source_path']
        target_path = plan['target_path']
        source_label, target_label = progress_labels(root, plan)
        emit_progress(callback, 'item_started', index=index, total=total, action=plan.get('action', 'Process'), source=source_label, target=target_label)
        target_path.mkdir(parents=True, exist_ok=True)
        extension = setting.image_format.lower()
        with PDFIUM_LOCK, closing(pdfium.PdfDocument(source_path)) as document:
            for page_number in range(len(document)):
                output_name = target_path / f'page_{page_number + 1}.{extension}'
                with closing(document[page_number]) as page, closing(page.render()) as bitmap:
                    with bitmap.to_pil() as image:
                        if extension == 'jpg':
                            image.save(output_name, 'JPEG', quality=setting.jpeg_quality)
                        else:
                            image.save(output_name, extension.upper())
        if setting.delete_source_pdfs:
            source_path.unlink(missing_ok=True)
        completed += 1
        emit_progress(callback, 'item_completed', index=index, total=total, action=plan.get('action', 'Process'), source=source_label, target=target_label)
    return {'completed': completed, 'planned': len(plans), 'dependency_missing': False}


def ffmpeg_command() -> str | None:
    return shutil.which("ffmpeg")


def is_animated_webp(path: Path) -> bool:
    try:
        with Image.open(path) as image:
            return getattr(image, "n_frames", 1) > 1
    except Exception:
        return False


def run_ffmpeg_command(command: list[str]) -> None:
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-2000:] or "ffmpeg failed")


def convert_static_webp_to_mp4(source_path: Path, target_path: Path, setting: WebpToMp4Setting) -> None:
    ffmpeg_bin = ffmpeg_command()
    if not ffmpeg_bin:
        raise RuntimeError("ffmpeg is not available")
    command = [
        ffmpeg_bin,
        "-y" if setting.overwrite_existing else "-n",
        "-i",
        str(source_path),
        "-movflags",
        "faststart",
        "-pix_fmt",
        "yuv420p",
        "-vf",
        "scale=trunc(iw/2)*2:trunc(ih/2)*2",
        "-c:v",
        "libx264",
        "-preset",
        setting.preset,
        "-crf",
        str(setting.crf),
        str(target_path),
    ]
    run_ffmpeg_command(command)


def convert_animated_webp_to_mp4(source_path: Path, target_path: Path, setting: WebpToMp4Setting) -> None:
    ffmpeg_bin = ffmpeg_command()
    if not ffmpeg_bin:
        raise RuntimeError("ffmpeg is not available")
    temp_dir = Path(tempfile.mkdtemp(prefix="webp_frames_"))
    list_path = temp_dir / "list.txt"
    try:
        with Image.open(source_path) as image:
            frame_count = getattr(image, "n_frames", 1)
            if frame_count <= 1:
                convert_static_webp_to_mp4(source_path, target_path, setting)
                return

            frame_paths: list[Path] = []
            durations: list[float] = []
            for index in range(frame_count):
                image.seek(index)
                frame = image.convert("RGBA")
                frame_path = temp_dir / f"frame_{index:05d}.png"
                frame.save(frame_path, "PNG")
                frame.close()
                frame_paths.append(frame_path)
                duration_ms = image.info.get("duration", 40)
                if not isinstance(duration_ms, (int, float)) or duration_ms <= 0:
                    duration_ms = 40
                durations.append(float(duration_ms) / 1000.0)

        with list_path.open("w", encoding="utf-8") as handle:
            for frame_path, duration in zip(frame_paths, durations):
                handle.write(f"file '{frame_path.name}'\n")
                handle.write(f"duration {duration}\n")
            if frame_paths:
                handle.write(f"file '{frame_paths[-1].name}'\n")

        command = [
            ffmpeg_bin,
            "-y" if setting.overwrite_existing else "-n",
            "-f",
            "concat",
            "-i",
            str(list_path),
            "-movflags",
            "faststart",
            "-pix_fmt",
            "yuv420p",
            "-vf",
            "scale=trunc(iw/2)*2:trunc(ih/2)*2",
            "-c:v",
            "libx264",
            "-preset",
            setting.preset,
            "-crf",
            str(setting.crf),
            str(target_path),
        ]
        run_ffmpeg_command(command)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def plan_webp_to_mp4_actions(root: Path, setting: WebpToMp4Setting) -> list[dict[str, Any]]:
    plans: list[dict[str, Any]] = []
    source_files = list_all_files(root, setting.include_subfolders)
    for file_path in source_files:
        if file_path.suffix.lower() != ".webp":
            continue
        relative_parent = file_path.parent.relative_to(root) if file_path.parent != root else Path()
        target_dir = setting.output_path / relative_parent
        target_path = target_dir / f"{file_path.stem}.mp4"
        animated = is_animated_webp(file_path)
        overwrite_note = "overwrite" if setting.overwrite_existing else ("skip existing" if target_path.exists() else "new file")
        plans.append(
            {
                "source_path": file_path,
                "display_path": file_path,
                "folder_path": file_path.parent,
                "target_path": target_path,
                "action": "Convert WebP",
                "note": f"{'animated' if animated else 'static'} webp ? {overwrite_note}",
                "mode": "animated" if animated else "static",
                "title": file_path.name,
            }
        )
    return plans


def execute_webp_to_mp4_actions(root: Path, setting: WebpToMp4Setting, callback: ProgressCallback | None = None) -> dict[str, Any]:
    if not ffmpeg_command():
        return {"completed": 0, "planned": 0, "dependency_missing": True}

    plans = plan_webp_to_mp4_actions(root, setting)
    emit_progress(callback, 'job_started', total=len(plans), operation='webp-to-mp4')
    completed = 0
    total = len(plans)
    for index, plan in enumerate(plans, start=1):
        source_path = plan['source_path']
        target_path = plan['target_path']
        source_label, target_label = progress_labels(root, plan)
        if target_path.exists() and not setting.overwrite_existing:
            emit_progress(callback, 'item_completed', index=index, total=total, action='Skip existing', source=source_label, target=target_label)
            completed += 1
            continue
        emit_progress(callback, 'item_started', index=index, total=total, action=plan.get('action', 'Process'), source=source_label, target=target_label)
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            if plan.get('mode') == 'animated':
                convert_animated_webp_to_mp4(source_path, target_path, setting)
            else:
                convert_static_webp_to_mp4(source_path, target_path, setting)
            completed += 1
            emit_progress(callback, 'item_completed', index=index, total=total, action=plan.get('action', 'Process'), source=source_label, target=target_label)
        except Exception:
            emit_progress(callback, 'item_failed', index=index, total=total, action=plan.get('action', 'Process'), source=source_label, target=target_label)
            raise
    return {'completed': completed, 'planned': len(plans), 'dependency_missing': False}


def extract_number_from_name(name: str, width: int) -> int | None:
    match = re.search(rf'(\d{{{width}}})', Path(name).stem)
    if not match:
        return None
    return int(match.group(1))


def replace_number_in_name(name: str, width: int, new_number: int) -> str:
    stem = Path(name).stem
    suffix = Path(name).suffix
    new_stem = re.sub(rf'(\d{{{width}}})', f'{new_number:0{width}d}', stem, count=1)
    return f'{new_stem}{suffix}'


def preview_rename_operation(root: Path) -> dict[str, Any]:
    return build_preview_from_plans(root, plan_rename_actions(root, RenameSetting.load()))


def preview_extension_operation(root: Path) -> dict[str, Any]:
    return build_preview_from_plans(root, plan_extension_actions(root, ExtensionSetting.load()))


def preview_zip_operation(root: Path) -> dict[str, Any]:
    return build_preview_from_plans(root, plan_zip_actions(root, ZipSetting.load()))


def preview_images_to_pdf_operation(root: Path) -> dict[str, Any]:
    return build_preview_from_plans(root, plan_images_to_pdf_actions(root, ImagesToPdfSetting.load()))


def preview_pdf_to_images_operation(root: Path) -> dict[str, Any]:
    return build_preview_from_plans(root, plan_pdf_to_images_actions(root, PdfToImagesSetting.load()))


def preview_webp_to_mp4_operation(root: Path) -> dict[str, Any]:
    return build_preview_from_plans(root, plan_webp_to_mp4_actions(root, WebpToMp4Setting.load()))





