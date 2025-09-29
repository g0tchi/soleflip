# StockX SKU Strategy and External IDs Management

## Overview

This document explains the SKU (Stock Keeping Unit) strategy for StockX integration and how StockX-specific metadata is managed using the `external_ids` JSON field.

## SKU Strategy Decision

### Problem with Original Approach
Initially, we used StockX `listing_id` as the SKU, but this approach had critical flaws:
- **Temporary Nature**: StockX listing IDs are temporary and disappear when listings are deleted/sold
- **Inventory Confusion**: Using temporary IDs as permanent product identifiers causes data integrity issues
- **Business Logic Issues**: SKUs should represent the actual product, not a specific listing instance

### Correct SKU Strategy
We now use a hierarchical approach for SKU generation:

```python
# Priority order for SKU generation:
1. styleId (e.g., "DR5540-006", "HQ8752") - PREFERRED
2. productId (fallback: "pid-{first_8_chars}")
3. listing_id (last resort: "stockx-{first_8_chars}")
```

**Example SKUs:**
- ✅ `DR5540-006` (Nike styleId - permanent product identifier)
- ✅ `HQ8752` (Adidas styleId - permanent product identifier)
- ✅ `pid-89b4275b` (fallback when no styleId available)
- ⚠️ `stockx-a1b2c3d4` (last resort only)

## External IDs JSON Field

All StockX-specific metadata is stored in the `external_ids` JSON field to maintain separation between permanent product data and integration-specific information.

### Complete External IDs Structure

```json
{
  "stockx_listing_id": "unique_listing_identifier",
  "stockx_product_id": "product_uuid_from_stockx",
  "stockx_variant_id": "variant_uuid_for_size_color",
  "stockx_ask_id": "ask_uuid_if_available",
  "created_from_sync": true,
  "sync_timestamp": "2024-01-15T10:30:00Z",
  "currency_code": "EUR",
  "listing_status": "ACTIVE"
}
```

### Field Descriptions

- **`stockx_listing_id`**: Temporary listing identifier (changes when relisted)
- **`stockx_product_id`**: StockX internal product UUID
- **`stockx_variant_id`**: Size/color variant UUID
- **`stockx_ask_id`**: Specific ask/bid UUID if applicable
- **`created_from_sync`**: Flag indicating item was created via StockX sync
- **`sync_timestamp`**: When this item was last synced from StockX
- **`currency_code`**: Currency for pricing (EUR, USD, etc.)
- **`listing_status`**: Current listing status (ACTIVE, SOLD, CANCELLED)

## Database Queries

### Finding Items by StockX Listing ID

```python
# Correct way to query by StockX listing ID
items = await session.execute(
    select(InventoryItem)
    .where(and_(
        InventoryItem.external_ids.is_not(None),
        InventoryItem.external_ids['stockx_listing_id'].astext == listing_id
    ))
)
```

### Preventing NULL JSON Access Errors

Always check for NULL before accessing JSON fields:

```python
# ✅ CORRECT - with NULL check
and_(
    InventoryItem.external_ids.is_not(None),
    InventoryItem.external_ids['stockx_listing_id'].astext == value
)

# ❌ INCORRECT - causes "Boolean value of this clause is not defined"
InventoryItem.external_ids['stockx_listing_id'].astext == value
```

## Benefits of This Approach

1. **Data Integrity**: SKUs remain stable even when listings are deleted/sold
2. **Traceability**: Complete StockX metadata preserved in external_ids
3. **Flexibility**: Can track multiple integration sources in same JSON field
4. **Performance**: Efficient JSON queries with proper NULL handling
5. **Business Logic**: SKUs represent actual products, not listing instances

## Implementation in Sync Service

The inventory service uses this strategy in `sync_all_stockx_listings_to_inventory()`:

1. **SKU Generation**: Extract styleId from StockX product data
2. **Product Lookup**: Find existing product by SKU or create new one
3. **External IDs Storage**: Store all StockX metadata in JSON field
4. **Duplicate Prevention**: Check external_ids for existing listing_id to prevent duplicates

## Migration Notes

When implementing this strategy:
- Existing items with listing_id-based SKUs should be migrated
- Update all queries to use proper JSON NULL checking
- Ensure external_ids field is properly indexed for performance
- Update API documentation to reflect new SKU strategy

## Security Considerations

- Never expose internal StockX IDs in public APIs
- Use SKUs for customer-facing operations
- Keep external_ids for internal tracking and debugging only