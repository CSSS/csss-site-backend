from fastapi import FastAPI

from officers import officers

app = FastAPI()
app.include_router(officers.router)

@app.get("/")
async def read_root():
    return { "message": "your random number is 4" }
