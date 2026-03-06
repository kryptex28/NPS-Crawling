const statusComplete = document.getElementById("status-complete");
const statusBlock = document.querySelector(".status-block");

const durationSeconds = 10;
const start = Date.now();

setTimeout(() => {
  const elapsed = Math.round((Date.now() - start) / 1000);
  const mm = String(Math.floor(elapsed / 60)).padStart(2, "0");
  const ss = String(elapsed % 60).padStart(2, "0");
  statusComplete.querySelector("p").textContent = `Process completed. Duration: ${mm}:${ss}. Newly crawled files: 12.`;
  statusBlock.style.display = "none";
  statusComplete.hidden = false;
}, durationSeconds * 1000);
