from pathlib import Path

from django import forms

from sorter.apps.catalog.models import CharacterImportSetting, Game, GameImportSetting
from sorter.apps.ui.text import get_page_ui_text


CHECKBOX_INPUT_CLASS = "h-5 w-5 rounded border-line text-warm focus:ring-warm/30"


def _apply_field_bundle(form: forms.BaseForm, bundle: dict[str, object]) -> None:
    fields_bundle = bundle.get("fields", {})
    if not isinstance(fields_bundle, dict):
        return
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
        if "empty_label" in config and hasattr(field, "empty_label"):
            field.empty_label = str(config["empty_label"])
        error_messages = config.get("error_messages")
        if isinstance(error_messages, dict):
            field.error_messages.update({key: str(value) for key, value in error_messages.items()})


def _apply_choice_bundle(field: forms.Field, labels: dict[str, object]) -> None:
    if not hasattr(field, "choices"):
        return
    normalized = {str(key): str(value) for key, value in labels.items()}
    field.choices = [
        (value, normalized.get(str(value), label))
        for value, label in list(field.choices)
    ]


class _BasePathSettingForm(forms.ModelForm):
    bundle_key = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.bundle_key:
            _apply_field_bundle(self, get_page_ui_text(self.bundle_key))

    def clean_root_folder(self):
        value = self.cleaned_data["root_folder"].strip()
        if not value:
            bundle = get_page_ui_text(self.bundle_key)
            raise forms.ValidationError(bundle["messages"]["blank_folder"])
        return str(Path(value).expanduser())


class GameImportSettingForm(_BasePathSettingForm):
    bundle_key = "catalog_game_import_form"

    skip_existing = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                "class": CHECKBOX_INPUT_CLASS,
            }
        ),
    )

    class Meta:
        model = GameImportSetting
        fields = ("root_folder",)
        widgets = {
            "root_folder": forms.TextInput(
                attrs={
                    "class": "input",
                    "placeholder": r"workspace/library",
                    "autocomplete": "off",
                    "autocapitalize": "off",
                    "autocorrect": "off",
                    "spellcheck": "false",
                }
            ),
        }


class GameManualEntryForm(forms.Form):
    use_required_attribute = False

    manual_kind = forms.ChoiceField(
        choices=(
            ("root", "Root game"),
            ("subfolder", "Subfolder"),
        ),
        initial="root",
        widget=forms.Select(
            attrs={
                "class": "input",
            }
        ),
    )
    manual_title = forms.CharField(
        max_length=200,
        widget=forms.TextInput(
            attrs={
                "class": "input",
                "placeholder": "Game title",
                "autocomplete": "off",
                "autocapitalize": "off",
                "autocorrect": "off",
                "spellcheck": "false",
            }
        ),
    )
    manual_folder_name = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "input",
                "placeholder": "Folder name (optional)",
                "autocomplete": "off",
                "autocapitalize": "off",
                "autocorrect": "off",
                "spellcheck": "false",
            }
        ),
    )
    manual_parent_game = forms.ModelChoiceField(
        queryset=Game.objects.none(),
        required=False,
        empty_label="Select root game",
        widget=forms.Select(
            attrs={
                "class": "input",
            }
        ),
    )
    manual_use_folder_name_as_filename = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                "class": CHECKBOX_INPUT_CLASS,
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        bundle = get_page_ui_text("catalog_game_manual_form")
        _apply_field_bundle(self, bundle)
        manual_kind_labels = bundle.get("choices", {}).get("manual_kind", {})
        if isinstance(manual_kind_labels, dict):
            _apply_choice_bundle(self.fields["manual_kind"], manual_kind_labels)
        self.fields["manual_parent_game"].queryset = Game.objects.filter(main_folder__isnull=True).order_by("title")

    def clean_manual_title(self):
        value = self.cleaned_data["manual_title"].strip()
        if not value:
            bundle = get_page_ui_text("catalog_game_manual_form")
            raise forms.ValidationError(bundle["messages"]["blank_title"])
        return value

    def clean_manual_folder_name(self):
        return self.cleaned_data["manual_folder_name"].strip()

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("manual_kind") == "subfolder" and not cleaned_data.get("manual_parent_game"):
            bundle = get_page_ui_text("catalog_game_manual_form")
            self.add_error("manual_parent_game", bundle["messages"]["missing_parent"])
        return cleaned_data


class CharacterImportSettingForm(_BasePathSettingForm):
    bundle_key = "catalog_character_import_form"

    skip_existing = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                "class": CHECKBOX_INPUT_CLASS,
            }
        ),
    )

    class Meta:
        model = CharacterImportSetting
        fields = ("root_folder",)
        widgets = {
            "root_folder": forms.TextInput(
                attrs={
                    "class": "input",
                    "placeholder": r"workspace/library/characters",
                    "autocomplete": "off",
                    "autocapitalize": "off",
                    "autocorrect": "off",
                    "spellcheck": "false",
                }
            ),
        }


class CharacterManualEntryForm(forms.Form):
    manual_game = forms.ModelChoiceField(
        queryset=Game.objects.none(),
        empty_label="Select root game",
        widget=forms.Select(
            attrs={
                "class": "input",
            }
        ),
    )
    manual_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(
            attrs={
                "class": "input",
                "placeholder": "Character name",
                "autocomplete": "off",
                "autocapitalize": "off",
                "autocorrect": "off",
                "spellcheck": "false",
            }
        ),
    )
    manual_description = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "input",
                "placeholder": "Description (optional)",
                "autocomplete": "off",
                "autocapitalize": "off",
                "autocorrect": "off",
                "spellcheck": "false",
            }
        ),
    )
    manual_reference_image = forms.ImageField(
        required=False,
        widget=forms.FileInput(
            attrs={
                "class": "input file:mr-4 file:rounded-full file:border-0 file:bg-white/80 file:px-4 file:py-2 file:text-sm file:font-semibold file:text-ink",
                "accept": "image/*",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        bundle = get_page_ui_text("catalog_character_manual_form")
        _apply_field_bundle(self, bundle)
        self.fields["manual_game"].queryset = Game.objects.filter(main_folder__isnull=True).order_by("title")

    def clean_manual_name(self):
        value = self.cleaned_data["manual_name"].strip()
        if not value:
            bundle = get_page_ui_text("catalog_character_manual_form")
            raise forms.ValidationError(bundle["messages"]["blank_name"])
        return value

    def clean_manual_description(self):
        return self.cleaned_data["manual_description"].strip()
