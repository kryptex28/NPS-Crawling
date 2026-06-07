const form = document.getElementById("edgar-form");
const resultsPanel = document.getElementById("results-panel");
const resultsList = document.getElementById("results-list");
const bulkSelect = document.getElementById("bulk-select");

document.querySelectorAll(".collapsible").forEach(button => {
  console.log("click")
  button.addEventListener("click", () => {
    button.classList.toggle("active");
    const content = button.nextElementSibling;
    content.style.display = content.style.display === "block" ? "none" : "block";
  });
});

function renderResults(items) {
  resultsList.innerHTML = "";

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
    link.textContent = item.filingId;
    const sub = document.createElement("span");
    sub.textContent = `CIK ${item.cik}`;
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

  try {
    const response = await fetch("/services/hub-flask/create-query", {
      method: "POST",
      body: formData
    });

    const result = await response.json()

    if (result.status) {
      queryList.innerHTML = "";
      queryMap.clear();
      getQueries();
    }

  } catch (err) {
    console.error("Failed to create query: ", err);
  }
});

form.addEventListener("reset", () => {
  resultsPanel.hidden = true;
  resultsList.innerHTML = "";
});


document.getElementById("search-form").addEventListener("submit", (event) =>  {
  document.getElementById("ids-input").value = JSON.stringify(getSelectedIds());
})
