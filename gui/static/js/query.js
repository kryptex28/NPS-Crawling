
let id = 0;

const queryList = document.getElementById("query-list");

const renderQuery = (query) => {
    console.log(query);
    const row = document.createElement("div");
    row.className = "query-item";
    
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = true;
    checkbox.name = "selected_query";
    checkbox.value = id++;
    

    const meta = document.createElement("div");
    meta.classList = "query-meta";
    const sub = document.createElement("span");
    sub.innerHTML = `
    Keyword: ${query.keyword} <br>
    From: ${query.from_date} To: ${query.to_date} (${query.date_range})<br>
    Filing categories: ${query.filing_categories} <br>
    Filing category (general): ${query.filing_category} <br>
    Specified CIK: ${query.individual_search_cik} <br>
    Specified Ticket: ${query.individual_search_ticker} <br>
    Specified Title: ${query.individual_search_title}
    `;

    meta.append(sub);

    row.append(checkbox, meta);
    queryList.appendChild(row);
};

const getQueries = () => {
    console.log("Test");
    fetch("/services/hub-flask/get-queries", { method: "GET" })
    .then(response => {
        if (!response.ok) throw new Error("Failed to fetch queries");
        return response.json();
    })
    .then(data => {
        data.results.forEach(renderQuery);
    })
    .catch(error => {
        console.error("Error fetching queries: ", error);
    })
};

const openLastQueries = () => {

};

document.addEventListener("DOMContentLoaded", getQueries);
