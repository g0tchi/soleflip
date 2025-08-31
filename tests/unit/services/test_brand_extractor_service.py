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
