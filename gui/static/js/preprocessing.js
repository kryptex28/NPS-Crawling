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
  mountEl: document.getElementById("preprocessing-actions-mount"),
  actions: [
    {
      id: "start-preprocessing",
      label: "Start preprocessing",
      variant: "primary",
      onClick: () => {
        fetch("/services/hub-flask/start-preprocessing", { method: "POST" }).catch(console.error);
        status.setState(StatusManager.State.RUNNING, "Preprocessing is running. Please keep this window open.");
      },
    },
    {
      id: "stop-preprocessing",
      label: "Stop preprocessing",
      variant: "ghost",
      onClick: () => {
        fetch("/services/hub-flask/stop-preprocessing", { method: "POST" }).catch(console.error);
        status.setState(StatusManager.State.STOPPED, "Preprocessing was stopped manually.");
      },
    },
    {
      id: "show-results",
      label: "Show results",
      variant: "ghost",
      onClick: () => {
        fetch("/services/hub-flask/preprocessing-results", { method: "GET" })
          .then(res => res.json())
          .then(data => {
            pager.addItems(Array.isArray(data) ? data : [data], item => item.filing_id);
          })
          .catch(console.error);
      },
    },
  ],
});

new FormSubmitter({
  mountEl: document.getElementById("preprocessing-actions-mount"),
  action: "/services/hub-flask/results",
  method: "post",
  label: "Start Classification",
  inputName: "ids",
  collectIds() {
    const checked = document.querySelectorAll('input[name="selected_results"]:checked');
    return Array.from(checked).map(cb => cb.value);
  },
});

const sse = new SseStream("/services/hub-flask/stream-preprocessing");
sse.connect({
  onMessage: (data) => {
    if (data.__done) return status.complete();
    if (data.__heartbeat) return;
    if (data.type === "paging") {
      return;
    }
    pager.addItems(Array.isArray(data) ? data : [data], item => item.filing_id);
  },
});