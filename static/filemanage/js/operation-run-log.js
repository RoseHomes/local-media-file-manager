(() => {
    const page = window.FileManageOperationPage;
    if (!page) {
        return;
    }

    const { config, uiText, elements, state, setRunButtonReady, syncReopenRunButton } = page;
    const runForm = document.getElementById("filemanage-run-form");
    const runButton = elements.runButton;
    const reopenRunButton = elements.reopenRunButton;
    const confirmModal = document.getElementById("filemanage-run-confirm-modal");
    const confirmTitle = document.getElementById("filemanage-run-confirm-title");
    const confirmCopy = document.getElementById("filemanage-run-confirm-copy");
    const confirmTarget = document.getElementById("filemanage-run-confirm-target");
    const confirmCancel = document.getElementById("filemanage-run-confirm-cancel");
    const confirmSubmit = document.getElementById("filemanage-run-confirm-submit");
    const modal = elements.modal;
    const modalTitle = document.getElementById("filemanage-run-title");
    const modalMessage = document.getElementById("filemanage-run-message");
    const totalNode = document.getElementById("filemanage-run-total");
    const completedNode = document.getElementById("filemanage-run-completed");
    const completedCopyNode = document.getElementById("filemanage-run-completed-copy");
    const currentNode = document.getElementById("filemanage-run-current");
    const finishedNode = document.getElementById("filemanage-run-finished");
    const statusChip = document.getElementById("filemanage-run-status-chip");
    const errorWrap = document.getElementById("filemanage-run-errors-wrap");
    const errorNode = document.getElementById("filemanage-run-errors");
    const closeButtons = modal ? Array.from(modal.querySelectorAll("[data-close-run-modal]")) : [];
    const csrfToken = runForm?.querySelector("input[name=csrfmiddlewaretoken]")?.value || "";

    function openConfirmModal() {
        if (!confirmModal) {
            return;
        }
        confirmTitle.textContent = uiText.confirmTitle || "";
        confirmCopy.textContent = uiText.confirmCopy || "";
        confirmTarget.textContent = `${uiText.confirmTargetLabel || ""}: ${config.previewTotalCount}`;
        confirmCancel.textContent = uiText.confirmCancel || "";
        confirmSubmit.textContent = uiText.confirmButton || "";
        confirmModal.classList.remove("hidden");
        confirmModal.setAttribute("aria-hidden", "false");
    }

    function closeConfirmModal() {
        if (!confirmModal) {
            return;
        }
        confirmModal.classList.add("hidden");
        confirmModal.setAttribute("aria-hidden", "true");
    }

    function openModal() {
        if (!modal) {
            return;
        }
        modal.classList.remove("hidden");
        modal.setAttribute("aria-hidden", "false");
        syncReopenRunButton.call(page);
    }

    function notifyRunFinished(job) {
        if (state.runCompletionNoticeShown || !window.showFlashMessage) {
            return;
        }
        if (modal && !modal.classList.contains("hidden")) {
            return;
        }
        const tone = {
            completed: "success",
            empty: "warning",
            dependency_missing: "warning",
            error: "error",
        }[job.status] || "default";
        window.showFlashMessage(job.message || uiText.completed || "", tone);
        state.runCompletionNoticeShown = true;
    }

    function closeModal() {
        if (!modal) {
            return;
        }
        modal.classList.add("hidden");
        modal.setAttribute("aria-hidden", "true");
        syncReopenRunButton.call(page);
        if (state.lastFinishedJob) {
            notifyRunFinished(state.lastFinishedJob);
        }
    }

    function renderRunningCard(item) {
        if (!currentNode) {
            return;
        }
        if (!item) {
            currentNode.innerHTML = `<div class="empty-state !min-h-0">${uiText.waiting || ""}</div>`;
            return;
        }
        currentNode.innerHTML = `
            <article class="fm-run-log-card fm-run-log-card-active">
                <div class="fm-run-log-meta">${uiText.currentLabel || ""} ${item.index}/${item.total || 0}</div>
                <div class="fm-run-log-title">${item.source || item.action}</div>
                <div class="fm-run-log-subtitle">${item.action}</div>
                ${item.target ? `<div class="fm-run-log-target"><span>${uiText.targetLabel || ""}</span><span>${item.target}</span></div>` : ""}
            </article>
        `;
    }

    function renderCompleted(items) {
        if (!finishedNode || !completedCopyNode) {
            return;
        }
        completedCopyNode.textContent = `${items.length} ${uiText.itemsSuffix || ""}`;
        if (!items.length) {
            finishedNode.innerHTML = `<div class="empty-state !min-h-0">${uiText.noCompleted || ""}</div>`;
            return;
        }
        finishedNode.innerHTML = items.map((item) => `
            <article class="fm-run-log-card">
                <div class="fm-run-log-meta">${uiText.doneLabel || ""} ${item.index}/${item.total || 0}</div>
                <div class="fm-run-log-title">${item.source || item.action}</div>
                <div class="fm-run-log-subtitle">${item.action}</div>
                ${item.target ? `<div class="fm-run-log-target"><span>${uiText.targetLabel || ""}</span><span>${item.target}</span></div>` : ""}
            </article>
        `).join("");
    }

    function renderErrors(items) {
        if (!errorWrap || !errorNode) {
            return;
        }
        errorWrap.classList.toggle("hidden", !items.length);
        if (!items.length) {
            errorNode.innerHTML = "";
            return;
        }
        errorNode.innerHTML = items.map((item) => `
            <article class="fm-run-log-card fm-run-log-card-error">
                <div class="fm-run-log-meta">${uiText.errorLabel || ""}</div>
                <div class="fm-run-log-title">${item.source || item.action}</div>
                ${item.target ? `<div class="fm-run-log-target"><span>${uiText.targetLabel || ""}</span><span>${item.target}</span></div>` : ""}
            </article>
        `).join("");
    }

    function updateStatusChip(status) {
        if (!statusChip) {
            return;
        }
        const map = {
            running: uiText.running,
            completed: uiText.completed,
            empty: uiText.completed,
            dependency_missing: uiText.errorLabel,
            error: uiText.errorLabel,
        };
        statusChip.textContent = map[status] || uiText.running || "";
    }

    function applyJobSnapshot(job) {
        modalTitle.textContent = job.operation_label || config.operationLabel || "";
        modalMessage.textContent = job.message || (job.status === "running" ? uiText.preparing || "" : uiText.nothingMatched || "");
        totalNode.textContent = String(job.total_count || 0);
        completedNode.textContent = String(job.completed_count || 0);
        updateStatusChip(job.status);
        renderRunningCard(job.current_item);
        renderCompleted(job.completed_items || []);
        renderErrors(job.failed_items || []);
        if ((job.completed_items || []).length !== state.lastCompletedCount) {
            finishedNode.scrollTop = finishedNode.scrollHeight;
            state.lastCompletedCount = (job.completed_items || []).length;
        }
        if (job.status !== "running" && !job.current_item && job.status !== "error" && (!job.completed_items || !job.completed_items.length) && !job.failed_items?.length) {
            currentNode.innerHTML = `<div class="empty-state !min-h-0">${job.message || uiText.nothingMatched || ""}</div>`;
        }
        if (job.status === "error" && !job.failed_items?.length) {
            errorWrap.classList.remove("hidden");
            errorNode.innerHTML = `<article class="fm-run-log-card fm-run-log-card-error"><div class="fm-run-log-meta">${uiText.errorLabel || ""}</div><div class="fm-run-log-title">${job.error_message || uiText.errorLabel || ""}</div></article>`;
            currentNode.innerHTML = `<div class="empty-state !min-h-0">${job.error_message || uiText.errorLabel || ""}</div>`;
        }
    }

    function stopPolling() {
        if (state.pollTimer) {
            window.clearTimeout(state.pollTimer);
            state.pollTimer = null;
        }
        state.activeStatusUrl = null;
        syncReopenRunButton.call(page);
    }

    function schedulePoll() {
        if (!state.activeStatusUrl) {
            return;
        }
        state.pollTimer = window.setTimeout(fetchJobStatus, 650);
    }

    async function fetchJobStatus() {
        if (!state.activeStatusUrl) {
            return;
        }
        try {
            const response = await fetch(state.activeStatusUrl, { headers: { Accept: "application/json" } });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            const job = await response.json();
            applyJobSnapshot(job);
            if (["completed", "empty", "dependency_missing", "error"].includes(job.status)) {
                state.lastFinishedJob = job;
                stopPolling();
                try {
                    await page.refreshOperationSnapshot?.();
                } catch (refreshError) {
                    console.error(refreshError);
                }
                notifyRunFinished(job);
                return;
            }
            schedulePoll();
        } catch (error) {
            modalMessage.textContent = error instanceof Error ? error.message : String(error);
            updateStatusChip("error");
            setRunButtonReady(config.previewTotalCount);
            stopPolling();
        }
    }

    async function startRunJob() {
        if (!runButton || runButton.disabled) {
            return;
        }
        closeConfirmModal();
        runButton.disabled = true;
        runButton.setAttribute("aria-disabled", "true");
        state.lastCompletedCount = 0;
        state.lastFinishedJob = null;
        state.runCompletionNoticeShown = false;
        openModal();
        modalTitle.textContent = config.operationLabel || "";
        modalMessage.textContent = uiText.preparing || "";
        totalNode.textContent = "0";
        completedNode.textContent = "0";
        updateStatusChip("running");
        renderRunningCard(null);
        renderCompleted([]);
        renderErrors([]);
        try {
            const response = await fetch(runForm.action, {
                method: "POST",
                headers: {
                    Accept: "application/json",
                    "X-CSRFToken": csrfToken,
                    "X-Requested-With": "XMLHttpRequest",
                },
            });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            const payload = await response.json();
            state.activeStatusUrl = payload.status_url;
            modalTitle.textContent = payload.operation_label || config.operationLabel || "";
            syncReopenRunButton.call(page);
            fetchJobStatus();
        } catch (error) {
            modalMessage.textContent = error instanceof Error ? error.message : String(error);
            updateStatusChip("error");
            setRunButtonReady(config.previewTotalCount);
            stopPolling();
        }
    }

    closeButtons.forEach((button) => button.addEventListener("click", closeModal));
    confirmCancel?.addEventListener("click", closeConfirmModal);
    confirmSubmit?.addEventListener("click", startRunJob);
    confirmModal?.addEventListener("click", (event) => {
        if (event.target === confirmModal) {
            closeConfirmModal();
        }
    });

    runForm?.addEventListener("submit", (event) => {
        event.preventDefault();
        if (!runButton || runButton.disabled) {
            return;
        }
        openConfirmModal();
    });

    reopenRunButton?.addEventListener("click", openModal);
    syncReopenRunButton.call(page);
})();
