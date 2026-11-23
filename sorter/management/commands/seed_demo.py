from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from PIL import Image, ImageDraw

from sorter.apps.catalog.models import Character, Game


def create_sample_image(folder: Path, name: str, accent: str) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    try:
        output = (folder / name).open("xb")
    except FileExistsError:
        return

    with output, Image.new("RGB", (640, 400), "#18152c") as image:
        draw = ImageDraw.Draw(image)
        draw.ellipse((220, 65, 420, 265), fill=accent)
        draw.line((80, 300, 560, 300), fill=accent, width=3)
        draw.text((100, 326), "ORBITAL GARDEN / SYNTHETIC DEMO", fill="white")
        image.save(output, format="PNG")


class Command(BaseCommand):
    help = "Add a fictional catalog and generated images to the default demo folders."

    def handle(self, *args, **options):
        game, _ = Game.objects.get_or_create(title="Orbital Garden", main_folder=None)
        Character.objects.get_or_create(game=game, name="Nova")
        Character.objects.get_or_create(game=game, name="Aster")

        create_sample_image(settings.INBOX_DIR, "demo-orbit-01.png", "#b9a0ff")
        create_sample_image(settings.INBOX_DIR, "demo-orbit-02.png", "#78dac8")
        filemanage_demo = settings.WORKSPACE_DIR / "filemanage" / "demo"
        create_sample_image(filemanage_demo, "demo-page-01.png", "#78dac8")
        create_sample_image(filemanage_demo, "demo-page-02.png", "#e8a4bf")

        self.stdout.write(self.style.SUCCESS("Demo catalog and sample images are ready."))
