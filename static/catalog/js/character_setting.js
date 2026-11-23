(() => {
        document.querySelectorAll('[data-remove-row]').forEach((button) => {
            button.addEventListener('click', () => {
                const row = button.closest('[data-row]');
                if (!row) {
                    return;
                }
                const activeInput = row.querySelector('[data-row-active]');
                if (activeInput) {
                    activeInput.value = '0';
                }
                row.classList.add('hidden');
            });
        });

        const importModeSelect = document.querySelector('[data-import-mode-select]');
        const importModeInput = document.querySelector('[data-import-mode-input]');
        const scanPanel = document.querySelector('[data-import-mode-panel="scan"]');
        const manualPanel = document.querySelector('[data-import-mode-panel="manual"]');

        const setPanelDisabled = (panel, disabled) => {
            panel?.querySelectorAll('input, select, textarea, button').forEach((field) => {
                if (field.hasAttribute('data-row-active')) {
                    return;
                }
                field.disabled = disabled;
            });
        };

        const syncImportMode = () => {
            const selectedMode = importModeSelect?.value === 'manual' ? 'manual' : 'scan';
            if (importModeInput) {
                importModeInput.value = selectedMode;
            }
            scanPanel?.classList.toggle('hidden', selectedMode !== 'scan');
            manualPanel?.classList.toggle('hidden', selectedMode !== 'manual');
            setPanelDisabled(scanPanel, selectedMode !== 'scan');
            setPanelDisabled(manualPanel, selectedMode !== 'manual');
        };

        importModeSelect?.addEventListener('change', syncImportMode);
        syncImportMode();
        const deleteForm = document.querySelector('[data-character-delete-form]');
        const deleteIdInput = document.querySelector('[data-character-delete-id]');

        const listModal = document.querySelector('[data-character-list-modal]');
        const listModalTitle = document.querySelector('[data-character-list-modal-title]');
        const listModalSubtitle = document.querySelector('[data-character-list-modal-subtitle]');
        const listModalBody = document.querySelector('[data-character-list-modal-body]');
        const listModalClose = document.querySelector('[data-character-list-modal-close]');

        const confirmModal = document.querySelector('[data-character-confirm-modal]');
        const confirmTarget = document.querySelector('[data-character-confirm-target]');
        const confirmSubmit = document.querySelector('[data-character-confirm-submit]');
        const confirmCancel = document.querySelector('[data-character-confirm-cancel]');

        const editModal = document.querySelector('[data-character-edit-modal]');
        const editForm = document.querySelector('[data-character-edit-form]');
        const editTarget = document.querySelector('[data-character-edit-target]');
        const editIdInput = document.querySelector('[data-character-edit-id]');
        const editNameInput = document.querySelector('[data-character-edit-name]');
        const editDescriptionInput = document.querySelector('[data-character-edit-description]');
        const editFileInput = document.querySelector('[data-character-edit-file]');
        const editImage = document.querySelector('[data-character-edit-image]');
        const editEmpty = document.querySelector('[data-character-edit-empty]');
        const editCancel = document.querySelector('[data-character-edit-cancel]');

                const config = JSON.parse(document.getElementById("character-setting-js-config").textContent);

        const savedCharactersTitle = config.savedCharactersTitle || "";
        const charactersSuffix = config.charactersSuffix || "";

        let currentGroupId = config.currentGroupId;

        const scrollKeyForGroup = (groupId) => `character-setting-scroll:${groupId}`;

        const persistCurrentScroll = () => {
            if (!listModalBody || currentGroupId === null || currentGroupId === undefined) {
                return;
            }
            sessionStorage.setItem(scrollKeyForGroup(currentGroupId), String(listModalBody.scrollTop || 0));
        };

        const restoreCurrentScroll = () => {
            if (!listModalBody || currentGroupId === null || currentGroupId === undefined) {
                return;
            }
            const rawValue = sessionStorage.getItem(scrollKeyForGroup(currentGroupId));
            if (rawValue === null) {
                listModalBody.scrollTop = 0;
                return;
            }
            const parsedValue = Number(rawValue);
            requestAnimationFrame(() => {
                listModalBody.scrollTop = Number.isFinite(parsedValue) ? parsedValue : 0;
            });
        };

        const hideConfirmModal = () => {
            confirmModal?.classList.add('hidden');
            if (deleteIdInput) {
                deleteIdInput.value = '';
            }
        };

        const setEditPreviewImage = (src, altText) => {
            if (!editImage || !editEmpty) {
                return;
            }
            if (src) {
                editImage.src = src;
                editImage.alt = altText || '';
                editImage.classList.remove('hidden');
                editEmpty.classList.add('hidden');
            } else {
                editImage.src = '';
                editImage.alt = '';
                editImage.classList.add('hidden');
                editEmpty.classList.remove('hidden');
            }
        };

        const hideEditModal = () => {
            if (editFileInput) {
                editFileInput.value = '';
            }
            editModal?.classList.add('hidden');
        };

        const closeListModal = () => {
            listModal?.classList.add('hidden');
            hideConfirmModal();
            hideEditModal();
            if (listModalBody) {
                listModalBody.innerHTML = '';
            }
        };

        const openListModal = (groupId, groupLabel, groupCount, templateId) => {
            const template = document.getElementById(templateId || '');
            if (!template || !listModal || !listModalBody) {
                return;
            }
            currentGroupId = groupId;
            listModalBody.innerHTML = template.innerHTML;
            if (listModalTitle) {
                listModalTitle.textContent = groupLabel || savedCharactersTitle;
            }
            if (listModalSubtitle) {
                listModalSubtitle.textContent = `${groupCount || '0'} ${charactersSuffix}`;
            }
            hideConfirmModal();
            hideEditModal();
            listModal.classList.remove('hidden');
            restoreCurrentScroll();
        };

        document.addEventListener('click', (event) => {
            const viewButton = event.target.closest('[data-character-group-view]');
            if (viewButton) {
                openListModal(
                    viewButton.dataset.groupId || '',
                    viewButton.dataset.groupLabel || savedCharactersTitle,
                    viewButton.dataset.groupCount || '0',
                    viewButton.dataset.templateId || ''
                );
                return;
            }

            const deleteButton = event.target.closest('[data-character-delete-trigger]');
            if (deleteButton) {
                if (!confirmModal || !deleteForm) {
                    return;
                }
                if (deleteIdInput) {
                    deleteIdInput.value = deleteButton.dataset.characterId || '';
                }
                if (confirmTarget) {
                    confirmTarget.textContent = deleteButton.dataset.characterLabel || '';
                }
                confirmModal.classList.remove('hidden');
                return;
            }

            const editButton = event.target.closest('[data-character-edit-trigger]');
            if (editButton) {
                if (!editModal || !editForm) {
                    return;
                }
                if (editTarget) {
                    editTarget.textContent = editButton.dataset.characterLabel || '';
                }
                if (editIdInput) {
                    editIdInput.value = editButton.dataset.characterId || '';
                }
                if (editNameInput) {
                    editNameInput.value = editButton.dataset.characterName || '';
                }
                if (editDescriptionInput) {
                    editDescriptionInput.value = editButton.dataset.characterDescription || '';
                }
                if (editFileInput) {
                    editFileInput.value = '';
                }
                setEditPreviewImage(editButton.dataset.characterImageUrl || '', editButton.dataset.characterName || '');
                editModal.classList.remove('hidden');
            }
        });

        listModalBody?.addEventListener('scroll', persistCurrentScroll, { passive: true });

        confirmCancel?.addEventListener('click', hideConfirmModal);
        confirmSubmit?.addEventListener('click', () => {
            persistCurrentScroll();
            if (deleteForm && deleteIdInput?.value) {
                deleteForm.submit();
            }
        });

        editForm?.addEventListener('submit', () => {
            persistCurrentScroll();
        });

        editFileInput?.addEventListener('change', () => {
            const file = editFileInput.files?.[0];
            if (!file) {
                return;
            }
            const objectUrl = URL.createObjectURL(file);
            setEditPreviewImage(objectUrl, file.name);
        });

        editCancel?.addEventListener('click', hideEditModal);

        listModalClose?.addEventListener('click', closeListModal);
        listModal?.addEventListener('click', (event) => {
            if (event.target === listModal) {
                closeListModal();
            }
        });
        confirmModal?.addEventListener('click', (event) => {
            if (event.target === confirmModal) {
                hideConfirmModal();
            }
        });
        editModal?.addEventListener('click', (event) => {
            if (event.target === editModal) {
                hideEditModal();
            }
        });

        if (currentGroupId) {
            const autoButton = document.querySelector(`[data-character-group-view][data-group-id="${currentGroupId}"]`);
            if (autoButton) {
                openListModal(
                    autoButton.dataset.groupId || '',
                    autoButton.dataset.groupLabel || savedCharactersTitle,
                    autoButton.dataset.groupCount || '0',
                    autoButton.dataset.templateId || ''
                );
            }
        }
    })();
