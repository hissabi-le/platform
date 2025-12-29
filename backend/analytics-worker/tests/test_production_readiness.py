"""
Tests for analytics worker production readiness improvements.

This test suite covers:
1. PnL Aggregator account_type classification
2. Transaction repository schema changes
3. Metrics module
4. Cache hygiene (no local fallback)
5. Dead Letter Queue configuration
"""
import os
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock

# Set test environment
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("ENVIRONMENT", "development")


class TestPnLAggregator:
    """Tests for the refactored PnL Aggregator."""
    
    def test_consume_revenue(self):
        """Revenue transactions should increase revenue_total."""
        from analytics_worker.services.analytics import PnLAggregator
        from analytics_worker.repositories.transactions import TransactionRow
        
        aggregator = PnLAggregator()
        
        row = TransactionRow(
            txn_date=datetime(2024, 1, 15),
            account_code="SALES",
            category="Product Sales",
            amount=1000.0,
            description="Sale to customer",
            account_type="REVENUE",
        )
        
        aggregator.consume(row)
        
        assert aggregator.revenue_total == 1000.0
        assert aggregator.cogs_total == 0.0
        assert len(aggregator.expenses) == 0
        assert aggregator.rows_processed == 1
    
    def test_consume_cogs(self):
        """COGS transactions should increase cogs_total."""
        from analytics_worker.services.analytics import PnLAggregator
        from analytics_worker.repositories.transactions import TransactionRow
        
        aggregator = PnLAggregator()
        
        row = TransactionRow(
            txn_date=datetime(2024, 1, 15),
            account_code="COGS",
            category="Cost of Goods Sold",
            amount=-500.0,
            description="Inventory cost",
            account_type="COGS",
        )
        
        aggregator.consume(row)
        
        assert aggregator.revenue_total == 0.0
        assert aggregator.cogs_total == 500.0  # abs value
        assert aggregator.rows_processed == 1
    
    def test_consume_expense(self):
        """Expense transactions should be added to expenses dict."""
        from analytics_worker.services.analytics import PnLAggregator
        from analytics_worker.repositories.transactions import TransactionRow
        
        aggregator = PnLAggregator()
        
        row = TransactionRow(
            txn_date=datetime(2024, 1, 15),
            account_code="RENT",
            category="Office Rent",
            amount=-2000.0,
            description="Monthly rent",
            account_type="EXPENSE",
        )
        
        aggregator.consume(row)
        
        assert aggregator.revenue_total == 0.0
        assert aggregator.cogs_total == 0.0
        assert aggregator.expenses["Office Rent"] == 2000.0  # abs value
    
    def test_consume_asset_no_pnl_impact(self):
        """Asset transactions should not affect P&L totals."""
        from analytics_worker.services.analytics import PnLAggregator
        from analytics_worker.repositories.transactions import TransactionRow
        
        aggregator = PnLAggregator()
        
        row = TransactionRow(
            txn_date=datetime(2024, 1, 15),
            account_code="CASH",
            category="Bank Account",
            amount=5000.0,
            description="Cash deposit",
            account_type="ASSET",
        )
        
        aggregator.consume(row)
        
        # Assets don't directly affect P&L
        assert aggregator.revenue_total == 0.0
        assert aggregator.cogs_total == 0.0
        assert len(aggregator.expenses) == 0
        assert aggregator.rows_processed == 1
    
    def test_consume_tracks_dates(self):
        """Aggregator should track first and latest transaction dates."""
        from analytics_worker.services.analytics import PnLAggregator
        from analytics_worker.repositories.transactions import TransactionRow
        
        aggregator = PnLAggregator()
        
        row1 = TransactionRow(
            txn_date=datetime(2024, 1, 15),
            account_code="SALES",
            category="Sales",
            amount=100.0,
            description="",
            account_type="REVENUE",
        )
        
        row2 = TransactionRow(
            txn_date=datetime(2024, 3, 20),
            account_code="SALES",
            category="Sales",
            amount=200.0,
            description="",
            account_type="REVENUE",
        )
        
        aggregator.consume(row1)
        aggregator.consume(row2)
        
        assert aggregator.first_txn == datetime(2024, 1, 15)
        assert aggregator.latest_txn == datetime(2024, 3, 20)
    
    def test_snapshot_returns_dict(self):
        """snapshot() should return aggregated data as dict."""
        from analytics_worker.services.analytics import PnLAggregator
        
        aggregator = PnLAggregator()
        snapshot = aggregator.snapshot()
        
        assert isinstance(snapshot, dict)
        assert "revenue" in snapshot
        assert "cogs" in snapshot
        assert "expenses" in snapshot


class TestTransactionRow:
    """Tests for TransactionRow dataclass."""
    
    def test_transaction_row_has_account_type(self):
        """TransactionRow should include account_type field."""
        from analytics_worker.repositories.transactions import TransactionRow
        import dataclasses
        
        fields = {f.name for f in dataclasses.fields(TransactionRow)}
        assert "account_type" in fields
    
    def test_from_record_extracts_account_type(self):
        """from_record should extract account_type from database row."""
        from analytics_worker.repositories.transactions import TransactionRow
        
        # Mock a database record
        class MockRecord:
            txn_date = datetime(2024, 1, 15)
            account_code = "SALES"
            category = "Sales"
            amount = 100.0
            description = "Test"
            account_type = "REVENUE"
        
        row = TransactionRow.from_record(MockRecord())
        
        assert row.account_type == "REVENUE"
    
    def test_from_record_defaults_to_expense(self):
        """from_record should default to EXPENSE if account_type is None."""
        from analytics_worker.repositories.transactions import TransactionRow
        
        class MockRecord:
            txn_date = datetime(2024, 1, 15)
            account_code = "UNKNOWN"
            category = "Unknown"
            amount = -50.0
            description = "Test"
            account_type = None
        
        row = TransactionRow.from_record(MockRecord())
        
        assert row.account_type == "EXPENSE"


class TestMetricsModule:
    """Tests for the Prometheus metrics module."""
    
    def test_track_job_duration_as_context_manager(self):
        """track_job_duration should work as a context manager."""
        from analytics_worker.metrics import track_job_duration
        
        # Should not raise
        with track_job_duration(1, "1m"):
            x = 1 + 1
        
        assert x == 2
    
    def test_record_rows_processed_callable(self):
        """record_rows_processed should be callable."""
        from analytics_worker.metrics import record_rows_processed
        
        # Should not raise
        record_rows_processed(1, 100)
    
    def test_get_metrics_returns_bytes(self):
        """get_metrics should return bytes for Prometheus format."""
        from analytics_worker.metrics import get_metrics
        
        result = get_metrics()
        assert isinstance(result, bytes)


class TestAnalyticsCache:
    """Tests for AnalyticsCache changes."""
    
    def test_cache_has_no_local_attribute(self):
        """AnalyticsCache should not have _local attribute."""
        from analytics_worker.cache import AnalyticsCache
        
        cache = AnalyticsCache(ttl_seconds=900)
        
        # The local fallback should be removed
        assert not hasattr(cache, "_local")
        assert not hasattr(cache, "_local_lock")
    
    @pytest.mark.asyncio
    async def test_cache_get_returns_none_when_redis_unavailable(self):
        """Cache should return None when Redis is unavailable."""
        from analytics_worker.cache import AnalyticsCache
        
        cache = AnalyticsCache(ttl_seconds=900)
        
        # With mocked Redis client returning None
        with patch("analytics_worker.cache.redis_client") as mock_redis:
            mock_redis.get = AsyncMock(return_value=None)
            
            result = await cache.get(1, "1m")
            
            # Should return None, not use local fallback
            assert result is None


class TestCeleryDLQConfiguration:
    """Tests for Celery Dead Letter Queue configuration."""
    
    def test_celery_config_has_task_acks_late(self):
        """Celery should be configured with task_acks_late=True."""
        from analytics_worker.tasks import celery_app
        
        assert celery_app.conf.task_acks_late is True
    
    def test_celery_config_has_task_reject_on_worker_lost(self):
        """Celery should be configured with task_reject_on_worker_lost=True."""
        from analytics_worker.tasks import celery_app
        
        assert celery_app.conf.task_reject_on_worker_lost is True
    
    def test_celery_config_has_default_queue(self):
        """Celery should have a default queue configured."""
        from analytics_worker.tasks import celery_app
        
        assert celery_app.conf.task_default_queue == "analytics"


class TestConfigEnvironment:
    """Tests for analytics worker configuration."""
    
    def test_settings_has_environment_field(self):
        """Settings should have environment field."""
        from analytics_worker.config import Settings
        
        assert "environment" in Settings.model_fields
    
    def test_settings_has_sentry_dsn_field(self):
        """Settings should have sentry_dsn field."""
        from analytics_worker.config import Settings
        
        assert "sentry_dsn" in Settings.model_fields


class TestAccountTypeConstants:
    """Tests for account type constants."""
    
    def test_all_account_types_defined(self):
        """All account type constants should be defined."""
        from analytics_worker.services.analytics import (
            ACCOUNT_TYPE_REVENUE,
            ACCOUNT_TYPE_COGS,
            ACCOUNT_TYPE_EXPENSE,
            ACCOUNT_TYPE_ASSET,
            ACCOUNT_TYPE_LIABILITY,
            ACCOUNT_TYPE_EQUITY,
        )
        
        assert ACCOUNT_TYPE_REVENUE == "REVENUE"
        assert ACCOUNT_TYPE_COGS == "COGS"
        assert ACCOUNT_TYPE_EXPENSE == "EXPENSE"
        assert ACCOUNT_TYPE_ASSET == "ASSET"
        assert ACCOUNT_TYPE_LIABILITY == "LIABILITY"
        assert ACCOUNT_TYPE_EQUITY == "EQUITY"
