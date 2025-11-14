"""
Unit tests for domain exceptions
Testing exception hierarchy and mapping functions for 100% coverage
"""

from shared.exceptions.domain_exceptions import (
    COMMON_EXCEPTION_MAPPINGS,
    AuthenticationException,
    BatchProcessingException,
    BusinessLogicException,
    ConfigurationException,
    DatabaseConnectionException,
    DatabaseOperationException,
    DataProcessingException,
    DomainException,
    DuplicateRecordException,
    ExternalApiException,
    FileFormatException,
    ImportException,
    InsufficientInventoryException,
    InvalidPriceException,
    OrderProcessingException,
    ParseException,
    RateLimitException,
    RecordNotFoundException,
    ServiceIntegrationException,
    ServiceUnavailableException,
    StockXApiException,
    TransformationException,
    ValidationException,
    create_specific_exception,
    map_exception_by_message,
)


class TestDomainException:
    """Test base DomainException"""

    def test_domain_exception_basic(self):
        """Test basic domain exception"""
        exception = DomainException("Test error")

        assert str(exception) == "Test error"
        assert exception.message == "Test error"
        assert exception.details == {}

    def test_domain_exception_with_details(self):
        """Test domain exception with details"""
        details = {"code": "E001", "field": "email"}
        exception = DomainException("Validation failed", details)

        assert exception.message == "Validation failed"
        assert exception.details == details


class TestExternalApiException:
    """Test ExternalApiException and status code handling"""

    def test_external_api_exception_basic(self):
        """Test external API exception without status code"""
        exception = ExternalApiException("API error")

        assert exception.message == "API error"
        assert exception.status_code is None
        assert exception.details == {}

    def test_external_api_exception_with_status_code(self):
        """Test external API exception with status code"""
        details = {"endpoint": "/api/v1/orders"}
        exception = ExternalApiException("Rate limit exceeded", 429, details)

        assert exception.message == "Rate limit exceeded"
        assert exception.status_code == 429
        assert exception.details == details

    def test_external_api_exception_inheritance(self):
        """Test that ExternalApiException inherits from DomainException"""
        exception = ExternalApiException("API error")
        assert isinstance(exception, DomainException)


class TestDatabaseExceptions:
    """Test database-related exceptions"""

    def test_database_operation_exception(self):
        """Test database operation exception"""
        exception = DatabaseOperationException("Database error")
        assert isinstance(exception, DomainException)
        assert str(exception) == "Database error"

    def test_record_not_found_exception(self):
        """Test record not found exception"""
        exception = RecordNotFoundException("User not found")
        assert isinstance(exception, DatabaseOperationException)
        assert str(exception) == "User not found"

    def test_duplicate_record_exception(self):
        """Test duplicate record exception"""
        exception = DuplicateRecordException("Email already exists")
        assert isinstance(exception, DatabaseOperationException)

    def test_database_connection_exception(self):
        """Test database connection exception"""
        exception = DatabaseConnectionException("Connection timeout")
        assert isinstance(exception, DatabaseOperationException)


class TestApiExceptions:
    """Test API-related exceptions"""

    def test_stockx_api_exception(self):
        """Test StockX API exception"""
        exception = StockXApiException("StockX API error", 500)
        assert isinstance(exception, ExternalApiException)
        assert exception.status_code == 500

    def test_authentication_exception(self):
        """Test authentication exception"""
        exception = AuthenticationException("Invalid token", 401)
        assert isinstance(exception, ExternalApiException)
        assert exception.status_code == 401

    def test_rate_limit_exception(self):
        """Test rate limit exception"""
        exception = RateLimitException("Too many requests", 429)
        assert isinstance(exception, ExternalApiException)
        assert exception.status_code == 429


class TestDataProcessingExceptions:
    """Test data processing exceptions"""

    def test_data_processing_exception(self):
        """Test base data processing exception"""
        exception = DataProcessingException("Processing failed")
        assert isinstance(exception, DomainException)

    def test_validation_exception(self):
        """Test validation exception"""
        exception = ValidationException("Invalid email format")
        assert isinstance(exception, DataProcessingException)

    def test_transformation_exception(self):
        """Test transformation exception"""
        exception = TransformationException("Failed to transform data")
        assert isinstance(exception, DataProcessingException)

    def test_parse_exception(self):
        """Test parse exception"""
        exception = ParseException("Invalid JSON format")
        assert isinstance(exception, DataProcessingException)


class TestBusinessLogicExceptions:
    """Test business logic exceptions"""

    def test_business_logic_exception(self):
        """Test base business logic exception"""
        exception = BusinessLogicException("Business rule violated")
        assert isinstance(exception, DomainException)

    def test_insufficient_inventory_exception(self):
        """Test insufficient inventory exception"""
        exception = InsufficientInventoryException("Not enough stock")
        assert isinstance(exception, BusinessLogicException)

    def test_invalid_price_exception(self):
        """Test invalid price exception"""
        exception = InvalidPriceException("Price cannot be negative")
        assert isinstance(exception, BusinessLogicException)

    def test_order_processing_exception(self):
        """Test order processing exception"""
        exception = OrderProcessingException("Failed to process order")
        assert isinstance(exception, BusinessLogicException)


class TestImportExceptions:
    """Test import/export exceptions"""

    def test_import_exception(self):
        """Test base import exception"""
        exception = ImportException("Import failed")
        assert isinstance(exception, DomainException)

    def test_file_format_exception(self):
        """Test file format exception"""
        exception = FileFormatException("Unsupported file type")
        assert isinstance(exception, ImportException)

    def test_batch_processing_exception(self):
        """Test batch processing exception"""
        exception = BatchProcessingException("Batch processing failed")
        assert isinstance(exception, ImportException)


class TestServiceIntegrationExceptions:
    """Test service integration exceptions"""

    def test_service_integration_exception(self):
        """Test base service integration exception"""
        exception = ServiceIntegrationException("Service error")
        assert isinstance(exception, DomainException)

    def test_service_unavailable_exception(self):
        """Test service unavailable exception"""
        exception = ServiceUnavailableException("Service is down")
        assert isinstance(exception, ServiceIntegrationException)

    def test_configuration_exception(self):
        """Test configuration exception"""
        exception = ConfigurationException("Invalid configuration")
        assert isinstance(exception, ServiceIntegrationException)


class TestExceptionMappings:
    """Test exception mapping functionality"""

    def test_common_exception_mappings_exist(self):
        """Test that common exception mappings dictionary exists"""
        assert isinstance(COMMON_EXCEPTION_MAPPINGS, dict)
        assert len(COMMON_EXCEPTION_MAPPINGS) > 0

    def test_map_exception_by_message_database_connection(self):
        """Test mapping database connection errors"""
        result = map_exception_by_message("Database connection timeout")
        assert result == DatabaseConnectionException

        result = map_exception_by_message("Connection failed")
        assert result == DatabaseConnectionException

    def test_map_exception_by_message_not_found(self):
        """Test mapping not found errors"""
        result = map_exception_by_message("User not found")
        assert result == RecordNotFoundException

    def test_map_exception_by_message_duplicate(self):
        """Test mapping duplicate errors"""
        result = map_exception_by_message("Duplicate key violation")
        assert result == DuplicateRecordException

    def test_map_exception_by_message_authentication(self):
        """Test mapping authentication errors"""
        result = map_exception_by_message("401 Unauthorized")
        assert result == AuthenticationException

        result = map_exception_by_message("403 Forbidden")
        assert result == AuthenticationException

        result = map_exception_by_message("Unauthorized access")
        assert result == AuthenticationException

    def test_map_exception_by_message_rate_limit(self):
        """Test mapping rate limit errors"""
        result = map_exception_by_message("429 Too Many Requests")
        assert result == RateLimitException

        result = map_exception_by_message("Rate limit exceeded")
        assert result == RateLimitException

    def test_map_exception_by_message_validation(self):
        """Test mapping validation errors"""
        result = map_exception_by_message("Validation error occurred")
        assert result == ValidationException

    def test_map_exception_by_message_parse_error(self):
        """Test mapping parse errors"""
        result = map_exception_by_message("Failed to parse JSON")
        assert result == ParseException

    def test_map_exception_by_message_transform_error(self):
        """Test mapping transformation errors"""
        result = map_exception_by_message("Transform operation failed")
        assert result == TransformationException

    def test_map_exception_by_message_format_error(self):
        """Test mapping format errors"""
        result = map_exception_by_message("Invalid format detected")
        assert result == FileFormatException

    def test_map_exception_by_message_business_logic(self):
        """Test mapping business logic errors"""
        result = map_exception_by_message("Insufficient inventory available")
        assert result == InsufficientInventoryException

        result = map_exception_by_message("Price validation failed")
        assert result == InvalidPriceException

        result = map_exception_by_message("Order processing error")
        assert result == OrderProcessingException

    def test_map_exception_by_message_unknown_error(self):
        """Test mapping unknown errors falls back to DomainException"""
        result = map_exception_by_message("Some random error")
        assert result == DomainException

    def test_map_exception_by_message_case_insensitive(self):
        """Test that mapping is case insensitive"""
        result = map_exception_by_message("CONNECTION TIMEOUT")
        assert result == DatabaseConnectionException

        result = map_exception_by_message("Validation ERROR")
        assert result == ValidationException


class TestCreateSpecificException:
    """Test create_specific_exception function"""

    def test_create_specific_exception_basic(self):
        """Test creating specific exception from generic exception"""
        original = ValueError("Invalid value provided")

        result = create_specific_exception(original)

        assert isinstance(result, DomainException)
        assert result.message == "Invalid value provided"
        assert result.details["original_exception"] == "ValueError"
        assert result.details["original_message"] == "Invalid value provided"
        assert result.details["context"] == ""

    def test_create_specific_exception_with_context(self):
        """Test creating specific exception with context"""
        original = ConnectionError("Database connection failed")
        context = "user_service.create_user"

        result = create_specific_exception(original, context)

        assert isinstance(result, DatabaseConnectionException)
        assert result.message == "user_service.create_user: Database connection failed"
        assert result.details["context"] == context
        assert result.details["original_exception"] == "ConnectionError"

    def test_create_specific_exception_validation_error(self):
        """Test creating specific exception for validation error"""
        original = Exception("Validation failed for email field")

        result = create_specific_exception(original)

        assert isinstance(result, ValidationException)
        assert "Validation failed" in result.message

    def test_create_specific_exception_not_found_error(self):
        """Test creating specific exception for not found error"""
        original = KeyError("User not found in database")

        result = create_specific_exception(original)

        assert isinstance(result, RecordNotFoundException)
        assert "not found" in result.message.lower()

    def test_create_specific_exception_rate_limit_error(self):
        """Test creating specific exception for rate limit error"""
        original = Exception("429 Rate limit exceeded")
        context = "stockx_api.get_orders"

        result = create_specific_exception(original, context)

        assert isinstance(result, RateLimitException)
        assert context in result.message
        assert result.details["context"] == context

    def test_create_specific_exception_details_structure(self):
        """Test that created exception has proper details structure"""
        original = FileNotFoundError("Config file not found")
        context = "app_startup"

        result = create_specific_exception(original, context)

        expected_details = {
            "original_exception": "FileNotFoundError",
            "original_message": "Config file not found",
            "context": context,
        }

        assert result.details == expected_details
