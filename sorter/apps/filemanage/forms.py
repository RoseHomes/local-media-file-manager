from pathlib import Path

from django import forms

from sorter.apps.ui.text import get_page_ui_text

from .models import (
    ExtensionSetting,
    FileManageWorkspaceSetting,
    ImagesToPdfSetting,
    PdfToImagesSetting,
    RenameSetting,
    WebpToMp4Setting,
    ZipSetting,
)


CHECKBOX_CLASS = "h-5 w-5 rounded border-line text-warm focus:ring-warm/30"


def checkbox_widget() -> forms.CheckboxInput:
    return forms.CheckboxInput(attrs={"class": CHECKBOX_CLASS})


EXTENSION_SOURCE_CHOICES = (
    (".all", ".all"),
    (".png", ".png"),
    (".jpg", ".jpg"),
    (".jpeg", ".jpeg"),
    (".webp", ".webp"),
    (".gif", ".gif"),
    (".bmp", ".bmp"),
    (".jfif", ".jfif"),
)

EXTENSION_TARGET_CHOICES = (
    (".png", ".png"),
    (".jpg", ".jpg"),
    (".jpeg", ".jpeg"),
    (".webp", ".webp"),
    (".gif", ".gif"),
    (".bmp", ".bmp"),
    (".jfif", ".jfif"),
)


def _apply_bundle(form: forms.BaseForm, bundle_key: str) -> None:
    bundle = get_page_ui_text(bundle_key)
    fields_bundle = bundle.get("fields", {})
    if isinstance(fields_bundle, dict):
        for name, config in fields_bundle.items():
            field = form.fields.get(name)
            if field is None or not isinstance(config, dict):
                continue
            if "label" in config:
                field.label = str(config["label"])
            if "help_text" in config:
                field.help_text = str(config["help_text"])
            if "placeholder" in config and hasattr(field.widget, "attrs"):
                field.widget.attrs["placeholder"] = str(config["placeholder"])
            error_messages = config.get("error_messages")
            if isinstance(error_messages, dict):
                field.error_messages.update({key: str(value) for key, value in error_messages.items()})

    choices_bundle = bundle.get("choices", {})
    if isinstance(choices_bundle, dict):
        for name, labels in choices_bundle.items():
            field = form.fields.get(name)
            if field is None or not isinstance(labels, dict) or not hasattr(field, "choices"):
                continue
            normalized = {str(key): str(value) for key, value in labels.items()}
            field.choices = [
                (value, normalized.get(str(value), label))
                for value, label in list(field.choices)
            ]
            if hasattr(field.widget, "choices"):
                field.widget.choices = field.choices


class FileManageWorkspaceSettingForm(forms.ModelForm):
    class Meta:
        model = FileManageWorkspaceSetting
        fields = ("root_folder",)
        widgets = {
            "root_folder": forms.TextInput(attrs={"class": "input", "autocomplete": "off", "autocapitalize": "off", "autocorrect": "off", "spellcheck": "false"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_bundle(self, "filemanage_workspace_form")

    def clean_root_folder(self):
        return str(Path(self.cleaned_data["root_folder"].strip()).expanduser())


class RenameSettingForm(forms.ModelForm):
    class Meta:
        model = RenameSetting
        fields = (
            "include_subfolders",
            "workflow",
            "text_action",
            "search_text",
            "replace_text",
            "added_text",
            "match_scope",
            "match_occurrence",
            "per_folder_alpha_mode",
            "trim_delimiter",
            "trim_action",
            "delimiter_occurrence",
            "include_delimiter",
            "order_ascending",
            "start_letter",
            "number_action",
            "start_number",
            "increment",
            "number_width",
            "number_separator",
            "reset_per_folder",
            "target_extensions",
        )
        widgets = {
            "include_subfolders": checkbox_widget(),
            "workflow": forms.Select(attrs={"class": "input"}),
            "text_action": forms.Select(attrs={"class": "input"}),
            "search_text": forms.TextInput(attrs={"class": "input", "autocomplete": "off", "autocapitalize": "off", "autocorrect": "off", "spellcheck": "false"}),
            "replace_text": forms.TextInput(attrs={"class": "input", "autocomplete": "off", "autocapitalize": "off", "autocorrect": "off", "spellcheck": "false"}),
            "added_text": forms.TextInput(attrs={"class": "input", "autocomplete": "off", "autocapitalize": "off", "autocorrect": "off", "spellcheck": "false"}),
            "match_scope": forms.Select(attrs={"class": "input"}),
            "match_occurrence": forms.Select(attrs={"class": "input"}),
            "per_folder_alpha_mode": checkbox_widget(),
            "trim_delimiter": forms.TextInput(attrs={"class": "input", "autocomplete": "off", "autocapitalize": "off", "autocorrect": "off", "spellcheck": "false"}),
            "trim_action": forms.Select(attrs={"class": "input"}),
            "delimiter_occurrence": forms.Select(attrs={"class": "input"}),
            "include_delimiter": checkbox_widget(),
            "order_ascending": checkbox_widget(),
            "start_letter": forms.TextInput(attrs={"class": "input", "maxlength": 1, "autocomplete": "off", "autocapitalize": "off", "autocorrect": "off", "spellcheck": "false"}),
            "number_action": forms.Select(attrs={"class": "input"}),
            "start_number": forms.NumberInput(attrs={"class": "input", "min": 1, "autocomplete": "off"}),
            "increment": forms.NumberInput(attrs={"class": "input", "min": 1, "autocomplete": "off"}),
            "number_width": forms.NumberInput(attrs={"class": "input", "min": 1, "max": 10, "autocomplete": "off"}),
            "number_separator": forms.TextInput(attrs={"class": "input", "autocomplete": "off", "autocapitalize": "off", "autocorrect": "off", "spellcheck": "false"}),
            "reset_per_folder": checkbox_widget(),
            "target_extensions": forms.TextInput(attrs={"class": "input", "autocomplete": "off", "autocapitalize": "off", "autocorrect": "off", "spellcheck": "false"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_bundle(self, "filemanage_rename_form")

    def clean_start_letter(self):
        value = (self.cleaned_data["start_letter"] or "a").strip().lower()[:1]
        return value or "a"

    def clean_trim_delimiter(self):
        return (self.cleaned_data["trim_delimiter"] or "").strip()

    def clean_number_separator(self):
        return (self.cleaned_data["number_separator"] or "").strip()

    def clean_target_extensions(self):
        return (self.cleaned_data["target_extensions"] or "").strip().lower()


class ExtensionSettingForm(forms.ModelForm):
    class Meta:
        model = ExtensionSetting
        fields = ("include_subfolders", "old_extension", "new_extension")
        widgets = {
            "include_subfolders": checkbox_widget(),
            "old_extension": forms.Select(attrs={"class": "input"}, choices=EXTENSION_SOURCE_CHOICES),
            "new_extension": forms.Select(attrs={"class": "input"}, choices=EXTENSION_TARGET_CHOICES),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["old_extension"].choices = EXTENSION_SOURCE_CHOICES
        self.fields["new_extension"].choices = EXTENSION_TARGET_CHOICES
        _apply_bundle(self, "filemanage_extension_form")

    def clean_old_extension(self):
        return (self.cleaned_data["old_extension"] or ".all").strip().lower()

    def clean_new_extension(self):
        return (self.cleaned_data["new_extension"] or ".jpg").strip().lower()


class ZipSettingForm(forms.ModelForm):
    class Meta:
        model = ZipSetting
        fields = ("include_subfolders", "delete_archives_after_extract")
        widgets = {
            "include_subfolders": checkbox_widget(),
            "delete_archives_after_extract": checkbox_widget(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_bundle(self, "filemanage_zip_form")


class ImagesToPdfSettingForm(forms.ModelForm):
    class Meta:
        model = ImagesToPdfSetting
        fields = (
            "include_subfolders",
            "image_extensions",
            "jpg_quality",
            "delete_source_images",
            "fit_to_largest",
            "upscale_method",
        )
        widgets = {
            "include_subfolders": checkbox_widget(),
            "image_extensions": forms.TextInput(attrs={"class": "input", "autocomplete": "off", "autocapitalize": "off", "autocorrect": "off", "spellcheck": "false"}),
            "jpg_quality": forms.NumberInput(attrs={"class": "input", "min": 1, "max": 100, "autocomplete": "off"}),
            "delete_source_images": checkbox_widget(),
            "fit_to_largest": checkbox_widget(),
            "upscale_method": forms.Select(attrs={"class": "input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_bundle(self, "filemanage_images_to_pdf_form")

    def clean_image_extensions(self):
        return (self.cleaned_data["image_extensions"] or "").strip().lower()


class PdfToImagesSettingForm(forms.ModelForm):
    class Meta:
        model = PdfToImagesSetting
        fields = ("include_subfolders", "delete_source_pdfs", "image_format", "jpeg_quality")
        widgets = {
            "include_subfolders": checkbox_widget(),
            "delete_source_pdfs": checkbox_widget(),
            "image_format": forms.Select(attrs={"class": "input"}),
            "jpeg_quality": forms.NumberInput(attrs={"class": "input", "min": 1, "max": 100, "autocomplete": "off"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_bundle(self, "filemanage_pdf_to_images_form")


class WebpToMp4SettingForm(forms.ModelForm):
    class Meta:
        model = WebpToMp4Setting
        fields = ("output_root", "include_subfolders", "overwrite_existing", "crf", "preset")
        widgets = {
            "output_root": forms.TextInput(attrs={"class": "input", "autocomplete": "off", "autocapitalize": "off", "autocorrect": "off", "spellcheck": "false"}),
            "include_subfolders": checkbox_widget(),
            "overwrite_existing": checkbox_widget(),
            "crf": forms.NumberInput(attrs={"class": "input", "min": 0, "max": 51, "autocomplete": "off"}),
            "preset": forms.Select(attrs={"class": "input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_bundle(self, "filemanage_webp_to_mp4_form")

    def clean_output_root(self):
        return str(Path(self.cleaned_data["output_root"].strip()).expanduser())


