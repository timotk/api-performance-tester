import asyncio
import random

from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()


@app.get("/")
@app.post("/")
async def index():
    # Sleep for a given amount
    delay = random.lognormvariate(-2, 0.3)
    await asyncio.sleep(delay)

    # Sometimes return an error
    if random.random() < 0.05:
        return JSONResponse({"status": "error"}, status_code=500)

    return {"status": "ok"}
