"""
Test the new StockX Catalog API v2 Endpoints

Tests all 5 new endpoints:
1. POST /catalog/enrich-by-sku - Complete enrichment workflow
2. GET /catalog/search - Search catalog
3. GET /catalog/products/{id} - Product details
4. GET /catalog/products/{id}/variants - All variants
5. GET /catalog/products/{id}/variants/{vid}/market-data - Market data
"""

import asyncio
from dotenv import load_dotenv

import httpx

load_dotenv()


async def test_catalog_endpoints():
    """Test all catalog API endpoints"""

    base_url = "http://localhost:8000/api/v1/products"

    # Test data
    test_sku = "JH9768"  # adidas Campus 00s from previous test
    test_size = "38"

    async with httpx.AsyncClient(timeout=30.0) as client:
        print("=" * 80)
        print("Testing StockX Catalog API v2 Endpoints")
        print("=" * 80)

        # Test 1: Search Catalog
        print("\n[1] Testing: GET /catalog/search")
        try:
            response = await client.get(
                f"{base_url}/catalog/search",
                params={"query": test_sku, "page_number": 1, "page_size": 3},
            )
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"Success: Found {data['pagination']['total_results']} results")
                print(f"Products: {len(data['products'])}")
                if data["products"]:
                    product = data["products"][0]
                    print(f"First product: {product.get('title')} ({product.get('productId')})")
                    product_id = product.get("productId")
            else:
                print(f"Error: {response.text}")
                return
        except Exception as e:
            print(f"ERROR: {e}")
            return

        # Test 2: Get Product Details
        print("\n[2] Testing: GET /catalog/products/{product_id}")
        try:
            response = await client.get(f"{base_url}/catalog/products/{product_id}")
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"Success: {data['product'].get('title')}")
                print(f"Brand: {data['product'].get('brand')}")
                print(f"Style ID: {data['product'].get('styleId')}")
            else:
                print(f"Error: {response.text}")
        except Exception as e:
            print(f"ERROR: {e}")

        # Test 3: Get Product Variants
        print("\n[3] Testing: GET /catalog/products/{product_id}/variants")
        try:
            response = await client.get(f"{base_url}/catalog/products/{product_id}/variants")
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"Success: Found {data['total_variants']} variants")
                # Find variant for test size
                variants = data["variants"]
                matching_variant = next(
                    (v for v in variants if v.get("variantValue") == test_size), None
                )
                if matching_variant:
                    variant_id = matching_variant["variantId"]
                    print(f"Found size {test_size}: variant_id = {variant_id}")
                else:
                    # Use first variant
                    variant_id = variants[0]["variantId"]
                    test_size = variants[0]["variantValue"]
                    print(f"Size {test_size} not found, using {test_size} instead")
            else:
                print(f"Error: {response.text}")
                return
        except Exception as e:
            print(f"ERROR: {e}")
            return

        # Test 4: Get Market Data
        print("\n[4] Testing: GET /catalog/products/{product_id}/variants/{variant_id}/market-data")
        try:
            response = await client.get(
                f"{base_url}/catalog/products/{product_id}/variants/{variant_id}/market-data",
                params={"currency_code": "EUR"},
            )
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                market = data["market_data"]
                print(f"Success: Market data for size {test_size}")
                print(f"  Lowest Ask: {market.get('lowest_ask')} EUR")
                print(f"  Highest Bid: {market.get('highest_bid')} EUR")
                print(f"  Sell Faster: {market.get('sell_faster_price')} EUR")
                print(f"  Earn More: {market.get('earn_more_price')} EUR")
            else:
                print(f"Error: {response.text}")
        except Exception as e:
            print(f"ERROR: {e}")

        # Test 5: Complete Enrichment (this updates database)
        print("\n[5] Testing: POST /catalog/enrich-by-sku")
        print("WARNING: This will update the database!")
        user_input = input("Continue? (y/n): ")

        if user_input.lower() == "y":
            try:
                response = await client.post(
                    f"{base_url}/catalog/enrich-by-sku", params={"sku": test_sku, "size": test_size}
                )
                print(f"Status: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    print(f"Success: {data['message']}")
                    enrichment = data["data"]
                    print(f"  SKU: {enrichment['sku']}")
                    print(f"  Product: {enrichment['product_title']}")
                    print(f"  Brand: {enrichment['brand']}")
                    print(f"  Variants: {enrichment['total_variants']}")
                    print(
                        f"  Market Data: {'Available' if enrichment['market_data_available'] else 'Not Available'}"
                    )
                    print(f"  Lowest Ask: {enrichment['lowest_ask']} EUR")
                else:
                    print(f"Error: {response.text}")
            except Exception as e:
                print(f"ERROR: {e}")
        else:
            print("Skipped enrichment test")

        print("\n" + "=" * 80)
        print("All catalog endpoint tests completed!")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_catalog_endpoints())
