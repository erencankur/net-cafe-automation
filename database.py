import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Iterable

# Core constants to avoid string drift across UI/DB
TABLE_KIND_VIP = "VIP"
TABLE_KIND_STANDARD = "Standard"
STATUS_EMPTY = "Empty"
STATUS_OCCUPIED = "Occupied"
STATUS_RESERVED = "Reserved"
STATUS_OUT_OF_ORDER = "OutOfOrder"
CATEGORY_FOOD = "Food"
CATEGORY_DRINK = "Drink"

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "cafe.db"


def connect_db():
    """Open a SQLite connection with Row factory for dict-like access."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _row_to_dict(row: sqlite3.Row | None):
    """Convert a sqlite Row to a plain dict (or None if missing)."""
    if not row:
        return None
    return {k: row[k] for k in row.keys()}

def init_db():
    """Create tables if they do not exist and seed demo data."""
    with connect_db() as con:
        cur = con.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS tables (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                kind TEXT NOT NULL,            -- VIP / Standard
                status TEXT NOT NULL,          -- Empty / Occupied / Reserved / OutOfOrder
                hardware TEXT NOT NULL,
                is_out_of_order INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_id INTEGER NOT NULL,
                start_ts TEXT NOT NULL,        -- ISO datetime
                end_ts TEXT,                   -- NULL means active
                kind TEXT NOT NULL,            -- Timed / Unlimited
                planned_minutes INTEGER,       -- Planned duration if Timed
                hourly_rate REAL NOT NULL,
                FOREIGN KEY(table_id) REFERENCES tables(id)
            );

            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,        -- Food / Drink
                price REAL NOT NULL,
                stock INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                amount REAL NOT NULL,          -- price * quantity at order time
                FOREIGN KEY(session_id) REFERENCES sessions(id),
                FOREIGN KEY(product_id) REFERENCES products(id)
            );
            """
        )

        # Seed tables if empty
        cur.execute("SELECT COUNT(*) AS cnt FROM tables")
        if cur.fetchone()[0] == 0:
            for i in range(1, 21):
                kind = TABLE_KIND_VIP if i <= 5 else TABLE_KIND_STANDARD
                hardware = "RTX 4060 Ti, 165Hz Monitor" if kind == TABLE_KIND_VIP else "GTX 1650, 75Hz Monitor"
                cur.execute(
                    "INSERT INTO tables(name, kind, status, hardware, is_out_of_order) VALUES(?,?,?,?,0)",
                    (f"Table {i}", kind, STATUS_EMPTY, hardware),
                )

        # Seed products if empty
        cur.execute("SELECT COUNT(*) AS cnt FROM products")
        if cur.fetchone()[0] == 0:
            products: Iterable[tuple[str, str, float, int]] = [
                ("Cheese Toast", CATEGORY_FOOD, 50.0, 50),
                ("Sausage Toast", CATEGORY_FOOD, 60.0, 50),
                ("Mixed Toast", CATEGORY_FOOD, 70.0, 50),
                ("Patso Sandwich", CATEGORY_FOOD, 45.0, 40),
                ("Pizza", CATEGORY_FOOD, 120.0, 30),
                ("Water", CATEGORY_DRINK, 10.0, 100),
                ("Tea", CATEGORY_DRINK, 15.0, 100),
                ("Cola", CATEGORY_DRINK, 25.0, 80),
                ("Fanta", CATEGORY_DRINK, 25.0, 80),
                ("Sprite", CATEGORY_DRINK, 25.0, 80),
            ]
            cur.executemany(
                "INSERT INTO products(name, category, price, stock) VALUES(?,?,?,?)",
                products,
            )

def fetch_tables():
    """Return all tables ordered by id."""
    with connect_db() as con:
        cur = con.cursor()
        cur.execute("SELECT * FROM tables ORDER BY id")
        rows = cur.fetchall()
    return [_row_to_dict(r) for r in rows]

def fetch_table(table_id: int):
    """Return a single table by id."""
    with connect_db() as con:
        cur = con.cursor()
        cur.execute("SELECT * FROM tables WHERE id=?", (table_id,))
        row = cur.fetchone()
    return _row_to_dict(row)

def get_hourly_rate(table_id: int) -> float:
    """Get hourly rate based on table kind (VIP/Standard)."""
    table = fetch_table(table_id)
    if not table:
        return 0.0
    return 30.0 if table["kind"] == TABLE_KIND_VIP else 20.0

def fetch_active_session(table_id: int):
    """Return active session for a table if it exists."""
    with connect_db() as con:
        cur = con.cursor()
        cur.execute("SELECT * FROM sessions WHERE table_id=? AND end_ts IS NULL", (table_id,))
        row = cur.fetchone()
    return _row_to_dict(row)

def start_timed_session(table_id: int, minutes: int):
    """Start a timed session for the table if none is active."""
    if fetch_active_session(table_id):
        return
    now = datetime.now().isoformat(timespec="seconds")
    rate = get_hourly_rate(table_id)
    with connect_db() as con:
        cur = con.cursor()
        cur.execute(
            "INSERT INTO sessions(table_id, start_ts, kind, planned_minutes, hourly_rate) VALUES(?,?,?,?,?)",
            (table_id, now, "Timed", minutes, rate),
        )
        cur.execute("UPDATE tables SET status=? WHERE id=?", (STATUS_OCCUPIED, table_id))
        con.commit()

def start_unlimited_session(table_id: int):
    """Start an unlimited session for the table if none is active."""
    if fetch_active_session(table_id):
        return
    now = datetime.now().isoformat(timespec="seconds")
    rate = get_hourly_rate(table_id)
    with connect_db() as con:
        cur = con.cursor()
        cur.execute(
            "INSERT INTO sessions(table_id, start_ts, kind, planned_minutes, hourly_rate) VALUES(?,?,?,?,?)",
            (table_id, now, "Unlimited", None, rate),
        )
        cur.execute("UPDATE tables SET status=? WHERE id=?", (STATUS_OCCUPIED, table_id))
        con.commit()

def add_order(table_id: int, product_id: int, quantity: int) -> bool:
    """Add an order to the active session; decrease stock; return success flag."""
    session = fetch_active_session(table_id)
    if not session:
        return False
    with connect_db() as con:
        cur = con.cursor()
        cur.execute("SELECT stock, price FROM products WHERE id=?", (product_id,))
        row = cur.fetchone()
        if not row:
            return False
        stock, price = row["stock"], row["price"]
        if stock < quantity:
            return False
        amount = float(price) * quantity
        cur.execute(
            "INSERT INTO orders(session_id, product_id, quantity, amount) VALUES(?,?,?,?)",
            (session["id"], product_id, quantity, amount),
        )
        cur.execute("UPDATE products SET stock=stock-? WHERE id=?", (quantity, product_id))
        con.commit()
        return True

def fetch_products(category: str | None = None):
    """Return all products, optionally filtered by category."""
    with connect_db() as con:
        cur = con.cursor()
        if category:
            cur.execute("SELECT * FROM products WHERE category=? ORDER BY name", (category,))
        else:
            cur.execute("SELECT * FROM products ORDER BY name")
        rows = cur.fetchall()
    return [_row_to_dict(r) for r in rows]

def fetch_active_session_orders(table_id: int):
    """Return aggregated orders for the active session of a table."""
    with connect_db() as con:
        cur = con.cursor()
        cur.execute(
            """
            SELECT p.name AS name,
                   SUM(o.quantity) AS total_qty,
                   SUM(o.amount) AS total_amount
            FROM orders o
            JOIN sessions s ON o.session_id = s.id
            JOIN products p ON o.product_id = p.id
            WHERE s.table_id=? AND s.end_ts IS NULL
            GROUP BY p.name
            ORDER BY p.name
            """,
            (table_id,),
        )
        rows = cur.fetchall()
    return [{"name": r["name"], "total_qty": r["total_qty"], "total_amount": float(r["total_amount"])} for r in rows]

def get_active_session_order_total(table_id: int) -> float:
    """Return total order amount for the active session of a table."""
    with connect_db() as con:
        cur = con.cursor()
        cur.execute(
            """
            SELECT COALESCE(SUM(o.amount), 0) AS total
            FROM orders o
            JOIN sessions s ON o.session_id = s.id
            WHERE s.table_id=? AND s.end_ts IS NULL
            """,
            (table_id,),
        )
        val = cur.fetchone()[0]
    return float(val or 0)

def _calculate_time_charge(session: dict) -> tuple[float, int]:
    """Calculate time-based charge and minutes for a session."""
    hourly = float(session["hourly_rate"]) if session["hourly_rate"] is not None else 0.0
    if session["kind"] == "Timed" and session.get("planned_minutes"):
        minutes = int(session["planned_minutes"])
        charge = round(hourly * (minutes / 60.0), 2)
        return (charge, minutes)
    start = datetime.fromisoformat(session["start_ts"]) if session["start_ts"] else datetime.now()
    end = datetime.now()
    minutes = int(round((end - start).total_seconds() / 60.0))
    if minutes < 1:
        minutes = 1
    charge = round(hourly * (minutes / 60.0), 2)
    return (charge, minutes)

def end_session(table_id: int) -> tuple[float, int]:
    """Close the active session, update table status, and return (charge, minutes)."""
    session = fetch_active_session(table_id)
    if not session:
        return (0.0, 0)
    charge, minutes = _calculate_time_charge(session)
    now = datetime.now().isoformat(timespec="seconds")
    with connect_db() as con:
        cur = con.cursor()
        cur.execute("UPDATE sessions SET end_ts=? WHERE id=?", (now, session["id"]))
        cur.execute(
            "UPDATE tables SET status=CASE WHEN is_out_of_order=1 THEN ? ELSE ? END WHERE id=?",
            (STATUS_OUT_OF_ORDER, STATUS_EMPTY, table_id),
        )
        con.commit()
    return (charge, minutes)

def mark_table_out_of_order(table_id: int):
    """Mark a table as out of order."""
    with connect_db() as con:
        cur = con.cursor()
        cur.execute("UPDATE tables SET is_out_of_order=1, status=? WHERE id=?", (STATUS_OUT_OF_ORDER, table_id))
        con.commit()

def get_end_of_day_report():
    """Return end-of-day revenue summary including category totals."""
    with connect_db() as con:
        cur = con.cursor()
        cur.execute("SELECT * FROM sessions WHERE DATE(end_ts) = DATE('now','localtime')")
        sessions_today = [_row_to_dict(r) for r in cur.fetchall()]
        session_revenue = 0.0
        for s in sessions_today:
            charge, _ = _calculate_time_charge(s)
            session_revenue += charge
        cur.execute(
            """
            SELECT COALESCE(SUM(o.amount),0) AS total, COALESCE(SUM(o.quantity),0) AS qty
            FROM orders o
            JOIN sessions s ON o.session_id = s.id
            WHERE DATE(s.end_ts) = DATE('now','localtime')
            """
        )
        row = cur.fetchone()
        order_revenue = float(row[0] or 0)
        order_count = int(row[1] or 0)

        cur.execute(
            """
            SELECT p.category AS category, COALESCE(SUM(o.amount),0) AS total
            FROM orders o
            JOIN sessions s ON o.session_id = s.id
            JOIN products p ON o.product_id = p.id
            WHERE DATE(s.end_ts) = DATE('now','localtime')
            GROUP BY p.category
            """
        )
        category_totals = {r["category"]: float(r["total"]) for r in cur.fetchall()}

    return {
        "session_revenue": round(session_revenue, 2),
        "order_revenue": round(order_revenue, 2),
        "total_revenue": round(session_revenue + order_revenue, 2),
        "order_count": order_count,
        "category_totals": category_totals,
    }

def get_end_of_day_product_report():
    """Return quantities sold per product name for the current day."""
    with connect_db() as con:
        cur = con.cursor()
        cur.execute(
            """
            SELECT p.name AS name, COALESCE(SUM(o.quantity),0) AS qty
            FROM orders o
            JOIN sessions s ON o.session_id = s.id
            JOIN products p ON o.product_id = p.id
            WHERE DATE(s.end_ts) = DATE('now','localtime')
            GROUP BY p.name
            ORDER BY p.name
            """
        )
        result = {r["name"]: int(r["qty"]) for r in cur.fetchall()}
    return result