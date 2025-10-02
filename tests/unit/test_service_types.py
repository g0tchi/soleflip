"""
Unit tests for service types
Testing service layer types and protocols for 100% coverage
"""

from shared.types.service_types import (
    ServiceResult,
    ServiceResultStatus,
    CacheStrategy,
    NotificationChannel,
    NotificationPriority,
    AuditAction,
    TaskPriority,
    TaskStatus,
    HealthStatus,
    ConfigurationScope
)


class TestServiceResultStatus:
    """Test ServiceResultStatus enum"""

    def test_service_result_status_values(self):
        """Test all service result status values"""
        assert ServiceResultStatus.SUCCESS == "success"
        assert ServiceResultStatus.FAILURE == "failure"
        assert ServiceResultStatus.PARTIAL == "partial"


class TestServiceResult:
    """Test ServiceResult class and all methods"""

    def test_service_result_init_success(self):
        """Test ServiceResult initialization for success case"""
        data = {"id": 123, "name": "Test"}
        metadata = {"request_id": "req-001"}

        result = ServiceResult(
            status=ServiceResultStatus.SUCCESS,
            data=data,
            error=None,
            metadata=metadata
        )

        assert result.status == ServiceResultStatus.SUCCESS
        assert result.data == data
        assert result.error is None
        assert result.metadata == metadata

    def test_service_result_init_failure(self):
        """Test ServiceResult initialization for failure case"""
        error = "Database connection failed"

        result = ServiceResult(
            status=ServiceResultStatus.FAILURE,
            data=None,
            error=error,
            metadata=None
        )

        assert result.status == ServiceResultStatus.FAILURE
        assert result.data is None
        assert result.error == error
        assert result.metadata == {}

    def test_service_result_init_with_empty_metadata(self):
        """Test ServiceResult initialization with None metadata converts to empty dict"""
        result = ServiceResult(
            status=ServiceResultStatus.SUCCESS,
            data="test",
            error=None,
            metadata=None
        )

        assert result.metadata == {}

    def test_service_result_success_factory(self):
        """Test ServiceResult.success() factory method"""
        data = [1, 2, 3]
        metadata = {"source": "database"}

        result = ServiceResult.success(data=data, metadata=metadata)

        assert result.status == ServiceResultStatus.SUCCESS
        assert result.data == data
        assert result.error is None
        assert result.metadata == metadata
        assert result.is_success() is True
        assert result.is_failure() is False
        assert result.is_partial() is False

    def test_service_result_success_factory_without_metadata(self):
        """Test ServiceResult.success() without metadata"""
        data = "success data"

        result = ServiceResult.success(data=data)

        assert result.status == ServiceResultStatus.SUCCESS
        assert result.data == data
        assert result.metadata == {}

    def test_service_result_failure_factory(self):
        """Test ServiceResult.failure() factory method"""
        error = "Validation failed"
        metadata = {"field": "email"}

        result = ServiceResult.failure(error=error, metadata=metadata)

        assert result.status == ServiceResultStatus.FAILURE
        assert result.data is None
        assert result.error == error
        assert result.metadata == metadata
        assert result.is_success() is False
        assert result.is_failure() is True
        assert result.is_partial() is False

    def test_service_result_failure_factory_without_metadata(self):
        """Test ServiceResult.failure() without metadata"""
        error = "Operation failed"

        result = ServiceResult.failure(error=error)

        assert result.status == ServiceResultStatus.FAILURE
        assert result.error == error
        assert result.metadata == {}

    def test_service_result_partial_factory(self):
        """Test ServiceResult.partial() factory method"""
        data = {"processed": 80, "total": 100}
        error = "20 items failed validation"
        metadata = {"batch_id": "batch-001"}

        result = ServiceResult.partial(data=data, error=error, metadata=metadata)

        assert result.status == ServiceResultStatus.PARTIAL
        assert result.data == data
        assert result.error == error
        assert result.metadata == metadata
        assert result.is_success() is False
        assert result.is_failure() is False
        assert result.is_partial() is True

    def test_service_result_partial_factory_without_metadata(self):
        """Test ServiceResult.partial() without metadata"""
        data = {"completed": 5}
        error = "Some items failed"

        result = ServiceResult.partial(data=data, error=error)

        assert result.status == ServiceResultStatus.PARTIAL
        assert result.data == data
        assert result.error == error
        assert result.metadata == {}

    def test_service_result_status_methods(self):
        """Test all status checking methods"""
        # Test success result
        success_result = ServiceResult.success("data")
        assert success_result.is_success() is True
        assert success_result.is_failure() is False
        assert success_result.is_partial() is False

        # Test failure result
        failure_result = ServiceResult.failure("error")
        assert failure_result.is_success() is False
        assert failure_result.is_failure() is True
        assert failure_result.is_partial() is False

        # Test partial result
        partial_result = ServiceResult.partial("data", "error")
        assert partial_result.is_success() is False
        assert partial_result.is_failure() is False
        assert partial_result.is_partial() is True


class TestCacheStrategy:
    """Test CacheStrategy enum"""

    def test_cache_strategy_values(self):
        """Test all cache strategy enum values"""
        assert CacheStrategy.NONE == "none"
        assert CacheStrategy.MEMORY == "memory"
        assert CacheStrategy.REDIS == "redis"
        assert CacheStrategy.DATABASE == "database"


class TestNotificationChannel:
    """Test NotificationChannel enum"""

    def test_notification_channel_values(self):
        """Test all notification channel values"""
        assert NotificationChannel.EMAIL == "email"
        assert NotificationChannel.SMS == "sms"
        assert NotificationChannel.SLACK == "slack"
        assert NotificationChannel.WEBHOOK == "webhook"
        assert NotificationChannel.PUSH == "push"


class TestNotificationPriority:
    """Test NotificationPriority enum"""

    def test_notification_priority_values(self):
        """Test all notification priority values"""
        assert NotificationPriority.LOW == "low"
        assert NotificationPriority.NORMAL == "normal"
        assert NotificationPriority.HIGH == "high"
        assert NotificationPriority.URGENT == "urgent"


class TestAuditAction:
    """Test AuditAction enum"""

    def test_audit_action_values(self):
        """Test all audit action values"""
        assert AuditAction.CREATE == "create"
        assert AuditAction.READ == "read"
        assert AuditAction.UPDATE == "update"
        assert AuditAction.DELETE == "delete"
        assert AuditAction.LOGIN == "login"
        assert AuditAction.LOGOUT == "logout"
        assert AuditAction.EXPORT == "export"
        assert AuditAction.IMPORT == "import"
        assert AuditAction.SYNC == "sync"
        assert AuditAction.CONFIGURE == "configure"


class TestTaskPriority:
    """Test TaskPriority enum"""

    def test_task_priority_values(self):
        """Test all task priority values"""
        assert TaskPriority.LOW == "low"
        assert TaskPriority.NORMAL == "normal"
        assert TaskPriority.HIGH == "high"
        assert TaskPriority.URGENT == "urgent"


class TestTaskStatus:
    """Test TaskStatus enum"""

    def test_task_status_values(self):
        """Test all task status values"""
        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.RUNNING == "running"
        assert TaskStatus.COMPLETED == "completed"
        assert TaskStatus.FAILED == "failed"
        assert TaskStatus.CANCELLED == "cancelled"
        assert TaskStatus.RETRYING == "retrying"


class TestHealthStatus:
    """Test HealthStatus enum"""

    def test_health_status_values(self):
        """Test all health status values"""
        assert HealthStatus.HEALTHY == "healthy"
        assert HealthStatus.DEGRADED == "degraded"
        assert HealthStatus.UNHEALTHY == "unhealthy"


class TestConfigurationScope:
    """Test ConfigurationScope enum"""

    def test_configuration_scope_values(self):
        """Test all configuration scope values"""
        assert ConfigurationScope.GLOBAL == "global"
        assert ConfigurationScope.DOMAIN == "domain"
        assert ConfigurationScope.USER == "user"