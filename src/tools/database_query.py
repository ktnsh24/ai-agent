"""Database query tool — safe SQL execution against a sample SQLite database."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

SAMPLE_DB_PATH = Path("data/sample.db")

SAMPLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    price REAL NOT NULL,
    stock INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    total_price REAL NOT NULL,
    order_date TEXT NOT NULL DEFAULT (date('now')),
    FOREIGN KEY (product_id) REFERENCES products(id)
);
"""

SAMPLE_DATA = """
INSERT OR IGNORE INTO products (id, name, category, price, stock) VALUES
    (1, 'Laptop Pro 15', 'Electronics', 1299.99, 45),
    (2, 'Wireless Mouse', 'Electronics', 29.99, 230),
    (3, 'USB-C Hub', 'Electronics', 49.99, 120),
    (4, 'Standing Desk', 'Furniture', 599.99, 15),
    (5, 'Office Chair', 'Furniture', 349.99, 28),
    (6, 'Desk Lamp', 'Furniture', 79.99, 67),
    (7, 'Python Cookbook', 'Books', 44.99, 89),
    (8, 'Cloud Architecture Guide', 'Books', 54.99, 42),
    (9, 'Mechanical Keyboard', 'Electronics', 149.99, 56),
    (10, 'Monitor 27inch', 'Electronics', 399.99, 33);

INSERT OR IGNORE INTO orders (id, product_id, quantity, total_price, order_date) VALUES
    (1, 1, 2, 2599.98, '2024-01-15'),
    (2, 2, 5, 149.95, '2024-01-16'),
    (3, 4, 1, 599.99, '2024-01-17'),
    (4, 7, 3, 134.97, '2024-01-18'),
    (5, 1, 1, 1299.99, '2024-01-20'),
    (6, 9, 2, 299.98, '2024-01-21'),
    (7, 3, 4, 199.96, '2024-01-22'),
    (8, 5, 1, 349.99, '2024-01-23'),
    (9, 10, 2, 799.98, '2024-01-24'),
    (10, 8, 1, 54.99, '2024-01-25');
"""

# Only allow SELECT queries for safety
BLOCKED_KEYWORDS = {"DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", "TRUNCATE", "EXEC"}


def _ensure_sample_db() -> None:
    """Create sample database if it doesn't exist."""
    SAMPLE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(SAMPLE_DB_PATH))
    try:
        conn.executescript(SAMPLE_SCHEMA)
        conn.executescript(SAMPLE_DATA)
        conn.commit()
    finally:
        conn.close()


def _is_safe_query(query: str) -> bool:
    """Check if a SQL query is read-only (SELECT only)."""
    query_upper = query.strip().upper()
    for keyword in BLOCKED_KEYWORDS:
        if keyword in query_upper.split():
            return False
    return query_upper.startswith("SELECT") or query_upper.startswith("PRAGMA")


def create_database_query_tool():
    """Factory: create the database query tool."""
    _ensure_sample_db()

    @tool
    def database_query(query: str) -> str:
        """Execute a read-only SQL query against the sample product database.

        Available tables:
        - products (id, name, category, price, stock)
        - orders (id, product_id, quantity, total_price, order_date)

        Only SELECT queries are allowed.

        Args:
            query: SQL SELECT query to execute.

        Returns:
            Query results as formatted text.
        """
        if not _is_safe_query(query):
            return "Error: Only SELECT queries are allowed for safety."

        try:
            conn = sqlite3.connect(str(SAMPLE_DB_PATH))
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query)
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            conn.close()

            if not rows:
                return "Query returned no results."

            # Format as table
            lines = [" | ".join(columns)]
            lines.append("-" * len(lines[0]))
            for row in rows[:50]:  # Limit to 50 rows
                lines.append(" | ".join(str(row[col]) for col in columns))

            result = "\n".join(lines)
            if len(rows) > 50:
                result += f"\n... ({len(rows)} total rows, showing first 50)"

            return result

        except sqlite3.Error as e:
            return f"SQL Error: {str(e)}"
        except Exception as e:
            return f"Error: {str(e)}"

    return database_query
