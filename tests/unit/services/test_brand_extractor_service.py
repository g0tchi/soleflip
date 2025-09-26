from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from domains.products.services.brand_service import BrandExtractorService
from shared.database.models import Brand, BrandPattern

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_db_session():
    return AsyncMock()


@pytest.fixture
def brand_extractor_service(mock_db_session):
    return BrandExtractorService(db_session=mock_db_session)


async def test_extract_brand_from_name(brand_extractor_service, mock_db_session):
    # Arrange
    product_name = "Nike Air Max 90"
    mock_brand = Brand(id=uuid4(), name="Nike")
    mock_pattern = BrandPattern(pattern=r"Nike", brand=mock_brand, pattern_type="keyword")

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_pattern]
    mock_db_session.execute.return_value = mock_result

    # Act
    brand = await brand_extractor_service.extract_brand_from_name(product_name)

    # Assert
    assert brand is not None
    assert brand.name == "Nike"


async def test_extract_brand_from_name_not_found(brand_extractor_service, mock_db_session):
    # Arrange
    product_name = "Unknown Brand"
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db_session.execute.return_value = mock_result

    # Act
    brand = await brand_extractor_service.extract_brand_from_name(product_name)

    # Assert
    assert brand is None


async def test_extract_brand_from_name_regex_pattern(brand_extractor_service, mock_db_session):
    # Arrange
    product_name = "Air Jordan 1 High"
    mock_brand = Brand(id=uuid4(), name="Jordan")
    mock_pattern = BrandPattern(pattern=r"(Air )?Jordan", brand=mock_brand, pattern_type="regex")

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_pattern]
    mock_db_session.execute.return_value = mock_result

    # Act
    brand = await brand_extractor_service.extract_brand_from_name(product_name)

    # Assert
    assert brand is not None
    assert brand.name == "Jordan"


async def test_extract_brand_from_name_empty_product_name(brand_extractor_service, mock_db_session):
    # Arrange
    product_name = ""

    # Pre-load patterns to avoid database calls
    mock_brand = Brand(id=uuid4(), name="Nike")
    mock_pattern = BrandPattern(pattern="Nike", brand=mock_brand, pattern_type="keyword")
    brand_extractor_service._patterns = [mock_pattern]  # Non-empty list so load_patterns won't be called

    # Act
    brand = await brand_extractor_service.extract_brand_from_name(product_name)

    # Assert
    assert brand is None
    # load_patterns should not be called for empty product names
    mock_db_session.execute.assert_not_called()


async def test_extract_brand_from_name_none_product_name(brand_extractor_service, mock_db_session):
    # Arrange
    product_name = None

    # Pre-load patterns to avoid database calls
    mock_brand = Brand(id=uuid4(), name="Nike")
    mock_pattern = BrandPattern(pattern="Nike", brand=mock_brand, pattern_type="keyword")
    brand_extractor_service._patterns = [mock_pattern]  # Non-empty list so load_patterns won't be called

    # Act
    brand = await brand_extractor_service.extract_brand_from_name(product_name)

    # Assert
    assert brand is None
    # load_patterns should not be called for None product names
    mock_db_session.execute.assert_not_called()


async def test_extract_brand_from_name_invalid_regex_pattern(brand_extractor_service, mock_db_session):
    # Arrange
    product_name = "Nike Air Max"
    mock_brand = Brand(id=uuid4(), name="Nike")
    # Invalid regex pattern that will cause re.error
    mock_pattern = BrandPattern(pattern=r"[invalid", brand=mock_brand, pattern_type="regex")

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_pattern]
    mock_db_session.execute.return_value = mock_result

    # Act
    brand = await brand_extractor_service.extract_brand_from_name(product_name)

    # Assert
    assert brand is None  # Should skip invalid regex and return None


async def test_extract_brand_from_name_loads_patterns_if_empty(brand_extractor_service, mock_db_session):
    # Arrange
    product_name = "Adidas Ultraboost"
    mock_brand = Brand(id=uuid4(), name="Adidas")
    mock_pattern = BrandPattern(pattern="Adidas", brand=mock_brand, pattern_type="keyword")

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_pattern]
    mock_db_session.execute.return_value = mock_result

    # Ensure patterns are empty initially
    brand_extractor_service._patterns = []

    # Act
    brand = await brand_extractor_service.extract_brand_from_name(product_name)

    # Assert
    assert brand is not None
    assert brand.name == "Adidas"
    # Verify that load_patterns was called (patterns should be loaded)
    assert len(brand_extractor_service._patterns) > 0


async def test_load_patterns_skips_if_already_loaded(brand_extractor_service, mock_db_session):
    # Arrange
    existing_pattern = BrandPattern(pattern="Nike", brand=Brand(id=uuid4(), name="Nike"), pattern_type="keyword")
    brand_extractor_service._patterns = [existing_pattern]

    # Act
    await brand_extractor_service.load_patterns()

    # Assert
    # Should not execute database query if patterns already exist
    mock_db_session.execute.assert_not_called()
    assert len(brand_extractor_service._patterns) == 1


async def test_load_patterns_loads_from_database(brand_extractor_service, mock_db_session):
    # Arrange
    mock_brand = Brand(id=uuid4(), name="Nike")
    mock_pattern = BrandPattern(pattern="Nike", brand=mock_brand, pattern_type="keyword")

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_pattern]
    mock_db_session.execute.return_value = mock_result

    # Ensure patterns are empty
    brand_extractor_service._patterns = []

    # Act
    await brand_extractor_service.load_patterns()

    # Assert
    mock_db_session.execute.assert_called_once()
    assert len(brand_extractor_service._patterns) == 1
    assert brand_extractor_service._patterns[0].pattern == "Nike"


async def test_extract_brand_regex_no_match(brand_extractor_service, mock_db_session):
    # Arrange
    product_name = "Reebok Classic"
    mock_brand = Brand(id=uuid4(), name="Nike")
    mock_pattern = BrandPattern(pattern=r"Nike", brand=mock_brand, pattern_type="regex")

    # Pre-load patterns to avoid database calls
    brand_extractor_service._patterns = [mock_pattern]

    # Act
    brand = await brand_extractor_service.extract_brand_from_name(product_name)

    # Assert
    assert brand is None


async def test_extract_brand_keyword_no_match(brand_extractor_service, mock_db_session):
    # Arrange
    product_name = "Reebok Classic"
    mock_brand = Brand(id=uuid4(), name="Nike")
    mock_pattern = BrandPattern(pattern="Nike", brand=mock_brand, pattern_type="keyword")

    # Pre-load patterns to avoid database calls
    brand_extractor_service._patterns = [mock_pattern]

    # Act
    brand = await brand_extractor_service.extract_brand_from_name(product_name)

    # Assert
    assert brand is None


async def test_extract_brand_multiple_patterns_mixed_types(brand_extractor_service, mock_db_session):
    # Arrange
    product_name = "Adidas Ultraboost"
    mock_nike_brand = Brand(id=uuid4(), name="Nike")
    mock_adidas_brand = Brand(id=uuid4(), name="Adidas")

    # First pattern is regex that won't match
    mock_nike_pattern = BrandPattern(pattern=r"Nike", brand=mock_nike_brand, pattern_type="regex")
    # Second pattern is keyword that will match
    mock_adidas_pattern = BrandPattern(pattern="Adidas", brand=mock_adidas_brand, pattern_type="keyword")

    # Pre-load patterns to avoid database calls
    brand_extractor_service._patterns = [mock_nike_pattern, mock_adidas_pattern]

    # Act
    brand = await brand_extractor_service.extract_brand_from_name(product_name)

    # Assert
    assert brand is not None
    assert brand.name == "Adidas"


async def test_extract_brand_unknown_pattern_type(brand_extractor_service, mock_db_session):
    # Arrange
    product_name = "Nike Air Max"
    mock_nike_brand = Brand(id=uuid4(), name="Nike")
    mock_adidas_brand = Brand(id=uuid4(), name="Adidas")

    # Pattern with unknown type (neither "regex" nor "keyword")
    mock_unknown_pattern = BrandPattern(pattern="Nike", brand=mock_nike_brand, pattern_type="unknown")
    # Second pattern is keyword that will match
    mock_adidas_pattern = BrandPattern(pattern="Nike", brand=mock_adidas_brand, pattern_type="keyword")

    # Pre-load patterns to avoid database calls
    brand_extractor_service._patterns = [mock_unknown_pattern, mock_adidas_pattern]

    # Act
    brand = await brand_extractor_service.extract_brand_from_name(product_name)

    # Assert
    assert brand is not None
    assert brand.name == "Adidas"  # Should match the second pattern
