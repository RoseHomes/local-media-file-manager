from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.db import models


SORT_OPTION_CHOICES = [
    ("date_desc", "Newest first"),
    ("date_asc", "Oldest first"),
    ("name_asc", "Name A-Z"),
    ("name_desc", "Name Z-A"),
]


def _coerce_json_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().casefold() in {"1", "true", "on", "yes"}


class FanartSetting(models.Model):
    source_folder = models.CharField(
        max_length=500,
        help_text="Folder that contains unsorted fanart files.",
    )
    include_subfolders = models.BooleanField(
        default=True,
        help_text="When enabled, Fanart File scans nested folders under the source path too.",
    )
    destination_folder = models.CharField(
        max_length=500,
        help_text="Root folder where sorted game folders will be created.",
    )
    filename_separator = models.CharField(
        max_length=10,
        blank=True,
        default="",
        help_text="Text inserted between filename parts. Leave blank for no separator.",
    )
    date_format_pattern = models.CharField(
        max_length=40,
        default="YYYYMMDD",
        help_text="Use tokens DD, MM, YYYY, YY and optional separators, for example YYYYMMDD or DD-MM-YY.",
    )
    sequence_padding = models.PositiveSmallIntegerField(
        default=3,
        help_text="Number of digits for the running number, for example 3 becomes 001.",
    )
    default_sort = models.CharField(
        max_length=20,
        choices=SORT_OPTION_CHOICES,
        default="date_desc",
        help_text="Default sort order used when fanart file opens.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Fanart setting"
        verbose_name_plural = "Fanart settings"

    def __str__(self) -> str:
        return "Fanart Setting"

    @classmethod
    def load(cls) -> "FanartSetting":
        instance, _ = cls.objects.get_or_create(
            pk=1,
            defaults={
                "source_folder": str(settings.INBOX_DIR),
                "include_subfolders": True,
                "destination_folder": str(settings.LIBRARY_ROOT),
            },
        )
        return instance

    @property
    def source_path(self) -> Path:
        return Path(self.source_folder).expanduser()

    @property
    def destination_path(self) -> Path:
        return Path(self.destination_folder).expanduser()

    def format_date_token(self, value: datetime) -> str:
        replacements = {
            "YYYY": value.strftime("%Y"),
            "YY": value.strftime("%y"),
            "MM": value.strftime("%m"),
            "DD": value.strftime("%d"),
        }
        result = self.date_format_pattern
        for token in ("YYYY", "YY", "MM", "DD"):
            result = result.replace(token, replacements[token])
        return result

    def sample_filename(self) -> str:
        separator = self.filename_separator
        date_token = self.format_date_token(datetime(2029, 2, 1, 0, 0))
        sequence_token = str(1).zfill(self.sequence_padding)
        return f"Character{separator}{date_token}{separator}{sequence_token}.jpg"


class AlbumSetting(models.Model):
    album_paths = models.JSONField(default=list, blank=True)
    default_sort = models.CharField(
        max_length=20,
        choices=SORT_OPTION_CHOICES,
        default="date_desc",
        help_text="Default sort order used when fanart album opens.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Album setting"
        verbose_name_plural = "Album settings"

    def __str__(self) -> str:
        return "Album Setting"

    @classmethod
    def load(cls) -> "AlbumSetting":
        instance, _ = cls.objects.get_or_create(pk=1, defaults={"album_paths": []})
        return instance

    @property
    def normalized_entries(self) -> list[dict[str, object]]:
        cleaned: list[dict[str, object]] = []
        seen: set[str] = set()

        for raw_entry in self.album_paths or []:
            if isinstance(raw_entry, dict):
                raw_path = raw_entry.get("path", "")
                raw_root_game_id = raw_entry.get("root_game_id", "")
                raw_follow_subfolder = raw_entry.get("follow_subfolder_from_url", False)
            else:
                raw_path = raw_entry
                raw_root_game_id = ""
                raw_follow_subfolder = False

            text = str(raw_path).strip()
            if not text:
                continue

            normalized = str(Path(text).expanduser())
            lowered = normalized.lower()
            if lowered in seen:
                continue

            seen.add(lowered)
            try:
                root_game_id = int(str(raw_root_game_id).strip()) if str(raw_root_game_id).strip() else None
            except (TypeError, ValueError):
                root_game_id = None

            cleaned.append(
                {
                    "path": normalized,
                    "root_game_id": root_game_id,
                    "follow_subfolder_from_url": _coerce_json_bool(raw_follow_subfolder),
                }
            )

        return cleaned

    @property
    def normalized_paths(self) -> list[str]:
        return [str(entry["path"]) for entry in self.normalized_entries]

