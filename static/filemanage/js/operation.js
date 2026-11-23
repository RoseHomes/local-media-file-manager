(() => {
    const configNode = document.getElementById("filemanage-operation-js-config");
    if (!configNode) {
        return;
    }

    const runButton = document.getElementById("filemanage-run-button");
    const reopenRunButton = document.getElementById("filemanage-reopen-run-button");
    const modal = document.getElementById("filemanage-run-modal");

    const config = JSON.parse(configNode.textContent || "{}");
    const uiText = config.uiText || {};

    window.FileManageOperationPage = {
        config,
        uiText,
        elements: {
            runButton,
            reopenRunButton,
            modal,
        },
        state: {
            pollTimer: null,
            activeStatusUrl: null,
            lastCompletedCount: 0,
            runCompletionNoticeShown: false,
            lastFinishedJob: null,
        },
        escapeHtml(value) {
            return String(value ?? "")
                .replaceAll("&", "&amp;")
                .replaceAll("<", "&lt;")
                .replaceAll(">", "&gt;")
                .replaceAll('"', "&quot;")
                .replaceAll("'", "&#39;");
        },
        setRunButtonReady(totalCount) {
            if (!runButton) {
                return;
            }
            const hasItems = Number(totalCount || 0) > 0;
            runButton.disabled = !hasItems;
            runButton.setAttribute("aria-disabled", hasItems ? "false" : "true");
            if (hasItems) {
                runButton.removeAttribute("title");
            } else {
                runButton.setAttribute("title", uiText.runDisabledTitle || "");
            }
        },
        syncReopenRunButton() {
            if (!reopenRunButton) {
                return;
            }
            const hasRunLog = Boolean(this.state.activeStatusUrl);
            const modalIsOpen = modal && !modal.classList.contains("hidden");
            reopenRunButton.classList.toggle("hidden", !hasRunLog || modalIsOpen);
        },
        refreshOperationSnapshot: null,
        applyPreviewSnapshot: null,
    };
})();
