const statusComplete = document.getElementById("status-complete");
const statusBlock = document.querySelector(".status-block");
const pagingControl = document.getElementById("paging-control");

const pagingPrev = document.getElementById("paging-prev");
const pagingNext = document.getElementById("paging-next");
const pagingInfo = document.getElementById("paging-info");

const elementCount = document.getElementById("element-count");

const start = Date.now();

const sseStream = new EventSource('/crawl-stream');
const resultsList = document.getElementById("results-list");

let totalCount = 0;
let pageCount = 0;
let maxItemsPerPage = 10;
let allItems = [];
let currentPage = 0;

const renderPage = (page) => {
  resultsList.innerHTML = "";

  const startIndex = page * maxItemsPerPage;
  const pageItems = allItems.slice(startIndex, startIndex + maxItemsPerPage);

  pageItems.forEach((item, index) => {
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
};

const updatePaging = () => {
  const totalPages = Math.ceil(allItems.length / maxItemsPerPage); 

  pagingControl.hidden = totalPages <= 1;
  
  pagingInfo.textContent = `Page ${currentPage + 1} of ${totalPages}`;

  if(totalPages > 1 && currentPage > 0) {
    pagingPrev.disabled = false;
  }
};

pagingPrev.addEventListener("click", () => {
  console.log("Click Prev");
  if(currentPage > 0) {
    currentPage--;
    renderPage(currentPage);
    updatePaging();
  }
});

pagingNext.addEventListener("click", () => {
  console.log("Click Next");
  const totalPages = Math.ceil(allItems.length / maxItemsPerPage); 
  if (currentPage < totalPages - 1) {
    currentPage++;
    renderPage(currentPage);
    updatePaging();
  }
});

sseStream.onmessage = (e) => {
  let result;
  try {
    result = JSON.parse(e.data);
  } catch(err) {
    console.error("JSON parse failed:", err);
    return;
  }

  // Check for completion signal
  if (result.__done) {
    const elapsed = Math.round((Date.now() - start) / 1000);
    const mm = String(Math.floor(elapsed / 60)).padStart(2, "0");
    const ss = String(elapsed % 60).padStart(2, "0");
    statusComplete.querySelector("p").textContent =
      `Process completed. Duration: ${mm}:${ss}. Newly crawled files: ${totalCount}.`;
    statusBlock.style.display = "none";
    statusComplete.hidden = false;
    sseStream.close();
    return;
  }

  const items = Array.isArray(result) ? result : [result];
  addResults(items);
};

const addResults = (items) => {
  allItems.push(...items);
  totalCount += items.length;

  const totalPages = Math.ceil(allItems.length / maxItemsPerPage);

  if(currentPage >= totalPages - 1) {
    renderPage(currentPage);
  }

  elementCount.textContent = `Elements: ${totalCount}`;

  updatePaging();
};

sseStream.onopen = () => {
    resultsPanel.hidden = false;
};

sseStream.onerror = (e) => {
  console.error("SSE error:", e);
  sseStream.close();
};