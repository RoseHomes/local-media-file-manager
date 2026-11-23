document.addEventListener("DOMContentLoaded", () => {
    const hiddenInput = document.querySelector('input[name="menu_config"]');
    const container = document.getElementById("menu-ordering-grid");
    const modal = document.querySelector("[data-menu-order-modal]");
    const openButton = document.querySelector("[data-menu-order-open]");
    const closeButtons = document.querySelectorAll("[data-menu-order-close]");
    const previewContainer = document.querySelector("[data-menu-order-preview]");

    if (!hiddenInput || !container) {
        return;
    }

    const syncPreview = () => {
        if (!previewContainer) {
            return;
        }

        const fragment = document.createDocumentFragment();
        container.querySelectorAll(".menu-group-block").forEach((groupEl) => {
            const title = groupEl.querySelector(".menu-order-group-title")?.textContent?.trim() || groupEl.dataset.groupId || "";
            const chip = document.createElement("div");
            chip.className = "menu-order-preview-chip";

            const dot = document.createElement("span");
            dot.className = "menu-order-preview-dot";

            const label = document.createElement("span");
            label.className = "menu-order-preview-label";
            label.textContent = title;

            chip.append(dot, label);
            fragment.appendChild(chip);
        });

        previewContainer.replaceChildren(fragment);
    };

    const updateMenuConfig = () => {
        const config = [];
        container.querySelectorAll(".menu-group-block").forEach((groupEl) => {
            const groupId = groupEl.dataset.groupId;
            const itemIds = Array.from(groupEl.querySelectorAll(".menu-item-node")).map(
                (itemEl) => itemEl.dataset.itemId,
            );
            config.push({ id: groupId, items: itemIds });
        });
        hiddenInput.value = JSON.stringify(config);
        syncPreview();
    };

    const openModal = () => {
        modal?.classList.remove("hidden");
    };

    const closeModal = () => {
        modal?.classList.add("hidden");
    };

    updateMenuConfig();

    openButton?.addEventListener("click", openModal);
    closeButtons.forEach((button) => {
        button.addEventListener("click", closeModal);
    });
    modal?.addEventListener("click", (event) => {
        if (event.target === modal) {
            closeModal();
        }
    });
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && modal && !modal.classList.contains("hidden")) {
            closeModal();
        }
    });

    let draggedEl = null;

    container.addEventListener("dragstart", (event) => {
        const target = event.target;
        if (!(target instanceof HTMLElement)) {
            return;
        }

        if (target.classList.contains("menu-item-node") || target.classList.contains("menu-group-block")) {
            draggedEl = target;
            if (event.dataTransfer) {
                event.dataTransfer.effectAllowed = "move";
                event.dataTransfer.setData("text/plain", "");
            }
            window.setTimeout(() => {
                if (draggedEl) {
                    draggedEl.classList.add("opacity-40");
                }
            }, 0);
            event.stopPropagation();
        }
    });

    container.addEventListener("dragend", () => {
        if (!draggedEl) {
            return;
        }

        draggedEl.classList.remove("opacity-40");
        draggedEl = null;
        updateMenuConfig();
    });

    container.addEventListener("dragover", (event) => {
        if (!draggedEl) {
            return;
        }

        if (draggedEl.classList.contains("menu-item-node")) {
            const targetElement = event.target;
            if (!(targetElement instanceof Element)) {
                return;
            }

            const targetItem = targetElement.closest(".menu-item-node");
            const targetList = targetElement.closest(".menu-item-list");
            const draggedGroup = draggedEl.closest(".menu-item-list");

            if (targetList && targetList !== draggedGroup) {
                return;
            }
            if (targetItem && targetItem.closest(".menu-item-list") !== draggedGroup) {
                return;
            }

            event.preventDefault();
            event.stopPropagation();

            if (targetItem && targetItem !== draggedEl) {
                const rect = targetItem.getBoundingClientRect();
                const insertAfter = event.clientY > rect.top + rect.height / 2;
                targetItem.parentNode.insertBefore(draggedEl, insertAfter ? targetItem.nextSibling : targetItem);
            }
            return;
        }

        if (draggedEl.classList.contains("menu-group-block")) {
            const targetElement = event.target;
            if (!(targetElement instanceof Element)) {
                return;
            }

            event.preventDefault();
            event.stopPropagation();

            const targetGroup = targetElement.closest(".menu-group-block");
            if (targetGroup && targetGroup !== draggedEl) {
                const rect = targetGroup.getBoundingClientRect();
                const insertAfter = event.clientX > rect.left + rect.width / 2 || event.clientY > rect.top + rect.height / 2;
                targetGroup.parentNode.insertBefore(draggedEl, insertAfter ? targetGroup.nextSibling : targetGroup);
            }
        }
    });
});
