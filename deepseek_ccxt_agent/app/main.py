from fastapi import FastAPI
from app.routes import strategy

app = FastAPI()
app.include_router(strategy.router, prefix="/strategy", tags=["strategy"])
