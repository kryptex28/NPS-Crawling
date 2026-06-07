export class StatusManager {
    #mountEl;
    #start = Date.now();

    static State = {
        IDLE:    "idle",
        RUNNING: "running",
        SUCCESS: "success",
        ERROR:   "error",
        STOPPED: "stopped",
    };

    #config = {
        [StatusManager.State.IDLE]: {
        icon: "",
        message: "",
        className: "status-idle",
        },
        [StatusManager.State.RUNNING]: {
        icon: `<div class="spinner" aria-hidden="true"></div>`,
        message: "The search has started. This may take some time. Please keep this window open.",
        className: "status-running",
        },
        [StatusManager.State.SUCCESS]: {
        icon: `<span class="status-icon">✓</span>`,
        message: "Process completed successfully.",
        className: "status-success",
        },
        [StatusManager.State.ERROR]: {
        icon: `<span class="status-icon"></span>`,
        message: "An error occurred.",
        className: "status-error",
        },
        [StatusManager.State.STOPPED]: {
        icon: `<span class="status-icon"></span>`,
        message: "Process was stopped.",
        className: "status-stopped",
        },
    };

    constructor({ mountEl, initialState = StatusManager.State.IDLE }) {
        this.#mountEl = mountEl;
        this.#mount();
        this.setState(initialState);
    }

    #mount() {
        this.#mountEl.innerHTML = `<div class="status-block"></div>`;
    }

    setState(state, message = null) {
        const conf = this.#config[state];
        if (!conf) return;

        const block = this.#mountEl.querySelector(".status-block");

        // Swap state class
        Object.values(StatusManager.State).forEach(s => block.classList.remove(this.#config[s].className));
        block.classList.add(conf.className);

        block.innerHTML = `
        ${conf.icon}
        <p class="status-text">${message ?? conf.message}</p>
        `;

        block.hidden = state === StatusManager.State.IDLE;
    }

    complete(message = null) {
        const elapsed = Math.round((Date.now() - this.#start) / 1000);
        const mm = String(Math.floor(elapsed / 60)).padStart(2, "0");
        const ss = String(elapsed % 60).padStart(2, "0");
        this.setState(
        StatusManager.State.SUCCESS,
        message ?? `Completed in ${mm}:${ss}.`
        );
    }

    error(message = null) {
        this.setState(StatusManager.State.ERROR, message);
    }

    stop(message = null) {
        this.setState(StatusManager.State.STOPPED, message);
    }

    running(message = null) {
        this.setState(StatusManager.State.RUNNING, message);
    }
}