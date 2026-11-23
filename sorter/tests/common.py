from __future__ import annotations

import io
import tempfile
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image


def create_test_image(path: Path, color: str = "navy") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (48, 48), color=color)
    image.save(path)
    image.close()


def create_uploaded_test_image(name: str = "reference.png", color: str = "navy") -> SimpleUploadedFile:
    buffer = io.BytesIO()
    image = Image.new("RGB", (48, 48), color=color)
    image.save(buffer, format="PNG")
    image.close()
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


class BaseSmokeTestCase(TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        self.base_path = Path(self.temp_dir.name)
        self.media_root = self.base_path / "media"
        self.workspace_dir = self.base_path / "workspace"
        self.inbox_dir = self.workspace_dir / "inbox"
        self.library_root = self.workspace_dir / "library"
        self.preview_cache_dir = self.base_path / ".cache" / "preview_cache"

        self.override = override_settings(
            MEDIA_ROOT=self.media_root,
            WORKSPACE_DIR=self.workspace_dir,
            INBOX_DIR=self.inbox_dir,
            LIBRARY_ROOT=self.library_root,
            PREVIEW_CACHE_DIR=self.preview_cache_dir,
        )
        self.override.enable()
        self.addCleanup(self.override.disable)

        for folder in (
            self.media_root,
            self.media_root / "references",
            self.workspace_dir,
            self.inbox_dir,
            self.library_root,
            self.preview_cache_dir,
        ):
            folder.mkdir(parents=True, exist_ok=True)
