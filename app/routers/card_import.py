from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.db import get_db_dependency
from app.services.card_import import CardImportError, import_card_items, parse_card_file

router = APIRouter(prefix="/api/import/card", tags=["card-import"])


async def _read_file(file: UploadFile) -> tuple[str, bytes]:
    filename = (file.filename or "fatura").strip()
    content = await file.read()
    return filename, content


@router.post("/preview")
async def preview_card_statement(file: UploadFile = File(...)):
    """Extrai uma prévia sem armazenar o arquivo ou os lançamentos."""

    filename, content = await _read_file(file)
    try:
        return parse_card_file(filename, content)
    except CardImportError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("")
async def import_card_statement(
    file: UploadFile = File(...),
    conn=Depends(get_db_dependency),
):
    """Importa os itens confirmados pelo usuário e ignora duplicados."""

    filename, content = await _read_file(file)
    try:
        preview = parse_card_file(filename, content)
        return import_card_items(conn, preview)
    except CardImportError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
