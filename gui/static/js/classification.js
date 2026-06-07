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
  mountEl: document.getElementById("classification-actions-mount"),
  actions: [
    {
      id: "start-classification",
      label: "Start classification",
      variant: "primary",
      onClick: () => {
        fetch("/services/hub-flask/start-classification", { method: "POST" }).catch(console.error);
        status.setState(StatusManager.State.RUNNING, "Classification is running. Please keep this window open.");
      },
    },
    {
      id: "stop-classification",
      label: "Stop classification",
      variant: "ghost",
      onClick: () => {
        fetch("/services/hub-flask/stop-classification", { method: "POST" }).catch(console.error);
        status.setState(StatusManager.State.STOPPED, "Classification was stopped manually.");
      },
    },
  ],
});

new FormSubmitter({
  mountEl: document.getElementById("classification-actions-mount"),
  action: "/services/hub-flask/results",
  method: "post",
  label: "Start Classification",
  inputName: "ids",
  collectIds() {
    const checked = document.querySelectorAll('input[name="selected_results"]:checked');
    return Array.from(checked).map(cb => cb.value);
  },
});

const sse = new SseStream("/services/hub-flask/stream-classification");
sse.connect({
  onMessage: (data) => {
    if (data.__done) return status.complete();
    if (data.__heartbeat) return;
    if (data.type === "paging") {
      return;
    }
    pager.addItems(Array.isArray(data) ? data : [data], item => item.filing_id);
  },
  onError: (err) => {
    console.error("SSE error:", err);
    status.setText("An error occurred while streaming data.");
  },
  onOpen: () => {
    console.log("SSE connection opened");
  }
});
