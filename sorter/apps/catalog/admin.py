from django import forms
from django.contrib import admin

from sorter.apps.catalog.models import Character, Game
from sorter.apps.fanart.models import AlbumSetting, FanartSetting


class GameAdminForm(forms.ModelForm):
    class Meta:
        model = Game
        fields = ("title", "folder_name", "main_folder")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        queryset = Game.objects.filter(main_folder__isnull=True).order_by("title")
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        self.fields["main_folder"].queryset = queryset


class CharacterInline(admin.TabularInline):
    model = Character
    extra = 1
    fields = ("name", "description", "reference_image")


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    form = GameAdminForm
    list_display = ("display_path", "resolved_folder_name", "main_folder", "updated_at")
    search_fields = ("title", "folder_name", "main_folder__title")
    fields = ("title", "folder_name", "main_folder")
    inlines = [CharacterInline]


@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "game", "updated_at")
    list_filter = ("game",)
    search_fields = ("name", "description", "game__title")
    fields = ("game", "name", "description", "reference_image")


@admin.register(FanartSetting)
class FanartSettingAdmin(admin.ModelAdmin):
    list_display = ("source_folder", "destination_folder", "updated_at")


@admin.register(AlbumSetting)
class AlbumSettingAdmin(admin.ModelAdmin):
    list_display = ("updated_at",)

