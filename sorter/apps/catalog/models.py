from pathlib import Path

from django.db import models
from django.db.models import Q
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils.text import slugify


class Game(models.Model):
    title = models.CharField(max_length=200)
    folder_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Optional custom folder name. Defaults to a slug based on the title.",
    )
    use_folder_name_as_filename = models.BooleanField(
        default=False,
        help_text="When enabled, Fanart File uses this game's folder name as the filename prefix instead of a character name.",
    )
    main_folder = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subfolder_games",
        help_text="Optional main folder. Leave blank for a normal top-level game.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]
        constraints = [
            models.UniqueConstraint(
                fields=["title", "main_folder"],
                name="unique_game_title_per_parent",
            ),
            models.UniqueConstraint(
                fields=["title"],
                condition=Q(main_folder__isnull=True),
                name="unique_root_game_title",
            ),
        ]

    def __str__(self) -> str:
        return self.display_path

    @property
    def resolved_folder_name(self) -> str:
        return self.folder_name or slugify(self.title) or self.title.replace(" ", "_")

    @property
    def display_path(self) -> str:
        if self.main_folder_id:
            return f"{self.main_folder.title}/{self.title}"
        return self.title

    @property
    def output_path(self) -> str:
        if self.main_folder_id:
            return f"{self.main_folder.resolved_folder_name}/{self.resolved_folder_name}"
        return self.resolved_folder_name

    @property
    def character_owner_id(self) -> int:
        return self.main_folder_id or self.id


class Character(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="characters")
    name = models.CharField(max_length=200)
    description = models.CharField(max_length=255, blank=True, default="")
    reference_image = models.ImageField(upload_to="references/", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["game", "name"],
                name="unique_character_per_game",
            )
        ]

    def __str__(self) -> str:
        return f"{self.game.title} / {self.name}"


@receiver(post_delete, sender=Character)
def delete_character_reference_image(sender, instance: Character, **kwargs) -> None:
    if instance.reference_image:
        instance.reference_image.delete(save=False)


class GameImportSetting(models.Model):
    root_folder = models.CharField(
        max_length=500,
        blank=True,
        default="",
        help_text="Path to the main game folder that should become one root game plus subfolders.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Game import setting"
        verbose_name_plural = "Game import settings"

    def __str__(self) -> str:
        return "Game Import Setting"

    @classmethod
    def load(cls) -> "GameImportSetting":
        instance, _ = cls.objects.get_or_create(pk=1)
        return instance

    @property
    def root_path(self) -> Path:
        return Path(self.root_folder).expanduser() if self.root_folder else Path()


class CharacterImportSetting(models.Model):
    root_folder = models.CharField(
        max_length=500,
        blank=True,
        default="",
        help_text="Path that contains game folders, with character reference images directly inside each game folder.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Character import setting"
        verbose_name_plural = "Character import settings"

    def __str__(self) -> str:
        return "Character Import Setting"

    @classmethod
    def load(cls) -> "CharacterImportSetting":
        instance, _ = cls.objects.get_or_create(pk=1)
        return instance

    @property
    def root_path(self) -> Path:
        return Path(self.root_folder).expanduser() if self.root_folder else Path()

