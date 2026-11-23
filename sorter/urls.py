from django.urls import path

from sorter.apps.catalog import views as catalog_views
from sorter.apps.fanart import views as fanart_views
from sorter.apps.filemanage import views as filemanage_views
from sorter.apps.ui import views as ui_views


urlpatterns = [
    path("", fanart_views.workspace, name="workspace"),
    path("album/", fanart_views.fanart_album, name="fanart_album"),
    path("settings/fanart/", fanart_views.fanart_setting, name="fanart_setting"),
    path("settings/games/", catalog_views.games_setting, name="games_setting"),
    path("settings/characters/", catalog_views.character_setting, name="character_setting"),
    path("settings/album/", fanart_views.album_setting, name="album_setting"),
    path("settings/interface-text/", ui_views.interface_text_setting, name="interface_text_setting"),
    path("stage/", fanart_views.stage_selection, name="stage_selection"),
    path("unstage/", fanart_views.unstage_selection, name="unstage_selection"),
    path("clear-preview-cache/", fanart_views.clear_preview_cache_view, name="clear_preview_cache"),
    path("process/", fanart_views.process_staging, name="process_staging"),
    path("games/<int:game_id>/characters/", catalog_views.characters_for_game, name="characters_for_game"),
    path("workspace-file/<path:relative_path>", fanart_views.serve_workspace_file, name="workspace_file"),
    path("workspace-preview/<path:relative_path>", fanart_views.serve_workspace_preview, name="workspace_preview"),
    path("album-file/<int:root_index>/<path:relative_path>", fanart_views.serve_album_file, name="album_file"),
    path("album-preview/<int:root_index>/<path:relative_path>", fanart_views.serve_album_preview, name="album_preview"),
    path("filemanage/rename-files/", filemanage_views.filemanage_operation, {"operation_slug": "rename-files"}, name="filemanage_rename_files"),
    path("filemanage/change-file-extension/", filemanage_views.filemanage_operation, {"operation_slug": "change-file-extension"}, name="filemanage_change_file_extension"),
    path("filemanage/extract-zip/", filemanage_views.filemanage_operation, {"operation_slug": "extract-zip"}, name="filemanage_extract_zip"),
    path("filemanage/images-to-pdf/", filemanage_views.filemanage_operation, {"operation_slug": "images-to-pdf"}, name="filemanage_images_to_pdf"),
    path("filemanage/pdf-to-images/", filemanage_views.filemanage_operation, {"operation_slug": "pdf-to-images"}, name="filemanage_pdf_to_images"),
    path("filemanage/webp-to-mp4/", filemanage_views.filemanage_operation, {"operation_slug": "webp-to-mp4"}, name="filemanage_webp_to_mp4"),
    path("filemanage/<slug:operation_slug>/run/", filemanage_views.filemanage_operation_run, name="filemanage_operation_run"),
    path("filemanage/<slug:operation_slug>/snapshot/", filemanage_views.filemanage_operation_snapshot, name="filemanage_operation_snapshot"),
    path("filemanage/jobs/<slug:job_id>/", filemanage_views.filemanage_operation_job_status, name="filemanage_operation_job_status"),
]
