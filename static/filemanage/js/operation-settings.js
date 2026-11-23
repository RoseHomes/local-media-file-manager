(() => {
    const settingForms = Array.from(document.querySelectorAll("form[data-filemanage-setting-form]"));
    if (!settingForms.length) {
        return;
    }

    function syncFormAfterReset(form) {
        window.requestAnimationFrame(() => {
            Array.from(form.elements).forEach((input) => {
                input.dispatchEvent(new Event("change", { bubbles: true }));
                if (input.tagName === "SELECT") {
                    input.dispatchEvent(new Event("rich-select:refresh", { bubbles: true }));
                }
            });
        });
    }

    settingForms.forEach((form) => {
        form.addEventListener("reset", () => {
            syncFormAfterReset(form);
        });
    });
})();
