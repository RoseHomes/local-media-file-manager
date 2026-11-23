import json

from django.urls import reverse

from sorter.apps.ui.models import InterfaceTextSetting
from sorter.apps.ui.services import DEFAULT_MENU_CONFIG

from .common import BaseSmokeTestCase


class InterfaceTextSettingTests(BaseSmokeTestCase):
    def test_interface_text_setting_uses_page_assets_for_menu_ordering(self) -> None:
        response = self.client.get(reverse("interface_text_setting"))

        self.assertContains(response, '/static/ui/css/interface_text_setting.css')
        self.assertContains(response, '/static/ui/js/interface_text_setting.js')
        self.assertContains(response, 'data-menu-order-open')
        self.assertContains(response, 'data-menu-order-modal')
        self.assertNotContains(response, "const hiddenInput = document.querySelector('input[name=\"menu_config\"]');")

    def test_interface_text_setting_accepts_valid_menu_ordering(self) -> None:
        setting = InterfaceTextSetting.load()
        setting.menu_config = DEFAULT_MENU_CONFIG
        setting.save(update_fields=["menu_config"])

        menu_config = [
            {"id": "filemanage", "items": list(reversed(DEFAULT_MENU_CONFIG[2]["items"]))},
            {"id": "fanart_filemanage", "items": list(reversed(DEFAULT_MENU_CONFIG[0]["items"]))},
            {"id": "setting_fanart_filemanage", "items": list(reversed(DEFAULT_MENU_CONFIG[1]["items"]))},
        ]

        response = self.client.post(
            reverse("interface_text_setting"),
            data={
                "language_mode": "en",
                "theme_name": "mystic-violet",
                "menu_config": json.dumps(menu_config),
            },
        )

        self.assertEqual(response.status_code, 302)
        setting.refresh_from_db()
        self.assertEqual(setting.menu_config, menu_config)

    def test_interface_text_setting_rejects_cross_group_menu_items(self) -> None:
        setting = InterfaceTextSetting.load()
        setting.menu_config = DEFAULT_MENU_CONFIG
        setting.save(update_fields=["menu_config"])

        invalid_menu_config = [
            {"id": "fanart_filemanage", "items": ["fanart_file", "fanart_setting"]},
            {"id": "setting_fanart_filemanage", "items": ["fanart_album", "games_setting", "character_setting", "album_setting"]},
            {"id": "filemanage", "items": DEFAULT_MENU_CONFIG[2]["items"]},
        ]

        response = self.client.post(
            reverse("interface_text_setting"),
            data={
                "language_mode": "en",
                "theme_name": "mystic-violet",
                "menu_config": json.dumps(invalid_menu_config),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "unexpected menu items")
        setting.refresh_from_db()
        self.assertEqual(setting.menu_config, DEFAULT_MENU_CONFIG)
