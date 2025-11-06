"""
Unit tests for database utility functions
Testing schema reference generation for PostgreSQL vs SQLite environments
"""

import os
from unittest.mock import patch


from shared.database.utils import get_schema_ref, IS_TESTING, IS_POSTGRES


class TestDatabaseUtils:
    """Test database utility functions"""

    def test_is_testing_flag(self):
        """Test IS_TESTING is correctly set when running under pytest"""
        assert IS_TESTING is True  # Should be True when running tests

    def test_is_postgres_flag_default(self):
        """Test IS_POSTGRES is False in testing environment"""
        assert IS_POSTGRES is False  # Should be False during tests

    def test_get_schema_ref_sqlite_behavior(self):
        """Test get_schema_ref returns table name only for SQLite (default test behavior)"""
        # In test environment (SQLite), should return just table name
        result = get_schema_ref("users", "public")
        assert result == "users"

    def test_get_schema_ref_different_table_and_schema(self):
        """Test get_schema_ref with different table and schema names"""
        # Test various combinations in SQLite mode
        assert get_schema_ref("products", "inventory") == "products"
        assert get_schema_ref("orders", "sales") == "orders"
        assert get_schema_ref("brands", "catalog") == "brands"

    @patch.dict(os.environ, {"DATABASE_URL": "postgresql://user:pass@localhost/db"})
    @patch("shared.database.utils.IS_TESTING", False)
    def test_get_schema_ref_postgres_behavior(self):
        """Test get_schema_ref returns schema.table for PostgreSQL in production"""
        # Mock PostgreSQL environment (not testing)
        with patch("shared.database.utils.IS_POSTGRES", True):
            result = get_schema_ref("users", "public")
            assert result == "public.users"

    @patch.dict(os.environ, {"DATABASE_URL": "postgresql://user:pass@localhost/db"})
    @patch("shared.database.utils.IS_TESTING", False)
    def test_get_schema_ref_postgres_various_schemas(self):
        """Test get_schema_ref with various schema names in PostgreSQL mode"""
        # Mock PostgreSQL environment
        with patch("shared.database.utils.IS_POSTGRES", True):
            assert get_schema_ref("products", "inventory") == "inventory.products"
            assert get_schema_ref("orders", "sales") == "sales.orders"
            assert get_schema_ref("brands", "catalog") == "catalog.brands"

    @patch.dict(os.environ, {"DATABASE_URL": "sqlite:///test.db"})
    def test_get_schema_ref_sqlite_url(self):
        """Test get_schema_ref with SQLite URL returns table name only"""
        result = get_schema_ref("users", "public")
        assert result == "users"

    @patch.dict(os.environ, {"DATABASE_URL": ""})
    def test_get_schema_ref_no_database_url(self):
        """Test get_schema_ref with no DATABASE_URL returns table name only"""
        result = get_schema_ref("users", "public")
        assert result == "users"

    def test_get_schema_ref_edge_cases(self):
        """Test get_schema_ref with edge case inputs"""
        # Test empty strings
        assert get_schema_ref("", "public") == ""
        assert get_schema_ref("users", "") == "users"

        # Test special characters (in SQLite mode during tests)
        assert get_schema_ref("user_profiles", "public_schema") == "user_profiles"
        assert get_schema_ref("table-with-dashes", "schema.with.dots") == "table-with-dashes"

    @patch.dict(os.environ, {"DATABASE_URL": "postgresql://user:pass@localhost/db"})
    @patch("shared.database.utils.IS_TESTING", False)
    def test_postgres_environment_detection(self):
        """Test PostgreSQL environment detection logic"""
        with patch("shared.database.utils.IS_POSTGRES", True):
            # Verify that PostgreSQL mode properly constructs schema references
            result = get_schema_ref("test_table", "test_schema")
            assert result == "test_schema.test_table"
            assert "." in result  # Should contain schema separator
