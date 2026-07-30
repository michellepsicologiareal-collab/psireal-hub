from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.db import get_connection
from app.models import ImportCsvResult
from app.services.csv_import import import_csv

router = APIRouter(prefix="/api/import", tags=["import"])


@router.post("/csv", response_model=ImportCsvResult)
async def import_csv_endpoint(file: UploadFile = File(...)):
    if file.filename and not file.filename.lower().endswith((".csv", ".txt")):
        raise HTTPException(status_code=422, detail="Envie um arquivo .csv")

    conteudo = await file.read()
    if not conteudo:
        raise HTTPException(status_code=422, detail="Arquivo vazio")

    # Conexão criada e usada dentro desta mesma chamada (não via Depends) para
    # evitar problemas de afinidade de thread entre o generator de dependência
    # (executado em threadpool) e o corpo async do endpoint.
    conn = get_connection()
    try:
        resultado = import_csv(conn, conteudo)
    finally:
        conn.close()
    return resultado
