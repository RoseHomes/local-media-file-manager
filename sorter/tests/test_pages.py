from io import StringIO

from django.core.management import call_command
from django.urls import reverse

from sorter.apps.catalog.models import Character, Game

from sorter.apps.ui.text import get_filemanage_setting_helper, get_page_ui_text, get_shared_js_text

from .common import BaseSmokeTestCase


class PageRenderingTests(BaseSmokeTestCase):
    def test_remote_peer_and_nonlocal_host_are_rejected(self):
        url = reverse("workspace")
        self.assertEqual(self.client.get(url, REMOTE_ADDR="192.0.2.1", HTTP_HOST="localhost").status_code, 403)
        self.assertEqual(self.client.get(url, HTTP_HOST="example.invalid").status_code, 400)
        self.assertEqual(self.client.get(url, REMOTE_ADDR="::1", HTTP_HOST="[::1]").status_code, 200)

    def test_demo_setup_can_be_repeated_without_overwriting_files(self):
        call_command("seed_demo", stdout=StringIO())
        first_image = self.inbox_dir / "demo-orbit-01.png"
        first_image.write_bytes(b"existing file")
        call_command("seed_demo", stdout=StringIO())

        self.assertEqual(first_image.read_bytes(), b"existing file")
        self.assertEqual(Game.objects.filter(title="Orbital Garden").count(), 1)
        self.assertEqual(Character.objects.filter(game__title="Orbital Garden").count(), 2)
        self.assertEqual(len(list((self.workspace_dir / "filemanage" / "demo").glob("*.png"))), 2)

    def test_primary_pages_render(self) -> None:
        urls = [
            reverse("workspace"),
            reverse("fanart_album"),
            reverse("fanart_setting"),
            reverse("games_setting"),
            reverse("character_setting"),
            reverse("album_setting"),
            reverse("interface_text_setting"),
            reverse("filemanage_rename_files"),
            reverse("filemanage_change_file_extension"),
            reverse("filemanage_extract_zip"),
            reverse("filemanage_images_to_pdf"),
            reverse("filemanage_pdf_to_images"),
            reverse("filemanage_webp_to_mp4"),
        ]

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)

    def test_workspace_html_keeps_gallery_filter_safe_when_inbox_is_empty(self) -> None:
        response = self.client.get(reverse("workspace"))
        self.assertContains(response, '/static/fanart/js/workspace.js')

    def test_workspace_queue_summary_hides_preview_actions_when_empty(self) -> None:
        response = self.client.get(reverse("workspace"))

        self.assertContains(response, 'class="staging-queue-summary staging-queue-summary-static" id="staging-queue-open" aria-disabled="true"')
        self.assertNotContains(response, 'id="staging-queue-summary-actions"')

    def test_workspace_queue_summary_shows_preview_actions_when_items_are_staged(self) -> None:
        session = self.client.session
        session["staged_assignments"] = [
            {
                "relative_path": "sample.png",
                "target_label": "Orbital Garden",
                "filename_label": "Nova",
            }
        ]
        session.save()

        response = self.client.get(reverse("workspace"))

        self.assertContains(response, 'id="staging-queue-open" type="button"')
        self.assertContains(response, 'id="staging-queue-summary-actions"')
        self.assertNotContains(response, 'staging-queue-summary-static" id="staging-queue-open"')

    def test_filemanage_extension_helper_mixed_mode_keeps_title_english_and_lines_thai(self) -> None:
        mixed = get_filemanage_setting_helper("extension", mode="mixed")
        english = get_filemanage_setting_helper("extension", mode="en")
        thai = get_filemanage_setting_helper("extension", mode="th")

        self.assertEqual(mixed["title"], english["title"])
        self.assertEqual(mixed["lines"], thai["lines"])

    def test_filemanage_operation_mixed_mode_keeps_structural_labels_english_and_supporting_copy_thai(self) -> None:
        mixed = get_page_ui_text("filemanage_operation", mode="mixed")
        english = get_page_ui_text("filemanage_operation", mode="en")
        thai = get_page_ui_text("filemanage_operation", mode="th")

        for key in (
            "preview_title",
            "panel_title",
            "workspace_root",
            "processing_now",
            "confirm_title",
        ):
            with self.subTest(key=key):
                self.assertEqual(mixed[key], english[key])

        for key in (
            "preview_intro",
            "filter_placeholder",
            "run_disabled_title",
            "starting_job",
            "waiting_first_file",
            "preview_capped_intro",
            "preview_capped_middle",
            "preview_capped_end",
            "empty_preview",
            "panel_intro",
        ):
            with self.subTest(key=key):
                self.assertEqual(mixed[key], thai[key])

    def test_filemanage_operation_page_does_not_render_literal_newline_markers(self) -> None:
        response = self.client.get(reverse("filemanage_rename_files"))

        self.assertNotContains(response, '`r`n')

    def test_all_filemanage_operation_pages_embed_inline_settings_panel(self) -> None:
        pages = [
            (reverse("filemanage_rename_files"), 'name="workflow"'),
            (reverse("filemanage_change_file_extension"), 'name="old_extension"'),
            (reverse("filemanage_extract_zip"), 'name="delete_archives_after_extract"'),
            (reverse("filemanage_images_to_pdf"), 'name="image_extensions"'),
            (reverse("filemanage_pdf_to_images"), 'name="image_format"'),
            (reverse("filemanage_webp_to_mp4"), 'name="output_root"'),
        ]

        for url, operation_field in pages:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, 'data-filemanage-setting-form', count=1)
                self.assertContains(response, 'name="root_folder"')
                self.assertContains(response, operation_field)
                self.assertContains(response, 'Save Settings')
                self.assertContains(response, 'type="reset"')
                self.assertContains(response, 'id="filemanage-reopen-run-button"')
                self.assertContains(response, '/static/filemanage/js/operation-preview.js')
                self.assertContains(response, '/static/filemanage/js/operation-run-log.js')
                self.assertContains(response, '/static/filemanage/js/operation-settings.js')

    def test_rename_operation_page_marks_text_transform_fields_with_action_scopes(self) -> None:
        response = self.client.get(reverse("filemanage_rename_files"))

        self.assertContains(
            response,
            'data-rename-field="search_text" data-rename-scope="text_transform" data-rename-actions="replace,remove"',
            html=False,
        )
        self.assertContains(
            response,
            'data-rename-field="replace_text" data-rename-scope="text_transform" data-rename-actions="replace"',
            html=False,
        )
        self.assertContains(
            response,
            'data-rename-field="per_folder_alpha_mode" data-rename-scope="text_transform" data-rename-actions="replace,add_prefix,add_suffix"',
            html=False,
        )
        self.assertContains(
            response,
            'data-rename-field="start_letter" data-rename-scope="text_transform" data-rename-actions="replace,add_prefix,add_suffix"',
            html=False,
        )
        self.assertContains(
            response,
            'data-rename-field="added_text" data-rename-scope="text_transform" data-rename-actions="add_prefix,add_suffix"',
            html=False,
        )

    def test_workspace_mixed_mode_keeps_structural_labels_english_and_supporting_copy_thai(self) -> None:
        mixed = get_page_ui_text("fanart_workspace", mode="mixed")
        english = get_page_ui_text("fanart_workspace", mode="en")
        thai = get_page_ui_text("fanart_workspace", mode="th")

        for key in (
            "inbox_title",
            "character_label",
            "reference_image_title",
            "staging_queue_title",
            "select_game_first",
        ):
            with self.subTest(key=key):
                self.assertEqual(mixed[key], english[key])

        for key in (
            "inbox_intro",
            "reference_appears_here",
            "select_character_for_preview",
            "queue_empty",
        ):
            with self.subTest(key=key):
                self.assertEqual(mixed[key], thai[key])

    def test_fanart_album_mixed_mode_keeps_structural_labels_english_and_supporting_copy_thai(self) -> None:
        mixed = get_page_ui_text("fanart_album_page", mode="mixed")
        english = get_page_ui_text("fanart_album_page", mode="en")
        thai = get_page_ui_text("fanart_album_page", mode="th")

        for key in (
            "viewer_title",
            "folder_panel_title",
            "character_filter_all",
            "character_filter_aria_label",
            "sort_aria_label",
        ):
            with self.subTest(key=key):
                self.assertEqual(mixed[key], english[key])

        for key in (
            "viewer_intro",
            "filter_placeholder",
            "character_filter_empty",
            "character_filter_placeholder",
            "no_subfolders",
        ):
            with self.subTest(key=key):
                self.assertEqual(mixed[key], thai[key])

    def test_album_setting_mixed_mode_keeps_modal_labels_english_and_helper_copy_thai(self) -> None:
        mixed = get_page_ui_text("album_setting_page", mode="mixed")
        english = get_page_ui_text("album_setting_page", mode="en")
        thai = get_page_ui_text("album_setting_page", mode="th")

        for key in (
            "confirm_kicker",
            "delete_confirm_title",
            "delete_confirm_button",
            "delete_confirm_cancel",
        ):
            with self.subTest(key=key):
                self.assertEqual(mixed[key], english[key])

        self.assertEqual(mixed["delete_confirm_copy"], thai["delete_confirm_copy"])

    def test_album_setting_page_renders_delete_confirmation_modal(self) -> None:
        response = self.client.get(reverse("album_setting"))

        self.assertContains(response, 'id="album-path-delete-modal"')
        self.assertContains(response, 'id="album-setting-js-config"')

    def test_shared_js_text_mixed_mode_keeps_labels_english_and_supporting_copy_thai(self) -> None:
        self.assertEqual(get_shared_js_text("select_label", mode="mixed"), get_shared_js_text("select_label", mode="en"))
        self.assertEqual(get_shared_js_text("clear_selection", mode="mixed"), get_shared_js_text("clear_selection", mode="en"))
        self.assertEqual(get_shared_js_text("close_notification", mode="mixed"), get_shared_js_text("close_notification", mode="en"))
        self.assertEqual(get_shared_js_text("search_placeholder", mode="mixed", description=True), get_shared_js_text("search_placeholder", mode="th"))
        self.assertEqual(get_shared_js_text("empty_label", mode="mixed", description=True), get_shared_js_text("empty_label", mode="th"))
