from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable

from django.contrib import messages
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from .forms import (
    ExtensionSettingForm,
    FileManageWorkspaceSettingForm,
    ImagesToPdfSettingForm,
    PdfToImagesSettingForm,
    RenameSettingForm,
    WebpToMp4SettingForm,
    ZipSettingForm,
)
from .services import (
    build_workspace_snapshot,
    execute_extension_actions,
    execute_images_to_pdf_actions,
    execute_pdf_to_images_actions,
    execute_rename_actions,
    execute_webp_to_mp4_actions,
    execute_zip_actions,
    get_filemanage_operation_job_snapshot,
    load_filemanage_workspace,
    preview_extension_operation,
    preview_images_to_pdf_operation,
    preview_pdf_to_images_operation,
    preview_rename_operation,
    preview_webp_to_mp4_operation,
    preview_zip_operation,
    start_filemanage_operation_job,
)
from .models import (
    ExtensionSetting,
    FileManageWorkspaceSetting,
    ImagesToPdfSetting,
    PdfToImagesSetting,
    RenameSetting,
    WebpToMp4Setting,
    ZipSetting,
)
from sorter.apps.ui.text import (
    get_current_language_mode,
    get_filemanage_run_button_label,
    get_filemanage_setting_helper,
    get_page_text,
    get_page_ui_text,
)


@dataclass(frozen=True)
class OperationConfig:
    slug: str
    label: str
    description: str
    route_name: str
    settings_slug: str
    settings_label: str
    button_label: str
    preview_builder: Callable[[Path], dict[str, Any]]
    executor: Callable[..., dict[str, Any]]
    setting_model: Any


@dataclass(frozen=True)
class SettingConfig:
    slug: str
    label: str
    title: str
    description: str
    route_name: str
    model: Any
    form_class: Any
    active_nav: str
    helper_title: str
    helper_lines: list[str]


FILEMANAGE_OPERATION_CONFIGS: dict[str, OperationConfig] = {
    "rename-files": OperationConfig(
        "rename-files",
        "",
        "",
        "filemanage_rename_files",
        "rename",
        "",
        "",
        preview_rename_operation,
        execute_rename_actions,
        RenameSetting,
    ),
    "change-file-extension": OperationConfig(
        "change-file-extension",
        "",
        "",
        "filemanage_change_file_extension",
        "extension",
        "",
        "",
        preview_extension_operation,
        execute_extension_actions,
        ExtensionSetting,
    ),
    "extract-zip": OperationConfig(
        "extract-zip",
        "",
        "",
        "filemanage_extract_zip",
        "zip",
        "",
        "",
        preview_zip_operation,
        execute_zip_actions,
        ZipSetting,
    ),
    "images-to-pdf": OperationConfig(
        "images-to-pdf",
        "",
        "",
        "filemanage_images_to_pdf",
        "images-to-pdf",
        "",
        "",
        preview_images_to_pdf_operation,
        execute_images_to_pdf_actions,
        ImagesToPdfSetting,
    ),
    "pdf-to-images": OperationConfig(
        "pdf-to-images",
        "",
        "",
        "filemanage_pdf_to_images",
        "pdf-to-images",
        "",
        "",
        preview_pdf_to_images_operation,
        execute_pdf_to_images_actions,
        PdfToImagesSetting,
    ),
    "webp-to-mp4": OperationConfig(
        "webp-to-mp4",
        "",
        "",
        "filemanage_webp_to_mp4",
        "webp-to-mp4",
        "",
        "",
        preview_webp_to_mp4_operation,
        execute_webp_to_mp4_actions,
        WebpToMp4Setting,
    ),
}


FILEMANAGE_SETTING_CONFIGS: dict[str, SettingConfig] = {
    "workspace": SettingConfig(
        "workspace",
        "",
        "",
        "",
        "filemanage_rename_files",
        FileManageWorkspaceSetting,
        FileManageWorkspaceSettingForm,
        "filemanage:rename-files",
        "",
        [],
    ),
    "rename": SettingConfig(
        "rename",
        "",
        "",
        "",
        "filemanage_rename_files",
        RenameSetting,
        RenameSettingForm,
        "filemanage:rename-files",
        "",
        [],
    ),
    "extension": SettingConfig(
        "extension",
        "",
        "",
        "",
        "filemanage_change_file_extension",
        ExtensionSetting,
        ExtensionSettingForm,
        "filemanage:change-file-extension",
        "",
        [],
    ),
    "zip": SettingConfig(
        "zip",
        "",
        "",
        "",
        "filemanage_extract_zip",
        ZipSetting,
        ZipSettingForm,
        "filemanage:extract-zip",
        "",
        [],
    ),
    "images-to-pdf": SettingConfig(
        "images-to-pdf",
        "",
        "",
        "",
        "filemanage_images_to_pdf",
        ImagesToPdfSetting,
        ImagesToPdfSettingForm,
        "filemanage:images-to-pdf",
        "",
        [],
    ),
    "pdf-to-images": SettingConfig(
        "pdf-to-images",
        "",
        "",
        "",
        "filemanage_pdf_to_images",
        PdfToImagesSetting,
        PdfToImagesSettingForm,
        "filemanage:pdf-to-images",
        "",
        [],
    ),
    "webp-to-mp4": SettingConfig(
        "webp-to-mp4",
        "",
        "",
        "",
        "filemanage_webp_to_mp4",
        WebpToMp4Setting,
        WebpToMp4SettingForm,
        "filemanage:webp-to-mp4",
        "",
        [],
    ),
}


def filemanage_operation_run(request: HttpRequest, operation_slug: str) -> JsonResponse:
    http_messages = get_page_ui_text("filemanage_http_messages")
    if request.method != 'POST':
        return JsonResponse({'error': http_messages['method_not_allowed']}, status=405)

    config = get_operation_config(operation_slug)
    _, root = load_filemanage_workspace()
    setting_instance = config.setting_model.load()
    mode = get_current_language_mode()
    job = start_filemanage_operation_job(
        operation_slug=config.slug,
        operation_label=config.label,
        executor=config.executor,
        root=root,
        setting_instance=setting_instance,
        mode=mode,
    )

    return JsonResponse({
        'job_id': job.pk,
        'status_url': reverse('filemanage_operation_job_status', args=[job.pk]),
        'operation_label': config.label,
    })


def filemanage_operation_job_status(request: HttpRequest, job_id: str) -> JsonResponse:
    job = get_filemanage_operation_job_snapshot(job_id)
    if job is None:
        http_messages = get_page_ui_text("filemanage_http_messages")
        return JsonResponse({'error': http_messages['job_not_found']}, status=404)
    return JsonResponse(job)


def filemanage_operation_snapshot(request: HttpRequest, operation_slug: str) -> JsonResponse:
    http_messages = get_page_ui_text("filemanage_http_messages")
    if request.method != 'GET':
        return JsonResponse({'error': http_messages['method_not_allowed']}, status=405)

    config = get_operation_config(operation_slug)
    _, root = load_filemanage_workspace()
    return JsonResponse(
        {
            'preview': config.preview_builder(root),
            'workspace_snapshot': build_workspace_snapshot(root),
        }
    )


def get_operation_config(slug: str) -> OperationConfig:
    config = FILEMANAGE_OPERATION_CONFIGS.get(slug)
    if not config:
        http_messages = get_page_ui_text("filemanage_http_messages")
        raise Http404(http_messages['unknown_operation'])

    page_text = get_page_text(f"filemanage:{slug}")
    settings_text = get_page_text(f"filemanage_setting:{config.settings_slug}")
    mode = get_current_language_mode()
    button_label = get_filemanage_run_button_label(slug, mode, fallback=slug)

    return replace(
        config,
        label=page_text["title"],
        description=page_text["intro"],
        settings_label=settings_text["title"],
        button_label=button_label,
    )


def get_setting_config(slug: str) -> SettingConfig:
    config = FILEMANAGE_SETTING_CONFIGS.get(slug)
    if not config:
        http_messages = get_page_ui_text("filemanage_http_messages")
        raise Http404(http_messages['unknown_setting_page'])

    page_text = get_page_text(f"filemanage_setting:{slug}")
    mode = get_current_language_mode()
    helper_bundle = get_filemanage_setting_helper(slug, mode)
    helper_title = helper_bundle["title"]
    helper_lines = helper_bundle["lines"]

    return replace(
        config,
        label=page_text["title"],
        title=page_text["title"],
        description=page_text["intro"],
        helper_title=helper_title,
        helper_lines=helper_lines,
    )


def filemanage_operation(request: HttpRequest, operation_slug: str) -> HttpResponse:
    config = get_operation_config(operation_slug)
    workspace_setting, root = load_filemanage_workspace()
    setting_instance = config.setting_model.load()
    setting_page = get_setting_config(config.settings_slug)
    page_text = get_page_text(f"filemanage:{operation_slug}")
    settings_text = get_page_text(f"filemanage_setting:{config.settings_slug}")
    operation_text = get_page_ui_text("filemanage_operation")
    setting_text = get_page_ui_text("filemanage_setting_page")
    filemanage_messages = get_page_ui_text("filemanage_messages")
    localized_operation = replace(
        config,
        label=page_text["title"],
        description=page_text["intro"],
        settings_label=settings_text["title"],
        button_label=get_filemanage_run_button_label(config.slug),
    )

    if request.method == "POST":
        workspace_form = FileManageWorkspaceSettingForm(request.POST, instance=workspace_setting)
        setting_form = setting_page.form_class(request.POST, instance=setting_instance)
        workspace_valid = workspace_form.is_valid()
        setting_valid = setting_form.is_valid()

        if workspace_valid and setting_valid:
            updated_workspace = workspace_form.save(commit=False)
            updated_workspace.root_path.mkdir(parents=True, exist_ok=True)
            updated_workspace.save()

            updated_setting = setting_form.save(commit=False)
            if hasattr(updated_setting, "root_path"):
                updated_setting.root_path.mkdir(parents=True, exist_ok=True)
            updated_setting.save()

            msg = filemanage_messages["setting_saved"].format(label=operation_text["saved_settings"])
            if request.headers.get("accept") == "application/json":
                return JsonResponse({"success": True, "message": msg})

            messages.success(request, msg)
            return redirect(config.route_name)

        if request.headers.get("accept") == "application/json":
            error_messages = [
                str(error)
                for form in (workspace_form, setting_form)
                for errors in form.errors.values()
                for error in errors
            ]
            err_msg = ", ".join(error_messages)
            return JsonResponse({"error": err_msg or get_page_ui_text("filemanage_http_messages")["invalid_data"]}, status=400)
    else:
        workspace_form = FileManageWorkspaceSettingForm(instance=workspace_setting)
        setting_form = setting_page.form_class(instance=setting_instance)

    workspace_setting, root = load_filemanage_workspace()
    preview = config.preview_builder(root)
    workspace_snapshot = build_workspace_snapshot(root)

    context = {
        "operation": localized_operation,
        "operation_text": operation_text,
        "setting_page": setting_page,
        "setting_text": setting_text,
        "workspace_form": workspace_form,
        "setting_form": setting_form,
        "page_title": page_text["title"],
        "page_heading": page_text["title"],
        "page_intro": page_text["intro"],
        "page_kicker": page_text["kicker"],
        "workspace_root": root,
        "workspace_snapshot": workspace_snapshot,
        "preview": preview,
        "run_url": reverse("filemanage_operation_run", args=[operation_slug]),
        "active_nav": f"filemanage:{operation_slug}",
    }
    return render(request, "filemanage/operation.html", context)
