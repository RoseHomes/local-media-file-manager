from .text import build_ui_bundle


def ui_bundle(request):
    return {"ui": build_ui_bundle()}


