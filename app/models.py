"""Schemas Pydantic do FinPilot.

Convenção: nos schemas de saída (Out), valores monetários são expostos em
reais (float, ex. 123.45) apenas na borda de serialização da API, mas
armazenados internamente sempre em centavos (int). Nos schemas de entrada
(Create/Update) aceitamos o valor em reais (float) vindo do cliente e
convertemos para centavos no service/router.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

TipoLancamento = Literal["despesa", "receita"]
TipoConta = Literal["bank", "credit_card", "investment"]
PrioridadeCompra = Literal["baixa", "media", "alta"]
StatusCompra = Literal["planejada", "comprada"]
RecorrenciaPrevista = Literal["unica", "mensal"]
EstadoBudget = Literal["normal", "atencao", "estourado"]
EmocaoFinanceira = Literal[
    "tranquilo",
    "feliz",
    "ansioso",
    "estressado",
    "triste",
    "entediado",
    "cansado",
    "pressionado",
    "outro",
    "prefiro_nao_informar",
]
TipoDecisaoFinanceira = Literal[
    "planejada",
    "necessaria",
    "impulso",
    "compensacao",
    "influencia_social",
    "outro",
]
AcaoConsciente = Literal[
    "pausa_30_min",
    "esperar_24h",
    "definir_teto",
    "alternativa_baixo_custo",
    "conversar_com_alguem",
    "nenhuma",
]


def reais_to_centavos(valor: float) -> int:
    """Converte reais para centavos com arredondamento decimal financeiro."""
    decimal = Decimal(str(valor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return int(decimal * 100)


def centavos_to_reais(valor_centavos: int) -> float:
    return round(valor_centavos / 100, 2)


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------


class CategoryCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=100)
    tipo: TipoLancamento
    cor: str = Field(min_length=4, max_length=9, description="Cor hex, ex. #4C8DFF")
    icone: Optional[str] = None
    essencial: bool = False
    parent_id: Optional[int] = None


class CategoryUpdate(BaseModel):
    nome: Optional[str] = Field(default=None, min_length=1, max_length=100)
    tipo: Optional[TipoLancamento] = None
    cor: Optional[str] = Field(default=None, min_length=4, max_length=9)
    icone: Optional[str] = None
    essencial: Optional[bool] = None
    parent_id: Optional[int] = None


class CategoryOut(BaseModel):
    id: int
    nome: str
    tipo: TipoLancamento
    cor: str
    icone: Optional[str] = None
    essencial: bool
    parent_id: Optional[int] = None
    created_at: str


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------


class TransactionCreate(BaseModel):
    data: date
    descricao: str = Field(min_length=1, max_length=255)
    valor: float = Field(gt=0, description="Valor em reais, ex. 123.45")
    tipo: TipoLancamento
    category_id: Optional[int] = None
    metodo_pagamento: Optional[str] = None
    recorrente: bool = False
    notas: Optional[str] = None

    @field_validator("valor")
    @classmethod
    def valor_positivo(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("valor deve ser maior que zero")
        return v


class TransactionUpdate(BaseModel):
    data: Optional[date] = None
    descricao: Optional[str] = Field(default=None, min_length=1, max_length=255)
    valor: Optional[float] = Field(default=None, gt=0)
    tipo: Optional[TipoLancamento] = None
    category_id: Optional[int] = None
    metodo_pagamento: Optional[str] = None
    recorrente: Optional[bool] = None
    notas: Optional[str] = None


class TransactionOut(BaseModel):
    id: int
    data: str
    descricao: str
    valor: float
    tipo: TipoLancamento
    category_id: Optional[int] = None
    metodo_pagamento: Optional[str] = None
    recorrente: bool
    notas: Optional[str] = None
    created_at: str
    updated_at: str


class TransactionListOut(BaseModel):
    items: list[TransactionOut]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Budgets
# ---------------------------------------------------------------------------


class BudgetCreate(BaseModel):
    category_id: int
    mes: Optional[str] = Field(default=None, description="YYYY-MM ou None para recorrente")
    limite: float = Field(ge=0, description="Limite em reais")


class BudgetUpdate(BaseModel):
    category_id: Optional[int] = None
    mes: Optional[str] = None
    limite: Optional[float] = Field(default=None, ge=0)


class BudgetOut(BaseModel):
    id: int
    category_id: int
    mes: Optional[str] = None
    limite: float


class BudgetStatusItem(BaseModel):
    category_id: int
    category_nome: str
    category_cor: str
    limite: float
    gasto: float
    percentual: float
    dias_restantes: int
    ritmo_diario_projetado: float
    estado: EstadoBudget


# ---------------------------------------------------------------------------
# Goals
# ---------------------------------------------------------------------------


class GoalCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=150)
    valor_alvo: float = Field(ge=0)
    valor_atual: float = Field(default=0, ge=0)
    prazo: Optional[date] = None


class GoalUpdate(BaseModel):
    nome: Optional[str] = Field(default=None, min_length=1, max_length=150)
    valor_alvo: Optional[float] = Field(default=None, ge=0)
    valor_atual: Optional[float] = Field(default=None, ge=0)
    prazo: Optional[date] = None


class GoalOut(BaseModel):
    id: int
    nome: str
    valor_alvo: float
    valor_atual: float
    prazo: Optional[str] = None
    created_at: str


# ---------------------------------------------------------------------------
# Reminders
# ---------------------------------------------------------------------------


class ReminderCreate(BaseModel):
    titulo: str = Field(min_length=1, max_length=180)
    data_vencimento: date
    valor: Optional[float] = Field(default=None, ge=0)
    recorrente: bool = False
    concluido: bool = False
    notas: Optional[str] = Field(default=None, max_length=500)


class ReminderUpdate(BaseModel):
    titulo: Optional[str] = Field(default=None, min_length=1, max_length=180)
    data_vencimento: Optional[date] = None
    valor: Optional[float] = Field(default=None, ge=0)
    recorrente: Optional[bool] = None
    concluido: Optional[bool] = None
    notas: Optional[str] = Field(default=None, max_length=500)


class ReminderOut(BaseModel):
    id: int
    titulo: str
    data_vencimento: str
    valor: Optional[float] = None
    recorrente: bool
    concluido: bool
    notas: Optional[str] = None
    created_at: str
    updated_at: str


# ---------------------------------------------------------------------------
# Accounts and patrimony
# ---------------------------------------------------------------------------


class FinancialAccountCreate(BaseModel):
    account_type: TipoConta
    nome: str = Field(min_length=1, max_length=120)
    instituicao: str = Field(default="", max_length=120)
    valor: float = Field(default=0, ge=0)
    limite: Optional[float] = Field(default=None, ge=0)
    dia_fechamento: Optional[int] = Field(default=None, ge=1, le=31)
    dia_vencimento: Optional[int] = Field(default=None, ge=1, le=31)
    subtipo: str = Field(default="", max_length=100)
    cor: str = Field(default="#7b8f69", min_length=4, max_length=9)


class FinancialAccountUpdate(BaseModel):
    nome: Optional[str] = Field(default=None, min_length=1, max_length=120)
    instituicao: Optional[str] = Field(default=None, max_length=120)
    valor: Optional[float] = Field(default=None, ge=0)
    limite: Optional[float] = Field(default=None, ge=0)
    dia_fechamento: Optional[int] = Field(default=None, ge=1, le=31)
    dia_vencimento: Optional[int] = Field(default=None, ge=1, le=31)
    subtipo: Optional[str] = Field(default=None, max_length=100)
    cor: Optional[str] = Field(default=None, min_length=4, max_length=9)


class FinancialAccountOut(BaseModel):
    id: int
    account_type: TipoConta
    nome: str
    instituicao: str
    valor: float
    limite: Optional[float] = None
    dia_fechamento: Optional[int] = None
    dia_vencimento: Optional[int] = None
    subtipo: str
    cor: str
    created_at: str
    updated_at: str


# ---------------------------------------------------------------------------
# Planning
# ---------------------------------------------------------------------------


class PurchasePlanCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=120)
    valor_estimado: float = Field(default=0, ge=0)
    prioridade: PrioridadeCompra = "media"
    data_desejada: Optional[date] = None
    notas: Optional[str] = Field(default=None, max_length=500)


class PurchasePlanUpdate(BaseModel):
    nome: Optional[str] = Field(default=None, min_length=1, max_length=120)
    valor_estimado: Optional[float] = Field(default=None, ge=0)
    prioridade: Optional[PrioridadeCompra] = None
    data_desejada: Optional[date] = None
    notas: Optional[str] = Field(default=None, max_length=500)
    status: Optional[StatusCompra] = None


class PurchasePlanOut(BaseModel):
    id: int
    nome: str
    valor_estimado: float
    prioridade: PrioridadeCompra
    data_desejada: Optional[str] = None
    notas: Optional[str] = None
    status: StatusCompra
    created_at: str
    updated_at: str


class ScheduledExpenseCreate(BaseModel):
    titulo: str = Field(min_length=1, max_length=180)
    valor: float = Field(gt=0)
    category_id: Optional[int] = None
    data_vencimento: date
    recorrencia: RecorrenciaPrevista = "mensal"
    notas: Optional[str] = Field(default=None, max_length=500)


class ScheduledExpenseUpdate(BaseModel):
    titulo: Optional[str] = Field(default=None, min_length=1, max_length=180)
    valor: Optional[float] = Field(default=None, gt=0)
    category_id: Optional[int] = None
    data_vencimento: Optional[date] = None
    recorrencia: Optional[RecorrenciaPrevista] = None
    notas: Optional[str] = Field(default=None, max_length=500)
    ativo: Optional[bool] = None


class ScheduledExpenseOut(BaseModel):
    id: int
    titulo: str
    valor: float
    category_id: Optional[int] = None
    data_vencimento: str
    recorrencia: RecorrenciaPrevista
    notas: Optional[str] = None
    ativo: bool
    atrasado: bool
    levado_de_outro_mes: bool
    created_at: str
    updated_at: str


# ---------------------------------------------------------------------------
# Summary / analytics
# ---------------------------------------------------------------------------


class SummaryOut(BaseModel):
    mes: str
    saldo: float
    total_receita: float
    total_despesa: float
    taxa_poupanca: float
    variacao_saldo_pct: Optional[float] = None
    variacao_receita_pct: Optional[float] = None
    variacao_despesa_pct: Optional[float] = None


class SpendingByCategoryItem(BaseModel):
    category_id: Optional[int] = None
    category_nome: str
    cor: str
    valor: float
    percentual: float


class TrendItem(BaseModel):
    mes: str
    receita: float
    despesa: float
    saldo: float


class RecurringItem(BaseModel):
    descricao_normalizada: str
    descricao_exemplo: str
    valor_medio: float
    periodicidade: str
    category_id: Optional[int] = None
    category_nome: Optional[str] = None
    total_ultimos_12_meses: float
    ocorrencias: int
    ultima_ocorrencia: str


class InsightItem(BaseModel):
    id: str
    tipo: str
    severidade: Literal["info", "atencao", "critico"]
    titulo: str
    descricao: str
    acao: str
    impacto_estimado: float = Field(ge=0)
    evidencia: dict[str, str | int | float | bool | None]
    fonte: Literal["local", "anthropic"]


class InsightsMeta(BaseModel):
    mes: str
    ia_solicitada: bool
    ia_usada: bool
    ia_status: str
    modelo: Optional[str] = None
    aviso: str


class InsightsOut(BaseModel):
    items: list[InsightItem]
    meta: InsightsMeta


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


class SettingItem(BaseModel):
    chave: str
    valor: Optional[str] = None


class SettingsUpdate(BaseModel):
    settings: dict[str, Optional[str]]


# ---------------------------------------------------------------------------
# CSV import
# ---------------------------------------------------------------------------


class ImportErrorItem(BaseModel):
    linha: int
    motivo: str
    conteudo: str


class ImportCsvResult(BaseModel):
    importadas: int
    ignoradas_duplicadas: int
    com_erro: int
    erros: list[ImportErrorItem]


# ---------------------------------------------------------------------------
# Modo Consciente
# ---------------------------------------------------------------------------


class ConsciousReflectionCreate(BaseModel):
    transaction_id: int = Field(gt=0)
    emotion: EmocaoFinanceira
    intensity: int = Field(ge=1, le=5)
    decision_type: TipoDecisaoFinanceira
    context: Optional[str] = Field(default=None, max_length=500)
    automatic_thought: Optional[str] = Field(default=None, max_length=500)
    chosen_action: Optional[AcaoConsciente] = None
    trigger_source: Optional[str] = Field(default=None, max_length=80)


class ConsciousReflectionOut(ConsciousReflectionCreate):
    id: int
    transaction_date: str
    transaction_description: str
    transaction_value: float
    category_name: Optional[str] = None
    created_at: str
    updated_at: str


class ConsciousWeeklyCheckinCreate(BaseModel):
    week_start: date
    financial_stress: int = Field(ge=1, le=5)
    confidence: int = Field(ge=1, le=5)
    avoided_finances: bool = False
    note: Optional[str] = Field(default=None, max_length=500)


class ConsciousWeeklyCheckinOut(BaseModel):
    id: int
    week_start: str
    financial_stress: int
    confidence: int
    avoided_finances: bool
    note: Optional[str] = None
    created_at: str
    updated_at: str
