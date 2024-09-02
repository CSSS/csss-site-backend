import logging

import auth.urls
import database
import officers.urls
import permission.urls
from fastapi import FastAPI

import tests.urls

logging.basicConfig(level=logging.DEBUG)
database.setup_database()

app = FastAPI(lifespan=database.lifespan, title="CSSS Site Backend", root_path="/api")

app.include_router(auth.urls.router)
app.include_router(officers.urls.router)
app.include_router(permission.urls.router)

app.include_router(tests.urls.router)

@app.get("/")
async def read_root():
    return {"message": "Hello! You might be lost, this is actually the sfucsss.org's backend api."}
