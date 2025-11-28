# Marketplace Fee Structure

## Overview

The `platform.marketplace_fee_structure` table provides detailed fee tracking for marketplace platforms, supporting historical changes and multiple fee types.

## Schema

```sql
CREATE TABLE platform.marketplace_fee_structure (
    id UUID PRIMARY KEY,
    marketplace_id UUID REFERENCES platform.marketplace(id) ON DELETE CASCADE,
    fee_type ENUM('transaction', 'payment_processing', 'shipping', 'custom'),
    fee_calculation_type ENUM('percentage', 'fixed', 'tiered'),
    fee_value NUMERIC(10,2) CHECK (fee_value >= 0),
    active BOOLEAN DEFAULT TRUE,
    effective_from TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    effective_until TIMESTAMP WITH TIME ZONE NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

## Fee Types

### StockX Fee Structure (as of 2025-11-28)

Based on real API data from active orders:

| Fee Type | Calculation | Value | Notes |
|----------|-------------|-------|-------|
| **Transaction Fee** | Percentage | 8.5% | **Minimum: 5.00 EUR** - StockX applies whichever is higher |
| **Payment Processing** | Percentage | 3.0% | Standard payment gateway fee |
| **Shipping** | Fixed | 4.50 EUR | Varies by region and product size |

### Example Calculation

**Sale: Nike Blazer Mid 77 - 48.94 EUR**

```
Transaction Fee:  max(48.94 * 8.5%, 5.00) = 5.00 EUR  (minimum applied)
Payment Process:  48.94 * 3.0%             = 1.47 EUR
Shipping:         fixed                    = 4.50 EUR
                                           ─────────
Total Fees:                                 10.97 EUR
Seller Payout:    48.94 - 10.97           = 38.03 EUR ✓
```

**API Response Verification:**
```json
{
  "salePrice": "48.94",
  "totalAdjustments": "-10.97",
  "totalPayout": "38.03",
  "adjustments": [
    {"amount": "-5", "percentage": "0.085", "adjustmentType": "MinTransactionFee"},
    {"amount": "-1.47", "percentage": "0.03", "adjustmentType": "Payment Proc. (3%)"},
    {"amount": "-4.5", "percentage": "0", "adjustmentType": "Shipping"}
  ]
}
```

## Important Notes

### Minimum Transaction Fee

StockX enforces a **minimum transaction fee of 5.00 EUR**. Even if the percentage (8.5%) calculates to less, the minimum is always applied.

**Example:**
- Sale Price: 30.00 EUR
- 8.5% would be: 2.55 EUR
- **Actual charged: 5.00 EUR** (minimum)

### Fee Variations

- **Shipping fees** vary by:
  - Product size and weight
  - Destination region
  - Shipping method
- **Regional differences** may apply for different currencies

## Historical Tracking

The `effective_from` and `effective_until` fields enable tracking fee changes over time:

```sql
-- Get current active fees
SELECT * FROM platform.marketplace_fee_structure
WHERE marketplace_id = '...' AND active = true;

-- Get historical fees for a specific date
SELECT * FROM platform.marketplace_fee_structure
WHERE marketplace_id = '...'
  AND effective_from <= '2025-01-01'
  AND (effective_until IS NULL OR effective_until > '2025-01-01');
```

## Usage in Code

### Query Active Fees

```python
async def get_active_fees(marketplace_id: UUID) -> list[FeeStructure]:
    query = select(MarketplaceFeeStructure).where(
        MarketplaceFeeStructure.marketplace_id == marketplace_id,
        MarketplaceFeeStructure.active == True
    )
    result = await session.execute(query)
    return result.scalars().all()
```

### Calculate Total Fees

```python
def calculate_fees(sale_price: Decimal, fees: list[FeeStructure]) -> Decimal:
    total = Decimal('0')
    for fee in fees:
        if fee.fee_calculation_type == 'percentage':
            amount = sale_price * (fee.fee_value / 100)
            # Apply minimum if it's a transaction fee
            if fee.fee_type == 'transaction':
                amount = max(amount, Decimal('5.00'))  # StockX minimum
            total += amount
        elif fee.fee_calculation_type == 'fixed':
            total += fee.fee_value
    return total
```

## Future Enhancements

### Planned Features

1. **Tiered Fee Support**
   - Different rates based on seller level
   - Volume-based discounts

2. **Multi-Currency Support**
   - Currency-specific minimum fees
   - Exchange rate tracking

3. **Fee Estimation API**
   - Endpoint to calculate fees before listing
   - Profit margin calculator

## Database Migrations

Migration file: `migrations/versions/2025_11_28_0705_1c9879bad9c0_add_marketplace_fee_structure_table.py`

To apply:
```bash
alembic upgrade head
```

To rollback:
```bash
alembic downgrade -1
```

## Related Tables

- `platform.marketplace` - Parent marketplace definition
- `sales.order` - Orders that use these fees
- `financial.transaction` - Financial records

## See Also

- [StockX API Integration](../guides/stockx_auth_setup.md)
- [Order Management](../architecture/orders.md)
- [Pricing Engine](../features/smart_pricing.md)
