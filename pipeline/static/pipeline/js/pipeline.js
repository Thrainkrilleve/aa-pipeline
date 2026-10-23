/**
 * Pipeline App — pipeline.js
 * Minimal vanilla JS. No build step required.
 * Runs after DOM is ready (script has defer attribute in base.html).
 */
(function () {
    "use strict";

    /**
     * Keep the acknowledgement button disabled until its checkbox is ticked.
     */
    function wireAckCheckbox() {
        document.querySelectorAll("[id^='ack-checkbox-']").forEach(function (checkbox) {
            const form = checkbox.closest("form");
            const btn = form && form.querySelector("button[type='submit']");
            if (!btn) return;

            btn.disabled = !checkbox.checked;
            checkbox.addEventListener("change", function () {
                btn.disabled = !checkbox.checked;
            });
        });
    }

    /**
     * Scroll the step list so the current step is visible when the list is
     * taller than the viewport.
     */
    function scrollStepperToCurrent() {
        const card = document.querySelector(".pipeline-stepper-card");
        const current = card && card.querySelector(".pipeline-stepper-item.is-current");
        if (!current || card.scrollHeight <= card.clientHeight) return;
        card.scrollTop = current.offsetTop - card.clientHeight / 2 + current.clientHeight / 2;
    }

    /**
     * Ask before submitting buttons that carry data-pipeline-confirm.
     */
    function wireConfirmations() {
        document.addEventListener("click", function (event) {
            const button = event.target.closest("[data-pipeline-confirm]");
            if (button && !window.confirm(button.dataset.pipelineConfirm)) {
                event.preventDefault();
            }
        });
    }

    /**
     * Show elements marked data-pipeline-when="field=value value" only while
     * the named field in the same form has one of the listed values. Hidden
     * fields stay enabled so their saved values are kept.
     */
    function wireConditionalFields() {
        document.querySelectorAll("form[data-pipeline-conditional]").forEach(function (form) {
            const targets = Array.from(form.querySelectorAll("[data-pipeline-when]"));
            const typeField = form.elements.namedItem("step_type");
            // Step-type dependent cards outside the form (e.g. Smart Filter checks).
            const outside = Array.from(document.querySelectorAll("[data-pipeline-when-type]"));

            function update() {
                targets.forEach(function (el) {
                    const [name, values] = el.dataset.pipelineWhen.split("=");
                    const field = form.elements.namedItem(name.trim());
                    el.hidden = !(field && values.trim().split(/\s+/).includes(field.value));
                });
                outside.forEach(function (el) {
                    el.hidden = !(typeField && typeField.value === el.dataset.pipelineWhenType);
                });
            }

            form.addEventListener("change", update);
            update();
        });
    }

    /**
     * Filter box above each audience multi-select, plus a "n selected" count.
     */
    function wireSelectFilters() {
        document.querySelectorAll("[data-pipeline-filter-select]").forEach(function (input) {
            const select = document.getElementById(input.dataset.pipelineFilterSelect);
            if (!select) return;
            const counter = document.querySelector(
                "[data-pipeline-selected-count='" + select.id + "']"
            );

            input.addEventListener("input", function () {
                const query = input.value.trim().toLowerCase();
                Array.from(select.options).forEach(function (option) {
                    option.hidden = query !== "" && !option.text.toLowerCase().includes(query);
                });
            });

            function updateCount() {
                if (!counter) return;
                const count = select.selectedOptions.length;
                counter.textContent = count ? count + " selected" : "";
            }
            select.addEventListener("change", updateCount);
            updateCount();
        });
    }

    // ── Init ──────────────────────────────────────────────────────────────────
    document.addEventListener("DOMContentLoaded", function () {
        wireAckCheckbox();
        scrollStepperToCurrent();
        wireConfirmations();
        wireConditionalFields();
        wireSelectFilters();
    });

}());
