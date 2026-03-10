const form = document.getElementById("edgar-form");
const resultsPanel = document.getElementById("results-panel");
const resultsList = document.getElementById("results-list");
const bulkSelect = document.getElementById("bulk-select");

const dummyResults = [
  {
    ciks: ['abc'],
    display_names: 'abc',
    form_type: '',
    cik: "0000320193",
    filingId: "0000320193-26-000001",
    url: "https://www.sec.gov/Archives/edgar/data/320193/000032019326000001/filing-index.html",
    status: "Crawled",
  },
  {
    cik: "0000789019",
    filingId: "0000789019-26-000002",
    url: "https://www.sec.gov/Archives/edgar/data/789019/000078901926000002/filing-index.html",
    status: "Crawled",
  },
  {
    cik: "0001652044",
    filingId: "0001652044-26-000003",
    url: "https://www.sec.gov/Archives/edgar/data/1652044/000165204426000003/filing-index.html",
    status: "Crawled",
  },
];

function renderResults(items) {
  // resultsList.innerHTML = "";

  items.forEach((item, index) => {
    const row = document.createElement("div");
    row.className = "result-item";

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = true;
    checkbox.name = "selected_results";
    checkbox.value = item.filingId;
    checkbox.id = `result-${index}`;

    const meta = document.createElement("div");
    meta.className = "result-meta";
    const link = document.createElement("a");
    link.href = item.url;
    link.target = "_blank";
    link.rel = "noreferrer";
    //link.textContent = item.filingId;
    link.textContent = item.display_names
    const sub = document.createElement("span");
    sub.innerHTML = `
    CIKs ${item.ciks} <br>
    Form: ${item.form}
    `;
    meta.append(link, sub);

    const status = document.createElement("span");
    status.className = "status-pill";
    status.textContent = item.status;

    row.append(checkbox, meta, status);
    resultsList.appendChild(row);
  });
}

function setAllCheckboxes(checked) {
  resultsList.querySelectorAll("input[type='checkbox']").forEach((cb) => {
    cb.checked = checked;
  });
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const formData = new FormData(form);

  const response = await fetch("/search", {
    method: "POST",
    body: formData
  });

  // const data = await response.json()

  // renderResults(data);


  resultsPanel.hidden = false;
});

form.addEventListener("reset", () => {
  resultsPanel.hidden = true;
  resultsList.innerHTML = "";
});

bulkSelect.addEventListener("change", () => {
  if (bulkSelect.value === "all") {
    setAllCheckboxes(true);
  } else if (bulkSelect.value === "none") {
    setAllCheckboxes(false);
  }
});

const source = new EventSource('/crawl-stream');

source.onmessage = (e) => {

  let result;
  try {
    result = JSON.parse(e.data);
  } catch(err) {
    console.error("JSON parse failed:", err);
    return;
  }

  const items = Array.isArray(result) ? result : [result];

  renderResults(items);
};

source.onopen = () => {
    resultsPanel.hidden = false;
};

source.onerror = (e) => {
  console.error("SSE error:", e);
};