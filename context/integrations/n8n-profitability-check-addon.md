# n8n Profitability Check - Workflow Extension

## Problem Statement

The current workflow imports **all** products that pass brand/category filters, without checking if they are **profitable** to sell.

**Risk:**
- Importing products with low/negative margins
- Wasting catalog space on unprofitable items
- Auto-listing products that lose money

---

## Solution: Add Profitability Check Layer

### Step 1: Define Profitability Logic

**Three Approaches:**

#### **Option A: Competitive Pricing (Recommended for Affiliate Products)**

```python
# Logic:
supplier_price = webgains_product.price  # €85.99
market_price = get_soleflip_current_price(product.ean)  # €119.99 (or fetch from StockX/competitors)

profit_margin = ((market_price - supplier_price) / market_price) * 100
# = ((119.99 - 85.99) / 119.99) * 100 = 28.3%

min_margin_threshold = 20  # Configurable

if profit_margin >= min_margin_threshold:
    import_product()
else:
    skip_or_flag_for_review()
```

**Use Case:**
- Compare supplier price vs. your current catalog price
- Only import if margin meets threshold (e.g., 20%+)

#### **Option B: Fixed Markup Strategy**

```python
# Logic:
supplier_price = webgains_product.price  # €85.99
target_markup = 1.30  # 30% markup
selling_price = supplier_price * target_markup  # €111.79

# Check if this price is competitive in market
competitor_avg_price = get_market_average(product.ean)  # €119.99

if selling_price <= competitor_avg_price:
    import_product(price=selling_price)
else:
    skip_product()  # Too expensive to compete
```

**Use Case:**
- Apply fixed markup (e.g., 30%)
- Import if resulting price is competitive

#### **Option C: Hybrid (Market + Margin Check)**

```python
# Logic:
supplier_price = webgains_product.price  # €85.99
market_price = get_market_average(product.ean)  # €119.99

# Calculate potential profit
potential_profit = market_price - supplier_price - operational_costs
# = 119.99 - 85.99 - 5.00 = €29.00

min_profit_threshold = 15.00  # €15 min profit

if potential_profit >= min_profit_threshold:
    import_product(
        supplier_price=supplier_price,
        selling_price=market_price - 5.00,  # Undercut slightly
        profit_margin=...
    )
```

**Use Case:**
- Most sophisticated
- Considers operational costs (shipping, fees, etc.)
- Ensures minimum absolute profit per unit

---

## Implementation: Add Nodes to Workflow

### New Node Structure

Insert **after** "Check for Duplicates", **before** "Route: New vs Duplicate":

```
[Existing nodes...]
    ↓
Check for Duplicates
    ↓
┌────────────────────────────────────┐
│ 1. Get Market Prices               │
│    (SoleFlip API or StockX API)    │
└────────────────────────────────────┘
    ↓
┌────────────────────────────────────┐
│ 2. Calculate Profitability         │
│    (Code Node)                     │
└────────────────────────────────────┘
    ↓
┌────────────────────────────────────┐
│ 3. Filter: Profitable Only         │
│    (Switch Node)                   │
└────────────────────────────────────┘
    ↓
┌──────────┬─────────────────────┐
│ ✅       │ ❌                  │
│ Profit   │ No Profit           │
│ OK       │ (Log & Skip)        │
└──────────┴─────────────────────┘
    ↓              ↓
Import       Skip or Store
             for Manual Review
```

---

## IMPORTANT: Use Existing SoleFlip Services

**DO NOT create duplicate profitability logic!**

SoleFlip already has:
- **AutoListingService** with profit margin rules (15-30%)
- **SmartPricingService** with market data integration
- **PricingEngine** for optimal price calculations

### Integration Options:

#### **Option A: Import ALL → AutoListing Filters Later**

```
n8n imports all filtered products
    ↓
Products stored with status = "in_stock"
    ↓
AutoListingService evaluates (existing service!)
    ↓
Only profitable items get listed to StockX
```

**Benefits:**
- Uses existing, tested system
- No code changes needed
- All AutoListing rules apply automatically

#### **Option B: Pre-Check via API Endpoint (Recommended)**

Create endpoint: `POST /pricing/evaluate-profitability`

```python
# domains/pricing/api/router.py

@router.post("/evaluate-profitability")
async def evaluate_profitability(
    data: ProfitabilityCheckRequest,
    session: AsyncSession = Depends(get_session)
):
    """
    Check if a product would be profitable BEFORE importing
    Used by n8n workflows for pre-filtering
    """
    smart_pricing = SmartPricingService(session)

    # Get market price from StockX
    market_price = await smart_pricing.get_market_price_by_ean(data.ean)

    if not market_price:
        return {"profitable": False, "reason": "No market data"}

    # Calculate margin
    margin = ((market_price - data.supplier_price) / data.supplier_price) * 100

    # Check against minimum threshold (reuse AutoListing logic)
    min_margin = 15.0  # From AutoListingService "Quick Turnover Items" rule

    return {
        "profitable": margin >= min_margin,
        "margin_percent": round(margin, 2),
        "supplier_price": data.supplier_price,
        "market_price": market_price,
        "should_import": margin >= min_margin
    }
```

**n8n Node:**
```javascript
// HTTP Request Node: Check Profitability
{
  "method": "POST",
  "url": "http://localhost:8000/pricing/evaluate-profitability",
  "body": {
    "ean": "{{ $json.ean }}",
    "supplier_price": {{ $json.price }},
    "brand": "{{ $json.brand }}",
    "model": "{{ $json.product_name }}"
  }
}

// Switch Node: Route by profitability
if (response.profitable === true) {
  // Continue to import
} else {
  // Skip or log
}
```

---

## Questions to Answer

Before implementing, clarify:

1. **What's your minimum acceptable profit margin?**
   - 10%? 20%? 30%?

2. **Where do you get market prices from?**
   - Your own catalog (products.product table)?
   - StockX API?
   - Competitors (manual research)?
   - Data Table (manually maintained)?

3. **What about operational costs?**
   - Fixed per item? (e.g., €5)
   - Percentage of price? (e.g., 5%)
   - Variable by brand/category?

4. **What to do with unprofitable products?**
   - Skip completely?
   - Store for manual review?
   - Import but mark as "do not auto-list"?

5. **How often to update market prices?**
   - Real-time (API call per product)?
   - Cached in Data Table (weekly update)?
   - Manual entry?

---

**Next Step:** Check existing endpoints and decide on integration approach! 🚀
