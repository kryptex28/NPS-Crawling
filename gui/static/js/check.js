const statusComplete = document.getElementById("status-complete");
const statusBlock = document.querySelector(".status-block");
const pagingControl = document.querySelector(".paging-control");

const pagingPrev = document.getElementById("paging-prev");
const pagingNext = document.getElementById("paging-next");
const pagingInfo = document.getElementById("paging-info");

const startCrawlBtn = document.getElementById("start-crawl");
const stopCrawlBtn = document.getElementById("stop-crawl");
const clearResultsBtn = document.getElementById("clear-results");

const elementCount = document.getElementById("element-count");

const start = Date.now();

const sseStream = new EventSource("/services/hub-flask/stream-crawl");
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
    row.classList.add(item.status);

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = true;
    checkbox.name = "selected_results";
    checkbox.value = item.filing_id;
    checkbox.id = `result-${startIndex + index}`;

    const meta = document.createElement("div");
    meta.className = "result-meta";
    const link = document.createElement("a");
    link.href = item.url;
    link.target = "_blank";
    link.rel = "noreferrer";
    //link.textContent = item.filingId;
    link.textContent = item.display_names[0]
    const sub = document.createElement("span");
    sub.innerHTML = `
    CIKs ${item.ciks} <br>
    Form: ${item.form}
    `;
    meta.append(link, sub);

    const status = document.createElement("span");
    // status.className = `status-pill ${item.status}`;
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
  console.log("Received SSE message:", e.data);
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

document.querySelectorAll('.segmented-control input[type="radio"]').forEach(radio => {
  radio.addEventListener('change', (e) => {
    maxItemsPerPage = parseInt(e.target.value);
    currentPage = 0;
    renderPage(currentPage);
    updatePaging();
  });
});

const addResults = (items) => {
  items.forEach(item => {
    const existingIndex = allItems.findIndex(i => i.filing_id === item.filing_id);

    if (existingIndex !== -1) {
      allItems[existingIndex] = item;
    }
    else {
      allItems.push(item);
      totalCount++;
    }
  });

  renderPage(currentPage);
  elementCount.textContent = `Elements: ${totalCount}`;
  updatePaging();
};

sseStream.onopen = () => {

};

sseStream.onerror = (e) => {
  console.error("SSE error:", e);
  sseStream.close();
};

startCrawlBtn.addEventListener("click", () => {
  fetch("/services/hub-flask/start-crawl", { method: "POST" })
    .then(response => {
      if (!response.ok) {
        throw new Error("Failed to start crawl");
      }
      console.log("Crawl started successfully");
    })
    .catch(error => {
      console.error("Error starting crawl:", error);
    });
});

stopCrawlBtn.addEventListener("click", () => {
  fetch("/services/hub-flask/stop-crawl", { method: "POST" })
    .then(response => {
      if (!response.ok) {
        throw new Error("Failed to stop crawl");
      }
      console.log("Crawl stopped successfully");
    })
    .catch(error => {
      console.error("Error stopping crawl:", error);
    });
});

clearResultsBtn.addEventListener("click", () => {
  allItems = [];
  totalCount = 0;
  currentPage = 0;
  renderPage(currentPage);
  updatePaging();
  elementCount.textContent = `Elements: ${totalCount}`;
});