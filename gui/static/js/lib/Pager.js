export class Pager {
    #items = [];
    #currentPage = 0;
    #pageSize;
    #onRender;

    #prevBtn;
    #nextBtn;
    #infoEl;

    constructor({ pageSize = 10, onRender, mountElement }) {
        this.#pageSize = pageSize;
        this.#onRender = onRender;

        this.#mount(mountElement);
    }

    #mount(mountElement) {
        if (!mountElement) return;

        mountElement.innerHTML = `
            <div class="paging-control">
                <button class="pager-prev" disabled>&#8592; Prev</button>
                <span class="paging-info"></span>
                <button class="pager-next">&#8594; Next</button>
            </div>
            <div class="segmented-control" role="group" aria-label="Items per page">
                ${[10, 25, 100, 1000].map(n => `
                    <label>
                        <input type="radio" name="elements" value="${n}" ${n === this.#pageSize ? "checked" : ""}>
                        <span>${n}</span>
                    </label>
                `).join("")}
            </div>
        `;

        this.#prevBtn = mountElement.querySelector(".pager-prev");
        this.#nextBtn = mountElement.querySelector(".pager-next");
        this.#infoEl  = mountElement.querySelector(".pager-info");

        this.#prevBtn.addEventListener("click", () => this.prev());
        this.#nextBtn.addEventListener("click", () => this.next());

        mountElement.querySelector(".segmented-control").addEventListener("change", (e) => {
            const val = parseInt(e.target.value);
            if (!isNaN(val)) this.setPageSize(val);
        });
    }

    get totalPages() {
        return Math.ceil(this.#items.length / this.#pageSize);
    }

    addItems(newItems, keyFn = null) {
        for (const item of newItems) {
        if (keyFn) {
            const idx = this.#items.findIndex(i => keyFn(i) === keyFn(item));
            if (idx !== -1) {
            this.#items[idx] = item;
            continue;
            }
        }
        this.#items.push(item);
        }
        this.render();
    }

    setPageSize(size) {
        this.#pageSize = size;
        this.#currentPage = 0;
        this.render();
    }

    prev() {
        if (this.#currentPage > 0) {
        this.#currentPage--;
        this.render();
        }
    }

    next() {
        if (this.#currentPage < this.totalPages - 1) {
        this.#currentPage++;
        this.render();
        }
    }

    render() {
        const start = this.#currentPage * this.#pageSize;
        const pageItems = this.#items.slice(start, start + this.#pageSize);
        this.#onRender(pageItems, start);
        this.#updateControls();
    }

    #updateControls() {
        const total = this.totalPages;
        if (this._infoEl)
        this._infoEl.textContent = `Page ${this.#currentPage + 1} of ${total}`;
        if (this._prevBtn)
        this._prevBtn.disabled = this.#currentPage === 0;
        if (this._nextBtn)
        this._nextBtn.disabled = this.#currentPage >= total - 1;
    }

    get count() {
        return this.#items.length;
    }
}