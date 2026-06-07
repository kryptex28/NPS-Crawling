export class SseStream {
    #url;
    #source = null;

    constructor(url) {
        this.#url = url;
    }

    connect({ onMessage, onError, onOpen} = {}) {
        this.#source = new EventSource(this.#url);
        this.#source.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                onMessage?.(data);
            }
            catch (err) {
                console.error("Error parsing SSE message:", err);
            }
        };
        
        this.#source.onError = (err) => {
            console.error("SSE error:", err);
            onError?.(err);
            this.close();
        };

        this.#source.onopen = () => {
            console.log("SSE connection opened");
            onOpen?.();
        };
    }

    close() {
        this.#source?.close();
        this.#source = null;
    }
}