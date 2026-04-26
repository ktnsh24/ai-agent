"""Tests for the database query tool."""

import sqlite3

from src.tools.database_query import _is_safe_query, _ensure_sample_db, SAMPLE_DB_PATH


class TestSafeQuery:
    """Test SQL query safety checks."""

    def test_select_allowed(self) -> None:
        assert _is_safe_query("SELECT * FROM products") is True

    def test_select_with_where(self) -> None:
        assert _is_safe_query("SELECT name, price FROM products WHERE category = 'Electronics'") is True

    def test_select_with_join(self) -> None:
        assert _is_safe_query("SELECT p.name, o.quantity FROM products p JOIN orders o ON p.id = o.product_id") is True

    def test_pragma_allowed(self) -> None:
        assert _is_safe_query("PRAGMA table_info(products)") is True

    def test_drop_blocked(self) -> None:
        assert _is_safe_query("DROP TABLE products") is False

    def test_delete_blocked(self) -> None:
        assert _is_safe_query("DELETE FROM products WHERE id = 1") is False

    def test_update_blocked(self) -> None:
        assert _is_safe_query("UPDATE products SET price = 0") is False

    def test_insert_blocked(self) -> None:
        assert _is_safe_query("INSERT INTO products (name) VALUES ('hack')") is False

    def test_truncate_blocked(self) -> None:
        assert _is_safe_query("TRUNCATE TABLE products") is False


class TestSampleDatabase:
    """Test sample database creation and content."""

    def test_ensure_sample_db_creates_file(self) -> None:
        _ensure_sample_db()
        assert SAMPLE_DB_PATH.exists()

    def test_products_table_has_data(self) -> None:
        _ensure_sample_db()
        conn = sqlite3.connect(str(SAMPLE_DB_PATH))
        cursor = conn.execute("SELECT COUNT(*) FROM products")
        count = cursor.fetchone()[0]
        conn.close()
        assert count == 10

    def test_orders_table_has_data(self) -> None:
        _ensure_sample_db()
        conn = sqlite3.connect(str(SAMPLE_DB_PATH))
        cursor = conn.execute("SELECT COUNT(*) FROM orders")
        count = cursor.fetchone()[0]
        conn.close()
        assert count == 10

    def test_products_have_categories(self) -> None:
        _ensure_sample_db()
        conn = sqlite3.connect(str(SAMPLE_DB_PATH))
        cursor = conn.execute("SELECT DISTINCT category FROM products ORDER BY category")
        categories = [row[0] for row in cursor.fetchall()]
        conn.close()
        assert "Electronics" in categories
        assert "Furniture" in categories
        assert "Books" in categories
