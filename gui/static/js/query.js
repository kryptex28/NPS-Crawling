
let id = 0;

const queryList = document.getElementById("query-list");
const btnSelectAll = document.getElementById("query-select-all");
const btnDelete = document.getElementById("query-delete");


const queryMap = new Map();

const renderQuery = (uuid, content) => {
    const row = document.createElement("div");
    row.className = "query-item";
    row.dataset.id = uuid;
    
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = true;
    checkbox.name = "selected_query";
    checkbox.value = uuid;
    

    const meta = document.createElement("div");
    meta.classList = "query-meta";
    const sub = document.createElement("span");
    sub.innerHTML = `
    Keyword: ${content.keyword} <br>
    From: ${content.from_date} To: ${content.to_date} (${content.date_range})<br>
    Filing categories: ${content.filing_categories} <br>
    Filing category (general): ${content.filing_category} <br>
    Specified CIK: ${content.individual_search_cik} <br>
    Specified Ticket: ${content.individual_search_ticker} <br>
    Specified Title: ${content.individual_search_title}
    `;

    meta.append(sub);

    row.append(checkbox, meta);
    queryList.appendChild(row);
};

const getQueries = () => {
    fetch("/services/hub-flask/get-queries", { method: "GET" })
        .then(response => {
            if (!response.ok) throw new Error("Failed to fetch queries");
            return response.json();
        })
        .then(data => {
            data.results.forEach((element) => {
                const uuid = element.id;
                const content = element[uuid];
                queryMap.set(uuid, content);
            });
            queryMap.forEach((content, uuid) => {
                renderQuery(uuid, content);
            });
        })
        .catch(error => {
            console.error("Error fetching queries: ", error);
        });
};

btnSelectAll.addEventListener("click", () => {
    const checkboxes = queryList.querySelectorAll("input[type='checkbox']");
    const allChecked = [...checkboxes].every(cb => cb.checked);
    checkboxes.forEach(cb => cb.checked = !allChecked);
});

btnDelete.addEventListener("click", async () => {
    const selectedIds = getSelectedIds();
    for (const uuid of selectedIds) {
        try {
            const response = await fetch("/services/hub-flask/delete-query", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ id: uuid })
            });
            const result = await response.json();
            if (result.status) {
                queryMap.delete(uuid);
                queryList.querySelector(`[data-id="${uuid}"]`).remove();
            }
        } catch(err) {
            console.error("Error deleting query: ", err);
        }
    }
});

document.addEventListener("DOMContentLoaded", getQueries);

const getSelectedIds = () => {
    return [...queryList.querySelectorAll("input[type='checkbox']:checked")].map(cb => cb.value);

};
