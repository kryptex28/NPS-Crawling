const resultsTable = document.getElementById("results-table");


const sseStream = new EventSource("/services/hub-flask/database-stream");

const renderResults = (item) => {
    // Build header row once
    if (resultsTable.rows.length === 0) {
        const thead = resultsTable.createTHead();
        const headerRow = thead.insertRow();
        const columns = ["Ticker", "Form", "File Type", "Period Ending", "File Date", "Company", "Keywords", "NPS Relevant", "Blacklisted"];
        columns.forEach(col => {
            const th = document.createElement("th");
            th.textContent = col;
            headerRow.appendChild(th);
        });
        resultsTable.createTBody();
    }

    const tbody = resultsTable.tBodies[0];
    const row = tbody.insertRow();

    const cells = [
        item.ticker?.join(", ") ?? "—",
        item.form ?? "—",
        item.file_type ?? "—",
        item.period_ending ?? "—",
        item.file_date ?? "—",
        item.display_names?.[0] ?? "—",
        item.keywords?.join(", ") ?? "—",
        item.nps_relevant ?? "—",
        item.blacklisted ? "Yes" : "No",
    ];

    cells.forEach(value => {
        const td = row.insertCell();
        td.textContent = value;
    });
};


sseStream.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log("Received data:", data);
  renderResults(data);
};