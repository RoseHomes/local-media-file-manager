import time
from unittest.mock import patch

from django.urls import reverse
from PIL import Image

from sorter.apps.filemanage.services import (
    execute_extension_actions,
    execute_images_to_pdf_actions,
    execute_pdf_to_images_actions,
    execute_rename_actions,
    reencode_images_for_pdf_quality,
)
from sorter.models import (
    ExtensionSetting,
    FileManageOperationJob,
    FileManageWorkspaceSetting,
    ImagesToPdfSetting,
    PdfToImagesSetting,
    WebpToMp4Setting,
    RenameSetting,
)

from .common import BaseSmokeTestCase, create_test_image


class FileManageWorkflowTests(BaseSmokeTestCase):
    def test_pdf_to_images_renders_each_page_and_preserves_the_original(self):
        source = self.base_path / "sample.pdf"
        with Image.new("RGB", (48, 48), "navy") as first, Image.new("RGB", (48, 48), "gold") as second:
            first.save(source, save_all=True, append_images=[second])

        result = execute_pdf_to_images_actions(self.base_path, PdfToImagesSetting(image_format="png"))

        self.assertEqual(result["completed"], 1)
        self.assertTrue(source.is_file())
        for index in (1, 2):
            with Image.open(source.with_suffix("") / f"page_{index}.png") as image:
                self.assertEqual(image.size, (48, 48))

    def test_webp_default_output_is_inside_the_active_workspace(self):
        self.assertEqual(WebpToMp4Setting().output_path, self.workspace_dir / "webp-to-mp4-output")

    def test_rename_operation_renames_matching_files(self) -> None:
        workspace_setting = FileManageWorkspaceSetting.load()
        workspace_root = workspace_setting.root_path
        workspace_root.mkdir(parents=True, exist_ok=True)

        source_file = workspace_root / "scene_old.png"
        create_test_image(source_file, color="purple")

        rename_setting = RenameSetting.load()
        rename_setting.workflow = "text_transform"
        rename_setting.search_text = "_old"
        rename_setting.replace_text = "_new"
        rename_setting.include_subfolders = True
        rename_setting.save(
            update_fields=[
                "workflow",
                "search_text",
                "replace_text",
                "include_subfolders",
                "updated_at",
            ]
        )

        result = execute_rename_actions(workspace_root, rename_setting)
        self.assertEqual(result["completed"], 1)
        self.assertFalse(source_file.exists())
        self.assertTrue((workspace_root / "scene_new.png").exists())

    def test_trim_delimiter_workflow_keeps_text_before_delimiter(self) -> None:
        workspace_root = FileManageWorkspaceSetting.load().root_path
        workspace_root.mkdir(parents=True, exist_ok=True)

        source_file = workspace_root / "test_(draft).png"
        create_test_image(source_file, color="blue")

        rename_setting = RenameSetting.load()
        rename_setting.workflow = "trim_delimiter"
        rename_setting.trim_delimiter = "_"
        rename_setting.trim_action = "keep_before"
        rename_setting.delimiter_occurrence = "first"
        rename_setting.include_delimiter = False
        rename_setting.include_subfolders = True
        rename_setting.save()

        result = execute_rename_actions(workspace_root, rename_setting)
        self.assertEqual(result["completed"], 1)
        self.assertFalse(source_file.exists())
        self.assertTrue((workspace_root / "test.png").exists())

    def test_numbering_workflow_adds_prefix_sequence(self) -> None:
        workspace_root = FileManageWorkspaceSetting.load().root_path
        workspace_root.mkdir(parents=True, exist_ok=True)

        first = workspace_root / "cover.png"
        second = workspace_root / "page.png"
        create_test_image(first, color="green")
        create_test_image(second, color="yellow")

        rename_setting = RenameSetting.load()
        rename_setting.workflow = "numbering"
        rename_setting.number_action = "add_prefix_sequence"
        rename_setting.start_number = 1
        rename_setting.increment = 1
        rename_setting.number_width = 3
        rename_setting.number_separator = "_"
        rename_setting.include_subfolders = True
        rename_setting.order_ascending = True
        rename_setting.save()

        result = execute_rename_actions(workspace_root, rename_setting)
        self.assertEqual(result["completed"], 2)
        self.assertTrue((workspace_root / "001_cover.png").exists())
        self.assertTrue((workspace_root / "002_page.png").exists())

    def test_numbering_workflow_replaces_filename_with_sequence(self) -> None:
        workspace_root = FileManageWorkspaceSetting.load().root_path
        workspace_root.mkdir(parents=True, exist_ok=True)

        first = workspace_root / "test.jpg"
        second = workspace_root / "test2.jpg"
        create_test_image(first, color="red")
        create_test_image(second, color="purple")

        rename_setting = RenameSetting.load()
        rename_setting.workflow = "numbering"
        rename_setting.number_action = "replace_with_sequence"
        rename_setting.start_number = 1
        rename_setting.increment = 1
        rename_setting.number_width = 3
        rename_setting.include_subfolders = True
        rename_setting.order_ascending = True
        rename_setting.save()

        result = execute_rename_actions(workspace_root, rename_setting)
        self.assertEqual(result["completed"], 2)
        self.assertTrue((workspace_root / "001.jpg").exists())
        self.assertTrue((workspace_root / "002.jpg").exists())

    def test_text_transform_prefix_action_uses_per_folder_alphabet_mode(self) -> None:
        workspace_root = FileManageWorkspaceSetting.load().root_path
        first_folder = workspace_root / "folder_a"
        second_folder = workspace_root / "folder_b"

        create_test_image(first_folder / "cover.jpg", color="green")
        create_test_image(second_folder / "cover.jpg", color="yellow")

        rename_setting = RenameSetting.load()
        rename_setting.workflow = "text_transform"
        rename_setting.text_action = "add_prefix"
        rename_setting.per_folder_alpha_mode = True
        rename_setting.start_letter = "a"
        rename_setting.added_text = ""
        rename_setting.include_subfolders = True
        rename_setting.order_ascending = True
        rename_setting.save(
            update_fields=[
                "workflow",
                "text_action",
                "per_folder_alpha_mode",
                "start_letter",
                "added_text",
                "include_subfolders",
                "order_ascending",
                "updated_at",
            ]
        )

        result = execute_rename_actions(workspace_root, rename_setting)
        self.assertEqual(result["completed"], 2)
        self.assertTrue((first_folder / "acover.jpg").exists())
        self.assertTrue((second_folder / "bcover.jpg").exists())

    def test_text_transform_suffix_action_uses_per_folder_alphabet_mode(self) -> None:
        workspace_root = FileManageWorkspaceSetting.load().root_path
        first_folder = workspace_root / "folder_a"
        second_folder = workspace_root / "folder_b"

        create_test_image(first_folder / "cover.jpg", color="green")
        create_test_image(second_folder / "cover.jpg", color="yellow")

        rename_setting = RenameSetting.load()
        rename_setting.workflow = "text_transform"
        rename_setting.text_action = "add_suffix"
        rename_setting.per_folder_alpha_mode = True
        rename_setting.start_letter = "a"
        rename_setting.added_text = ""
        rename_setting.include_subfolders = True
        rename_setting.order_ascending = True
        rename_setting.save(
            update_fields=[
                "workflow",
                "text_action",
                "per_folder_alpha_mode",
                "start_letter",
                "added_text",
                "include_subfolders",
                "order_ascending",
                "updated_at",
            ]
        )

        result = execute_rename_actions(workspace_root, rename_setting)
        self.assertEqual(result["completed"], 2)
        self.assertTrue((first_folder / "covera.jpg").exists())
        self.assertTrue((second_folder / "coverb.jpg").exists())

    def test_change_extension_operation_skips_files_already_using_target_extension(self) -> None:
        workspace_root = FileManageWorkspaceSetting.load().root_path
        workspace_root.mkdir(parents=True, exist_ok=True)

        source_file = workspace_root / "already.jpg"
        create_test_image(source_file, color="red")
        original_mtime = source_file.stat().st_mtime_ns

        extension_setting = ExtensionSetting.load()
        extension_setting.old_extension = ".all"
        extension_setting.new_extension = ".jpg"
        extension_setting.save(update_fields=["old_extension", "new_extension", "updated_at"])

        result = execute_extension_actions(workspace_root, extension_setting)
        self.assertEqual(result["completed"], 0)
        self.assertTrue(source_file.exists())
        self.assertEqual(source_file.stat().st_mtime_ns, original_mtime)

    def test_extension_operation_page_embeds_settings_form_and_saves_changes(self) -> None:
        url = reverse("filemanage_change_file_extension")
        current_workspace = FileManageWorkspaceSetting.load()
        new_workspace_root = current_workspace.root_path.parent / "filemanage-inline-root"

        response = self.client.get(url)
        self.assertContains(response, 'data-filemanage-setting-form', count=1)
        self.assertContains(response, 'name="root_folder"')
        self.assertContains(response, 'name="old_extension"')
        self.assertContains(response, 'name="new_extension"')
        self.assertContains(response, 'All (all image types)')
        self.assertContains(response, 'Save Settings')
        self.assertContains(response, 'type="reset"')

        save_response = self.client.post(
            url,
            {
                "root_folder": str(new_workspace_root),
                "include_subfolders": "on",
                "old_extension": ".png",
                "new_extension": ".webp",
            },
        )

        self.assertRedirects(save_response, url)
        workspace_setting = FileManageWorkspaceSetting.load()
        setting = ExtensionSetting.load()
        self.assertEqual(workspace_setting.root_folder, str(new_workspace_root))
        self.assertEqual(setting.old_extension, ".png")
        self.assertEqual(setting.new_extension, ".webp")
        self.assertTrue(setting.include_subfolders)

    def test_images_to_pdf_operation_uses_configured_jpg_quality(self) -> None:
        workspace_root = FileManageWorkspaceSetting.load().root_path
        source_folder = workspace_root / "pages"
        create_test_image(source_folder / "page_1.png", color="orange")
        create_test_image(source_folder / "page_2.png", color="yellow")

        setting = ImagesToPdfSetting.load()
        setting.include_subfolders = True
        setting.delete_source_images = False
        setting.jpg_quality = 42
        setting.save(update_fields=["include_subfolders", "delete_source_images", "jpg_quality", "updated_at"])

        with patch("sorter.apps.filemanage.services.reencode_images_for_pdf_quality", wraps=reencode_images_for_pdf_quality) as reencode_mock:
            result = execute_images_to_pdf_actions(workspace_root, setting)

        self.assertEqual(result["planned"], 1)
        self.assertEqual(result["completed"], 1)
        reencode_mock.assert_called_once()
        self.assertEqual(reencode_mock.call_args.args[1], 42)
        self.assertTrue((source_folder / "pages.pdf").exists())

    def test_operation_snapshot_endpoint_returns_latest_preview_after_run(self) -> None:
        workspace_root = FileManageWorkspaceSetting.load().root_path
        workspace_root.mkdir(parents=True, exist_ok=True)

        source_file = workspace_root / "scene_old.png"
        create_test_image(source_file, color="purple")

        rename_setting = RenameSetting.load()
        rename_setting.workflow = "text_transform"
        rename_setting.search_text = "_old"
        rename_setting.replace_text = "_new"
        rename_setting.include_subfolders = True
        rename_setting.save(
            update_fields=[
                "workflow",
                "search_text",
                "replace_text",
                "include_subfolders",
                "updated_at",
            ]
        )

        snapshot_url = reverse("filemanage_operation_snapshot", args=["rename-files"])

        before_payload = self.client.get(snapshot_url).json()
        self.assertEqual(before_payload["preview"]["total_count"], 1)
        self.assertIn("created_label", before_payload["preview"]["items"][0])

        execute_rename_actions(workspace_root, rename_setting)

        after_payload = self.client.get(snapshot_url).json()
        self.assertEqual(after_payload["preview"]["total_count"], 0)
        self.assertEqual(after_payload["workspace_snapshot"]["file_count"], 1)

    def test_run_endpoint_persists_job_status_in_database(self) -> None:
        workspace_root = FileManageWorkspaceSetting.load().root_path
        workspace_root.mkdir(parents=True, exist_ok=True)
        create_test_image(workspace_root / "scene_old.png", color="purple")

        rename_setting = RenameSetting.load()
        rename_setting.workflow = "text_transform"
        rename_setting.search_text = "_old"
        rename_setting.replace_text = "_new"
        rename_setting.include_subfolders = True
        rename_setting.save(
            update_fields=[
                "workflow",
                "search_text",
                "replace_text",
                "include_subfolders",
                "updated_at",
            ]
        )

        run_response = self.client.post(reverse("filemanage_operation_run", args=["rename-files"]))
        self.assertEqual(run_response.status_code, 200)
        payload = run_response.json()
        self.assertTrue(FileManageOperationJob.objects.filter(pk=payload["job_id"]).exists())

        terminal_status = None
        for _ in range(40):
            status_response = self.client.get(payload["status_url"])
            self.assertEqual(status_response.status_code, 200)
            job = status_response.json()
            if job["status"] in {"completed", "empty", "dependency_missing", "error"}:
                terminal_status = job["status"]
                break
            time.sleep(0.05)

        self.assertEqual(terminal_status, "completed")
        persisted_job = FileManageOperationJob.objects.get(pk=payload["job_id"])
        self.assertEqual(persisted_job.status, "completed")
        self.assertEqual(persisted_job.completed_count, 1)
