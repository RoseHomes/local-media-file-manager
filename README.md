# Local Media File Manager

A local Django app for organizing media and running batch file operations on Windows. Preview changes before running them, track batch progress in the browser, and browse the resulting library from the same workspace.

## Features

- **Media workspace.** Preview an inbox, stage images, assign a catalog entry, and batch move and rename files into a library.
- **Catalog and albums.** Manage games and characters, import them from folders, upload reference images, and browse completed albums.
- **Batch operations.** Rename files, change filename extensions, extract ZIP archives, assemble images into PDFs, render PDF pages to images, and convert static or animated WebP files to MP4.
- **Interface settings.** Customize navigation, choose a theme, and use English, Thai, or mixed interface text.

## Quick start on Windows

To start the synthetic demo from Command Prompt or PowerShell with Python 3.13 installed, run this command from the project folder.

```text
py -3.13 local_media_file_manager.py
```

Open [the demo](http://127.0.0.1:8001/) and press **Ctrl+C** in the same terminal to stop it. The launcher installs the pinned packages on first run and stores the demo under `%LOCALAPPDATA%/LocalMediaFileManager`.

### Manual setup

Open PowerShell in the project folder with Python 3.13 and the Windows Python Launcher installed. The setup script creates a virtual environment and installs the pinned Python packages.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\setup_python.ps1
$python = '.\.venv\Scripts\python.exe'
$env:DJANGO_SECRET_KEY = & $python -c "import secrets; print(secrets.token_urlsafe(48))"
$env:DJANGO_DEBUG = '1'
& $python manage.py migrate
& $python manage.py seed_demo
& $python manage.py runserver 127.0.0.1:8000
```

Open [the workspace](http://127.0.0.1:8000/). The demo command is optional. It creates a fictional **Orbital Garden** catalog, two generated inbox images, and two source images under `workspace/filemanage/demo/`. Stage an inbox image and assign it to Nova or Aster, or open FileManage and preview an Images to PDF job. The demo command keeps existing files with the same names.

Run `& $python manage.py createsuperuser` if you want to sign in to [Django admin](http://127.0.0.1:8000/admin/). Use the same signing key in later sessions if you want to keep existing session cookies valid. Set `DJANGO_DEBUG=1` when using Django's local development server to serve CSS and uploads. Debug mode defaults to off.

## Local files and optional tools

| Location | Contents |
| --- | --- |
| `workspace/inbox/` and `workspace/library/` | Source images and organized media |
| `workspace/filemanage/` | Default source for batch operations |
| `workspace/webp-to-mp4-output/` | Default MP4 output |
| `media/references/` | Uploaded character references |
| `db.sqlite3` and `.cache/` | Local settings, catalog, operation history, and preview cache |

Set `LMM_DATA_DIR` before startup to put all of these files under another directory. The app uses UTC unless you set `DJANGO_TIME_ZONE` to an IANA time zone, such as `America/Toronto`. Date-based file naming uses the file creation timestamp on Windows.

For WebP-to-MP4, install [FFmpeg](https://ffmpeg.org/download.html) with the `libx264` encoder and make `ffmpeg.exe` available on `PATH`. The other workflows work with the Python setup above. Changing an extension changes the filename only. Review previews and use disposable copies when trying move, rename, extraction, or conversion settings.

Local Media File Manager is a single-user application. Its routes are restricted to loopback connections and local Host headers. Run it directly on your machine, without a public proxy or tunnel, and process files you trust. Use screenshots or recordings to share a demo.

## Development

Django project settings live in `fanart_manager/`. The domains under `sorter/apps/` are catalog, fanart, file management, and interface settings. Templates and static assets follow those domains. English and Thai UI strings live in `sorter/ui_text_data/`.

The compiled stylesheet ships with the source. Install Node.js 22 or newer to rebuild it from `static/shared/src/input.css` using the npm lockfile.

```powershell
npm.cmd ci
npm.cmd run build:css
# Or use npm.cmd run watch:css while editing styles.
```

With the virtual environment and signing key configured as above, run the checks from the project folder.

```powershell
& $python manage.py check
& $python manage.py makemigrations --check --dry-run
& $python manage.py test
```

## Copyright and usage

Copyright © 2026 the Local Media File Manager project owner. **All Rights Reserved.**

The original source code and assets are publicly viewable for portfolio review. Reuse, modification, and redistribution require prior written permission from the copyright holder, except as permitted by applicable law or the rights granted under GitHub's Terms of Service. [Copyright notice](COPYRIGHT.md)

Third-party components and materials remain under their respective licenses. [Third-party notices](docs/THIRD_PARTY.md)
