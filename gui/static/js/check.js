import { SseStream } from "./lib/SseStream.js";
import { Pager } from "./lib/Pager.js";
import { StatusManager } from "./lib/StatusManager.js";
import { ActionBar } from "./lib/ActionBar.js";
import { FormSubmitter } from "./lib/FormSubmitter.js";

const resultsList = document.getElementById("results-list");
const elementCount = document.getElementById("element-count");
const currentCrawlerStatus = document.getElementById("current-crawler-status");

const status = new StatusManager({
  mountEl:      document.getElementById("status-mount"),
  initialState: StatusManager.State.IDLE,
});

new ActionBar({
  mountEl: document.getElementById("crawl-actions-mount"),
  actions: [
    {
      id: "start-crawl",
      label: "Start new crawl",
      variant: "primary",
      onClick: () => {
        fetch("/services/hub-flask/start-crawl", { method: "POST" }).catch(console.error),
        status.setState(StatusManager.State.RUNNING, "Please keep this window open while the crawl is running. This may take a while.");
      },
    },
    {
      id: "stop-crawl",
      label: "Stop crawl",
      variant: "ghost",
      onClick: () => {
        fetch("/services/hub-flask/stop-crawl", { method: "POST" }).catch(console.error),
        status.setState(StatusManager.State.STOPPED, "Crawl was stopped manually.");
      },
    },
  ],
});

new FormSubmitter({
  mountEl: document.getElementById("crawl-actions-mount"),
  action: "/services/hub-flask/preprocessing",
  method: "post",
  label: "Start Preprocessing",
  inputName: "ids",
  collectIds() {
    const checked = document.querySelectorAll('input[name="selected_results"]:checked');
    return Array.from(checked).map(cb => cb.value);
  },
});

const pager = new Pager({
  pageSize:    10,
  mountElement: document.querySelector("#control-container"),
  onRender: (items, startIndex) => {
    resultsList.innerHTML = "";
    items.forEach((item, index) => {
      const row = document.createElement("div");
      row.className = `result-item ${item.status}`;

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
      link.textContent = item.display_names[0];

      const sub = document.createElement("span");
      sub.innerHTML = `CIKs ${item.ciks} <br> Form: ${item.form}`;
      meta.append(link, sub);

      const statusEl = document.createElement("span");
      statusEl.textContent = item.status;

      row.append(checkbox, meta, statusEl);
      resultsList.appendChild(row);
    });

    elementCount.textContent = `Elements: ${pager.count}`;
  },
});

const sse = new SseStream("/services/hub-flask/stream-crawl");
sse.connect({
  onMessage(data) {
    if (data.__done) {
      status.complete(`Completed in ${mm}:${ss}. Newly crawled: ${pager.count}`);
      return;
    }
    if (data.__heartbeat) return;
    if (data.type === "paging") {
      return;
    }
    pager.addItems(Array.isArray(data) ? data : [data], i => i.filing_id);
  },
  onError() {
    status.setText("Connection lost.");
  }
});

document.getElementById("stop-crawl").addEventListener("click", () => {
  fetch("/services/hub-flask/stop-crawl", { method: "POST" })
    .then(() => status.stop("Crawl was stopped manually."))
    .catch(() => status.error("Failed to stop crawl."));
});