from fastapi import APIRouter

from app.api.auth import router as auth_router

api_router = APIRouter()
api_router.include_router(auth_router)



@api_router.get("/api/ping", tags=["system"])
async def ping():
    return {"pong": True}
