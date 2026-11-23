from pathlib import Path
import re

from django import forms

from sorter.apps.catalog.models import Game
from sorter.apps.fanart.models import FanartSetting
from sorter.apps.ui.text import get_page_ui_text, get_sort_choices


TOKEN_PATTERN = re.compile(r"^(?:DD|MM|YYYY|YY|[^A-Za-z])+$")
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
        error_messages = config.get("error_messages")
        if isinstance(error_messages, dict):
            field.error_messages.update({key: str(value) for key, value in error_messages.items()})


class FanartSettingForm(forms.ModelForm):
    class Meta:
        model = FanartSetting
        fields = (
            "source_folder",
            "include_subfolders",
            "destination_folder",
            "filename_separator",
            "date_format_pattern",
            "sequence_padding",
            "default_sort",
        )
        widgets = {
            "source_folder": forms.TextInput(
                attrs={
                    "class": "input",
                    "placeholder": r"workspace/inbox",
                }
            ),
            "include_subfolders": forms.CheckboxInput(
                attrs={
                    "class": CHECKBOX_INPUT_CLASS,
                }
            ),
            "destination_folder": forms.TextInput(
                attrs={
                    "class": "input",
                    "placeholder": r"workspace/library",
                }
            ),
            "filename_separator": forms.TextInput(
                attrs={
                    "class": "input",
                    "placeholder": "Leave blank for no separator",
                }
            ),
            "date_format_pattern": forms.TextInput(
                attrs={
                    "class": "input",
                    "placeholder": "YYYYMMDD",
                    "autocomplete": "off",
                    "autocapitalize": "off",
                    "autocorrect": "off",
                    "spellcheck": "false",
                }
            ),
            "sequence_padding": forms.NumberInput(
                attrs={
                    "class": "input",
                    "min": 1,
                    "max": 9,
                    "autocomplete": "off",
                }
            ),
            "default_sort": forms.Select(
                attrs={
                    "class": "input",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["default_sort"].choices = get_sort_choices()
        _apply_field_bundle(self, get_page_ui_text("fanart_setting_form"))

    def clean_source_folder(self):
        return str(Path(self.cleaned_data["source_folder"].strip()).expanduser())

    def clean_destination_folder(self):
        return str(Path(self.cleaned_data["destination_folder"].strip()).expanduser())

    def clean_filename_separator(self):
        return self.cleaned_data["filename_separator"]

    def clean_date_format_pattern(self):
        value = self.cleaned_data["date_format_pattern"].strip().upper()
        messages = get_page_ui_text("fanart_setting_form")["messages"]
        if not value:
            raise forms.ValidationError(messages["blank_date_format"])
        if not TOKEN_PATTERN.fullmatch(value):
            raise forms.ValidationError(messages["invalid_date_format"])
        return value

    def clean_sequence_padding(self):
        value = self.cleaned_data["sequence_padding"]
        if value < 1 or value > 9:
            message = get_page_ui_text("fanart_setting_form")["messages"]["invalid_sequence_padding"]
            raise forms.ValidationError(message)
        return value


class AlbumSettingForm(forms.Form):
    default_sort = forms.ChoiceField(
        choices=(),
        widget=forms.Select(
            attrs={
                "class": "input",
            }
        ),
    )

    def __init__(self, *args, initial_rows: list[dict[str, object]] | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        album_setting_text = get_page_ui_text("album_setting_page")
        self.root_games = list(Game.objects.filter(main_folder__isnull=True).order_by("title"))
        self.root_game_lookup = {str(game.id): game for game in self.root_games}
        self.fields["default_sort"].choices = get_sort_choices()
        self.fields["default_sort"].label = str(album_setting_text["default_sort_label"])
        self.initial_rows = self._normalize_rows(initial_rows or [])
        self.submitted_rows = self._rows_from_bound_data() if self.is_bound else self.initial_rows
        if not self.submitted_rows:
            self.submitted_rows = [self._blank_row()]

    @staticmethod
    def _blank_row(row_id: str = "0") -> dict[str, object]:
        return {
            "row_id": row_id,
            "path": "",
            "root_game_id": "",
            "follow_subfolder_from_url": False,
        }

    def _normalize_rows(self, rows: list[dict[str, object]]) -> list[dict[str, object]]:
        normalized_rows: list[dict[str, object]] = []
        for index, row in enumerate(rows):
            normalized_rows.append(
                {
                    "row_id": str(index),
                    "path": str(row.get("path", "")),
                    "root_game_id": str(row.get("root_game_id", "") or ""),
                    "follow_subfolder_from_url": bool(row.get("follow_subfolder_from_url", False)),
                }
            )
        return normalized_rows

    def _rows_from_bound_data(self) -> list[dict[str, object]]:
        row_ids = list(dict.fromkeys(self.data.getlist("album_row_id")))
        rows: list[dict[str, object]] = []
        for row_id in row_ids:
            rows.append(
                {
                    "row_id": row_id,
                    "path": self.data.get(f"album_path_{row_id}", ""),
                    "root_game_id": self.data.get(f"album_root_game_{row_id}", ""),
                    "follow_subfolder_from_url": self.data.get(f"album_follow_sub_from_url_{row_id}") in {"1", "true", "on", "yes"},
                }
            )
        return rows

    @property
    def rows_for_render(self) -> list[dict[str, object]]:
        return self.submitted_rows

    def clean(self):
        cleaned_data = super().clean()
        album_setting_text = get_page_ui_text("album_setting_page")
        messages = album_setting_text.get("messages", {})
        cleaned_rows: list[dict[str, object]] = []
        seen_paths: set[str] = set()

        for row in self._rows_from_bound_data():
            raw_path = str(row["path"]).strip()
            root_game_id = str(row["root_game_id"]).strip()
            follow_subfolder = bool(row["follow_subfolder_from_url"])

            if not raw_path and not root_game_id and not follow_subfolder:
                continue

            if not raw_path:
                self.add_error(None, str(messages.get("path_required", "Enter an album path before saving.")))
                continue

            normalized = str(Path(raw_path).expanduser())
            lowered = normalized.lower()
            if lowered in seen_paths:
                self.add_error(None, str(messages.get("duplicate_path", "Album path is duplicated: {path}")).format(path=normalized))
                continue

            seen_paths.add(lowered)

            candidate = Path(normalized)
            if not candidate.exists():
                self.add_error(None, str(messages.get("path_not_found", "Album path was not found: {path}")).format(path=normalized))
                continue
            if not candidate.is_dir():
                self.add_error(None, str(messages.get("path_not_folder", "Album path is not a folder: {path}")).format(path=normalized))
                continue

            if root_game_id and root_game_id not in self.root_game_lookup:
                self.add_error(None, str(messages.get("invalid_root_game", "Selected root game is invalid.")))
                continue

            cleaned_rows.append(
                {
                    "path": str(candidate),
                    "root_game_id": int(root_game_id) if root_game_id else None,
                    "follow_subfolder_from_url": follow_subfolder,
                }
            )

        self.cleaned_album_rows = cleaned_rows
        cleaned_data["album_rows"] = cleaned_rows
        return cleaned_data
