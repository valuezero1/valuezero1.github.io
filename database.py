import sqlite3

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

    _ensure_column("tobacco", "category", "TEXT")
    conn.commit()


def is_employee(tg_id: int) -> bool:
    cursor.execute(
        """
        SELECT 1 FROM employees
        WHERE tg_id=? AND active=1
        """,
        (tg_id,),
    )
    return cursor.fetchone() is not None
