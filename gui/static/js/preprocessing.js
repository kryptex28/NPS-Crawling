const statusComplete = document.getElementById("status-complete");
const statusBlock = document.querySelector(".status-block");
const pagingControl = document.querySelector(".paging-control");

const pagingPrev = document.getElementById("paging-prev");
const pagingNext = document.getElementById("paging-next");
const pagingInfo = document.getElementById("paging-info");

const startPreprocessingBtn = document.getElementById("start-preprocessing");
const stopPreprocessingBtn = document.getElementById("stop-preprocessing");
const clearResultsBtn = document.getElementById("clear-results");

const elementCount = document.getElementById("element-count");

const start = Date.now();

const sseStream = new EventSource("/services/hub-flask/stream-preprocessing");
const resultsList = document.getElementById("results-list");

const currentCrawlerStatus = document.getElementById("current-crawler-status");

const preprocessingForm = document.getElementById("start-preprocessing-form");

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
    console.log(item);

    const row = document.createElement("div");
    const meta = document.createElement("div");
    meta.className = "result-meta";
    const sub = document.createElement("span");
    sub.innerHTML = `
    CIKs ${item}
    `;

    row.append(checkbox, meta, sub);
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
      `Preprocessing complete! Time taken: ${mm}:${ss}. Total elements: ${totalCount}`;
    statusBlock.style.display = "none";
    statusComplete.hidden = false;
    sseStream.close();
    return;
  }

  if (result.__heartbeat) return;

  if (result.type == "paging") {
    currentCrawlerStatus.textContent = `Fetching page ${result.page}. Remaining pages: ${result.total}`;
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

startPreprocessingBtn.addEventListener("click", () => {
  fetch("/services/hub-flask/start-preprocessing", { method: "POST" })
    .then(response => {
      if (!response.ok) {
        throw new Error("Failed to start preprocessing");
      }
      console.log("Preprocessing started successfully");
    })
    .catch(error => {
      console.error("Error starting preprocessing:", error);
    });
});

stopPreprocessingBtn.addEventListener("click", () => {
  fetch("/services/hub-flask/stop-preprocessing", { method: "POST" })
    .then(response => {
      if (!response.ok) {
        throw new Error("Failed to stop preprocessing");
      }
      console.log("Preprocessing stopped successfully");
    })
    .catch(error => {
      console.error("Error stopping preprocessing:", error);
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

preprocessingForm.addEventListener("submit", (e) => {
  // Collect checked IDs and stuff them into the hidden input
  const checkedBoxes = document.querySelectorAll('input[name="selected_results"]:checked');
  const ids = Array.from(checkedBoxes).map(cb => cb.value).join(",");
  
  document.getElementById("ids-input").value = ids;
  
});