export class ActionBar {
    #el;

    /**
     * @param {object} options
     * @param {HTMLElement} options.mountEl
     * @param {Array<{id: string, label: string, variant: string, onClick: Function}>} options.actions
     */
    constructor({ mountEl, actions = [] }) {
        this.#mount(mountEl, actions);
    }

    #mount(mountEl, actions) {
        this.#el = document.createElement("div");
        this.#el.className = "action-bar";

        actions.forEach(({ id, label, variant = "primary", onClick }) => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.id = id;
        btn.className = variant;
        btn.textContent = label;
        btn.addEventListener("click", onClick);
        this.#el.appendChild(btn);
        });

        mountEl.appendChild(this.#el);
    }

    setDisabled(id, disabled) {
        const btn = this.#el.querySelector(`#${id}`);
        if (btn) btn.disabled = disabled;
    }
}