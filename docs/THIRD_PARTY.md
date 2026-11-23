# Third-party notices

| Component | Role | License |
| --- | --- | --- |
| [Django](https://github.com/django/django/blob/main/LICENSE) | Web application framework | BSD-3-Clause |
| [asgiref](https://github.com/django/asgiref/blob/main/LICENSE) | Django dependency | BSD-3-Clause |
| [sqlparse](https://github.com/andialbrecht/sqlparse/blob/master/LICENSE) | Django dependency | BSD-3-Clause |
| [tzdata](https://pypi.org/project/tzdata/) | IANA time zone data for Windows | Apache-2.0 package distribution, with upstream time zone data notices |
| [Pillow](https://github.com/python-pillow/Pillow/blob/main/LICENSE) | Image processing | MIT-CMU |
| [pypdfium2](https://pypi.org/project/pypdfium2/) | PDF-to-image rendering | Apache-2.0 or BSD-3-Clause for the bindings, with a BSD-style license and bundled notices for PDFium |
| [Tailwind CSS](https://github.com/tailwindlabs/tailwindcss/blob/main/LICENSE) | Stylesheet build | MIT. The distributed CSS includes the Tailwind banner and the [license text](TAILWIND-LICENSE.txt) ships with the project. |
| [FFmpeg](https://ffmpeg.org/legal.html) | Optional external WebP-to-MP4 encoder | Build-dependent LGPL or GPL terms. This project invokes a separately installed executable. |

Python and npm dependencies are downloaded from their public registries during setup. Retain the notices packaged with wheels and binaries if redistributing them. FFmpeg builds with libx264 typically carry GPL terms. The earlier PyMuPDF integration was replaced with PDFium in this edition. The export includes no Python wheels, npm dependency directories, or FFmpeg binary.
