from django.urls import reverse

from sorter.models import AlbumSetting, Character, FanartSetting, Game

from .common import BaseSmokeTestCase, create_test_image


class FanartWorkflowTests(BaseSmokeTestCase):
    def test_album_setting_saves_root_game_binding_and_follow_flag(self) -> None:
        game = Game.objects.create(title="Orbital Garden", folder_name="orbital-garden")

        response = self.client.post(
            reverse("album_setting"),
            {
                "album_row_id": ["0"],
                "album_path_0": str(self.library_root),
                "album_root_game_0": str(game.id),
                "album_follow_sub_from_url_0": "1",
                "default_sort": "date_desc",
            },
        )

        self.assertEqual(response.status_code, 302)
        album_setting = AlbumSetting.load()
        self.assertEqual(
            album_setting.normalized_entries,
            [
                {
                    "path": str(self.library_root),
                    "root_game_id": game.id,
                    "follow_subfolder_from_url": True,
                }
            ],
        )

    def test_album_setting_can_delete_the_last_saved_album_path(self) -> None:
        album_setting = AlbumSetting.load()
        album_setting.album_paths = [
            {
                "path": str(self.library_root),
                "root_game_id": None,
                "follow_subfolder_from_url": False,
            }
        ]
        album_setting.default_sort = "date_desc"
        album_setting.save(update_fields=["album_paths", "default_sort", "updated_at"])

        response = self.client.post(
            reverse("album_setting"),
            {
                "default_sort": "date_desc",
            },
        )

        self.assertEqual(response.status_code, 302)
        album_setting.refresh_from_db()
        self.assertEqual(album_setting.normalized_entries, [])

    def test_fanart_album_hides_character_filter_when_legacy_album_path_has_no_root_game(self) -> None:
        album_setting = AlbumSetting.load()
        album_setting.album_paths = [str(self.library_root)]
        album_setting.save(update_fields=["album_paths", "updated_at"])

        game = Game.objects.create(title="Orbital Garden", folder_name="orbital-garden")
        Character.objects.create(game=game, name="Airi")
        create_test_image(self.library_root / game.output_path / "Airi240608001.jpg")

        response = self.client.get(
            reverse("fanart_album"),
            {"library": "0", "path": game.output_path},
        )

        self.assertNotContains(response, 'id="album-character-filter"')

    def test_fanart_album_hides_character_filter_for_folder_name_mode(self) -> None:
        album_setting = AlbumSetting.load()
        game = Game.objects.create(
            title="Starfield",
            folder_name="starfield",
            use_folder_name_as_filename=True,
        )
        album_setting.album_paths = [
            {
                "path": str(self.library_root),
                "root_game_id": game.id,
                "follow_subfolder_from_url": False,
            }
        ]
        album_setting.save(update_fields=["album_paths", "updated_at"])

        create_test_image(self.library_root / game.output_path / "Starfield230916002.jpg")

        response = self.client.get(
            reverse("fanart_album"),
            {"library": "0", "path": game.output_path},
        )

        self.assertNotContains(response, 'id="album-character-filter"')

    def test_fanart_album_hides_character_filter_when_album_root_points_to_game_folder_without_root_game(self) -> None:
        game = Game.objects.create(title="Orbital Garden", folder_name="Orbital Garden")
        Character.objects.create(game=game, name="Airi")
        create_test_image(self.library_root / game.output_path / "Airi240608001.jpg")

        album_setting = AlbumSetting.load()
        album_setting.album_paths = [str(self.library_root / game.output_path)]
        album_setting.save(update_fields=["album_paths", "updated_at"])

        response = self.client.get(reverse("fanart_album"), {"library": "0"})

        self.assertNotContains(response, 'id="album-character-filter"')

    def test_fanart_album_uses_configured_root_game_without_sub_lookup(self) -> None:
        root_game = Game.objects.create(title="Orbital Garden", folder_name="orbital-garden")
        Character.objects.create(game=root_game, name="Airi")
        create_test_image(self.library_root / "album-root" / "Comics" / "Airi240608001.jpg")

        album_setting = AlbumSetting.load()
        album_setting.album_paths = [
            {
                "path": str(self.library_root / "album-root"),
                "root_game_id": root_game.id,
                "follow_subfolder_from_url": False,
            }
        ]
        album_setting.save(update_fields=["album_paths", "updated_at"])

        response = self.client.get(reverse("fanart_album"), {"library": "0", "path": "Comics"})

        self.assertContains(response, 'id="album-character-filter"')
        self.assertContains(response, 'value="airi"')
        self.assertContains(response, 'data-character-name="airi"')

    def test_fanart_album_uses_subfolder_from_url_when_enabled(self) -> None:
        root_game = Game.objects.create(title="Orbital Garden", folder_name="orbital-garden")
        Game.objects.create(
            title="Event",
            folder_name="event",
            main_folder=root_game,
            use_folder_name_as_filename=True,
        )
        Character.objects.create(game=root_game, name="Airi")
        create_test_image(self.library_root / "album-root" / "Event" / "Airi240608001.jpg")

        album_setting = AlbumSetting.load()
        album_setting.album_paths = [
            {
                "path": str(self.library_root / "album-root"),
                "root_game_id": root_game.id,
                "follow_subfolder_from_url": True,
            }
        ]
        album_setting.save(update_fields=["album_paths", "updated_at"])

        response = self.client.get(reverse("fanart_album"), {"library": "0", "path": "Event"})

        self.assertNotContains(response, 'id="album-character-filter"')

    def test_stage_and_process_moves_image_to_library(self) -> None:
        create_test_image(self.inbox_dir / "sample.png")

        game = Game.objects.create(title="Orbital Garden", folder_name="orbital-garden")
        character = Character.objects.create(game=game, name="Nova")

        fanart_setting = FanartSetting.load()
        fanart_setting.filename_separator = "_"
        fanart_setting.sequence_padding = 3
        fanart_setting.save(update_fields=["filename_separator", "sequence_padding", "updated_at"])

        stage_response = self.client.post(
            reverse("stage_selection"),
            {
                "selected_images": ["sample.png"],
                "target_game": str(game.id),
                "game": str(game.id),
                "character": str(character.id),
            },
        )
        self.assertEqual(stage_response.status_code, 302)

        session = self.client.session
        staged_entries = session.get("staged_assignments", [])
        self.assertEqual(len(staged_entries), 1)
        self.assertEqual(staged_entries[0]["relative_path"], "sample.png")

        process_response = self.client.post(reverse("process_staging"))
        self.assertEqual(process_response.status_code, 302)

        moved_files = list((self.library_root / "orbital-garden").glob("Nova_*.png"))
        self.assertEqual(len(moved_files), 1)
        self.assertFalse((self.inbox_dir / "sample.png").exists())
        self.assertEqual(self.client.session.get("staged_assignments", []), [])

    def test_stage_selection_with_blank_ids_redirects_instead_of_crashing(self) -> None:
        create_test_image(self.inbox_dir / "sample.png")

        response = self.client.post(
            reverse("stage_selection"),
            {
                "selected_images": ["sample.png"],
                "target_game": "",
                "game": "",
                "character": "",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Select a valid game before saving to the queue.")
        self.assertEqual(self.client.session.get("staged_assignments", []), [])

    def test_stage_selection_uses_folder_name_without_character_when_enabled(self) -> None:
        create_test_image(self.inbox_dir / "sample.png")

        game = Game.objects.create(
            title="Orbital Garden",
            folder_name="orbital-garden",
            use_folder_name_as_filename=True,
        )

        response = self.client.post(
            reverse("stage_selection"),
            {
                "selected_images": ["sample.png"],
                "target_game": str(game.id),
                "game": "",
                "character": "",
            },
        )
        self.assertEqual(response.status_code, 302)

        process_response = self.client.post(reverse("process_staging"))
        self.assertEqual(process_response.status_code, 302)

        moved_files = list((self.library_root / "orbital-garden").glob("orbital-garden*.png"))
        self.assertEqual(len(moved_files), 1)
