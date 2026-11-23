from django import forms

from sorter.apps.ui.models import InterfaceTextSetting
from sorter.apps.ui.services import InvalidMenuConfig, parse_menu_config
from sorter.apps.ui.text import get_language_mode_choices, get_page_ui_text, get_theme_choices


class InterfaceTextSettingForm(forms.ModelForm):
    class Meta:
        model = InterfaceTextSetting
        fields = ("language_mode", "theme_name", "menu_config")
        widgets = {
            "language_mode": forms.Select(
                attrs={
                    "class": "input",
                }
            ),
            "theme_name": forms.Select(
                attrs={
                    "class": "input",
                }
            ),
            "menu_config": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["language_mode"].choices = get_language_mode_choices()
        self.fields["theme_name"].choices = get_theme_choices()
        self.interface_text = get_page_ui_text("ui_interface_text_setting")

    def clean_menu_config(self):
        try:
            return parse_menu_config(self.cleaned_data.get("menu_config"))
        except InvalidMenuConfig as exc:
            error_key = {
                "invalid_json": "invalid_menu_config",
                "invalid_shape": "invalid_menu_config",
                "unknown_group": "invalid_menu_config",
                "missing_group": "missing_menu_group",
                "duplicate_group": "duplicate_menu_group",
                "invalid_items": "invalid_menu_items",
                "duplicate_item": "duplicate_menu_item",
            }.get(str(exc), "invalid_menu_config")
            raise forms.ValidationError(self.interface_text["error_messages"][error_key])
