export class FormSubmitter {
    #form; 
    #hiddenInput;

    constructor({ mountEl, action, method = "post", label, inputName, collectIds }) {
        this.#mount(mountEl, { action, method, label, inputName, collectIds });
    }

    #mount(mountEl, { action, method, label, inputName, collectIds }) {
        this.#form = document.createElement("form");
        this.#form.action = action;
        this.#form.method = method;

        this.#hiddenInput = document.createElement("input");
        this.#hiddenInput.type = "hidden";
        this.#hiddenInput.name = inputName;

        const submitBtn = document.createElement("button");
        submitBtn.type = "submit";
        submitBtn.textContent = label;

        this.#form.append(this.#hiddenInput, submitBtn);
        this.#form.addEventListener("submit", () => {
        this.#hiddenInput.value = collectIds().join(",");
        });

        mountEl.appendChild(this.#form);
    }
}