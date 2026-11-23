(() => {
        const config = JSON.parse(document.getElementById("fanart-setting-js-config").textContent);
        const separatorInput = document.getElementById(config.separatorInputId);
        const dateFormatInput = document.getElementById(config.dateFormatInputId);
        const sequencePaddingInput = document.getElementById(config.sequencePaddingInputId);
        const previewNode = document.getElementById("filename-preview");

        if (!separatorInput || !dateFormatInput || !sequencePaddingInput || !previewNode) {
            return;
        }

        const sampleDate = new Date(2029, 1, 1, 13, 45);

        function formatDate(pattern) {
            let result = pattern.toUpperCase();
            const replacements = [
                ["YYYY", String(sampleDate.getFullYear())],
                ["YY", String(sampleDate.getFullYear()).slice(-2)],
                ["MM", String(sampleDate.getMonth() + 1).padStart(2, "0")],
                ["DD", String(sampleDate.getDate()).padStart(2, "0")],
            ];

            replacements.forEach(([token, value]) => {
                result = result.replaceAll(token, value);
            });
            return result;
        }

        function renderPreview() {
            const separator = separatorInput.value;
            const rawPattern = dateFormatInput.value.trim() || "YYYYMMDD";
            const normalizedPattern = rawPattern.toUpperCase();
            const parsedPadding = Number.parseInt(sequencePaddingInput.value, 10);
            const padding = Number.isNaN(parsedPadding) ? 3 : Math.min(Math.max(parsedPadding, 1), 9);
            const dateToken = formatDate(normalizedPattern);
            const sequenceToken = String(1).padStart(padding, "0");

            previewNode.textContent = `Character${separator}${dateToken}${separator}${sequenceToken}.jpg`;
        }

        dateFormatInput.addEventListener("input", () => {
            const selectionStart = dateFormatInput.selectionStart;
            const selectionEnd = dateFormatInput.selectionEnd;
            dateFormatInput.value = dateFormatInput.value.toUpperCase();
            dateFormatInput.setSelectionRange(selectionStart, selectionEnd);
            renderPreview();
        });

        [separatorInput, sequencePaddingInput].forEach((input) => {
            input.addEventListener("input", renderPreview);
        });

        renderPreview();
    })();
