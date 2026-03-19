/**
 * Pipeline App — pipeline.js
 * Minimal vanilla JS. No build step required.
 * Runs after DOM is ready (script has defer attribute in base.html).
 */
(function () {
    "use strict";

    /**
     * Auto-scroll the sidebar step list so the active/current step is visible.
     * Called on page load.
     */
    function scrollSidebarToActive() {
        const sidebar = document.getElementById("pipelineSidebarBody");
        if (!sidebar) return;

        const listGroup = sidebar.querySelector(".list-group");
        const activeItem = sidebar.querySelector(".pipeline-step-item.active");
        if (!listGroup || !activeItem) return;

        // Only scroll if the list group itself scrolls (overflow-y: auto)
        const listGroupStyle = window.getComputedStyle(listGroup);
        if (listGroupStyle.overflowY !== "auto" && listGroupStyle.overflowY !== "scroll") return;

        // Scroll the active item into view within the list group, not the page
        const itemTop = activeItem.offsetTop - listGroup.offsetTop;
        const listGroupHeight = listGroup.clientHeight;
        const itemHeight = activeItem.clientHeight;

        if (itemTop < listGroup.scrollTop || itemTop + itemHeight > listGroup.scrollTop + listGroupHeight) {
            listGroup.scrollTop = itemTop - listGroupHeight / 2 + itemHeight / 2;
        }
    }

    /**
     * Disable acknowledgement submit button until the checkbox is checked.
     */
    function wireAckCheckbox() {
        document.querySelectorAll("[id^='ack-checkbox-']").forEach(function (checkbox) {
            const form = checkbox.closest("form");
            if (!form) return;
            const btn = form.querySelector("button[type='submit']");
            if (!btn) return;

            // Set initial state
            btn.disabled = !checkbox.checked;

            checkbox.addEventListener("change", function () {
                btn.disabled = !checkbox.checked;
            });
        });
    }

    /**
     * Collapse sidebar on mobile: update icon direction on show/hide events.
     */
    function wireSidebarCollapse() {
        const sidebarBody = document.getElementById("pipelineSidebarBody");
        if (!sidebarBody) return;

        sidebarBody.addEventListener("show.bs.collapse", function () {
            const icon = document.querySelector(".pipeline-collapse-icon");
            if (icon) icon.style.transform = "rotate(180deg)";
        });

        sidebarBody.addEventListener("hide.bs.collapse", function () {
            const icon = document.querySelector(".pipeline-collapse-icon");
            if (icon) icon.style.transform = "rotate(0deg)";
        });
    }

    // ── Init ──────────────────────────────────────────────────────────────────
    document.addEventListener("DOMContentLoaded", function () {
        scrollSidebarToActive();
        wireAckCheckbox();
        wireSidebarCollapse();
    });

}());
