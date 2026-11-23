import re
from pathlib import Path

from django.test import SimpleTestCase


BROKEN_THAI_PATTERN = re.compile(r"\?\?|&#|\\u[0-9a-fA-F]{4}|[\u0080-\u009f\ufffd]")


def has_broken_thai_markers(content: str) -> bool:
    return BROKEN_THAI_PATTERN.search(content) is not None


class UITextCatalogTests(SimpleTestCase):
    def test_thai_locale_files_do_not_contain_broken_encoding_markers(self) -> None:
        thai_root = Path(__file__).resolve().parents[1] / "ui_text_data" / "th"

        for path in sorted(thai_root.rglob("*.json")):
            with self.subTest(path=path.name):
                content = path.read_text(encoding="utf-8-sig")
                self.assertFalse(
                    has_broken_thai_markers(content),
                    msg=f"Found suspicious Thai text marker in {path.name}",
                )

    def test_broken_thai_marker_helper_detects_common_mojibake_sample(self) -> None:
        broken = "เนเธเธฅเน€เธ”เธญเธฃเนเธซเธฅเธฑเธ"
        clean = "โฟลเดอร์หลัก"

        self.assertTrue(has_broken_thai_markers(broken))
        self.assertFalse(has_broken_thai_markers(clean))
