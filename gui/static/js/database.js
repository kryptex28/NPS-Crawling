const resultsTable = document.getElementById("results-table");
const modalOverlay = document.getElementById("modal-overlay");
const modalClose = document.getElementById("modal-close");
const modalFooter = document.getElementById("modal-footer");
const showDbBtn = document.getElementById("show-db-btn");

let rowCount = 0;
let sseStream = null;

const openModal = () => {
    resultsTable.innerHTML = "";
    rowCount = 0;
    modalFooter.textContent = "Loading…";
    modalOverlay.classList.add("active");
};

const closeModal = () => {
    modalOverlay.classList.remove("active");
    if (sseStream) {
        sseStream.close();
        sseStream = null;
    }
};

const renderRow = (item) => {
    // Build header once
    if (rowCount === 0) {
        const thead = resultsTable.createTHead();
        const headerRow = thead.insertRow();
        ["Ticker", "Form", "File Type", "Period Ending", "File Date", "Company", "Keywords", "NPS Relevant", "Blacklisted"]
            .forEach(col => {
                const th = document.createElement("th");
                th.textContent = col;
                headerRow.appendChild(th);
            });
        resultsTable.createTBody();
    }

    const tbody = resultsTable.tBodies[0];
    const row = tbody.insertRow();

    [
        item.ticker?.join(", ") ?? "—",
        item.form ?? "—",
        item.file_type ?? "—",
        item.period_ending ?? "—",
        item.file_date ?? "—",
        item.display_names?.[0] ?? "—",
        item.keywords?.join(", ") ?? "—",
        item.nps_relevant ?? "—",
        item.blacklisted ? "Yes" : "No",
    ].forEach(value => {
        const td = row.insertCell();
        td.textContent = value;
    });

    rowCount++;
    modalFooter.textContent = `${rowCount} entries loaded…`;
};

const startStream = () => {
    sseStream = new EventSource("/services/hub-flask/database-stream");

    sseStream.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            renderRow(data);
        } catch (e) {
            console.error("Failed to parse SSE payload:", event.data, e);
        }
    };

    sseStream.onerror = () => {
        if (sseStream.readyState === EventSource.CLOSED) {
            modalFooter.textContent = `${rowCount} entries loaded.`;
        } else {
            console.error("SSE stream error");
            modalFooter.textContent = "Error loading entries.";
        }
        sseStream.close();
        sseStream = null;
    };
};

showDbBtn.addEventListener("click", () => {
    openModal();
    startStream();
    fetch("/services/hub-flask/database-count")
});

modalClose.addEventListener("click", closeModal);

modalOverlay.addEventListener("click", (e) => {
    if (e.target === modalOverlay) closeModal(); // close on backdrop click
});

document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeModal();
});