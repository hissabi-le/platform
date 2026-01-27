"""Tests for Accounts Receivable / Payable feature."""
from __future__ import annotations

from decimal import Decimal

import pytest

from src.excel_cleaner import parse_payment_status


class TestPaymentStatusParsing:
    """Test parse_payment_status function - pure unit tests, no DB needed."""
    
    def test_default_is_paid(self):
        """Empty/None values default to 'paid'."""
        assert parse_payment_status(None) == "paid"
        assert parse_payment_status("") == "paid"
        assert parse_payment_status("   ") == "paid"
    
    def test_paid_indicators(self):
        """Test various 'paid' indicators in different languages."""
        assert parse_payment_status("paid") == "paid"
        assert parse_payment_status("PAID") == "paid"
        assert parse_payment_status("Settled") == "paid"
        assert parse_payment_status("yes") == "paid"
        assert parse_payment_status("true") == "paid"
        assert parse_payment_status("1") == "paid"
        assert parse_payment_status("payé") == "paid"
        assert parse_payment_status("oui") == "paid"
        assert parse_payment_status("مدفوع") == "paid"
    
    def test_unpaid_indicators(self):
        """Test various 'unpaid' indicators in different languages."""
        assert parse_payment_status("unpaid") == "unpaid"
        assert parse_payment_status("UNPAID") == "unpaid"
        assert parse_payment_status("outstanding") == "unpaid"
        assert parse_payment_status("due") == "unpaid"
        assert parse_payment_status("pending") == "unpaid"
        assert parse_payment_status("no") == "unpaid"
        assert parse_payment_status("false") == "unpaid"
        assert parse_payment_status("0") == "unpaid"
        assert parse_payment_status("impayé") == "unpaid"
        assert parse_payment_status("non") == "unpaid"
        assert parse_payment_status("غير مدفوع") == "unpaid"
    
    def test_not_paid_matches_unpaid(self):
        """'Not paid' should match unpaid, not 'paid'."""
        assert parse_payment_status("not paid") == "unpaid"
        assert parse_payment_status("NOT PAID") == "unpaid"


class TestPaymentStatusModel:
    """Test that models have payment_status field with correct default."""
    
    def test_transaction_has_payment_status(self):
        """Transaction model should have payment_status with default 'paid'."""
        from src.models import Transaction
        
        # Check column exists
        assert hasattr(Transaction, 'payment_status')
        assert hasattr(Transaction, 'payment_date')
    
    def test_journal_entry_has_payment_status(self):
        """JournalEntry model should have payment_status with default 'paid'."""
        from src.models import JournalEntry
        
        # Check column exists
        assert hasattr(JournalEntry, 'payment_status')
        assert hasattr(JournalEntry, 'payment_date')


class TestPaymentStatusSchema:
    """Test that schemas include payment_status field."""
    
    def test_transaction_schema_has_payment_status(self):
        """TransactionBase schema should have payment_status field."""
        from src.schemas import TransactionBase
        
        schema_fields = TransactionBase.model_fields
        assert 'payment_status' in schema_fields
        assert 'payment_date' in schema_fields
    
    def test_journal_entry_schema_has_payment_status(self):
        """JournalEntryBase schema should have payment_status field."""
        from src.schemas import JournalEntryBase
        
        schema_fields = JournalEntryBase.model_fields
        assert 'payment_status' in schema_fields
        assert 'payment_date' in schema_fields
    
    def test_payment_status_default_is_paid(self):
        """Default payment_status should be 'paid'."""
        from src.schemas import JournalEntryBase
        
        # Create a minimal entry
        entry = JournalEntryBase(
            entry_type="revenue",
            total=Decimal("100.00"),
        )
        assert entry.payment_status == "paid"


class TestARAPEndpointsExist:
    """Test that AR/AP endpoints are registered."""
    
    def test_receivables_endpoint_exists(self):
        """Receivables endpoint should be registered."""
        from src.main import app
        
        routes = [r.path for r in app.routes]
        assert "/analytics/receivables" in routes
    
    def test_payables_endpoint_exists(self):
        """Payables endpoint should be registered."""
        from src.main import app
        
        routes = [r.path for r in app.routes]
        assert "/analytics/payables" in routes
    
    def test_features_endpoint_exists(self):
        """Features endpoint should be registered."""
        from src.main import app
        
        routes = [r.path for r in app.routes]
        assert "/settings/features" in routes
    
    def test_receivables_list_endpoint_exists(self):
        """Receivables list endpoint should be registered."""
        from src.main import app
        
        routes = [r.path for r in app.routes]
        assert "/analytics/receivables/list" in routes
    
    def test_payables_list_endpoint_exists(self):
        """Payables list endpoint should be registered."""
        from src.main import app
        
        routes = [r.path for r in app.routes]
        assert "/analytics/payables/list" in routes
    
    def test_transaction_payment_toggle_endpoint_exists(self):
        """Transaction payment status toggle endpoint should be registered."""
        from src.main import app
        
        routes = [r.path for r in app.routes]
        assert "/analytics/transaction/{txn_id}/payment-status" in routes
