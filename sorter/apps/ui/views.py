from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from sorter.apps.ui.forms import InterfaceTextSettingForm
from sorter.apps.ui.models import InterfaceTextSetting
from sorter.apps.ui.text import get_language_mode_label, get_page_text, get_page_ui_text, get_theme_label


def interface_text_setting(request: HttpRequest) -> HttpResponse:
    setting_instance = InterfaceTextSetting.load()
    page_text = get_page_text("interface_text_setting")
    interface_text = get_page_ui_text("ui_interface_text_setting")

    if request.method == "POST":
        form = InterfaceTextSettingForm(request.POST, instance=setting_instance)
        if form.is_valid():
            form.save()
            messages.success(request, interface_text["messages"]["saved"])
            return redirect("interface_text_setting")
    else:
        form = InterfaceTextSettingForm(instance=setting_instance)

    context = {
        "form": form,
        "setting_instance": setting_instance,
        "current_mode_label": get_language_mode_label(setting_instance.language_mode),
        "current_theme_label": get_theme_label(setting_instance.theme_name),
        "interface_text": interface_text,
        "active_nav": "interface_text_setting",
        "page_title": page_text["title"],
        "page_heading": page_text["title"],
        "page_intro_text": page_text["intro"],
        "page_kicker": page_text["kicker"],
    }
    return render(request, "ui/interface_text_setting.html", context)

