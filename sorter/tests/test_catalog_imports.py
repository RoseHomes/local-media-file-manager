from pathlib import Path

from django.conf import settings
from django.urls import reverse

from sorter.models import Character, Game

from .common import BaseSmokeTestCase, create_test_image, create_uploaded_test_image


class ImportFlowTests(BaseSmokeTestCase):
    def test_games_setting_preview_and_save_imports_root_and_subfolder(self) -> None:
        scan_root = self.base_path / "scan-games"
        (scan_root / "Orbital Garden" / "Chibi").mkdir(parents=True, exist_ok=True)

        preview_response = self.client.post(
            reverse("games_setting"),
            {
                "root_folder": str(scan_root),
                "action": "preview",
            },
        )
        self.assertEqual(preview_response.status_code, 302)
        preview_payload = self.client.session.get("games_setting_preview")
        self.assertIsNotNone(preview_payload)

        save_response = self.client.post(
            reverse("games_setting"),
            {
                "root_folder": str(scan_root),
                "action": "save",
                "row_index": ["0", "1"],
                "row_active_0": "1",
                "row_game_id_0": "",
                "row_title_0": "Orbital Garden Custom",
                "row_folder_name_0": "Orbital Garden",
                "row_parent_index_0": "",
                "row_kind_0": "root",
                "row_use_folder_name_0": "1",
                "row_active_1": "1",
                "row_game_id_1": "",
                "row_title_1": "Chibi Alt",
                "row_folder_name_1": "Chibi",
                "row_parent_index_1": "0",
                "row_kind_1": "subfolder",
            },
        )
        self.assertEqual(save_response.status_code, 302)

        root_game = Game.objects.get(main_folder__isnull=True, title="Orbital Garden Custom")
        subfolder_game = Game.objects.get(main_folder=root_game, title="Chibi Alt")
        self.assertEqual(root_game.folder_name, "Orbital Garden")
        self.assertEqual(subfolder_game.folder_name, "Chibi")
        self.assertTrue(root_game.use_folder_name_as_filename)

    def test_character_setting_save_creates_character_and_reference_image(self) -> None:
        game = Game.objects.create(title="OrbitalGarden", folder_name="Orbital Garden")
        source_root = self.base_path / "character-import"
        image_path = source_root / "Orbital Garden" / "GDDC_Game Development Department.png"
        create_test_image(image_path, color="green")

        response = self.client.post(
            reverse("character_setting"),
            {
                "root_folder": str(source_root),
                "action": "save",
                "row_index": ["0"],
                "row_active_0": "1",
                "row_game_id_0": str(game.id),
                "row_game_title_0": game.title,
                "row_game_folder_0": "Orbital Garden",
                "row_character_name_0": "GDDC",
                "row_character_description_0": "Game Development Department",
                "row_source_dir_0": str(image_path.parent),
                "row_source_image_path_0": str(image_path),
            },
        )
        self.assertEqual(response.status_code, 302)

        character = Character.objects.get(game=game, name="GDDC")
        self.assertEqual(character.description, "Game Development Department")
        self.assertTrue(character.reference_image.name.endswith(".png"))
        self.assertTrue((Path(settings.MEDIA_ROOT) / character.reference_image.name).exists())

    def test_character_setting_preview_splits_name_and_description_on_first_underscore(self) -> None:
        game = Game.objects.create(title="OrbitalGarden", folder_name="Orbital Garden")
        source_root = self.base_path / "character-preview"
        image_path = source_root / "Orbital Garden" / "GDDC_Game Development Department.png"
        create_test_image(image_path, color="green")

        response = self.client.post(
            reverse("character_setting"),
            {
                "root_folder": str(source_root),
                "action": "preview",
            },
        )
        self.assertEqual(response.status_code, 302)

        preview_payload = self.client.session.get("character_setting_preview")
        self.assertIsNotNone(preview_payload)
        self.assertEqual(preview_payload["rows"][0]["character_name"], "GDDC")
        self.assertEqual(preview_payload["rows"][0]["character_description"], "Game Development Department")
        self.assertEqual(preview_payload["rows"][0]["game_id"], game.id)

    def test_character_setting_preview_keeps_plain_filename_as_name_without_description(self) -> None:
        Game.objects.create(title="OrbitalGarden", folder_name="Orbital Garden")
        source_root = self.base_path / "character-preview-plain"
        image_path = source_root / "Orbital Garden" / "Shiroko.png"
        create_test_image(image_path, color="green")

        response = self.client.post(
            reverse("character_setting"),
            {
                "root_folder": str(source_root),
                "action": "preview",
            },
        )
        self.assertEqual(response.status_code, 302)

        preview_payload = self.client.session.get("character_setting_preview")
        self.assertIsNotNone(preview_payload)
        self.assertEqual(preview_payload["rows"][0]["character_name"], "Shiroko")
        self.assertEqual(preview_payload["rows"][0]["character_description"], "")

    def test_character_setting_manual_preview_builds_single_row_with_uploaded_image(self) -> None:
        game = Game.objects.create(title="OrbitalGarden", folder_name="Orbital Garden")

        response = self.client.post(
            reverse("character_setting"),
            {
                "import_mode": "manual",
                "action": "preview",
                "manual_game": str(game.id),
                "manual_name": "Arona",
                "manual_description": "System guide",
                "manual_reference_image": create_uploaded_test_image("arona.png", color="green"),
            },
        )
        self.assertEqual(response.status_code, 302)

        preview_payload = self.client.session.get("character_setting_preview")
        self.assertIsNotNone(preview_payload)
        self.assertEqual(preview_payload["import_mode"], "manual")
        self.assertEqual(preview_payload["rows"][0]["game_id"], game.id)
        self.assertEqual(preview_payload["rows"][0]["character_name"], "Arona")
        self.assertEqual(preview_payload["rows"][0]["character_description"], "System guide")
        self.assertTrue(preview_payload["rows"][0]["source_image_path"])
        self.assertTrue(Path(preview_payload["rows"][0]["source_image_path"]).exists())

    def test_character_setting_manual_save_creates_character_with_reference_image(self) -> None:
        game = Game.objects.create(title="OrbitalGarden", folder_name="Orbital Garden")

        preview_response = self.client.post(
            reverse("character_setting"),
            {
                "import_mode": "manual",
                "action": "preview",
                "manual_game": str(game.id),
                "manual_name": "Plana",
                "manual_description": "Support AI",
                "manual_reference_image": create_uploaded_test_image("plana.png", color="purple"),
            },
        )
        self.assertEqual(preview_response.status_code, 302)

        preview_payload = self.client.session.get("character_setting_preview")
        self.assertIsNotNone(preview_payload)
        temp_image_path = Path(preview_payload["rows"][0]["source_image_path"])
        self.assertTrue(temp_image_path.exists())

        response = self.client.post(
            reverse("character_setting"),
            {
                "import_mode": "manual",
                "action": "save",
                "preview_import_mode": "manual",
                "preview_root_path": "Manual entry",
                "preview_skip_existing": "0",
                "row_index": ["0"],
                "row_active_0": "1",
                "row_game_id_0": str(game.id),
                "row_game_title_0": game.title,
                "row_game_folder_0": game.folder_name,
                "row_character_name_0": "Plana",
                "row_character_description_0": "Support AI",
                "row_source_dir_0": "Manual upload",
                "row_source_image_path_0": str(temp_image_path),
            },
        )
        self.assertEqual(response.status_code, 302)

        character = Character.objects.get(game=game, name="Plana")
        self.assertEqual(character.description, "Support AI")
        self.assertTrue(bool(character.reference_image))
        self.assertTrue((Path(settings.MEDIA_ROOT) / character.reference_image.name).exists())
        self.assertFalse(temp_image_path.exists())

    def test_deleting_character_setting_entry_removes_reference_image_file(self) -> None:
        game = Game.objects.create(title="OrbitalGarden", folder_name="Orbital Garden")
        character = Character.objects.create(game=game, name="Shiroko", reference_image="references/shiroko.png")
        image_path = Path(settings.MEDIA_ROOT) / character.reference_image.name
        create_test_image(image_path, color="green")

        response = self.client.post(
            reverse("character_setting"),
            {
                "action": "delete_saved",
                "character_id": str(character.id),
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Character.objects.filter(pk=character.id).exists())
        self.assertFalse(image_path.exists())

    def test_deleting_game_setting_entry_removes_cascaded_character_reference_images(self) -> None:
        game = Game.objects.create(title="OrbitalGarden", folder_name="Orbital Garden")
        character = Character.objects.create(game=game, name="Shiroko", reference_image="references/shiroko.png")
        image_path = Path(settings.MEDIA_ROOT) / character.reference_image.name
        create_test_image(image_path, color="green")

        response = self.client.post(
            reverse("games_setting"),
            {
                "action": "delete_saved",
                "game_id": str(game.id),
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Game.objects.filter(pk=game.id).exists())
        self.assertFalse(Character.objects.filter(pk=character.id).exists())
        self.assertFalse(image_path.exists())

    def test_updating_saved_game_setting_persists_folder_name_mode(self) -> None:
        game = Game.objects.create(title="OrbitalGarden", folder_name="Orbital Garden")

        response = self.client.post(
            reverse("games_setting"),
            {
                "action": "update_saved",
                "game_id": str(game.id),
                "saved_title": "Orbital Garden Edited",
                "saved_folder_name": "Orbital Garden Folder",
                "saved_use_folder_name_as_filename": "1",
            },
        )
        self.assertEqual(response.status_code, 302)

        game.refresh_from_db()
        self.assertEqual(game.title, "Orbital Garden Edited")
        self.assertEqual(game.folder_name, "Orbital Garden Folder")
        self.assertTrue(game.use_folder_name_as_filename)
