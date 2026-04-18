from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from src.db.database import get_db
from src.middleware.auth import get_current_user

router = APIRouter(prefix="/transactions", tags=["Transactions"])

# ── Schemas ────────────────────────────────────────────────────────────

class TransactionCreate(BaseModel):
    type: str
    category: str
    description: Optional[str] = ""
    amount: float
    date: date

    class Config:
        json_encoders = {date: str}

# ── Routes ─────────────────────────────────────────────────────────────

@router.get("")
def get_transactions(
    month: Optional[str] = Query(None, description="Filter by YYYY-MM"),
    type: Optional[str] = Query(None, description="income or expense"),
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["sub"]
    conditions = ["user_id = %s"]
    params = [user_id]

    if month:
        conditions.append("TO_CHAR(date, 'YYYY-MM') = %s")
        params.append(month)
    if type in ("income", "expense"):
        conditions.append("type = %s")
        params.append(type)

    where = " AND ".join(conditions)
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT id, type, category, description, amount, date, created_at
                FROM transactions
                WHERE {where}
                ORDER BY date DESC, created_at DESC
                """,
                params
            )
            rows = cur.fetchall()

    return [
        {**dict(r), "id": str(r["id"]), "amount": float(r["amount"]), "date": str(r["date"])}
        for r in rows
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_transaction(
    body: TransactionCreate,
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["sub"]
    if body.type not in ("income", "expense"):
        raise HTTPException(400, "type must be 'income' or 'expense'")
    if body.amount <= 0:
        raise HTTPException(400, "amount must be greater than 0")

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO transactions (user_id, type, category, description, amount, date)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, type, category, description, amount, date, created_at
                """,
                (user_id, body.type, body.category, body.description or "", body.amount, body.date)
            )
            row = dict(cur.fetchone())

    return {**row, "id": str(row["id"]), "amount": float(row["amount"]), "date": str(row["date"])}


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    transaction_id: str,
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["sub"]
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM transactions WHERE id = %s AND user_id = %s RETURNING id",
                (transaction_id, user_id)
            )
            if not cur.fetchone():
                raise HTTPException(404, "Transaction not found")


@router.get("/summary/monthly")
def get_monthly_summary(
    months: int = Query(6, ge=1, le=24),
    current_user: dict = Depends(get_current_user)
):
    """Returns income and expense totals for the last N months."""
    user_id = current_user["sub"]
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    TO_CHAR(date, 'YYYY-MM') AS month,
                    TO_CHAR(date, 'Mon') AS label,
                    type,
                    SUM(amount) AS total
                FROM transactions
                WHERE user_id = %s
                  AND date >= DATE_TRUNC('month', NOW()) - INTERVAL '%s months'
                GROUP BY month, label, type
                ORDER BY month
                """,
                (user_id, months - 1)
            )
            rows = cur.fetchall()

    result = {}
    for r in rows:
        m = r["month"]
        if m not in result:
            result[m] = {"month": m, "label": r["label"], "income": 0, "expense": 0}
        result[m][r["type"]] = float(r["total"])

    return list(result.values())
