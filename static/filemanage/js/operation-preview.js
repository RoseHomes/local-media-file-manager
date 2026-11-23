(() => {
    const page = window.FileManageOperationPage;
    if (!page) {
        return;
    }

    const { config, uiText, escapeHtml, setRunButtonReady } = page;
    const filterInput = document.getElementById("operation-filter");
    const sortSelect = document.getElementById("operation-sort");
    const list = document.getElementById("operation-list");
    const previewListWrap = document.getElementById("filemanage-preview-list-wrap");
    const previewEmpty = document.getElementById("filemanage-preview-empty");
    const previewTotal = document.getElementById("filemanage-preview-total");
    const previewFolderCount = document.getElementById("filemanage-preview-folder-count");
    const previewTruncated = document.getElementById("filemanage-preview-truncated");
    const previewTruncatedVisible = document.getElementById("filemanage-preview-truncated-visible");
    const previewTruncatedTotal = document.getElementById("filemanage-preview-truncated-total");
    const workspaceFolderCount = document.getElementById("filemanage-workspace-folder-count");
    const workspaceFileCount = document.getElementById("filemanage-workspace-file-count");
    const plannedActionsCount = document.getElementById("filemanage-planned-actions-count");

    function rows() {
        return Array.from(list?.querySelectorAll(":scope > article") || []);
    }

    function applyFilter() {
        const query = (filterInput?.value || "").trim().toLowerCase();
        rows().forEach((row) => {
            row.classList.toggle("hidden", Boolean(query) && !(row.dataset.search || "").includes(query));
        });
    }

    function applySort() {
        if (!list || !sortSelect) {
            return;
        }
        const currentRows = rows();
        currentRows.sort((left, right) => {
            const leftName = left.dataset.name || "";
            const rightName = right.dataset.name || "";
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
        currentRows.forEach((row) => list.appendChild(row));
    }

    function renderPreviewItems(items) {
        if (!list || !previewListWrap || !previewEmpty) {
            return;
        }
        if (!items.length) {
            list.innerHTML = "";
            previewListWrap.classList.add("hidden");
            previewEmpty.classList.remove("hidden");
            previewEmpty.textContent = uiText.emptyPreview || "";
            return;
        }
        previewListWrap.classList.remove("hidden");
        previewEmpty.classList.add("hidden");
        list.innerHTML = items.map((item) => `
            <article class="file-task-card" data-search="${escapeHtml(item.searchable)}" data-name="${escapeHtml((item.title || "").toLowerCase())}" data-created="${escapeHtml(item.created_ts || 0)}">
                <div class="file-task-head">
                    <div>
                        <div class="file-task-title">${escapeHtml(item.title)}</div>
                        <div class="file-task-subtitle">${escapeHtml(item.folder)}</div>
                    </div>
                    <div class="file-kind-badge">${escapeHtml(item.kind)}</div>
                </div>
                <div class="mt-4 grid gap-3 text-sm text-muted md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
                    <div class="file-task-block">
                        <div class="file-task-label">${escapeHtml(uiText.source)}</div>
                        <div class="file-task-value">${escapeHtml(item.source)}</div>
                    </div>
                    <div class="file-task-block">
                        <div class="file-task-label">${escapeHtml(uiText.target)}</div>
                        <div class="file-task-value">${escapeHtml(item.target)}</div>
                    </div>
                </div>
                <div class="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm text-muted">
                    <div class="flex flex-wrap items-center gap-3">
                        <span class="operation-chip">${escapeHtml(item.action)}</span>
                        ${item.note ? `<span>${escapeHtml(item.note)}</span>` : ""}
                    </div>
                    <div class="flex flex-wrap items-center gap-3">
                        <span>${escapeHtml(item.created_label)}</span>
                        <span>${escapeHtml(item.size_label)}</span>
                    </div>
                </div>
            </article>
        `).join("");
    }

    function applyPreviewSnapshot(snapshot) {
        const preview = snapshot?.preview || {};
        const workspaceSnapshot = snapshot?.workspace_snapshot || {};
        config.previewTotalCount = Number(preview.total_count || 0);
        if (previewTotal) {
            previewTotal.textContent = String(preview.total_count || 0);
        }
        if (previewFolderCount) {
            previewFolderCount.textContent = String(preview.folder_count || 0);
        }
        if (plannedActionsCount) {
            plannedActionsCount.textContent = String(preview.total_count || 0);
        }
        if (workspaceFolderCount) {
            workspaceFolderCount.textContent = String(workspaceSnapshot.folder_count || 0);
        }
        if (workspaceFileCount) {
            workspaceFileCount.textContent = String(workspaceSnapshot.file_count || 0);
        }
        if (previewTruncated) {
            previewTruncated.classList.toggle("hidden", !preview.truncated);
        }
        if (previewTruncatedVisible) {
            previewTruncatedVisible.textContent = String((preview.items || []).length);
        }
        if (previewTruncatedTotal) {
            previewTruncatedTotal.textContent = String(preview.total_count || 0);
        }
        renderPreviewItems(preview.items || []);
        setRunButtonReady(preview.total_count || 0);
        applySort();
        applyFilter();
    }

    async function refreshOperationSnapshot() {
        if (!config.refreshUrl) {
            return;
        }
        const response = await fetch(config.refreshUrl, { headers: { Accept: "application/json" } });
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        applyPreviewSnapshot(await response.json());
    }

    page.applyPreviewSnapshot = applyPreviewSnapshot;
    page.refreshOperationSnapshot = refreshOperationSnapshot;

    filterInput?.addEventListener("input", applyFilter);
    sortSelect?.addEventListener("change", applySort);

    applySort();
    applyFilter();
    setRunButtonReady(config.previewTotalCount);

    document.addEventListener("filemanage:settingsSaved", async () => {
        try {
            await refreshOperationSnapshot();
        } catch (error) {
            console.error("Failed to refresh preview snapshot:", error);
        }
    });
})();
