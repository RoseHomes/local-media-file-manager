(() => {
            const flashStack = document.getElementById('flash-message-stack');
            const flashMessages = Array.from(document.querySelectorAll('[data-flash-message]'));
            const defaultFlashDuration = Number(document.body?.dataset?.flashDurationMs || '5000');
            const closeFlash = (node) => {
                if (!node || node.dataset.closing === '1') {
                    return;
                }
                node.dataset.closing = '1';
                node.classList.add('flash-message-closing');
                window.setTimeout(() => node.remove(), 220);
            };

            const wireFlash = (node, duration = defaultFlashDuration) => {
                if (!node) {
                    return;
                }
                const closeButton = node.querySelector('[data-flash-close]');
                closeButton?.addEventListener('click', () => closeFlash(node));
                window.setTimeout(() => closeFlash(node), duration);
            };

            window.showFlashMessage = (message, level = 'default', duration = defaultFlashDuration) => {
                if (!flashStack || !message) {
                    return;
                }
                const toneClass = {
                    success: 'flash-message-success',
                    warning: 'flash-message-warning',
                    error: 'flash-message-error',
                    default: 'flash-message-default',
                }[level] || 'flash-message-default';
                const node = document.createElement('div');
                node.className = `flash-message pointer-events-auto ${toneClass}`;
                node.setAttribute('data-flash-message', '');
                node.innerHTML = `
                    <div class="min-w-0 pr-3"></div>
                    <button class="flash-message-close" type="button" data-flash-close aria-label="${defaultCloseNotificationLabel}">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                            <path d="M18 6 6 18"></path>
                            <path d="m6 6 12 12"></path>
                        </svg>
                    </button>
                `;
                node.querySelector('div').textContent = message;
                flashStack.prepend(node);
                wireFlash(node, duration);
            };

            flashMessages.forEach((node) => wireFlash(node));

            const enhanced = new WeakSet();
            const config = JSON.parse(document.getElementById("base-js-config").textContent);
            const defaultSearchPlaceholder = config.searchPlaceholder;
            const defaultEmptyLabel = config.emptyLabel;
            const defaultSelectLabel = config.selectLabel;
            const defaultClearSelectionLabel = config.clearSelection;
            const defaultCloseNotificationLabel = config.closeNotification;

            const widthClassPattern = /^(?:[a-z]+:)?(?:w-|min-w-|max-w-|flex-|shrink-|grow-|basis-)/;

            function getWidthClasses(select) {
                return Array.from(select.classList).filter((className) => widthClassPattern.test(className)).join(" ");
            }

            function createOptionButton(option, nativeSelect, onClose) {
                const button = document.createElement("button");
                button.type = "button";
                button.className = `rich-select-option${option.selected ? " rich-select-option-selected" : ""}`;
                button.dataset.value = option.value;
                button.setAttribute("role", "option");
                button.setAttribute("aria-selected", option.selected ? "true" : "false");
                button.innerHTML = `
                    <span class="rich-select-option-copy">${option.textContent}</span>
                    ${option.selected ? '<span class="rich-select-option-check" aria-hidden="true"></span>' : ''}
                `;
                button.addEventListener("click", () => {
                    if (nativeSelect.value !== option.value) {
                        nativeSelect.value = option.value;
                        nativeSelect.dispatchEvent(new Event("input", { bubbles: true }));
                        nativeSelect.dispatchEvent(new Event("change", { bubbles: true }));
                    }
                    onClose();
                });
                button.addEventListener("keydown", (event) => {
                    if (event.key === "Escape") {
                        event.preventDefault();
                        onClose();
                    }
                });
                return button;
            }

            function enhanceSelect(nativeSelect) {
                if (enhanced.has(nativeSelect) || nativeSelect.multiple || nativeSelect.dataset.richSelect === "off") {
                    return;
                }

                enhanced.add(nativeSelect);
                nativeSelect.classList.add("rich-select-native");

                const wrapper = document.createElement("div");
                const widthClasses = getWidthClasses(nativeSelect);
                const clearableClass = nativeSelect.dataset.richClearable === "true" ? "rich-select-shell-clearable" : "";
                wrapper.className = `rich-select-shell ${widthClasses} ${nativeSelect.classList.contains("hero-root-select") ? "rich-select-shell-hero" : ""} ${clearableClass}`.trim();

                const trigger = document.createElement("button");
                trigger.type = "button";
                trigger.className = "rich-select-trigger";
                trigger.setAttribute("aria-haspopup", "listbox");
                trigger.setAttribute("aria-expanded", "false");

                const value = document.createElement("span");
                value.className = "rich-select-value";

                let clearButton = null;
                if (nativeSelect.dataset.richClearable === "true") {
                    clearButton = document.createElement("button");
                    clearButton.type = "button";
                    clearButton.className = "rich-select-clear hidden";
                    clearButton.setAttribute("aria-label", nativeSelect.dataset.richClearLabel || defaultClearSelectionLabel);
                    clearButton.innerHTML = `
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                            <path d="M18 6 6 18"></path>
                            <path d="m6 6 12 12"></path>
                        </svg>
                    `;
                }

                const chevron = document.createElement("span");
                chevron.className = "rich-select-chevron";
                chevron.setAttribute("aria-hidden", "true");

                trigger.append(value, chevron);

                const menu = document.createElement("div");
                menu.className = "rich-select-menu hidden";

                const searchable = nativeSelect.options.length > 8 || nativeSelect.dataset.richSearch === "true";
                let searchInput = null;
                if (searchable) {
                    const searchRow = document.createElement("div");
                    searchRow.className = "rich-select-search-row";
                    searchInput = document.createElement("input");
                    searchInput.type = "search";
                    searchInput.className = "input";
                    searchInput.placeholder = nativeSelect.dataset.richPlaceholder || defaultSearchPlaceholder;
                    searchRow.appendChild(searchInput);
                    menu.appendChild(searchRow);
                }

                const list = document.createElement("div");
                list.className = "custom-scrollbar rich-select-list";
                list.setAttribute("role", "listbox");
                menu.appendChild(list);

                if (clearButton) {
                    wrapper.append(trigger, clearButton, menu);
                } else {
                    wrapper.append(trigger, menu);
                }
                nativeSelect.insertAdjacentElement("afterend", wrapper);

                const closeMenu = () => {
                    menu.classList.add("hidden");
                    wrapper.classList.remove("rich-select-open");
                    trigger.setAttribute("aria-expanded", "false");
                    searchInput?.blur();
                };

                const openMenu = () => {
                    if (nativeSelect.disabled) {
                        return;
                    }
                    menu.classList.remove("hidden");
                    wrapper.classList.add("rich-select-open");
                    trigger.setAttribute("aria-expanded", "true");
                    if (searchInput) {
                        searchInput.value = "";
                        renderOptions();
                        searchInput.focus();
                    }
                };

                const renderLabel = () => {
                    const selected = nativeSelect.options[nativeSelect.selectedIndex] || nativeSelect.options[0];
                    const label = selected ? selected.textContent : defaultSelectLabel;
                    value.textContent = label;
                    value.classList.toggle("rich-select-value-placeholder", !selected || !selected.value);
                    trigger.disabled = nativeSelect.disabled;
                    if (clearButton) {
                        const showClear = Boolean(nativeSelect.value) && !nativeSelect.disabled;
                        clearButton.classList.toggle("hidden", !showClear);
                    }
                };

                const renderOptions = () => {
                    const query = (searchInput?.value || "").trim().toLowerCase();
                    list.innerHTML = "";
                    const options = Array.from(nativeSelect.options).filter((option) => {
                        const visible = !option.hidden || option.selected;
                        if (!visible) {
                            return false;
                        }
                        if (!query) {
                            return true;
                        }
                        return option.textContent.toLowerCase().includes(query);
                    });

                    if (!options.length) {
                        const empty = document.createElement("div");
                        empty.className = "rich-select-empty";
                        empty.textContent = nativeSelect.dataset.richEmpty || defaultEmptyLabel;
                        list.appendChild(empty);
                        return;
                    }

                    options.forEach((option) => {
                        const optionButton = createOptionButton(option, nativeSelect, closeMenu);
                        if (option.disabled) {
                            optionButton.disabled = true;
                            optionButton.classList.add("opacity-45", "cursor-not-allowed");
                        }
                        list.appendChild(optionButton);
                    });
                };

                trigger.addEventListener("click", () => {
                    if (menu.classList.contains("hidden")) {
                        openMenu();
                    } else {
                        closeMenu();
                    }
                });

                trigger.addEventListener("keydown", (event) => {
                    if (["ArrowDown", "Enter", " "].includes(event.key)) {
                        event.preventDefault();
                        openMenu();
                    }
                    if (event.key === "Escape") {
                        closeMenu();
                    }
                });

                clearButton?.addEventListener("click", (event) => {
                    event.preventDefault();
                    event.stopPropagation();
                    if (!nativeSelect.value) {
                        return;
                    }
                    nativeSelect.value = "";
                    nativeSelect.dispatchEvent(new Event("input", { bubbles: true }));
                    nativeSelect.dispatchEvent(new Event("change", { bubbles: true }));
                    closeMenu();
                });

                searchInput?.addEventListener("input", renderOptions);
                menu.addEventListener("click", (event) => event.stopPropagation());
                document.addEventListener("click", (event) => {
                    if (!wrapper.contains(event.target)) {
                        closeMenu();
                    }
                });
                nativeSelect.addEventListener("change", () => {
                    renderLabel();
                    renderOptions();
                });
                nativeSelect.addEventListener("rich-select:refresh", renderOptions);

                const observer = new MutationObserver(() => {
                    renderLabel();
                    renderOptions();
                });
                observer.observe(nativeSelect, {
                    attributes: true,
                    childList: true,
                    subtree: true,
                    attributeFilter: ["hidden", "disabled", "label", "selected", "value"],
                });

                renderLabel();
                renderOptions();
            }

            const sidebarStateKey = "fm-sidebar-groups";
            const sidebarGroups = document.querySelectorAll("details[data-sidebar-group]");

            try {
                const savedSidebarState = JSON.parse(localStorage.getItem(sidebarStateKey) || "{}");
                sidebarGroups.forEach((group) => {
                    const key = group.dataset.sidebarGroup;
                    if (Object.prototype.hasOwnProperty.call(savedSidebarState, key)) {
                        group.open = Boolean(savedSidebarState[key]);
                    }
                });

                sidebarGroups.forEach((group) => {
                    group.addEventListener("toggle", () => {
                        const nextState = JSON.parse(localStorage.getItem(sidebarStateKey) || "{}");
                        nextState[group.dataset.sidebarGroup] = group.open;
                        localStorage.setItem(sidebarStateKey, JSON.stringify(nextState));
                    });
                });
            } catch (error) {
                console.warn("Failed to persist sidebar group state", error);
            }

            document.querySelectorAll("select").forEach(enhanceSelect);
        })();
