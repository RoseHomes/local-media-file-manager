from pathlib import Path

from django.conf import settings
from django.db import models


RENAME_WORKFLOW_CHOICES = [
    ("text_transform", "Text transform"),
    ("trim_delimiter", "Trim by delimiter"),
    ("numbering", "Numbering"),
]

TEXT_ACTION_CHOICES = [
    ("replace", "Replace text"),
    ("add_prefix", "Add prefix"),
    ("add_suffix", "Add suffix"),
    ("remove", "Remove text"),
]

MATCH_SCOPE_CHOICES = [
    ("stem", "Filename only"),
    ("full_name", "Include extension"),
]

MATCH_OCCURRENCE_CHOICES = [
    ("all", "All matches"),
    ("first", "First match"),
    ("last", "Last match"),
]

TRIM_ACTION_CHOICES = [
    ("keep_before", "Keep text before delimiter"),
    ("keep_after", "Keep text after delimiter"),
    ("remove_before", "Remove text before delimiter"),
    ("remove_after", "Remove text after delimiter"),
]

DELIMITER_OCCURRENCE_CHOICES = [
    ("first", "First delimiter"),
    ("last", "Last delimiter"),
]

NUMBER_ACTION_CHOICES = [
    ("swap_numbers", "Swap numbers"),
    ("add_prefix_sequence", "Add sequence prefix"),
    ("add_suffix_sequence", "Add sequence suffix"),
    ("replace_with_sequence", "Replace with sequence"),
]

UPSCALE_METHOD_CHOICES = [
    ("scale", "Scale to fit"),
    ("pad", "Pad canvas"),
]

EXPORT_IMAGE_FORMAT_CHOICES = [
    ("jpg", "JPG"),
    ("png", "PNG"),
]

WEBP_TO_MP4_PRESET_CHOICES = [
    ("ultrafast", "ultrafast"),
    ("superfast", "superfast"),
    ("veryfast", "veryfast"),
    ("faster", "faster"),
    ("fast", "fast"),
    ("medium", "medium"),
    ("slow", "slow"),
    ("slower", "slower"),
    ("veryslow", "veryslow"),
]


class FileManageWorkspaceSetting(models.Model):
    root_folder = models.CharField(
        max_length=500,
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "FileManage workspace setting"
        verbose_name_plural = "FileManage workspace settings"

    def __str__(self) -> str:
        return "FileManage Workspace Setting"

    @classmethod
    def load(cls) -> "FileManageWorkspaceSetting":
        instance, _ = cls.objects.get_or_create(
            pk=1,
            defaults={"root_folder": str(settings.WORKSPACE_DIR / "filemanage")},
        )
        return instance

    @property
    def root_path(self) -> Path:
        return Path(self.root_folder).expanduser()


class FileManageOperationJob(models.Model):
    id = models.CharField(max_length=32, primary_key=True)
    operation_slug = models.CharField(max_length=80)
    operation_label = models.CharField(max_length=200)
    status = models.CharField(max_length=40, default="running")
    total_count = models.PositiveIntegerField(default=0)
    completed_count = models.PositiveIntegerField(default=0)
    current_item = models.JSONField(blank=True, null=True)
    completed_items = models.JSONField(default=list, blank=True)
    failed_items = models.JSONField(default=list, blank=True)
    message = models.TextField(blank=True, default="")
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)

    def __str__(self) -> str:
        return f"{self.operation_slug}:{self.id}"


class RenameSetting(models.Model):
    include_subfolders = models.BooleanField(default=True)
    workflow = models.CharField(max_length=20, choices=RENAME_WORKFLOW_CHOICES, default="text_transform")
    text_action = models.CharField(max_length=20, choices=TEXT_ACTION_CHOICES, default="replace")
    search_text = models.CharField(max_length=200, blank=True, default="")
    replace_text = models.CharField(max_length=200, blank=True, default="")
    added_text = models.CharField(max_length=200, blank=True, default="")
    match_scope = models.CharField(max_length=20, choices=MATCH_SCOPE_CHOICES, default="stem")
    match_occurrence = models.CharField(max_length=20, choices=MATCH_OCCURRENCE_CHOICES, default="all")
    per_folder_alpha_mode = models.BooleanField(default=False)
    trim_delimiter = models.CharField(max_length=50, blank=True, default="")
    trim_action = models.CharField(max_length=20, choices=TRIM_ACTION_CHOICES, default="keep_before")
    delimiter_occurrence = models.CharField(max_length=20, choices=DELIMITER_OCCURRENCE_CHOICES, default="first")
    include_delimiter = models.BooleanField(default=False)
    order_ascending = models.BooleanField(default=True)
    start_letter = models.CharField(max_length=1, default="a")
    number_action = models.CharField(max_length=30, choices=NUMBER_ACTION_CHOICES, default="swap_numbers")
    start_number = models.PositiveIntegerField(default=1)
    increment = models.PositiveIntegerField(default=1)
    number_width = models.PositiveSmallIntegerField(default=2)
    number_separator = models.CharField(max_length=10, blank=True, default="_")
    reset_per_folder = models.BooleanField(default=False)
    target_extensions = models.CharField(max_length=200, blank=True, default=".png,.jpg,.jpeg,.webp")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Rename setting"
        verbose_name_plural = "Rename settings"

    def __str__(self) -> str:
        return "Rename Setting"

    @classmethod
    def load(cls) -> "RenameSetting":
        instance, _ = cls.objects.get_or_create(pk=1)
        needs_save = False
        legacy_workflow_map = {
            "replace_text": "text_transform",
            "swap_numbers": "numbering",
        }
        if instance.workflow in legacy_workflow_map:
            instance.workflow = legacy_workflow_map[instance.workflow]
            needs_save = True
        if instance.workflow not in {"text_transform", "trim_delimiter", "numbering"}:
            instance.workflow = "text_transform"
            needs_save = True
        if instance.text_action not in {"replace", "add_prefix", "add_suffix", "remove"}:
            instance.text_action = "replace"
            needs_save = True
        if instance.match_scope not in {"stem", "full_name"}:
            instance.match_scope = "stem"
            needs_save = True
        if instance.match_occurrence not in {"all", "first", "last"}:
            instance.match_occurrence = "all"
            needs_save = True
        if instance.trim_action not in {"keep_before", "keep_after", "remove_before", "remove_after"}:
            instance.trim_action = "keep_before"
            needs_save = True
        if instance.delimiter_occurrence not in {"first", "last"}:
            instance.delimiter_occurrence = "first"
            needs_save = True
        if instance.number_action not in {"swap_numbers", "add_prefix_sequence", "add_suffix_sequence", "replace_with_sequence"}:
            instance.number_action = "swap_numbers"
            needs_save = True
        if instance.start_number < 1:
            instance.start_number = 1
            needs_save = True
        if instance.increment < 1:
            instance.increment = 1
            needs_save = True
        if instance.number_width < 1:
            instance.number_width = 2
            needs_save = True
        if needs_save:
            instance.save()
        return instance


class ExtensionSetting(models.Model):
    include_subfolders = models.BooleanField(default=True)
    old_extension = models.CharField(max_length=20, default=".all")
    new_extension = models.CharField(max_length=20, default=".jpg")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Extension setting"
        verbose_name_plural = "Extension settings"

    def __str__(self) -> str:
        return "Extension Setting"

    @classmethod
    def load(cls) -> "ExtensionSetting":
        instance, _ = cls.objects.get_or_create(pk=1)
        return instance


class ZipSetting(models.Model):
    include_subfolders = models.BooleanField(default=True)
    delete_archives_after_extract = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "ZIP setting"
        verbose_name_plural = "ZIP settings"

    def __str__(self) -> str:
        return "ZIP Setting"

    @classmethod
    def load(cls) -> "ZipSetting":
        instance, _ = cls.objects.get_or_create(pk=1)
        return instance


class ImagesToPdfSetting(models.Model):
    include_subfolders = models.BooleanField(default=True)
    image_extensions = models.CharField(max_length=200, default=".png,.jpg,.jpeg,.webp")
    jpg_quality = models.PositiveSmallIntegerField(default=100)
    delete_source_images = models.BooleanField(default=False)
    fit_to_largest = models.BooleanField(default=True)
    upscale_method = models.CharField(max_length=10, choices=UPSCALE_METHOD_CHOICES, default="scale")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Images To PDF setting"
        verbose_name_plural = "Images To PDF settings"

    def __str__(self) -> str:
        return "Images To PDF Setting"

    @classmethod
    def load(cls) -> "ImagesToPdfSetting":
        instance, _ = cls.objects.get_or_create(pk=1)
        return instance


class PdfToImagesSetting(models.Model):
    include_subfolders = models.BooleanField(default=True)
    delete_source_pdfs = models.BooleanField(default=False)
    image_format = models.CharField(max_length=10, choices=EXPORT_IMAGE_FORMAT_CHOICES, default="jpg")
    jpeg_quality = models.PositiveSmallIntegerField(default=95)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "PDF To Images setting"
        verbose_name_plural = "PDF To Images settings"

    def __str__(self) -> str:
        return "PDF To Images Setting"

    @classmethod
    def load(cls) -> "PdfToImagesSetting":
        instance, _ = cls.objects.get_or_create(pk=1)
        return instance


class WebpToMp4Setting(models.Model):
    output_root = models.CharField(max_length=500, default="webp-to-mp4-output")
    include_subfolders = models.BooleanField(default=True)
    overwrite_existing = models.BooleanField(default=False)
    crf = models.PositiveSmallIntegerField(default=18)
    preset = models.CharField(max_length=20, choices=WEBP_TO_MP4_PRESET_CHOICES, default="slow")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "WebP To MP4 setting"
        verbose_name_plural = "WebP To MP4 settings"

    def __str__(self) -> str:
        return "WebP To MP4 Setting"

    @classmethod
    def load(cls) -> "WebpToMp4Setting":
        instance, _ = cls.objects.get_or_create(pk=1)
        return instance

    @property
    def output_path(self) -> Path:
        return settings.WORKSPACE_DIR / Path(self.output_root).expanduser()

