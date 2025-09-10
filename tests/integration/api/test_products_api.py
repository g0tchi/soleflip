from unittest.mock import AsyncMock

import pytest

from domains.integration.services.stockx_service import StockXService
from tests.fixtures import async_client


@pytest.mark.api
@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_stockx_product_details_success(
    async_client, api_helper, mock_external_services, override_get_db
):
    """
    Test successful retrieval of product details from StockX via our API endpoint.
    """
    product_id = "test-product-123"
    mock_response_data = {
        "productId": product_id,
        "title": "Test Product",
        "brand": "Test Brand",
        "styleId": "TP-123",
    }

    # Use the pre-configured mock from fixtures
    mock_external_services["stockx"].get_product_details.return_value = mock_response_data

    # Make the request using the async client
    response_data = await api_helper.get_json(f"/api/v1/products/{product_id}/stockx-details")

    # Assertions using the API helper
    assert response_data == mock_response_data
    mock_external_services["stockx"].get_product_details.assert_called_once_with(product_id)


@pytest.mark.api
@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_stockx_product_details_not_found(
    async_client, api_helper, mock_external_services, override_get_db
):
    """
    Test the case where the product is not found on StockX.
    """
    product_id = "non-existent-product"

    # Configure mock to return None
    mock_external_services["stockx"].get_product_details.return_value = None

    # Make the request expecting 404
    response = await async_client.get(f"/api/v1/products/{product_id}/stockx-details")

    # Assertions
    assert response.status_code == 404
    response_data = response.json()
    assert "error" in response_data
    assert (
        response_data["error"]["message"] == f"Product with ID '{product_id}' not found on StockX."
    )
    mock_external_services["stockx"].get_product_details.assert_called_once_with(product_id)


@pytest.mark.api
@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_stockx_products_success(
    async_client, api_helper, mock_external_services, override_get_db
):
    """
    Test successful search of products from StockX via our API endpoint.
    """
    search_query = "jordan 1"
    mock_response_data = {
        "count": 1,
        "products": [{"productId": "search-result-123", "title": "Air Jordan 1"}],
    }

    # Configure mock service
    mock_external_services["stockx"].search_stockx_catalog.return_value = mock_response_data

    # Make the request using helper
    response_data = await api_helper.get_json(
        "/api/v1/products/search-stockx",
        params={"query": search_query, "pageNumber": 1, "pageSize": 5},
    )

    # Assertions
    assert response_data == mock_response_data
    mock_external_services["stockx"].search_stockx_catalog.assert_called_once_with(
        query=search_query, page=1, page_size=5
    )


@pytest.mark.usefixtures("override_db_dependency")
@pytest.mark.asyncio
async def test_search_stockx_products_service_error(mocker):
    """
    Test the case where the search service returns an error (None).
    """
    search_query = "error-query"

    # Mock the service method to return None
    mocker.patch.object(
        StockXService, "search_stockx_catalog", new_callable=AsyncMock, return_value=None
    )

    # Make the request to our API
    response = await async_client.get(f"/api/v1/products/search-stockx?query={search_query}")

    # Assertions
    assert response.status_code == 502
    response_data = response.json()
    assert "error" in response_data
    assert response_data["error"]["message"] == "Failed to retrieve search results from StockX."
    StockXService.search_stockx_catalog.assert_called_once_with(
        query=search_query, page=1, page_size=10
    )


@pytest.mark.usefixtures("override_db_dependency")
@pytest.mark.asyncio
async def test_get_market_data_success(mocker):
    """
    Test successful retrieval of market data from StockX.
    """
    product_id = "product-abc-789"
    mock_response_data = [{"variantId": "v1", "lowestAskAmount": "150", "highestBidAmount": "140"}]

    mocker.patch.object(
        StockXService,
        "get_market_data_from_stockx",
        new_callable=AsyncMock,
        return_value=mock_response_data,
    )

    # Test without currency
    response = await async_client.get(f"/api/v1/products/{product_id}/stockx-market-data")
    assert response.status_code == 200
    assert response.json() == mock_response_data
    StockXService.get_market_data_from_stockx.assert_called_once_with(
        product_id=product_id, currency_code=None
    )

    # Test with currency
    StockXService.get_market_data_from_stockx.reset_mock()
    response = await async_client.get(f"/api/v1/products/{product_id}/stockx-market-data?currencyCode=EUR")
    assert response.status_code == 200
    assert response.json() == mock_response_data
    StockXService.get_market_data_from_stockx.assert_called_once_with(
        product_id=product_id, currency_code="EUR"
    )


@pytest.mark.usefixtures("override_db_dependency")
@pytest.mark.asyncio
async def test_get_market_data_not_found(mocker):
    """
    Test 404 case for market data when product is not found on StockX.
    """
    product_id = "not-real-product"

    mocker.patch.object(
        StockXService, "get_market_data_from_stockx", new_callable=AsyncMock, return_value=None
    )

    response = await async_client.get(f"/api/v1/products/{product_id}/stockx-market-data")

    assert response.status_code == 404
    response_data = response.json()
    assert "error" in response_data
    assert (
        response_data["error"]["message"] == f"Product with ID '{product_id}' not found on StockX."
    )
