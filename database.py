import os
import json
import sqlite3

os.makedirs("data", exist_ok=True)

conn = sqlite3.connect("data/hookah.db", check_same_thread=False)
cursor = conn.cursor()


def _ensure_column(table, column, definition):
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    if column not in columns:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db():
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS employees(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id INTEGER,
            name TEXT,
            active INTEGER DEFAULT 1
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS orders(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_number TEXT,
            zone TEXT,
            flavor TEXT,
            employee_id INTEGER,
            status TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            closed_at TEXT,
            duration INTEGER
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS tobacco(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            grams INTEGER,
            category TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS food_items(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price INTEGER DEFAULT 0,
            cook_minutes INTEGER DEFAULT 10,
            active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS food_orders(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER,
            item_name TEXT NOT NULL,
            table_number TEXT,
            employee_id INTEGER,
            status TEXT DEFAULT 'active',
            cook_minutes INTEGER DEFAULT 10,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            ready_at TEXT,
            closed_at TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS tobacco_mixes(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            recipe TEXT NOT NULL,
            note TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS shifts(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            opened_at TEXT,
            closed_at TEXT,
            status TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS shift_employees(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shift_id INTEGER,
            employee_id INTEGER
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS employee_requests(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id INTEGER,
            name TEXT,
            status TEXT DEFAULT 'pending'
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS finance_reports(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            message_id INTEGER,
            employees TEXT,
            report_date TEXT,
            shift_type TEXT,
            total INTEGER,
            total_lg INTEGER,
            cashless INTEGER,
            cash INTEGER,
            acquiring INTEGER,
            sbp INTEGER,
            bar_total INTEGER,
            ps_total INTEGER,
            hookah_total INTEGER,
            cork_total INTEGER,
            refunds INTEGER,
            cashbox_change INTEGER,
            bonuses INTEGER,
            expenses_text TEXT,
            closed_by TEXT,
            accepted_by TEXT,
            raw_text TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(chat_id, message_id)
        )
        """
    )

    # Планы выручки по месяцам: month = 'YYYY-MM'
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS monthly_plans(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            month TEXT UNIQUE,
            plan INTEGER,
            set_by INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    _ensure_column("tobacco", "category", "TEXT")
    _ensure_column("tobacco", "stock", "TEXT DEFAULT 'full'")
    _seed_initial_data()
    conn.commit()


def _seed_initial_data():
    seed_path = "data/seed_data.json"
    if not os.path.exists(seed_path):
        return

    with open(seed_path, encoding="utf-8") as seed_file:
        seed = json.load(seed_file)

    def table_empty(table: str) -> bool:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        return cursor.fetchone()[0] == 0

    if table_empty("employees"):
        for row in seed.get("employees", []):
            cursor.execute(
                "INSERT OR IGNORE INTO employees(id, tg_id, name, active) VALUES (?, ?, ?, ?)",
                (row.get("id"), row.get("tg_id"), row.get("name"), row.get("active", 1)),
            )

    for row in seed.get("finance_reports", []):
        cursor.execute(
            """
            INSERT INTO finance_reports(
                chat_id, message_id, employees, report_date, shift_type,
                total, total_lg, cashless, cash, acquiring, sbp,
                bar_total, ps_total, hookah_total, cork_total,
                refunds, cashbox_change, bonuses, expenses_text,
                closed_by, accepted_by, raw_text, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(chat_id, message_id) DO UPDATE SET
                employees=excluded.employees,
                report_date=excluded.report_date,
                shift_type=excluded.shift_type,
                total=excluded.total,
                total_lg=excluded.total_lg,
                cashless=excluded.cashless,
                cash=excluded.cash,
                acquiring=excluded.acquiring,
                sbp=excluded.sbp,
                bar_total=excluded.bar_total,
                ps_total=excluded.ps_total,
                hookah_total=excluded.hookah_total,
                cork_total=excluded.cork_total,
                refunds=excluded.refunds,
                cashbox_change=excluded.cashbox_change,
                bonuses=excluded.bonuses,
                expenses_text=excluded.expenses_text,
                closed_by=excluded.closed_by,
                accepted_by=excluded.accepted_by,
                raw_text=excluded.raw_text,
                created_at=excluded.created_at
            """,
            (
                row.get("chat_id"), row.get("message_id"),
                row.get("employees"), row.get("report_date"), row.get("shift_type"),
                row.get("total"), row.get("total_lg"), row.get("cashless"), row.get("cash"),
                row.get("acquiring"), row.get("sbp"), row.get("bar_total"), row.get("ps_total"),
                row.get("hookah_total"), row.get("cork_total"), row.get("refunds"),
                row.get("cashbox_change"), row.get("bonuses"), row.get("expenses_text"),
                row.get("closed_by"), row.get("accepted_by"), row.get("raw_text"),
                row.get("created_at"),
            ),
        )

    if table_empty("monthly_plans"):
        for row in seed.get("monthly_plans", []):
            cursor.execute(
                """
                INSERT OR IGNORE INTO monthly_plans(id, month, plan, set_by, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (row.get("id"), row.get("month"), row.get("plan"), row.get("set_by"), row.get("created_at")),
            )

    if table_empty("tobacco"):
        for row in seed.get("tobacco", []):
            cursor.execute(
                """
                INSERT OR IGNORE INTO tobacco(id, name, grams, category, stock)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    row.get("id"), row.get("name"), row.get("grams", 0),
                    row.get("category"), row.get("stock", "full"),
                ),
            )


def is_employee(tg_id: int) -> bool:
    cursor.execute(
        """
        SELECT 1 FROM employees
        WHERE tg_id=? AND active=1
        """,
        (tg_id,),
    )
    return cursor.fetchone() is not None


def get_plan(month: str) -> int | None:
    """Возвращает план выручки для указанного месяца (YYYY-MM) или None."""
    cursor.execute("SELECT plan FROM monthly_plans WHERE month=?", (month,))
    row = cursor.fetchone()
    return row[0] if row else None


def set_plan(month: str, plan: int, admin_tg_id: int) -> None:
    """Устанавливает или обновляет план выручки для месяца."""
    cursor.execute(
        """
        INSERT INTO monthly_plans(month, plan, set_by)
        VALUES (?, ?, ?)
        ON CONFLICT(month) DO UPDATE SET plan=excluded.plan, set_by=excluded.set_by,
            created_at=CURRENT_TIMESTAMP
        """,
        (month, plan, admin_tg_id),
    )
    conn.commit()
