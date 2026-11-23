(() => {
    const workflow = document.getElementById('id_workflow');
    const textAction = document.getElementById('id_text_action');
    const form = workflow?.closest('form[data-filemanage-setting-form]') || document.querySelector('form[data-filemanage-setting-form]');
    const scopedFields = Array.from(document.querySelectorAll('[data-rename-scope]'));
    const currentValuesPanel = document.getElementById('current-values-panel');
    const config = JSON.parse(document.getElementById('filemanage-setting-js-config').textContent);
    const enabledLabel = config.enabledLabel;
    const disabledLabel = config.disabledLabel;
    const emptyLabel = config.emptyLabel;

    function visibleRenameNodes() {
        return scopedFields.filter((node) => !node.classList.contains('hidden'));
    }

    function fieldLabel(node, input) {
        const strong = node.querySelector('.text-sm.font-semibold.text-ink');
        if (strong) {
            return strong.textContent.trim();
        }
        const label = node.querySelector(`label[for="${input.id}"]`);
        return label ? label.textContent.trim() : input.name;
    }

    function fieldValue(input) {
        if (!input) {
            return emptyLabel;
        }
        if (input.type === 'checkbox') {
            return input.checked ? enabledLabel : disabledLabel;
        }
        if (input.tagName === 'SELECT') {
            const option = input.options[input.selectedIndex];
            return option ? option.text.trim() : emptyLabel;
        }
        return (input.value || '').trim() || emptyLabel;
    }

    function fieldSupportsAction(node, activeAction) {
        const actions = (node.dataset.renameActions || '')
            .split(',')
            .map((value) => value.trim())
            .filter(Boolean);
        if (!actions.length || actions.includes('all')) {
            return true;
        }
        return actions.includes(activeAction);
    }

    function renderCurrentValues() {
        if (!currentValuesPanel) {
            return;
        }
        const rows = [];
        visibleRenameNodes().forEach((node) => {
            const input = node.querySelector('input, select, textarea');
            if (!input || !input.name) {
                return;
            }
            rows.push(`
                <div class="file-setting-row">
                    <div class="file-task-label">${fieldLabel(node, input)}</div>
                    <div class="file-task-value">${fieldValue(input)}</div>
                </div>
            `);
        });
        currentValuesPanel.innerHTML = rows.join('');
    }

    function syncRenameVisibility() {
        if (!workflow) {
            return;
        }
        const activeWorkflow = workflow.value || 'text_transform';
        const activeAction = textAction?.value || 'replace';
        scopedFields.forEach((node) => {
            const scope = node.dataset.renameScope;
            const workflowVisible = scope === 'shared' || scope === activeWorkflow;
            const actionVisible = activeWorkflow !== 'text_transform' || fieldSupportsAction(node, activeAction);
            const visible = workflowVisible && actionVisible;
            node.classList.toggle('hidden', !visible);
        });
        renderCurrentValues();
    }

    form?.addEventListener('input', renderCurrentValues);
    form?.addEventListener('change', renderCurrentValues);
    workflow?.addEventListener('change', syncRenameVisibility);
    textAction?.addEventListener('change', syncRenameVisibility);
    syncRenameVisibility();

    const forms = document.querySelectorAll('form[data-filemanage-setting-form]');
    forms.forEach(f => {
        f.addEventListener('submit', async (e) => {
            e.preventDefault();
            const submitBtn = f.querySelector('button[type="submit"]');
            if (submitBtn) submitBtn.disabled = true;

            try {
                const response = await fetch(window.location.href, {
                    method: 'POST',
                    body: new FormData(f),
                    headers: {
                        'Accept': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });

                if (!response.ok) {
                    const data = await response.json().catch(() => ({}));
                    throw new Error(data.error || `HTTP ${response.status}`);
                }

                const data = await response.json();
                if (window.showFlashMessage && data.message) {
                    window.showFlashMessage(data.message, 'success');
                }

                Array.from(f.elements).forEach(input => {
                    if (input.type === 'checkbox' || input.type === 'radio') {
                        input.defaultChecked = input.checked;
                    } else if (input.tagName === 'SELECT') {
                        Array.from(input.options).forEach(opt => opt.defaultSelected = opt.selected);
                    } else if (input.name && input.type !== 'submit' && input.type !== 'reset') {
                        input.defaultValue = input.value;
                    }
                });

                document.dispatchEvent(new Event('filemanage:settingsSaved'));
            } catch (err) {
                if (window.showFlashMessage) {
                    window.showFlashMessage(err.message, 'error');
                }
            } finally {
                if (submitBtn) submitBtn.disabled = false;
            }
        });

        f.addEventListener('reset', () => {
            window.requestAnimationFrame(() => {
                if (workflow) {
                    workflow.dispatchEvent(new Event('change', { bubbles: true }));
                }
                Array.from(f.elements).forEach(input => {
                    input.dispatchEvent(new Event('change', { bubbles: true }));
                    if (input.tagName === 'SELECT') {
                        input.dispatchEvent(new Event('rich-select:refresh', { bubbles: true }));
                    }
                });
            });
        });
    });
})();
