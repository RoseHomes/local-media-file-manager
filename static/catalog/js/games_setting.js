(() => {
    document.querySelectorAll('[data-remove-game-row]').forEach((button) => {
        button.addEventListener('click', () => {
            const row = button.closest('[data-game-preview-row]');
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
        const config = JSON.parse(document.getElementById("games-setting-js-config").textContent);
    const manualKindSelect = document.getElementById(config.manualKindSelectId);
    const savedGamesTitle = config.savedGamesTitle || "";
    const entriesSuffix = config.entriesSuffix || "";
    const manualParentRow = document.querySelector('[data-manual-parent-row]');

    const syncImportMode = () => {
        const selectedMode = importModeSelect?.value === 'manual' ? 'manual' : 'scan';
        if (importModeInput) {
            importModeInput.value = selectedMode;
        }
        scanPanel?.classList.toggle('hidden', selectedMode !== 'scan');
        manualPanel?.classList.toggle('hidden', selectedMode !== 'manual');
    };

    const syncManualKind = () => {
        const isSubfolder = manualKindSelect?.value === 'subfolder';
        manualParentRow?.classList.toggle('hidden', !isSubfolder);
    };

    importModeSelect?.addEventListener('change', syncImportMode);
    manualKindSelect?.addEventListener('change', syncManualKind);
    syncImportMode();
    syncManualKind();

    const deleteForm = document.querySelector('[data-game-delete-form]');
    const deleteIdInput = document.querySelector('[data-game-delete-id]');

    const listModal = document.querySelector('[data-saved-game-list-modal]');
    const listModalTitle = document.querySelector('[data-saved-game-list-title]');
    const listModalSubtitle = document.querySelector('[data-saved-game-list-subtitle]');
    const listModalBody = document.querySelector('[data-saved-game-list-body]');
    const listModalClose = document.querySelector('[data-saved-game-list-close]');

    const deleteModal = document.querySelector('[data-confirm-modal]');
    const editModal = document.querySelector('[data-edit-modal]');
    const editForm = document.querySelector('[data-edit-form]');
        let currentGroupId = config.currentGroupId;

    const scrollKeyForGroup = (groupId) => `games-setting-scroll:${groupId}`;

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

    const hideDeleteModal = () => {
        deleteModal?.classList.add('hidden');
        if (deleteIdInput) {
            deleteIdInput.value = '';
        }
    };

    const hideEditModal = () => {
        editModal?.classList.add('hidden');
    };

    const closeListModal = () => {
        listModal?.classList.add('hidden');
        hideDeleteModal();
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
            listModalTitle.textContent = groupLabel || savedGamesTitle;
        }
        if (listModalSubtitle) {
            listModalSubtitle.textContent = `${groupCount || '0'} ${entriesSuffix}`;
        }
        hideDeleteModal();
        hideEditModal();
        listModal.classList.remove('hidden');
        restoreCurrentScroll();
    };

    document.addEventListener('click', (event) => {
        const viewButton = event.target.closest('[data-saved-game-group-view]');
        if (viewButton) {
            openListModal(
                viewButton.dataset.groupId || '',
                viewButton.dataset.groupLabel || savedGamesTitle,
                viewButton.dataset.groupCount || '0',
                viewButton.dataset.templateId || ''
            );
            return;
        }

        const deleteButton = event.target.closest('[data-delete-trigger]');
        if (deleteButton) {
            if (!deleteModal || !deleteForm) {
                return;
            }
            if (deleteIdInput) {
                deleteIdInput.value = deleteButton.dataset.gameId || '';
            }
            const targetLabel = deleteModal.querySelector('[data-confirm-target]');
            if (targetLabel) {
                targetLabel.textContent = deleteButton.dataset.gameLabel || '';
            }
            deleteModal.classList.remove('hidden');
            return;
        }

        const editButton = event.target.closest('[data-edit-trigger]');
        if (editButton && editModal) {
            const editTarget = editModal.querySelector('[data-edit-target]');
            const editGameId = editModal.querySelector('[data-edit-game-id]');
            const editTitle = editModal.querySelector('[data-edit-title]');
            const editFolderName = editModal.querySelector('[data-edit-folder-name]');
            const editUseFolderName = editModal.querySelector('[data-edit-use-folder-name]');
            if (editTarget) {
                editTarget.textContent = editButton.dataset.gameLabel || '';
            }
            if (editGameId) {
                editGameId.value = editButton.dataset.gameId || '';
            }
            if (editTitle) {
                editTitle.value = editButton.dataset.title || '';
            }
            if (editFolderName) {
                editFolderName.value = editButton.dataset.folderName || '';
            }
            if (editUseFolderName) {
                editUseFolderName.checked = (editButton.dataset.useFolderName || '0') === '1';
            }
            editModal.classList.remove('hidden');
            editTitle?.focus();
            editTitle?.select();
        }
    });

    listModalBody?.addEventListener('scroll', persistCurrentScroll, { passive: true });

    const confirmCancelButtons = deleteModal?.querySelectorAll('[data-confirm-cancel]') || [];
    confirmCancelButtons.forEach((button) => {
        button.addEventListener('click', hideDeleteModal);
    });

    deleteModal?.querySelector('[data-confirm-submit]')?.addEventListener('click', () => {
        persistCurrentScroll();
        if (deleteForm && deleteIdInput?.value) {
            deleteForm.submit();
        }
    });

    editForm?.addEventListener('submit', persistCurrentScroll);
    editModal?.querySelectorAll('[data-edit-cancel]').forEach((button) => {
        button.addEventListener('click', hideEditModal);
    });

    listModalClose?.addEventListener('click', closeListModal);
    listModal?.addEventListener('click', (event) => {
        if (event.target === listModal) {
            closeListModal();
        }
    });
    deleteModal?.addEventListener('click', (event) => {
        if (event.target === deleteModal) {
            hideDeleteModal();
        }
    });
    editModal?.addEventListener('click', (event) => {
        if (event.target === editModal) {
            hideEditModal();
        }
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            if (editModal && !editModal.classList.contains('hidden')) {
                hideEditModal();
                return;
            }
            if (deleteModal && !deleteModal.classList.contains('hidden')) {
                hideDeleteModal();
                return;
            }
            if (listModal && !listModal.classList.contains('hidden')) {
                closeListModal();
            }
        }
    });

    if (currentGroupId) {
        const autoButton = document.querySelector(`[data-saved-game-group-view][data-group-id="${currentGroupId}"]`);
        if (autoButton) {
            openListModal(
                autoButton.dataset.groupId || '',
                autoButton.dataset.groupLabel || savedGamesTitle,
                autoButton.dataset.groupCount || '0',
                autoButton.dataset.templateId || ''
            );
        }
    }
})();
