import pytest
from unittest.mock import MagicMock, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

from domains.products.services.brand_service import BrandExtractorService
from shared.database.models import Brand, BrandPattern

@pytest.fixture
def mock_db_session():
    return MagicMock(spec=AsyncSession)

@pytest.mark.asyncio
async def test_load_patterns_loads_from_db_once(mock_db_session):
    """Tests that patterns are loaded from the database only on the first call."""
    service = BrandExtractorService(mock_db_session)

    mock_patterns = [
        BrandPattern(pattern="Nike", brand=Brand(name="Nike")),
        BrandPattern(pattern="Adidas", brand=Brand(name="Adidas"))
    ]

    # Mock the return value of session.execute
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = mock_patterns
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    # First call
    await service.load_patterns()
    assert len(service._patterns) == 2
    mock_db_session.execute.assert_called_once()

    # Second call should not hit the DB again
    await service.load_patterns()
    assert mock_db_session.execute.call_count == 1

@pytest.mark.asyncio
async def test_extract_brand_from_name_finds_match(mock_db_session):
    """Tests that a brand is correctly extracted from a product name."""
    service = BrandExtractorService(mock_db_session)

    # Setup mock patterns
    nike_brand = Brand(name="Nike")
    adidas_brand = Brand(name="Adidas")
    service._patterns = [
        BrandPattern(pattern=r'^Nike', brand=nike_brand, pattern_type='regex'),
        BrandPattern(pattern=r'^Adidas', brand=adidas_brand, pattern_type='regex')
    ]

    product_name = "Nike Air Force 1"
    extracted_brand = await service.extract_brand_from_name(product_name)

    assert extracted_brand is not None
    assert extracted_brand.name == "Nike"

@pytest.mark.asyncio
async def test_extract_brand_from_name_no_match(mock_db_session):
    """Tests that None is returned when no pattern matches."""
    service = BrandExtractorService(mock_db_session)
    service._patterns = [
        BrandPattern(pattern=r'^Nike', brand=Brand(name="Nike"), pattern_type='regex')
    ]

    product_name = "Puma Suede"
    extracted_brand = await service.extract_brand_from_name(product_name)

    assert extracted_brand is None

@pytest.mark.asyncio
async def test_extract_brand_respects_priority(mock_db_session):
    """Tests that patterns are checked in order of priority."""
    service = BrandExtractorService(mock_db_session)

    # Setup mock patterns with different priorities
    jordan_brand = Brand(name="Nike Jordan")
    nike_brand = Brand(name="Nike")

    # Jordan pattern has higher priority (lower number)
    service._patterns = [
        BrandPattern(pattern=r'Jordan', brand=jordan_brand, pattern_type='regex', priority=90),
        BrandPattern(pattern=r'Nike', brand=nike_brand, pattern_type='regex', priority=100)
    ]

    product_name = "Nike Air Jordan 1"
    extracted_brand = await service.extract_brand_from_name(product_name)

    # It should match "Jordan" first because of the higher priority
    assert extracted_brand is not None
    assert extracted_brand.name == "Nike Jordan"

@pytest.mark.asyncio
async def test_extract_brand_handles_empty_product_name(mock_db_session):
    """Tests that an empty product name returns None."""
    service = BrandExtractorService(mock_db_session)

    # Mock the database call to prevent it from actually running
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    extracted_brand = await service.extract_brand_from_name("")
    assert extracted_brand is None

    extracted_brand_none = await service.extract_brand_from_name(None)
    assert extracted_brand_none is None
