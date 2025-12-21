# src/tokenizer_service.py
from fastapi import FastAPI
from pydantic import BaseModel
from src.nlp.tokenizer import Tokenizer
import os

app = FastAPI()

# Tokenizer 초기화
tokenizer = Tokenizer()

class TokenizeRequest(BaseModel):
    text: str
    n_gram: int = 1

@app.post("/tokenize")
async def tokenize(request: TokenizeRequest):
    tokens = tokenizer.tokenize(request.text, n_gram=request.n_gram)
    return {"tokens": tokens}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
