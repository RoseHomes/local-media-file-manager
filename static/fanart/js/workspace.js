const gameSelect = document.getElementById("game-select");
    const targetGameInput = document.getElementById("target-game-input");
    const gameInput = document.getElementById("game-input");
    const characterSearch = document.getElementById("character-search");
    const characterDropdown = document.getElementById("character-dropdown");
    const characterDropdownTrigger = document.getElementById("character-dropdown-trigger");
    const characterDropdownMenu = document.getElementById("character-dropdown-menu");
    const characterOptionList = document.getElementById("character-option-list");
    const characterSelectedLabel = document.getElementById("character-selected-label");
    const characterSelectedSubcopy = document.getElementById("character-selected-subcopy");
    const characterSelectedAvatarWrap = document.getElementById("character-selected-avatar-wrap");
    const characterSelectedAvatar = document.getElementById("character-selected-avatar");
    const characterInput = document.getElementById("character-input");
    const referenceImage = document.getElementById("reference-image");
    const referenceCopy = document.getElementById("reference-copy");
    const galleryFilter = document.getElementById("gallery-filter");
    const galleryShell = document.getElementById("gallery-shell");
    const gallery = document.getElementById("gallery");
    const galleryEmptyState = document.getElementById("gallery-empty-state");
    const visibleImagesCount = document.getElementById("visible-images-count");
    const queuedItemsCount = document.getElementById("queued-items-count");
    const selectedCount = document.getElementById("selected-count");
    const clearSelectedButton = document.getElementById("clear-selected");
    const saveToQueueButton = document.getElementById("save-to-queue-button");
    const sortSelect = document.getElementById("sort-select");
    const stagingQueueModal = document.getElementById("staging-queue-modal");
    const stagingQueueModalClose = document.getElementById("staging-queue-modal-close");
    const stagingQueueBulkForm = document.getElementById("staging-queue-bulk-form");
    const stagingQueueModalList = document.getElementById("staging-queue-modal-list");
    const stagingQueueSelectAll = document.getElementById("staging-queue-select-all");
    const stagingQueueSelectedCount = document.getElementById("staging-queue-selected-count");
    const stagingQueueBulkRemove = document.getElementById("staging-queue-bulk-remove");
    const stagingQueueOpenButton = document.getElementById("staging-queue-open");
    const stagingQueueSummaryCount = document.getElementById("staging-queue-summary-count");
    const stagingQueueSummarySubtitle = document.getElementById("staging-queue-summary-subtitle");
    const stagingQueueSummaryActions = document.getElementById("staging-queue-summary-actions");
    const stagingQueueModalEmpty = document.getElementById("staging-queue-modal-empty");
    const characterData = JSON.parse(document.getElementById("character-data").textContent);
    const workspaceText = JSON.parse(document.getElementById("workspace-text").textContent);
    let activeCharacters = [];
    let selectedCharacter = null;
    let lastSelectedCheckbox = null;
    let lastStagingQueueCheckbox = null;

    function selectedGameUsesFolderName() {
        const selectedOption = gameSelect?.options?.[gameSelect.selectedIndex];
        return (selectedOption?.dataset?.useFolderNameAsFilename || "0") === "1";
    }

    function selectedGameFilenameLabel() {
        const selectedOption = gameSelect?.options?.[gameSelect.selectedIndex];
        return selectedOption?.dataset?.filenameLabel || "";
    }

    function updateStageButtonState() {
        if (!saveToQueueButton) {
            return;
        }

        const hasImages = document.querySelectorAll('input[name="selected_images"]:checked').length > 0;
        const hasTargetGame = Boolean(targetGameInput?.value);
        const hasCharacterGame = Boolean(gameInput?.value);
        const hasCharacter = Boolean(characterInput?.value);
        const enabled = hasImages && hasTargetGame && (selectedGameUsesFolderName() || (hasCharacterGame && hasCharacter));

        saveToQueueButton.disabled = !enabled;
        saveToQueueButton.classList.toggle("opacity-50", !enabled);
        saveToQueueButton.classList.toggle("cursor-not-allowed", !enabled);
    }

    function updateSelectedCount() {
        const count = document.querySelectorAll('input[name="selected_images"]:checked').length;
        selectedCount.textContent = String(count);
        if (clearSelectedButton) {
            clearSelectedButton.disabled = count === 0;
            clearSelectedButton.classList.toggle("opacity-50", count === 0);
            clearSelectedButton.classList.toggle("cursor-not-allowed", count === 0);
        }
        updateStageButtonState();
    }

    function closeCharacterDropdown() {
        characterDropdownMenu.classList.add("hidden");
        characterDropdownTrigger.setAttribute("aria-expanded", "false");
        characterDropdown.classList.remove("rich-dropdown-open");
    }

    function openCharacterDropdown() {
        if (selectedGameUsesFolderName()) {
            return;
        }
        const selectedOption = gameSelect.options[gameSelect.selectedIndex];
        if (!selectedOption?.dataset?.characterGameId || !activeCharacters.length) {
            return;
        }
        characterDropdownMenu.classList.remove("hidden");
        characterDropdownTrigger.setAttribute("aria-expanded", "true");
        characterDropdown.classList.add("rich-dropdown-open");
        characterSearch.focus();
    }

    function syncSelectedCharacterPresentation() {
        if (!selectedCharacter) {
            characterInput.value = "";
            characterSelectedAvatarWrap.classList.add("hidden");
            characterSelectedAvatar.removeAttribute("src");

            const selectedOption = gameSelect.options[gameSelect.selectedIndex];
            if (!selectedOption?.dataset?.targetGameId) {
                characterSelectedLabel.textContent = workspaceText.select_game_first;
                characterSelectedSubcopy.textContent = workspaceText.reference_appears_here;
            } else if (selectedGameUsesFolderName()) {
                characterSelectedLabel.textContent = selectedGameFilenameLabel() || workspaceText.folder_name_mode;
                characterSelectedSubcopy.textContent = workspaceText.folder_name_character_not_required;
            } else if (!selectedOption?.dataset?.characterGameId) {
                characterSelectedLabel.textContent = workspaceText.select_game_first;
                characterSelectedSubcopy.textContent = workspaceText.reference_appears_here;
            } else if (!activeCharacters.length) {
                characterSelectedLabel.textContent = workspaceText.no_characters_for_game;
                characterSelectedSubcopy.textContent = workspaceText.add_characters_in_admin;
            } else {
                characterSelectedLabel.textContent = workspaceText.select_character;
                characterSelectedSubcopy.textContent = workspaceText.pick_from_list;
            }
            return;
        }

        characterInput.value = String(selectedCharacter.id);
        characterSelectedLabel.textContent = selectedCharacter.name;
        characterSelectedSubcopy.textContent = selectedCharacter.description || (
            selectedCharacter.reference_image_url
                ? workspaceText.reference_linked
                : workspaceText.no_reference_linked
        );

        if (selectedCharacter.reference_image_url) {
            characterSelectedAvatar.src = selectedCharacter.reference_image_url;
            characterSelectedAvatarWrap.classList.remove("hidden");
        } else {
            characterSelectedAvatarWrap.classList.add("hidden");
            characterSelectedAvatar.removeAttribute("src");
        }
    }

    function updateReferencePreview() {
        if (selectedGameUsesFolderName()) {
            referenceImage.classList.add("hidden");
            referenceImage.removeAttribute("src");
            referenceCopy.textContent = workspaceText.folder_name_no_reference_needed;
        } else if (selectedCharacter?.reference_image_url) {
            referenceImage.src = selectedCharacter.reference_image_url;
            referenceImage.classList.remove("hidden");
            referenceCopy.textContent = selectedCharacter.description || selectedCharacter.name;
        } else if (selectedCharacter) {
            referenceImage.classList.add("hidden");
            referenceImage.removeAttribute("src");
            referenceCopy.textContent = selectedCharacter.description || workspaceText.no_reference_yet;
        } else {
            referenceImage.classList.add("hidden");
            referenceImage.removeAttribute("src");
            referenceCopy.textContent = workspaceText.select_character_for_preview;
        }
    }

    function chooseCharacter(character) {
        selectedCharacter = character;
        syncSelectedCharacterPresentation();
        updateReferencePreview();
        renderCharacterOptions();
        updateStageButtonState();
        closeCharacterDropdown();
    }

    function renderCharacterOptions() {
        const query = characterSearch.value.trim().toLowerCase();
        const filteredCharacters = activeCharacters.filter((character) => {
            if (!query) {
                return true;
            }
            return character.name.toLowerCase().includes(query) || character.description.toLowerCase().includes(query);
        });

        characterOptionList.innerHTML = "";

        const selectedOption = gameSelect.options[gameSelect.selectedIndex];
        if (!selectedOption?.dataset?.targetGameId) {
            characterOptionList.innerHTML = `<div class="rich-dropdown-empty">${workspaceText.select_game_before_character}</div>`;
            return;
        }

        if (selectedGameUsesFolderName()) {
            characterOptionList.innerHTML = `<div class="rich-dropdown-empty">${workspaceText.folder_name_optional}</div>`;
            return;
        }

        if (!filteredCharacters.length) {
            characterOptionList.innerHTML = `<div class="rich-dropdown-empty">${workspaceText.no_characters_match}</div>`;
            return;
        }

        filteredCharacters.forEach((character) => {
            const option = document.createElement("button");
            option.type = "button";
            option.className = "rich-dropdown-option";
            option.setAttribute("role", "option");
            option.dataset.characterId = String(character.id);
            option.setAttribute("aria-selected", String(selectedCharacter?.id === character.id));

            const imageMarkup = character.reference_image_url
                ? `<span class="rich-dropdown-option-avatar"><img class="rich-dropdown-option-avatar-image" src="${character.reference_image_url}" alt="${character.name}"></span>`
                : `<span class="rich-dropdown-option-avatar rich-dropdown-option-avatar-placeholder">${workspaceText.no_preview}</span>`;

            option.innerHTML = `
                ${imageMarkup}
                <span class="rich-dropdown-option-copy">
                    <span class="rich-dropdown-option-title">${character.name}</span>
                    <span class="rich-dropdown-option-subcopy">${character.description || (character.reference_image_url ? workspaceText.reference_ready : workspaceText.no_reference_image)}</span>
                </span>
            `;

            option.addEventListener("click", () => chooseCharacter(character));
            characterOptionList.appendChild(option);
        });
    }

    function renderCharacters() {
        const selectedOption = gameSelect.options[gameSelect.selectedIndex];
        const characterGameId = Number(selectedOption?.dataset?.characterGameId || "0");
        activeCharacters = characterData.filter((item) => item.game_id === characterGameId);
        targetGameInput.value = selectedOption?.dataset?.targetGameId || "";
        gameInput.value = selectedGameUsesFolderName() ? "" : (characterGameId ? String(characterGameId) : "");
        selectedCharacter = null;
        characterSearch.value = "";
        syncSelectedCharacterPresentation();
        updateReferencePreview();
        renderCharacterOptions();
        updateStageButtonState();
        closeCharacterDropdown();
    }

    function sortGallery() {
        const galleryNode = document.getElementById("gallery");
        if (!galleryNode || !sortSelect) {
            return;
        }

        const cards = Array.from(galleryNode.querySelectorAll(":scope > label"));
        cards.sort((left, right) => {
            const leftName = left.dataset.fileName || "";
            const rightName = right.dataset.fileName || "";
            const leftCreated = Number(left.dataset.created || "0");
            const rightCreated = Number(right.dataset.created || "0");

            switch (sortSelect.value) {
                case "name_asc":
                    return leftName.localeCompare(rightName);
                case "name_desc":
                    return rightName.localeCompare(leftName);
                case "date_asc":
                    return leftCreated - rightCreated;
                case "date_desc":
                default:
                    return rightCreated - leftCreated;
            }
        });

        cards.forEach((card) => galleryNode.appendChild(card));
    }

    function getGalleryCards() {
        return Array.from(document.querySelectorAll("#gallery > [data-gallery-card]"));
    }

    function getVisibleGalleryCheckboxes() {
        return Array.from(document.querySelectorAll("#gallery > [data-gallery-card]:not(.hidden) .gallery-check"));
    }

    function syncGallerySelectionState() {
        getGalleryCards().forEach((card) => {
            const checkbox = card.querySelector(".gallery-check");
            card.classList.toggle("gallery-card-selected", Boolean(checkbox?.checked));
        });
    }

    function updateGalleryPresentation() {
        const totalCards = getGalleryCards().length;
        if (visibleImagesCount) {
            visibleImagesCount.textContent = String(totalCards);
        }
        galleryEmptyState?.classList.toggle("hidden", totalCards !== 0);
        document.getElementById("gallery")?.classList.toggle("hidden", totalCards === 0);
    }

    function updateQueuedItemsCount(count) {
        if (queuedItemsCount) {
            queuedItemsCount.textContent = String(count);
        }
    }

    function applyGalleryFilter() {
        const galleryNode = document.getElementById("gallery");
        const query = galleryFilter?.value.trim().toLowerCase() || "";
        Array.from(galleryNode?.querySelectorAll(":scope > label") || []).forEach((card) => {
            const matches = !query || card.dataset.fileName.includes(query);
            card.classList.toggle("hidden", !matches);
        });
    }

    function applyGallerySelection(checkbox, shiftKey) {
        if (!(checkbox instanceof HTMLInputElement)) {
            return;
        }

        if (shiftKey && lastSelectedCheckbox && lastSelectedCheckbox !== checkbox) {
            const visibleCheckboxes = getVisibleGalleryCheckboxes();
            const startIndex = visibleCheckboxes.indexOf(lastSelectedCheckbox);
            const endIndex = visibleCheckboxes.indexOf(checkbox);

            if (startIndex !== -1 && endIndex !== -1) {
                const [rangeStart, rangeEnd] = startIndex < endIndex
                    ? [startIndex, endIndex]
                    : [endIndex, startIndex];

                for (let index = rangeStart; index <= rangeEnd; index += 1) {
                    visibleCheckboxes[index].checked = checkbox.checked;
                }
            }
        }

        lastSelectedCheckbox = checkbox;
        syncGallerySelectionState();
        updateSelectedCount();
    }

    function bindGalleryCard(card) {
        if (!(card instanceof HTMLElement) || card.dataset.galleryBound === "1") {
            return;
        }

        const checkbox = card.querySelector(".gallery-check");
        if (!(checkbox instanceof HTMLInputElement)) {
            return;
        }

        card.dataset.galleryBound = "1";

        card.addEventListener("click", (event) => {
            if (event.target instanceof Element && event.target.closest(".gallery-check")) {
                return;
            }

            event.preventDefault();
            checkbox.checked = !checkbox.checked;
            applyGallerySelection(checkbox, event.shiftKey);
        });

        checkbox.addEventListener("click", (event) => {
            event.stopPropagation();
            window.setTimeout(() => applyGallerySelection(checkbox, event.shiftKey), 0);
        });
    }

    function createGalleryCard(image) {
        const card = document.createElement("label");
        card.className = "gallery-card group cursor-pointer";
        card.dataset.galleryCard = "1";
        card.dataset.fileName = (image.file_name || "").toLowerCase();
        card.dataset.created = String(image.created_at_timestamp || 0);
        card.innerHTML = `
            <span class="gallery-media block">
                <input class="gallery-check" type="checkbox" name="selected_images" value="${image.relative_path}" form="stage-form">
                <img class="gallery-image" src="${image.preview_url}" alt="${image.file_name}" loading="lazy" decoding="async" fetchpriority="low">
            </span>
            <span class="block space-y-2 px-4 py-3">
                <span class="block break-all text-base font-semibold leading-6 text-ink">${image.file_name}</span>
                <span class="block text-sm text-muted">${new Date((image.created_at_timestamp || 0) * 1000).toLocaleString("en-GB", {
                    day: "2-digit",
                    month: "2-digit",
                    year: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                    hour12: false,
                }).replace(",", "")}</span>
            </span>
        `;
        bindGalleryCard(card);
        return card;
    }

    function restoreImageToGallery(image) {
        if (!image || !galleryShell) {
            return;
        }

        let galleryNode = document.getElementById("gallery");
        if (!galleryNode) {
            galleryNode = document.createElement("div");
            galleryNode.className = "grid grid-cols-2 gap-4 lg:grid-cols-3 xl:grid-cols-4";
            galleryNode.id = "gallery";
            galleryShell.prepend(galleryNode);
        }

        if (galleryNode.querySelector(`.gallery-check[value="${CSS.escape(image.relative_path)}"]`)) {
            return;
        }

        const card = createGalleryCard(image);
        galleryNode.appendChild(card);
        applyGalleryFilter();
        sortGallery();
        updateGalleryPresentation();
        syncGallerySelectionState();
    }

    function getStagingQueueCheckboxes() {
        return Array.from(document.querySelectorAll(".staging-queue-item-check"));
    }

    function getVisibleStagingQueueCheckboxes() {
        return Array.from(document.querySelectorAll("#staging-queue-modal-list [data-staged-item]:not(.hidden) .staging-queue-item-check"));
    }

    function syncStagingQueueSelectionState() {
        const checkboxes = getStagingQueueCheckboxes();
        const selected = checkboxes.filter((input) => input.checked).length;

        document.querySelectorAll("[data-staged-item]").forEach((item) => {
            const checkbox = item.querySelector(".staging-queue-item-check");
            item.classList.toggle("staging-queue-modal-item-selected", Boolean(checkbox?.checked));
        });

        if (stagingQueueSelectedCount) {
            stagingQueueSelectedCount.textContent = String(selected);
        }
        if (stagingQueueBulkRemove) {
            stagingQueueBulkRemove.disabled = selected === 0;
        }
        if (stagingQueueSelectAll) {
            stagingQueueSelectAll.checked = checkboxes.length > 0 && selected === checkboxes.length;
            stagingQueueSelectAll.indeterminate = selected > 0 && selected < checkboxes.length;
        }
    }

    function bindStagingQueueItem(item) {
        if (!(item instanceof HTMLElement) || item.dataset.queueBound === "1") {
            return;
        }

        const checkbox = item.querySelector(".staging-queue-item-check");
        if (!(checkbox instanceof HTMLInputElement)) {
            return;
        }

        item.dataset.queueBound = "1";

        item.addEventListener("click", (event) => {
            if (event.target instanceof Element && event.target.closest(".staging-queue-item-check")) {
                return;
            }

            event.preventDefault();
            checkbox.checked = !checkbox.checked;
            applyStagingQueueSelection(checkbox, event.shiftKey);
        });

        checkbox.addEventListener("click", (event) => {
            event.stopPropagation();
            window.setTimeout(() => applyStagingQueueSelection(checkbox, event.shiftKey), 0);
        });
    }

    function applyStagingQueueSelection(checkbox, shiftKey) {
        if (!(checkbox instanceof HTMLInputElement)) {
            return;
        }

        if (shiftKey && lastStagingQueueCheckbox && lastStagingQueueCheckbox !== checkbox) {
            const visibleCheckboxes = getVisibleStagingQueueCheckboxes();
            const startIndex = visibleCheckboxes.indexOf(lastStagingQueueCheckbox);
            const endIndex = visibleCheckboxes.indexOf(checkbox);

            if (startIndex !== -1 && endIndex !== -1) {
                const [rangeStart, rangeEnd] = startIndex < endIndex ? [startIndex, endIndex] : [endIndex, startIndex];
                for (let index = rangeStart; index <= rangeEnd; index += 1) {
                    visibleCheckboxes[index].checked = checkbox.checked;
                }
            }
        }

        lastStagingQueueCheckbox = checkbox;
        syncStagingQueueSelectionState();
    }

    function removeQueueRows(relativePaths) {
        const paths = new Set(relativePaths || []);
        document.querySelectorAll("[data-staged-item]").forEach((row) => {
            if (paths.has(row.dataset.relativePath || "")) {
                row.remove();
            }
        });
    }

    function restoreImagesToGallery(images) {
        (images || []).forEach((image) => restoreImageToGallery(image));
    }

    function updateStagingQueuePresentation(count) {
        const queueIsEmpty = count === 0;

        if (stagingQueueSummaryCount) {
            stagingQueueSummaryCount.textContent = String(count);
        }
        if (stagingQueueSummarySubtitle) {
            const suffix = count === 1 ? workspaceText.queue_ready_review_singular : workspaceText.queue_ready_review_plural;
            stagingQueueSummarySubtitle.textContent = String(count) + " " + suffix;
        }
        if (stagingQueueOpenButton instanceof HTMLButtonElement) {
            stagingQueueOpenButton.disabled = queueIsEmpty;
            stagingQueueOpenButton.setAttribute("aria-disabled", String(queueIsEmpty));
            stagingQueueOpenButton.classList.toggle("staging-queue-summary-static", queueIsEmpty);
        } else if (stagingQueueOpenButton) {
            stagingQueueOpenButton.setAttribute("aria-disabled", String(queueIsEmpty));
            stagingQueueOpenButton.classList.toggle("staging-queue-summary-static", queueIsEmpty);
        }
        stagingQueueSummaryActions?.classList.toggle("hidden", queueIsEmpty);
        stagingQueueModalEmpty?.classList.toggle("hidden", !queueIsEmpty);
        updateQueuedItemsCount(count);
        syncStagingQueueSelectionState();
    }

    async function handleUnstageSubmit(event) {
        event.preventDefault();
        const form = event.currentTarget;
        if (!(form instanceof HTMLFormElement)) {
            return;
        }

        const selectedCheckboxes = getStagingQueueCheckboxes().filter((input) => input.checked);
        if (!selectedCheckboxes.length) {
            syncStagingQueueSelectionState();
            return;
        }

        const modalScrollTop = stagingQueueModalList?.scrollTop ?? 0;
        const formData = new FormData();
        const csrfToken = form.querySelector('input[name="csrfmiddlewaretoken"]')?.value;
        if (csrfToken) {
            formData.append("csrfmiddlewaretoken", csrfToken);
        }
        selectedCheckboxes.forEach((input) => formData.append("relative_paths", input.value));

        try {
            const response = await fetch(form.action, {
                method: "POST",
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                },
                body: formData,
                credentials: "same-origin",
            });
            if (!response.ok) {
                throw new Error("Request failed with status " + response.status);
            }
            const payload = await response.json();
            const remainingCount = Number(payload.remaining_count || 0);
            removeQueueRows(payload.relative_paths);
            updateStagingQueuePresentation(remainingCount);
            restoreImagesToGallery(payload.restored_images);
            if (remainingCount === 0) {
                closeStagingQueueModal();
            } else if (stagingQueueModalList) {
                const maxScrollTop = Math.max(0, stagingQueueModalList.scrollHeight - stagingQueueModalList.clientHeight);
                stagingQueueModalList.scrollTop = Math.min(modalScrollTop, maxScrollTop);
            }
            if (typeof window.showFlashMessage === "function" && payload.message) {
                window.showFlashMessage(payload.message, "default");
            }
        } catch (error) {
            if (typeof window.showFlashMessage === "function") {
                window.showFlashMessage(workspaceText.queue_remove_failed, "error");
            }
        }
    }

    function clearSelectedImages() {

        document.querySelectorAll('input[name="selected_images"]:checked').forEach((input) => {
            input.checked = false;
        });
        lastSelectedCheckbox = null;
        syncGallerySelectionState();
        updateSelectedCount();
    }

    function closeStagingQueueModal() {

        if (!stagingQueueModal) {
            return;
        }
        stagingQueueModal.classList.add("hidden");
        stagingQueueModal.setAttribute("aria-hidden", "true");
        document.body.classList.remove("overflow-hidden");
    }

    function openStagingQueueModal() {
        if (!stagingQueueModal || !stagingQueueSummaryActions || stagingQueueSummaryActions.classList.contains("hidden") || stagingQueueOpenButton?.classList.contains("staging-queue-summary-static") || (stagingQueueOpenButton instanceof HTMLButtonElement && stagingQueueOpenButton.disabled)) {
            return;
        }

        stagingQueueModal.classList.remove("hidden");
        stagingQueueModal.setAttribute("aria-hidden", "false");
        document.body.classList.add("overflow-hidden");
    }

    gameSelect?.addEventListener("change", renderCharacters);
    characterSearch?.addEventListener("input", renderCharacterOptions);
    sortSelect?.addEventListener("change", sortGallery);
    clearSelectedButton?.addEventListener("click", clearSelectedImages);
    document.getElementById("stage-form")?.addEventListener("submit", (event) => {
        if (saveToQueueButton?.disabled) {
            event.preventDefault();
        }
    });
    characterDropdownTrigger?.addEventListener("click", () => {
        if (characterDropdownMenu.classList.contains("hidden")) {
            openCharacterDropdown();
        } else {
            closeCharacterDropdown();
        }
    });

    document.addEventListener("click", (event) => {
        if (characterDropdown && !characterDropdown.contains(event.target)) {
            closeCharacterDropdown();
        }
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            closeStagingQueueModal();
        }
    });

    galleryFilter?.addEventListener("input", applyGalleryFilter);

    getGalleryCards().forEach(bindGalleryCard);
    document.querySelectorAll("[data-staged-item]").forEach(bindStagingQueueItem);
    document.getElementById("staging-queue-open")?.addEventListener("click", openStagingQueueModal);
    stagingQueueBulkForm?.addEventListener("submit", handleUnstageSubmit);
    stagingQueueSelectAll?.addEventListener("change", () => {
        getStagingQueueCheckboxes().forEach((input) => {
            input.checked = Boolean(stagingQueueSelectAll.checked);
        });
        lastStagingQueueCheckbox = null;
        syncStagingQueueSelectionState();
    });

    stagingQueueModalList?.addEventListener("mousedown", (event) => {
        if (event.shiftKey) {
            event.preventDefault();
        }
    });

    stagingQueueModalClose?.addEventListener("click", closeStagingQueueModal);
    stagingQueueModal?.addEventListener("click", (event) => {
        if (event.target === stagingQueueModal) {
            closeStagingQueueModal();
        }
    });

    applyGalleryFilter();
    sortGallery();
    renderCharacters();
    syncGallerySelectionState();
    updateGalleryPresentation();
    updateSelectedCount();
    updateStageButtonState();
    updateStagingQueuePresentation(document.querySelectorAll("[data-staged-item]").length);
    syncStagingQueueSelectionState();
