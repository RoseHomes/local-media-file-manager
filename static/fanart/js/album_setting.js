(() => {
    const list = document.getElementById("album-path-list");
    const addButton = document.getElementById("add-album-path");
    const template = document.getElementById("album-path-template");
    const modal = document.getElementById("album-path-delete-modal");
    const modalTarget = document.getElementById("album-path-delete-modal-target");
    const modalCancel = document.getElementById("album-path-delete-modal-cancel");
    const modalConfirm = document.getElementById("album-path-delete-modal-confirm");
    const configNode = document.getElementById("album-setting-js-config");
    const config = configNode ? JSON.parse(configNode.textContent) : {};
    const emptyRowTitle = String(config.emptyRowTitle || "").trim();

    if (!list || !template) {
        return;
    }

    let pendingRemoveRow = null;
    let pendingRemoveTrigger = null;
    let nextRowId = Array.from(list.querySelectorAll("[data-row-id-field]")).reduce((maxValue, field) => {
        const candidate = Number(field.value || "0");
        return Number.isFinite(candidate) ? Math.max(maxValue, candidate + 1) : maxValue;
    }, 0);

    function getRows() {
        return Array.from(list.querySelectorAll(".album-setting-row"));
    }

    function syncOpenRowState() {
        getRows().forEach((row) => {
            row.style.position = "relative";
            row.style.overflow = "visible";
            row.style.zIndex = row.querySelector(".rich-select-open") ? "20" : "0";
        });
    }

    function getRowTitle(row) {
        const pathInput = row.querySelector('input[id^="album_path_"]');
        const currentPath = pathInput instanceof HTMLInputElement ? pathInput.value.trim() : "";
        return currentPath || emptyRowTitle;
    }

    function syncRowTitle(row) {
        const title = row.querySelector("[data-album-row-title]");
        if (!title) {
            return;
        }
        title.textContent = getRowTitle(row);
    }

    function closeDeleteModal({ restoreFocus = true } = {}) {
        if (!modal) {
            return;
        }
        modal.classList.add("hidden");
        modal.setAttribute("aria-hidden", "true");
        document.body.classList.remove("overflow-hidden");

        const restoreTarget = pendingRemoveTrigger;
        pendingRemoveRow = null;
        pendingRemoveTrigger = null;

        if (restoreFocus && restoreTarget instanceof HTMLElement && document.contains(restoreTarget)) {
            restoreTarget.focus();
        }
    }

    function openDeleteModal(row, trigger) {
        if (!modal || !modalTarget) {
            row.remove();
            syncOpenRowState();
            addButton?.focus();
            return;
        }

        pendingRemoveRow = row;
        pendingRemoveTrigger = trigger;
        modalTarget.textContent = getRowTitle(row);
        modal.classList.remove("hidden");
        modal.setAttribute("aria-hidden", "false");
        document.body.classList.add("overflow-hidden");
        modalConfirm?.focus();
    }

    function removePendingRow() {
        if (!pendingRemoveRow) {
            closeDeleteModal();
            return;
        }

        const rowToRemove = pendingRemoveRow;
        closeDeleteModal({ restoreFocus: false });
        rowToRemove.remove();
        syncOpenRowState();

        const lastInput = list.querySelector(".album-setting-row:last-child input[id^='album_path_']");
        if (lastInput instanceof HTMLInputElement) {
            lastInput.focus();
            return;
        }
        addButton?.focus();
    }

    function bindRow(row) {
        if (!(row instanceof HTMLElement) || row.dataset.albumSettingBound === "true") {
            return;
        }

        row.dataset.albumSettingBound = "true";
        syncRowTitle(row);

        const removeButton = row.querySelector("[data-remove-path]");
        removeButton?.addEventListener("click", () => {
            openDeleteModal(row, removeButton);
        });

        const pathInput = row.querySelector('input[id^="album_path_"]');
        pathInput?.addEventListener("input", () => {
            syncRowTitle(row);
        });
    }

    function appendNewRow() {
        const rowId = String(nextRowId);
        nextRowId += 1;

        const fragment = template.content.cloneNode(true);
        fragment.querySelectorAll("[name],[id],[for],[value]").forEach((node) => {
            ["name", "id", "for", "value"].forEach((attribute) => {
                const currentValue = node.getAttribute(attribute);
                if (!currentValue || !currentValue.includes("__ROW_ID__")) {
                    return;
                }
                node.setAttribute(attribute, currentValue.replaceAll("__ROW_ID__", rowId));
            });
        });

        list.appendChild(fragment);
        const row = list.querySelector(".album-setting-row:last-child");
        if (row instanceof HTMLElement) {
            bindRow(row);
        }
        syncOpenRowState();

        const lastInput = list.querySelector(".album-setting-row:last-child input[id^='album_path_']");
        if (lastInput instanceof HTMLInputElement) {
            lastInput.focus();
        }
    }

    addButton?.addEventListener("click", appendNewRow);
    getRows().forEach(bindRow);
    syncOpenRowState();

    modalCancel?.addEventListener("click", () => {
        closeDeleteModal();
    });
    modalConfirm?.addEventListener("click", removePendingRow);
    modal?.addEventListener("click", (event) => {
        if (event.target === modal) {
            closeDeleteModal();
        }
    });

    document.addEventListener("click", () => {
        window.setTimeout(syncOpenRowState, 0);
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && modal && !modal.classList.contains("hidden")) {
            closeDeleteModal();
        }
    });
})();
