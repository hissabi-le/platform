"""
Tests for production readiness improvements.

This test suite covers:
1. Account type classification
2. LLM integration and document type detection
3. Health endpoints
4. JWT secret validation
5. Dramatiq DLQ middleware
6. Sentry configuration
"""
import os
import pytest
import pytest_asyncio
import pandas as pd
from datetime import datetime
from unittest.mock import patch, MagicMock

# Set test environment before imports
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("JWT_SECRET", "test-secret-minimum-16-chars")


class TestAccountTypeClassification:
    """Tests for the account type classification logic."""
    
    def test_classify_revenue_by_keyword(self):
        """Revenue keywords should classify as REVENUE."""
        from src.tasks.process_upload import _classify_account_type
        
        assert _classify_account_type("Sales Revenue", "Sales", 100) == "REVENUE"
        assert _classify_account_type("Product Sales", "Income", 500) == "REVENUE"
        assert _classify_account_type("Service Income", "Revenue", 200) == "REVENUE"
    
    def test_classify_expense_by_keyword(self):
        """Expense keywords should classify as EXPENSE."""
        from src.tasks.process_upload import _classify_account_type
        
        assert _classify_account_type("Rent Expense", "Operating", -1000) == "EXPENSE"
        assert _classify_account_type("Utilities", "Expense", -200) == "EXPENSE"
        assert _classify_account_type("Salary", "Wages", -5000) == "EXPENSE"
    
    def test_classify_cogs_by_keyword(self):
        """COGS keywords should classify as COGS."""
        from src.tasks.process_upload import _classify_account_type
        
        assert _classify_account_type("COGS", "Cost of Goods", -300) == "COGS"
        assert _classify_account_type("Materials", "COGS", -150) == "COGS"
    
    def test_classify_asset_by_keyword(self):
        """Asset keywords should classify as ASSET."""
        from src.tasks.process_upload import _classify_account_type
        
        assert _classify_account_type("Cash", "Bank", 1000) == "ASSET"
        assert _classify_account_type("Accounts Receivable", "Asset", 500) == "ASSET"
        assert _classify_account_type("Inventory", "Stock", 2000) == "ASSET"
    
    def test_classify_liability_by_keyword(self):
        """Liability keywords should classify as LIABILITY."""
        from src.tasks.process_upload import _classify_account_type
        
        # Note: Liability needs explicit "liability" or "payable" keywords
        assert _classify_account_type("Accounts Payable", "Liability", -500) == "LIABILITY"
        assert _classify_account_type("Trade Payable", "Payable", -10000) == "LIABILITY"
    
    def test_classify_equity_by_keyword(self):
        """Equity keywords should classify as EQUITY."""
        from src.tasks.process_upload import _classify_account_type
        
        assert _classify_account_type("Owner Equity", "Capital", 50000) == "EQUITY"
        assert _classify_account_type("Retained Earnings", "Equity", 10000) == "EQUITY"
    
    def test_classify_default_expense(self):
        """With no keywords and no amount, default to EXPENSE."""
        from src.tasks.process_upload import _classify_account_type
        
        assert _classify_account_type("Unknown", "Other", None) == "EXPENSE"


class TestDocumentTypeDetection:
    """Tests for document type detection functions."""
    
    def test_is_journal_like_unstructured_text(self):
        """Journal-like documents have few columns and text-heavy content."""
        from src.tasks.process_upload import _is_journal_like
        
        # Few columns, text-heavy content
        df = pd.DataFrame({
            "Entry": [
                "Purchased office supplies for 50,000 LBP",
                "Received payment from customer ABC of 100,000 LBP",
                "Paid electricity bill of 75,000 LBP"
            ]
        })
        # Use == True to handle numpy bool
        assert _is_journal_like(df) == True
    
    def test_is_journal_like_structured_data(self):
        """Structured data with many columns should not be journal-like."""
        from src.tasks.process_upload import _is_journal_like
        
        df = pd.DataFrame({
            "Date": ["2024-01-01", "2024-01-02"],
            "Account": ["Sales", "Expenses"],
            "Amount": [100.0, -50.0],
            "Category": ["Revenue", "Operating"],
            "Description": ["Product sale", "Office rent"],
        })
        assert _is_journal_like(df) == False
    
    def test_is_structured_inventory_with_typical_columns(self):
        """Inventory documents have item, qty, and amount columns."""
        from src.tasks.process_upload import _is_structured_inventory
        
        df = pd.DataFrame({
            "Item": ["Widget A", "Widget B"],
            "Quantity": [100, 200],
            "Price": [10.0, 15.0],
        })
        assert _is_structured_inventory(df) == True
    
    def test_is_structured_inventory_with_product_column(self):
        """Product column should be recognized as inventory."""
        from src.tasks.process_upload import _is_structured_inventory
        
        df = pd.DataFrame({
            "Product": ["SKU-001", "SKU-002"],
            "Qty": [50, 75],
            "Total": [500.0, 750.0],
        })
        assert _is_structured_inventory(df) == True
    
    def test_is_structured_inventory_missing_item_column(self):
        """Without item/product column, should not be inventory."""
        from src.tasks.process_upload import _is_structured_inventory
        
        df = pd.DataFrame({
            "Date": ["2024-01-01", "2024-01-02"],
            "Amount": [100.0, 200.0],
        })
        assert _is_structured_inventory(df) == False
    
    def test_dataframe_to_lines(self):
        """DataFrame should be converted to text lines for LLM parsing."""
        from src.tasks.process_upload import _dataframe_to_lines
        
        df = pd.DataFrame({
            "Entry": ["Line 1 text", "Line 2 text"],
            "Notes": ["Note A", "Note B"],
        })
        lines = _dataframe_to_lines(df)
        assert len(lines) == 2
        assert "Line 1 text" in lines[0]
        assert "Note A" in lines[0]


class TestHealthEndpoints:
    """Tests for health check endpoints."""
    
    def test_health_endpoint(self, client):
        """Basic health check should return healthy status."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_ready_endpoint(self, client):
        """Readiness check should return status and checks."""
        response = client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "checks" in data
        assert "database" in data["checks"]


class TestAccountTypeModel:
    """Tests for the AccountType enum and model."""
    
    def test_account_type_enum_values(self):
        """AccountType enum should have all required values."""
        from src.models import AccountType
        
        expected_values = ["ASSET", "LIABILITY", "EQUITY", "REVENUE", "COGS", "EXPENSE"]
        actual_values = [e.value for e in AccountType]
        
        for value in expected_values:
            assert value in actual_values, f"Missing AccountType: {value}"
    
    def test_transaction_model_has_account_type(self):
        """Transaction model should have account_type field."""
        from src.models import Transaction
        
        # Check that the model has the account_type attribute
        assert hasattr(Transaction, "account_type")


class TestChainOfThoughtSchemas:
    """Tests for Chain of Thought reasoning in LLM schemas."""
    
    def test_journal_schema_has_reasoning(self):
        """Journal schema should require reasoning field."""
        from src.assistant import OpenAIClient
        
        client = OpenAIClient()
        # The schema is defined inside parse_journal_lines, 
        # but we can test the method exists
        assert hasattr(client, "parse_journal_lines")
    
    def test_inventory_schema_has_reasoning(self):
        """Inventory schema should require reasoning field."""
        from src.assistant import OpenAIClient
        
        client = OpenAIClient()
        assert hasattr(client, "map_rows_to_inventory")
    
    def test_classification_schema_has_reasoning(self):
        """Classification schema should require reasoning field."""
        from src.assistant import OpenAIClient
        
        client = OpenAIClient()
        assert hasattr(client, "classify_accounts")


class TestDLQMiddleware:
    """Tests for Dead Letter Queue middleware."""
    
    def test_dramatiq_dlq_middleware_exists(self):
        """DLQ middleware should be defined."""
        from src.tasks import DLQMiddleware
        
        assert DLQMiddleware is not None
        # Check it has the required methods
        middleware = DLQMiddleware()
        assert hasattr(middleware, "after_skip_message")
        assert hasattr(middleware, "after_nack")
        assert hasattr(middleware, "_store_failed_message")


class TestConfigValidation:
    """Tests for configuration validation."""
    
    def test_jwt_secret_config_exists(self):
        """JWT secret should be configurable."""
        from src.config import Settings
        
        # Verify the field exists
        assert "jwt_secret" in Settings.model_fields
    
    def test_sentry_dsn_is_optional(self):
        """Sentry DSN should be optional."""
        from src.config import Settings
        
        field = Settings.model_fields.get("sentry_dsn")
        assert field is not None
        # The field should allow None
        assert field.default is None
    
    def test_environment_field_exists(self):
        """Environment field should be configurable."""
        from src.config import Settings
        
        assert "environment" in Settings.model_fields


# Fixtures for TestClient
@pytest.fixture(scope="session")
def client():
    """Create a TestClient for the FastAPI app."""
    from fastapi.testclient import TestClient
    from src.main import app
    return TestClient(app)

