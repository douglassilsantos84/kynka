from pathlib import Path
from fastapi import APIRouter,File,Form,HTTPException,Request,UploadFile
from pydantic import BaseModel
from kynka.application.quote_imports import QuoteImportError,QuoteImportService
from kynka.infrastructure.quote_imports import SQLiteQuoteImportRepository

class MatchRequest(BaseModel): material_code:str

def build_quote_import_router(database_path):
    router=APIRouter(prefix="/api/v1/quote-imports",tags=["quote-imports"])
    repo=SQLiteQuoteImportRepository(database_path)
    def svc(request): return QuoteImportService(repo,request.app.state.supplier_service,request.app.state.inventory_service)
    @router.post("/preview")
    async def preview(request:Request,file:UploadFile=File(...),supplier_id:int|None=Form(default=None)):
        try:return svc(request).import_file(file.filename or "cotacao",await file.read(),supplier_id)
        except Exception as e:raise HTTPException(status_code=400,detail=str(e))
    @router.get("")
    def listing(request:Request):return svc(request).list()
    @router.get("/{import_id}")
    def get(import_id:int,request:Request):
        try:return svc(request).get(import_id)
        except QuoteImportError as e:raise HTTPException(status_code=404,detail=str(e))
    @router.put("/{import_id}/items/{item_id}/match")
    def match(import_id:int,item_id:int,body:MatchRequest,request:Request):
        try:return svc(request).set_match(import_id,item_id,body.material_code)
        except Exception as e:raise HTTPException(status_code=400,detail=str(e))
    @router.post("/{import_id}/approve")
    def approve(import_id:int,request:Request):
        try:return svc(request).approve(import_id)
        except QuoteImportError as e:raise HTTPException(status_code=409,detail=str(e))
    return router
