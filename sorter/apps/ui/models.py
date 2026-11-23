from django.db import models


INTERFACE_LANGUAGE_MODE_CHOICES = [
    ("en", "English"),
    ("th", "ไทย"),
    ("mixed", "English title + Thai description"),
]

INTERFACE_THEME_CHOICES = [
    ("cocoa-brown", "Cocoa Brown"),
    ("mystic-violet", "Mystic Violet"),
    ("cotton-candy-cloud", "Cotton Candy Cloud"),
    ("lunar-cloud", "Lunar Cloud"),
    ("electric-violet", "Electric Violet"),
]


class InterfaceTextSetting(models.Model):
    language_mode = models.CharField(
        max_length=20,
        choices=INTERFACE_LANGUAGE_MODE_CHOICES,
        default="en",
        help_text="Choose how menus, page titles, and page descriptions are displayed.",
    )
    theme_name = models.CharField(
        max_length=40,
        choices=INTERFACE_THEME_CHOICES,
        default="mystic-violet",
        help_text="Choose the global interface theme.",
    )
    menu_config = models.JSONField(
        default=list,
        blank=True,
        help_text="Custom order and grouping for the sidebar navigation.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Interface text setting"
        verbose_name_plural = "Interface text settings"

    def __str__(self) -> str:
        return "Interface Text Setting"

    @classmethod
    def load(cls) -> "InterfaceTextSetting":
        instance, _ = cls.objects.get_or_create(pk=1)
        return instance
