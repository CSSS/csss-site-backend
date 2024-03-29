from fastapi import FastAPI

import database
from auth import auth
#from officers import officers

app = FastAPI(lifespan=database.lifespan, title="CSSS Site Backend")
app.include_router(auth.router)
#app.include_router(officers.router)

@app.get("/")
async def read_root():
    return { "message": "Hello! You might be lost, this is actually the sfucsss.org's backend api." }
