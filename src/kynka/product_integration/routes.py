from fastapi import APIRouter
from .status import product_readiness

def build_product_integration_router() -> APIRouter:
    router = APIRouter(prefix="/api/v1/product", tags=["product"])
    @router.get("/readiness")
    def readiness():
        return product_readiness()
    return router
