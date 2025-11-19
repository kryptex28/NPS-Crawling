from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import os
import asyncio

app = FastAPI(title="Local Mistral AI Server")

OLLAMA_PORT = 11434
OLLAMA_HOST = os.getenv("OLLAMA_HOST", f"http://localhost:{OLLAMA_PORT}")
MODEL_NAME = "mistral"

class ChatRequest(BaseModel):
    message: str
    model: str = MODEL_NAME

class ChatResponse(BaseModel):
    response: str

async def ensure_model_loaded():
    """Pull Mistral model if not already available"""
    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            await client.post(
                f"{OLLAMA_HOST}/api/pull",
                json={"name": MODEL_NAME}
            )
        except Exception as e:
            print(f"Model pull error (may already exist): {e}")

@app.on_event("startup")
async def startup():
    print("Ensuring Mistral model is available...")
    await ensure_model_loaded()
    print("Ready!")

@app.get("/")
async def root():
    return {"status": "Local Mistral AI Server running", "model": MODEL_NAME}

@app.get("/health")
async def health():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{OLLAMA_HOST}/api/tags")
            return {"status": "healthy", "ollama": response.status_code == 200}
    except:
        return {"status": "unhealthy"}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{OLLAMA_HOST}/api/generate",
                json={
                    "model": request.model,
                    "prompt": request.message,
                    "options": {
                        "temperature": request.temperature,
                        "top_k": request.top_k,
                        "top_p": request.top_p,
                        "seed": request.seed,
                    },
                    "stream": False
                }
            )

            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Ollama error")

            result = response.json()
            return ChatResponse(response=result["response"])

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")