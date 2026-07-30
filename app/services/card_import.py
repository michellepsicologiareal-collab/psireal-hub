"""Leitura segura de faturas de cartão em PDF ou CSV.

O arquivo é processado em memória e descartado ao final da requisição. A
importação exige uma etapa de prévia para que o usuário confira os lançamentos.
"""
from __future__ import annotations

import csv
import io
import re
import unicodedata
from collections import Counter
from datetime import date, datetime
from typing import Any

from app.db import insert_and_get_id
from app.services.csv_import import _parse_valor_centavos

MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_PDF_PAGES = 40
CARD_PAYMENT_METHOD = "Cartão de crédito"

DATE_HEADERS = {
    "data", "date", "data da compra", "data compra", "data de compra",
    "data lancamento", "data do lancamento", "purchase date",
}
DESCRIPTION_HEADERS = {
    "descricao", "description", "estabelecimento", "historico", "lancamento",
    "detalhes", "nome", "merchant", "titulo",
}
AMOUNT_HEADERS = {
    "valor", "amount", "valor da compra", "valor compra", "total", "quantia",
    "valor r$", "valor (r$)",
}
IGNORE_DESCRIPTIONS = (
    "pagamento recebido",
    "pagamento de fatura",
    "pagamento da fatura",
    "total da fatura",
    "saldo anterior",
    "saldo da fatura",
    "limite disponivel",
    "limite total",
    "melhor dia de compra",
    "vencimento",
    "encargos totais",
    "resumo da fatura",
)
MONTHS = {
    "JAN": 1, "FEV": 2, "MAR": 3, "ABR": 4, "MAI": 5, "JUN": 6,
    "JUL": 7, "AGO": 8, "SET": 9, "OUT": 10, "NOV": 11, "DEZ": 12,
}
CATEGORY_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Alimentação", ("mercado", "supermerc", "ifood", "restaurante", "padaria", "lanch", "food", "cafe", "açougue", "acougue")),
    ("Moradia", ("aluguel", "condominio", "energia", "enel", "cemig", "copel", "sabesp", "internet", "claro", "vivo fibra")),
    ("Transporte", ("uber", "99app", "posto", "combust", "shell", "ipiranga", "estacion", "pedagio", "metro", "passagem")),
    ("Saúde", ("farmacia", "drogaria", "drogasil", "raia", "hospital", "clinica", "medic", "laboratorio")),
    ("Educação", ("curso", "escola", "faculdade", "universidade", "livraria", "udemy", "alura", "material escolar")),
    ("Lazer", ("cinema", "netflix", "spotify", "hotel", "viagem", "ingresso", "steam", "playstation", "show")),
    ("Assinaturas", ("assinatura", "subscription", "google one", "icloud", "amazon prime", "youtube premium", "canva")),
    ("Roupas e calçados", ("roupa", "tenis", "calcado", "renner", "riachuelo", "cea", "zara", "shein")),
    ("Cuidados pessoais", ("shampoo", "cosmet", "beleza", "salao", "barbearia", "boticario", "natura")),
    ("Presentes", ("presente", "floricultura", "gift")),
)


class CardImportError(ValueError):
    """Erro de arquivo seguro para exibição ao usuário."""


def _normalize(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    return " ".join(
        "".join(char for char in text if not unicodedata.combining(char))
        .casefold()
        .strip()
        .split()
    )


def _decode_csv(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise CardImportError("Não foi possível ler o arquivo CSV.")


def _detect_delimiter(text: str) -> str:
    sample = "\n".join(text.splitlines()[:6])
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
    except csv.Error:
        first = text.splitlines()[0] if text.splitlines() else ""
        counts = {item: first.count(item) for item in (",", ";", "\t", "|")}
        return max(counts, key=counts.get) if any(counts.values()) else ";"


def _find_column(headers: list[str], accepted: set[str]) -> int | None:
    normalized = [_normalize(item) for item in headers]
    for index, name in enumerate(normalized):
        if name in accepted:
            return index
    for index, name in enumerate(normalized):
        if any(candidate in name for candidate in accepted):
            return index
    return None


def _infer_year(month: int, reference: date) -> int:
    return reference.year - 1 if month > reference.month + 2 else reference.year


def _parse_card_date(value: str, reference: date) -> str:
    raw = value.strip()
    for pattern in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y", "%d-%m-%y"):
        try:
            return datetime.strptime(raw, pattern).date().isoformat()
        except ValueError:
            continue
    short_match = re.fullmatch(r"(\d{1,2})[/-](\d{1,2})", raw)
    if short_match:
        day, month = map(int, short_match.groups())
        return date(_infer_year(month, reference), month, day).isoformat()
    month_match = re.fullmatch(r"(\d{1,2})\s+([A-Za-zÇç]{3,})", raw)
    if month_match:
        day = int(month_match.group(1))
        month = MONTHS.get(_normalize(month_match.group(2))[:3].upper())
        if month:
            return date(_infer_year(month, reference), month, day).isoformat()
    raise CardImportError(f"Data não reconhecida: {raw}")


def _is_ignored(description: str) -> bool:
    normalized = _normalize(description)
    return len(normalized) < 2 or any(item in normalized for item in IGNORE_DESCRIPTIONS)


def _installment(description: str) -> dict[str, int] | None:
    match = re.search(r"(?:parc(?:ela)?\s*)?(\d{1,2})\s*(?:/|de)\s*(\d{1,2})", description, re.IGNORECASE)
    if not match:
        return None
    current, total = map(int, match.groups())
    if current < 1 or total < current or total > 99:
        return None
    return {"atual": current, "total": total, "restantes": total - current}


def _category_suggestion(description: str) -> str:
    normalized = _normalize(description)
    for category, keywords in CATEGORY_KEYWORDS:
        if any(keyword in normalized for keyword in keywords):
            return category
    return "Outros"


def _item(data: str, description: str, cents: int) -> dict[str, Any]:
    transaction_type = "receita" if cents < 0 else "despesa"
    return {
        "data": data,
        "descricao": " ".join(description.strip().split())[:255],
        "valor": round(abs(cents) / 100, 2),
        "tipo": transaction_type,
        "categoria_sugerida": _category_suggestion(description),
        "parcela": _installment(description),
    }


def parse_card_csv(content: bytes, *, reference: date | None = None) -> list[dict[str, Any]]:
    reference = reference or date.today()
    text = _decode_csv(content)
    rows = [row for row in csv.reader(io.StringIO(text), delimiter=_detect_delimiter(text)) if any(cell.strip() for cell in row)]
    if len(rows) < 2:
        raise CardImportError("O CSV não possui lançamentos.")

    date_index = _find_column(rows[0], DATE_HEADERS)
    description_index = _find_column(rows[0], DESCRIPTION_HEADERS)
    amount_index = _find_column(rows[0], AMOUNT_HEADERS)
    if None in (date_index, description_index, amount_index):
        raise CardImportError("O CSV precisa ter as colunas data, descrição e valor.")

    items: list[dict[str, Any]] = []
    max_index = max(date_index, description_index, amount_index)
    for row in rows[1:]:
        if len(row) <= max_index:
            continue
        description = row[description_index].strip()
        if _is_ignored(description):
            continue
        try:
            parsed_date = _parse_card_date(row[date_index], reference)
            cents = _parse_valor_centavos(row[amount_index])
        except (ValueError, CardImportError):
            continue
        if cents:
            items.append(_item(parsed_date, description, cents))
    if not items:
        raise CardImportError("Nenhuma compra foi encontrada no CSV.")
    return _deduplicate_items(items)


def _amount_cents(value: str) -> int:
    raw = value.strip()
    negative_parentheses = raw.startswith("(") and raw.endswith(")")
    raw = raw.strip("()").replace("−", "-")
    cents = _parse_valor_centavos(raw)
    return -abs(cents) if negative_parentheses else cents


def _parse_statement_text(text: str, *, reference: date | None = None) -> list[dict[str, Any]]:
    reference = reference or date.today()
    lines = [" ".join(line.split()) for line in text.splitlines() if line.strip()]
    date_token = r"(?:\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?|\d{1,2}\s+[A-Za-zÇç]{3,})"
    amount_token = r"(?:R\$\s*)?(?:\(?-?\s*\d{1,3}(?:\.\d{3})*,\d{2}\)?|\(?-?\s*\d+,\d{2}\)?)"
    combined = re.compile(rf"^(?P<date>{date_token})\s+(?P<desc>.+?)\s+(?P<amount>{amount_token})$")
    date_only = re.compile(rf"^(?P<date>{date_token})$")
    amount_only = re.compile(rf"^(?P<amount>{amount_token})$")

    items: list[dict[str, Any]] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        match = combined.match(line)
        description = ""
        date_text = ""
        amount_text = ""
        consumed = 1
        if match:
            date_text, description, amount_text = match.group("date", "desc", "amount")
        else:
            match_date = date_only.match(line)
            if match_date and index + 2 < len(lines) and amount_only.match(lines[index + 2]):
                date_text = match_date.group("date")
                description = lines[index + 1]
                amount_text = amount_only.match(lines[index + 2]).group("amount")  # type: ignore[union-attr]
                consumed = 3
        if date_text and not _is_ignored(description):
            try:
                parsed_date = _parse_card_date(date_text, reference)
                cents = _amount_cents(amount_text)
                if cents:
                    items.append(_item(parsed_date, description, cents))
            except (ValueError, CardImportError):
                pass
        index += consumed
    if not items:
        raise CardImportError(
            "Não encontrei compras neste PDF. Tente baixar a fatura em CSV ou um PDF com texto selecionável."
        )
    return _deduplicate_items(items)


def parse_card_pdf(content: bytes, *, reference: date | None = None) -> list[dict[str, Any]]:
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(content), strict=False)
    except Exception as exc:
        raise CardImportError("O PDF está danificado ou não pôde ser lido.") from exc
    if reader.is_encrypted:
        try:
            unlocked = reader.decrypt("")
        except Exception:
            unlocked = 0
        if not unlocked:
            raise CardImportError("O PDF possui senha. Salve uma cópia sem senha antes de enviar.")
    if len(reader.pages) > MAX_PDF_PAGES:
        raise CardImportError(f"A fatura pode ter no máximo {MAX_PDF_PAGES} páginas.")
    text_parts: list[str] = []
    for page in reader.pages:
        try:
            text_parts.append(page.extract_text() or "")
        except Exception:
            continue
    return _parse_statement_text("\n".join(text_parts), reference=reference)


def _deduplicate_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, int, str]] = set()
    output: list[dict[str, Any]] = []
    for item in items:
        key = (
            item["data"],
            _normalize(item["descricao"]),
            int(round(float(item["valor"]) * 100)),
            item["tipo"],
        )
        if key not in seen:
            seen.add(key)
            output.append(item)
    return sorted(output, key=lambda item: (item["data"], item["descricao"]))


def parse_card_file(filename: str, content: bytes) -> dict[str, Any]:
    if not content:
        raise CardImportError("O arquivo está vazio.")
    if len(content) > MAX_FILE_BYTES:
        raise CardImportError("O arquivo pode ter no máximo 8 MB.")
    extension = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if extension == "pdf":
        if not content.startswith(b"%PDF"):
            raise CardImportError("O arquivo enviado não é um PDF válido.")
        items = parse_card_pdf(content)
        file_format = "PDF"
    elif extension in {"csv", "txt"}:
        items = parse_card_csv(content)
        file_format = "CSV"
    else:
        raise CardImportError("Envie uma fatura em PDF ou CSV.")

    expenses = sum(item["valor"] for item in items if item["tipo"] == "despesa")
    refunds = sum(item["valor"] for item in items if item["tipo"] == "receita")
    categories = Counter(item["categoria_sugerida"] for item in items if item["tipo"] == "despesa")
    return {
        "arquivo": filename,
        "formato": file_format,
        "items": items,
        "quantidade": len(items),
        "total_compras": round(expenses, 2),
        "total_estornos": round(refunds, 2),
        "total_liquido": round(expenses - refunds, 2),
        "categorias": [{"nome": name, "quantidade": count} for name, count in categories.most_common()],
        "aviso": "Confira a prévia. O arquivo é descartado após a leitura e não fica armazenado.",
    }


def _resolve_category_id(conn, suggested_name: str, transaction_type: str) -> int | None:
    categories = conn.execute(
        "SELECT id, nome FROM categories WHERE tipo = ? ORDER BY id",
        (transaction_type,),
    ).fetchall()
    normalized_target = _normalize(suggested_name)
    for category in categories:
        if _normalize(category["nome"]) == normalized_target:
            return int(category["id"])
    if transaction_type == "despesa":
        for category in categories:
            if _normalize(category["nome"]) in {"outros", "compras"}:
                return int(category["id"])
    return None


def import_card_items(conn, preview: dict[str, Any]) -> dict[str, Any]:
    existing = {
        (
            row["data"],
            _normalize(row["descricao"]),
            int(row["valor_centavos"]),
            row["tipo"],
        )
        for row in conn.execute(
            "SELECT data, descricao, valor_centavos, tipo FROM transactions"
        ).fetchall()
    }
    imported = 0
    duplicates = 0
    for item in preview["items"]:
        cents = int(round(float(item["valor"]) * 100))
        key = (item["data"], _normalize(item["descricao"]), cents, item["tipo"])
        if key in existing:
            duplicates += 1
            continue
        category_id = _resolve_category_id(conn, item["categoria_sugerida"], item["tipo"])
        notes = f"Fatura importada: {preview['arquivo']} ({preview['formato']})"
        insert_and_get_id(
            conn,
            """
            INSERT INTO transactions
                (data, descricao, valor_centavos, tipo, category_id,
                 metodo_pagamento, recorrente, notas)
            VALUES (?, ?, ?, ?, ?, ?, 0, ?)
            """,
            (
                item["data"],
                item["descricao"],
                cents,
                item["tipo"],
                category_id,
                CARD_PAYMENT_METHOD,
                notes[:500],
            ),
        )
        existing.add(key)
        imported += 1
    conn.commit()
    return {
        "importadas": imported,
        "ignoradas_duplicadas": duplicates,
        "arquivo": preview["arquivo"],
        "total_liquido": preview["total_liquido"],
    }
