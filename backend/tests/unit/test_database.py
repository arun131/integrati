import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.connection import Base, create_db_tables, get_db


class TestDatabaseConnection:
    """Test cases for database connection"""

    def test_create_db_tables(self):
        """Test that database tables can be created"""
        # Create a test engine
        test_engine = create_engine(
            "sqlite:///:memory:", connect_args={"check_same_thread": False}
        )

        # Test that create_db_tables doesn't raise an exception
        try:
            create_db_tables()
            # If we get here, the function executed successfully
            assert True
        except Exception as e:
            pytest.fail(f"create_db_tables raised an exception: {e}")

    def test_base_metadata_tables(self):
        """Test that Base metadata contains expected tables"""
        expected_tables = [
            "users",
            "user_integrations",
            "pending_actions",
            "user_tools",  # This is the actual table name, not 'tools'
        ]

        for table_name in expected_tables:
            assert (
                table_name in Base.metadata.tables
            ), f"Table {table_name} should exist in metadata"

    def test_get_db_generator(self):
        """Test that get_db returns a generator"""
        db_gen = get_db()
        assert hasattr(db_gen, "__iter__"), "get_db should return a generator"

    def test_database_url_configuration(self):
        """Test that database URL is properly configured"""
        from app.core.config import settings

        assert hasattr(settings, "DATABASE_URL"), "DATABASE_URL should be configured"
        assert settings.DATABASE_URL is not None, "DATABASE_URL should not be None"

    def test_sqlite_connection_string(self):
        """Test that SQLite connection string is valid"""
        from app.core.config import settings

        assert (
            "sqlite" in settings.DATABASE_URL.lower()
        ), "Database URL should be SQLite"

    def test_base_model_inheritance(self):
        """Test that models inherit from Base"""
        from app.models.integration import UserIntegration
        from app.models.user import User

        assert issubclass(User, Base), "User model should inherit from Base"
        assert issubclass(
            UserIntegration, Base
        ), "UserIntegration model should inherit from Base"

    def test_table_names(self):
        """Test that table names are correctly defined"""
        from app.models.integration import UserIntegration
        from app.models.user import User

        assert User.__tablename__ == "users", "User table name should be 'users'"
        assert (
            UserIntegration.__tablename__ == "user_integrations"
        ), "UserIntegration table name should be 'user_integrations'"
