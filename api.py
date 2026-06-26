"""
Hookah CRM — REST API для Telegram Mini App
"""

import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

DB_PATH = "data/hookah.db"

app = FastAPI(title="Hookah CRM API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── DB ──────────────────────────────────────────────────────────────────────

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ─── Models ──────────────────────────────────────────────────────────────────

class OrderCreate(BaseModel):
    table_number: str
    zone: str
    flavor: str
    employee_id: int


class TobaccoCreate(BaseModel):
    name: str
    category: str
    grams: int = 0
    stock: str = "full"   # full | half | low | empty


class TobaccoStockUpdate(BaseModel):
    stock: str            # full | half | low | empty


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _clean_name(name: str) -> str:
    """Убирает кавычки и emoji-префиксы: '😋 Михаил' → 'Михаил'."""
    name = name.strip().strip('"').strip("'")
    if name and not name[0].isalpha() and not name[0].isdigit():
        parts = name.split(maxsplit=1)
        name = parts[1] if len(parts) > 1 else name
    return name.strip()


# ─── Dashboard ───────────────────────────────────────────────────────────────

@app.get("/api/dashboard")
def dashboard():
    with get_db() as conn:
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM orders WHERE status='active'")
        active_orders = cur.fetchone()[0]

        cur.execute("SELECT id, opened_at FROM shifts WHERE status='open' ORDER BY id DESC LIMIT 1")
        shift_row = cur.fetchone()
        active_shift = dict(shift_row) if shift_row else None

        cur.execute("SELECT COUNT(*) FROM employees WHERE active=1")
        employee_count = cur.fetchone()[0]

        cur.execute(
            """
            SELECT id, report_date, shift_type, employees, total, cashless, cash,
                   acquiring, sbp, bar_total, ps_total, hookah_total, cork_total,
                   refunds, bonuses, expenses_text, closed_by, accepted_by
            FROM finance_reports
            ORDER BY report_date DESC, id DESC
            LIMIT 1
            """
        )
        last_report = cur.fetchone()

        cur.execute(
            """
            SELECT substr(report_date,1,7) as month,
                   COUNT(*) as cnt,
                   SUM(total) as total,
                   SUM(hookah_total) as hookahs,
                   SUM(bar_total) as bar,
                   SUM(ps_total) as ps
            FROM finance_reports
            WHERE substr(report_date,1,7) = substr(date('now'),1,7)
            """
        )
        month_row = cur.fetchone()

        return {
            "active_orders": active_orders,
            "active_shift": active_shift,
            "employee_count": employee_count,
            "last_report": dict(last_report) if last_report else None,
            "current_month": dict(month_row) if month_row and month_row["cnt"] else None,
        }


# ─── Finance ─────────────────────────────────────────────────────────────────

@app.get("/api/finance/reports")
def finance_reports(
    month: Optional[str] = Query(None),
    limit: int = Query(20, le=100),
    offset: int = Query(0),
):
    with get_db() as conn:
        cur = conn.cursor()
        if month:
            cur.execute(
                """
                SELECT id, report_date, shift_type, employees, total, cashless, cash,
                       acquiring, sbp, bar_total, ps_total, hookah_total, cork_total,
                       refunds, bonuses, expenses_text, closed_by, accepted_by
                FROM finance_reports
                WHERE substr(report_date,1,7)=?
                ORDER BY report_date DESC, id DESC
                LIMIT ? OFFSET ?
                """,
                (month, limit, offset),
            )
        else:
            cur.execute(
                """
                SELECT id, report_date, shift_type, employees, total, cashless, cash,
                       acquiring, sbp, bar_total, ps_total, hookah_total, cork_total,
                       refunds, bonuses, expenses_text, closed_by, accepted_by
                FROM finance_reports
                ORDER BY report_date DESC, id DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            )
        rows = [dict(r) for r in cur.fetchall()]

        cur.execute(
            "SELECT DISTINCT substr(report_date,1,7) as m FROM finance_reports ORDER BY m DESC"
        )
        months = [r["m"] for r in cur.fetchall()]

    return {"reports": rows, "months": months}


@app.get("/api/finance/month/{month}")
def finance_month(month: str):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT COUNT(*) as cnt,
                   SUM(total) as total,
                   SUM(cashless) as cashless,
                   SUM(cash) as cash,
                   SUM(acquiring) as acquiring,
                   SUM(sbp) as sbp,
                   SUM(bar_total) as bar_total,
                   SUM(ps_total) as ps_total,
                   SUM(hookah_total) as hookah_total,
                   SUM(cork_total) as cork_total,
                   SUM(refunds) as refunds,
                   SUM(bonuses) as bonuses
            FROM finance_reports
            WHERE substr(report_date,1,7)=?
            """,
            (month,),
        )
        row = cur.fetchone()
        return dict(row) if row and row["cnt"] else {}


# ─── Plan ────────────────────────────────────────────────────────────────────

@app.get("/api/plan")
def get_plan_api(month: Optional[str] = Query(None)):
    if not month:
        month = datetime.now().strftime("%Y-%m")

    with get_db() as conn:
        cur = conn.cursor()

        # Проверяем существует ли таблица
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='monthly_plans'")
        if not cur.fetchone():
            return {"month": month, "plan": None, "total": 0, "bar_total": 0, "shifts": 0, "pct": None}

        cur.execute("SELECT plan FROM monthly_plans WHERE month=?", (month,))
        row = cur.fetchone()
        plan = row["plan"] if row else None

        cur.execute(
            """
            SELECT COALESCE(SUM(total), 0) AS total,
                   COALESCE(SUM(bar_total), 0) AS bar_total,
                   COUNT(*) AS shifts
            FROM finance_reports
            WHERE substr(report_date, 1, 7) = ?
            """,
            (month,),
        )
        fact = dict(cur.fetchone())

    pct = round(fact["total"] / plan * 100) if plan else None
    return {"month": month, "plan": plan, "total": fact["total"],
            "bar_total": fact["bar_total"], "shifts": fact["shifts"], "pct": pct}


# ─── Top employees ────────────────────────────────────────────────────────────

@app.get("/api/top")
def get_top_api(month: Optional[str] = Query(None)):
    """
    Топ сотрудников по СРЕДНЕМУ значению выручки и бара за смену.
    Выручка смены делится поровну между сотрудниками.
    """
    if not month:
        month = datetime.now().strftime("%Y-%m")

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT employees, total, bar_total FROM finance_reports WHERE substr(report_date,1,7)=?",
            (month,),
        )
        rows = cur.fetchall()

    # Накапливаем сумму и количество смен для каждого сотрудника
    totals_sum:   dict[str, int] = {}
    bars_sum:     dict[str, int] = {}
    shift_count:  dict[str, int] = {}

    for row in rows:
        names_raw = row["employees"] or ""
        names = [_clean_name(n) for n in names_raw.split(",") if n.strip()]
        names = [n for n in names if n]
        if not names:
            continue
        share_total = (row["total"] or 0) // len(names)
        share_bar   = (row["bar_total"] or 0) // len(names)
        for name in names:
            totals_sum[name]  = totals_sum.get(name, 0) + share_total
            bars_sum[name]    = bars_sum.get(name, 0) + share_bar
            shift_count[name] = shift_count.get(name, 0) + 1

    def rank(sums: dict, counts: dict) -> list:
        result = []
        for name, s in sums.items():
            cnt = counts.get(name, 1)
            result.append({"name": name, "value": s // cnt, "shifts": cnt, "total": s})
        return sorted(result, key=lambda x: -x["value"])

    return {
        "month":    month,
        "by_total": rank(totals_sum, shift_count),
        "by_bar":   rank(bars_sum, shift_count),
    }


# ─── Orders ──────────────────────────────────────────────────────────────────

@app.get("/api/orders")
def get_orders(
    status: Optional[str] = Query(None),
    employee_id: Optional[int] = Query(None),
    limit: int = Query(50, le=200),
):
    with get_db() as conn:
        cur = conn.cursor()
        wheres, params = [], []
        if status:
            wheres.append("o.status=?"); params.append(status)
        if employee_id:
            wheres.append("o.employee_id=?"); params.append(employee_id)
        where = ("WHERE " + " AND ".join(wheres)) if wheres else ""
        params.append(limit)
        cur.execute(
            f"""
            SELECT o.id, o.table_number, o.zone, o.flavor, o.status, o.created_at,
                   e.name as employee_name, e.id as employee_id
            FROM orders o
            LEFT JOIN employees e ON e.id=o.employee_id
            {where}
            ORDER BY o.id DESC
            LIMIT ?
            """,
            params,
        )
        return {"orders": [dict(r) for r in cur.fetchall()]}


@app.post("/api/orders")
def create_order(body: OrderCreate):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, tg_id, name FROM employees WHERE id=? AND active=1", (body.employee_id,))
        emp = cur.fetchone()
        if not emp:
            raise HTTPException(404, "Сотрудник не найден")
        cur.execute(
            "INSERT INTO orders(table_number, zone, flavor, employee_id, status) VALUES (?, ?, ?, ?, 'active')",
            (body.table_number, body.zone, body.flavor, body.employee_id),
        )
        conn.commit()
        order_id = cur.lastrowid
        emp_tg = emp["tg_id"]

    import threading
    def _notify():
        import asyncio
        async def _send():
            try:
                from config import BOT_TOKEN
                from aiogram import Bot
                from keyboards import order_started_kb
                bot = Bot(BOT_TOKEN)
                await bot.send_message(
                    emp_tg,
                    f"🔥 Новый кальян\n"
                    f"ID: {order_id}\n"
                    f"Зона: {body.zone}\n"
                    f"Номер: {body.table_number}\n"
                    f"Вкус: {body.flavor}",
                    reply_markup=order_started_kb(order_id),
                )
                await bot.session.close()
            except Exception as e:
                print(f"[API] Ошибка уведомления: {e}")
        asyncio.run(_send())
    threading.Thread(target=_notify, daemon=True).start()

    return {"id": order_id, "status": "active"}


@app.patch("/api/orders/{order_id}/close")
def close_order(order_id: int):
    with get_db() as conn:
        cur = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute("UPDATE orders SET status='closed', closed_at=? WHERE id=?", (now, order_id))
        if cur.rowcount == 0:
            raise HTTPException(404, "Заказ не найден")
        conn.commit()
        return {"ok": True}


# ─── Employees ───────────────────────────────────────────────────────────────

@app.get("/api/employees")
def get_employees(active_only: bool = Query(True)):
    with get_db() as conn:
        cur = conn.cursor()
        if active_only:
            cur.execute("SELECT id, tg_id, name, active FROM employees WHERE active=1 ORDER BY name")
        else:
            cur.execute("SELECT id, tg_id, name, active FROM employees ORDER BY name")
        employees = [dict(r) for r in cur.fetchall()]
        for emp in employees:
            cur.execute("SELECT COUNT(*) FROM orders WHERE employee_id=? AND status='closed'", (emp["id"],))
            emp["hookahs_total"] = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM orders WHERE employee_id=? AND status='active'", (emp["id"],))
            emp["hookahs_active"] = cur.fetchone()[0]
        return {"employees": employees}


@app.get("/api/shifts/current")
def current_shift():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, opened_at FROM shifts WHERE status='open' ORDER BY id DESC LIMIT 1")
        shift = cur.fetchone()
        if not shift:
            return {"shift": None}
        cur.execute(
            """
            SELECT e.id, e.name
            FROM shift_employees se
            JOIN employees e ON e.id=se.employee_id
            WHERE se.shift_id=?
            """,
            (shift["id"],),
        )
        employees = [dict(r) for r in cur.fetchall()]
        return {"shift": {"id": shift["id"], "opened_at": shift["opened_at"], "employees": employees}}


# ─── Tobacco ─────────────────────────────────────────────────────────────────

TOBACCO_CATEGORIES = {
    "sour_berries":  "Кислые ягоды",
    "sweet_berries": "Сладкие ягоды",
    "sour_fruits":   "Кислые фрукты",
    "sweet_fruits":  "Сладкие фрукты",
    "herbal_fresh":  "Травяные и свежие",
    "floral":        "Цветочные",
    "desserts":      "Десертные и кондитерские",
    "drinks":        "Напитки",
    "mixes":         "Миксы и авторские вкусы",
}

STOCK_LABELS = {
    "full":  "Полная",
    "half":  "Половина",
    "low":   "Мало",
    "empty": "Закончился",
}


@app.get("/api/tobacco")
def get_tobacco():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, name, grams, category, stock FROM tobacco ORDER BY category, name")
        items = [dict(r) for r in cur.fetchall()]

    grouped = {code: {"name": name, "items": []} for code, name in TOBACCO_CATEGORIES.items()}
    uncategorized = []
    for item in items:
        item["stock"] = item.get("stock") or "full"
        cat = item.get("category") or ""
        if cat in grouped:
            grouped[cat]["items"].append(item)
        else:
            uncategorized.append(item)

    result = [
        {"code": code, "name": grouped[code]["name"], "items": grouped[code]["items"]}
        for code in TOBACCO_CATEGORIES
        if grouped[code]["items"]
    ]
    if uncategorized:
        result.append({"code": "other", "name": "Другое", "items": uncategorized})

    return {"categories": result, "total": len(items)}


@app.post("/api/tobacco")
def add_tobacco(body: TobaccoCreate):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO tobacco(name, grams, category, stock) VALUES (?, ?, ?, ?)",
            (body.name, body.grams, body.category, body.stock or "full"),
        )
        conn.commit()
        return {"id": cur.lastrowid}


@app.patch("/api/tobacco/{tobacco_id}/stock")
def update_tobacco_stock(tobacco_id: int, body: TobaccoStockUpdate):
    if body.stock not in STOCK_LABELS:
        raise HTTPException(400, f"stock должен быть одним из: {list(STOCK_LABELS.keys())}")
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE tobacco SET stock=? WHERE id=?", (body.stock, tobacco_id))
        if cur.rowcount == 0:
            raise HTTPException(404, "Не найдено")
        conn.commit()
        return {"ok": True}


@app.delete("/api/tobacco/{tobacco_id}")
def delete_tobacco(tobacco_id: int):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM tobacco WHERE id=?", (tobacco_id,))
        if cur.rowcount == 0:
            raise HTTPException(404, "Не найдено")
        conn.commit()
        return {"ok": True}
