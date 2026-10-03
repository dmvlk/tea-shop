from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.categories import router as categories_router
from app.api.products import router as products_router
from app.api.addresses import router as addresses_router
from app.api.cart import router as cart_router
from app.api.orders import router as orders_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(categories_router)
api_router.include_router(products_router)
api_router.include_router(addresses_router)
api_router.include_router(cart_router)
api_router.include_router(orders_router)






@api_router.get("/api/ping", tags=["system"])
async def ping():
    return {"pong": True}
