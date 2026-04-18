from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from src.db.database import get_db
from src.middleware.auth import get_current_user

router = APIRouter(prefix="/budgets", tags=["Budgets"])

# Default budget targets as % of total expenses (used only as suggestions)
DEFAULT_BUDGET_SUGGESTIONS = {
    "Food & Dining": 30,
    "Rent": 30,
    "Bills & Utilities": 15,
    "Transport": 10,
    "Health": 5,
    "Entertainment": 5,
    "Shopping": 5,
    "Education": 5,
    "Other": 5
}

# ── Schemas ────────────────────────────────────────────────────────────

class BudgetUpsert(BaseModel):
    category: str
    monthly_limit: float

class BudgetBulkUpsert(BaseModel):
    budgets: List[BudgetUpsert]

# ── Routes ─────────────────────────────────────────────────────────────

@router.get("")
def get_budgets(current_user: dict = Depends(get_current_user)):
    """Return all user-defined budget limits with current month's actual spend."""
    user_id = current_user["sub"]
    with get_db() as conn:
        with conn.cursor() as cur:
            # User's saved budgets
            cur.execute(
                "SELECT category, monthly_limit FROM budgets WHERE user_id = %s ORDER BY category",
                (user_id,)
            )
            budgets = {r["category"]: float(r["monthly_limit"]) for r in cur.fetchall()}

            # Current month actuals per category
            cur.execute(
                """
                SELECT category, SUM(amount) AS spent
                FROM transactions
                WHERE user_id = %s
                  AND type = 'expense'
                  AND TO_CHAR(date, 'YYYY-MM') = TO_CHAR(NOW(), 'YYYY-MM')
                GROUP BY category
                """,
                (user_id,)
            )
            actuals = {r["category"]: float(r["spent"]) for r in cur.fetchall()}

    result = []
    all_cats = set(list(budgets.keys()) + list(actuals.keys()))
    for cat in sorted(all_cats):
        limit = budgets.get(cat)
        spent = actuals.get(cat, 0)
        result.append({
            "category": cat,
            "monthly_limit": limit,
            "spent_this_month": spent,
            "remaining": (limit - spent) if limit is not None else None,
            "percentage_used": round((spent / limit * 100), 1) if limit else None,
            "over_budget": (spent > limit) if limit is not None else False
        })

    return {
        "budgets": result,
        "suggestions": DEFAULT_BUDGET_SUGGESTIONS
    }


@router.put("")
def upsert_budgets(
    body: BudgetBulkUpsert,
    current_user: dict = Depends(get_current_user)
):
    """Create or update budget limits for multiple categories at once."""
    user_id = current_user["sub"]
    if not body.budgets:
        raise HTTPException(400, "No budgets provided")

    with get_db() as conn:
        with conn.cursor() as cur:
            for b in body.budgets:
                if b.monthly_limit < 0:
                    raise HTTPException(400, f"Budget for {b.category} cannot be negative")
                cur.execute(
                    """
                    INSERT INTO budgets (user_id, category, monthly_limit)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (user_id, category)
                    DO UPDATE SET monthly_limit = EXCLUDED.monthly_limit
                    """,
                    (user_id, b.category, b.monthly_limit)
                )

    return {"message": f"Updated {len(body.budgets)} budget(s) successfully"}


@router.delete("/{category}")
def delete_budget(
    category: str,
    current_user: dict = Depends(get_current_user)
):
    """Remove a budget limit for a category."""
    user_id = current_user["sub"]
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM budgets WHERE user_id = %s AND category = %s RETURNING id",
                (user_id, category)
            )
            if not cur.fetchone():
                raise HTTPException(404, "Budget not found for this category")

    return {"message": f"Budget for '{category}' removed"}
