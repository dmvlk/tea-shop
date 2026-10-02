from fastapi import FastAPI
from sqlalchemy import text
from app.api.router import api_router
from app.db.session import engine

app = FastAPI(title="Tea Shop API", version="0.1.0")

app.include_router(api_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/db-check")
async def db_check():
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        return {"db": result.scalar()}
