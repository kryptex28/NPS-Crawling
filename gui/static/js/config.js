const openConfig = document.getElementById("open-config");
const dialog = document.getElementById("config-dialog");
const configForm = document.getElementById("config-form");
const dialogClose = dialog.querySelector("#dialog-close");
const dialogCancel = dialog.querySelector("#dialog-cancel");

dialogClose.addEventListener("click", () => {
    dialog.close();
});
dialogCancel.addEventListener("click", () => {
    dialog.close();
});


configForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const formData = new FormData(configForm);

    try {
    const response = await fetch("/services/hub-flask/set-config", {
        method: "POST",
        body: formData
    });

    const result = await response.json()

    if (result.status) {
        alert("Configuration updated successfully!");
    } else {
        alert("Failed to update configuration.");
    }
    } catch (err) {
    console.error("Failed to update configuration: ", err);
    alert("An error occurred while updating configuration.");
    }
});

openConfig.addEventListener("click", () => {
    dialog.showModal();
});