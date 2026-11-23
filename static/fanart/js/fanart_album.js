(() => {
        const galleryFilter = document.getElementById("album-gallery-filter");
        const characterFilter = document.getElementById("album-character-filter");
        const gallery = document.getElementById("album-gallery");
        const sortSelect = document.getElementById("album-sort-select");
        const previewOverlay = document.getElementById("album-preview-overlay");
        const previewImage = document.getElementById("album-preview-image");
        const previewTitle = document.getElementById("album-preview-title");
        const previewDate = document.getElementById("album-preview-date");
        const previewCopy = document.getElementById("album-preview-copy");
        const previewMetaToggle = document.getElementById("album-preview-meta-toggle");
        const previewPrev = document.getElementById("album-preview-prev");
        const previewNext = document.getElementById("album-preview-next");
        const metaPopover = document.getElementById("album-meta-popover");
        const metaName = document.getElementById("album-meta-name");
        const metaSize = document.getElementById("album-meta-size");
        const metaCreated = document.getElementById("album-meta-created");
        const metaModified = document.getElementById("album-meta-modified");
        const metaPath = document.getElementById("album-meta-path");
        const config = JSON.parse(document.getElementById("fanart-album-js-config").textContent);
        const copyDefaultText = config.copyDefaultText;
        const copyDoneText = config.copyDoneText;
        const copyFailedText = config.copyFailedText;
        const previewFallbackTitle = config.previewFallbackTitle;
        let activeFilePath = "";
        let activeCardIndex = -1;

        function visibleCards() {
            return Array.from(gallery?.querySelectorAll(":scope > button") || []).filter((card) => !card.classList.contains("hidden"));
        }

        function syncNavButtons() {
            const cards = visibleCards();
            const hasMultiple = cards.length > 1;
            const disablePrev = !hasMultiple || activeCardIndex <= 0;
            const disableNext = !hasMultiple || activeCardIndex >= cards.length - 1 || activeCardIndex === -1;

            previewPrev.disabled = disablePrev;
            previewNext.disabled = disableNext;
        }

        function sortGallery() {
            if (!gallery || !sortSelect) {
                return;
            }

            const cards = Array.from(gallery.querySelectorAll(":scope > button"));
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

            cards.forEach((card) => gallery.appendChild(card));
            syncNavButtons();
        }

        function closePreview() {
            if (!previewOverlay) {
                return;
            }
            previewOverlay.classList.add("hidden");
            previewOverlay.setAttribute("aria-hidden", "true");
            document.body.classList.remove("overflow-hidden");
            previewImage.removeAttribute("src");
            metaPopover?.classList.add("hidden");
            activeFilePath = "";
            activeCardIndex = -1;
            if (previewCopy) {
                previewCopy.textContent = copyDefaultText;
            }
        }

        function toggleMetadata() {
            metaPopover?.classList.toggle("hidden");
        }

        async function copyFilePath() {
            if (!activeFilePath || !navigator.clipboard) {
                return;
            }

            try {
                await navigator.clipboard.writeText(activeFilePath);
                previewCopy.textContent = copyDoneText;
                window.setTimeout(() => {
                    previewCopy.textContent = copyDefaultText;
                }, 1400);
            } catch (error) {
                previewCopy.textContent = copyFailedText;
                window.setTimeout(() => {
                    previewCopy.textContent = copyDefaultText;
                }, 1800);
            }
        }

        function populatePreview(card) {
            previewImage.src = card.dataset.fileUrl || card.dataset.previewUrl || "";
            previewTitle.textContent = card.dataset.fileTitle || previewFallbackTitle;
            previewDate.textContent = card.dataset.fileCreated || "";
            activeFilePath = card.dataset.filePath || "";
            metaName.textContent = card.dataset.fileTitle || "";
            metaSize.textContent = card.dataset.fileSize || "";
            metaCreated.textContent = card.dataset.fileCreated || "";
            metaModified.textContent = card.dataset.fileModified || "";
            metaPath.textContent = activeFilePath;
            previewCopy.textContent = copyDefaultText;
            syncNavButtons();
        }

        function openPreview(card) {
            const cards = visibleCards();
            activeCardIndex = cards.indexOf(card);
            if (activeCardIndex === -1) {
                activeCardIndex = 0;
            }
            populatePreview(card);
            metaPopover?.classList.add("hidden");
            previewOverlay.classList.remove("hidden");
            previewOverlay.setAttribute("aria-hidden", "false");
            document.body.classList.add("overflow-hidden");
        }

        function navigatePreview(direction) {
            const cards = visibleCards();
            if (!cards.length) {
                return;
            }
            if (activeCardIndex < 0) {
                activeCardIndex = 0;
            } else {
                activeCardIndex = Math.min(cards.length - 1, Math.max(0, activeCardIndex + direction));
            }
            populatePreview(cards[activeCardIndex]);
            metaPopover?.classList.add("hidden");
        }

        function applyGalleryFilters() {
            const query = galleryFilter?.value.trim().toLowerCase() || "";
            const characterQuery = characterFilter?.value.trim().toLowerCase() || "";
            Array.from(gallery?.querySelectorAll(":scope > button") || []).forEach((card) => {
                const matchesFile = !query || (card.dataset.fileName || "").includes(query);
                const matchesCharacter = !characterQuery || (card.dataset.characterName || "") === characterQuery;
                card.classList.toggle("hidden", !(matchesFile && matchesCharacter));
            });
            syncNavButtons();
        }

        galleryFilter?.addEventListener("input", applyGalleryFilters);
        characterFilter?.addEventListener("change", applyGalleryFilters);

        sortSelect?.addEventListener("change", sortGallery);
        gallery?.querySelectorAll(":scope > button").forEach((card) => {
            card.addEventListener("click", () => openPreview(card));
        });

        previewMetaToggle?.addEventListener("click", (event) => {
            event.stopPropagation();
            toggleMetadata();
        });
        previewCopy?.addEventListener("click", copyFilePath);
        previewPrev?.addEventListener("click", (event) => {
            event.stopPropagation();
            navigatePreview(-1);
        });
        previewNext?.addEventListener("click", (event) => {
            event.stopPropagation();
            navigatePreview(1);
        });
        metaPopover?.addEventListener("click", (event) => {
            event.stopPropagation();
        });
        previewOverlay?.addEventListener("click", (event) => {
            if (event.target === previewOverlay) {
                closePreview();
            }
        });

        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape") {
                closePreview();
            }
            if (previewOverlay?.classList.contains("hidden")) {
                return;
            }
            if (event.key === "ArrowLeft") {
                navigatePreview(-1);
            }
            if (event.key === "ArrowRight") {
                navigatePreview(1);
            }
        });

        sortGallery();
        applyGalleryFilters();
        syncNavButtons();
    })();
