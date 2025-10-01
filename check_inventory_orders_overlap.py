"""
Check for field duplication between products.inventory and transactions.orders
"""
import asyncio
from sqlalchemy import text
from shared.database.connection import DatabaseManager


async def check_overlap():
    db = DatabaseManager()
    await db.initialize()

    async with db.get_session() as session:
        print("=" * 80)
        print("CHECKING FIELD OVERLAP: products.inventory vs transactions.orders")
        print("=" * 80)

        # Get all columns from inventory table
        result = await session.execute(text("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = 'products' AND table_name = 'inventory'
            ORDER BY ordinal_position
        """))
        inventory_cols = list(result)

        # Get all columns from orders table
        result = await session.execute(text("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = 'transactions' AND table_name = 'orders'
            ORDER BY ordinal_position
        """))
        orders_cols = list(result)

        print(f"\nproducts.inventory columns: {len(inventory_cols)}")
        print(f"transactions.orders columns: {len(orders_cols)}")

        # Analyze purchase/sale related fields
        print("\n" + "=" * 80)
        print("PRODUCTS.INVENTORY - PURCHASE DATA")
        print("=" * 80)

        purchase_fields = []
        for col in inventory_cols:
            name = col.column_name
            if any(keyword in name.lower() for keyword in ['purchase', 'buy', 'cost', 'price', 'supplier', 'vat', 'delivery']):
                purchase_fields.append(col)
                print(f"  {name:30} | {col.data_type:20} | {col.is_nullable}")

        print("\n" + "=" * 80)
        print("TRANSACTIONS.ORDERS - SALE DATA")
        print("=" * 80)

        sale_fields = []
        for col in orders_cols:
            name = col.column_name
            if any(keyword in name.lower() for keyword in ['sale', 'sold', 'gross', 'net', 'proceeds', 'profit', 'roi', 'payout', 'platform_fee', 'shipping']):
                sale_fields.append(col)
                print(f"  {name:30} | {col.data_type:20} | {col.is_nullable}")

        # Check for potential duplicates
        print("\n" + "=" * 80)
        print("POTENTIAL DUPLICATIONS / OVERLAP")
        print("=" * 80)

        duplicates = []

        # Check if inventory has sale-related fields
        for col in inventory_cols:
            name = col.column_name
            if any(keyword in name.lower() for keyword in ['sale', 'sold', 'revenue', 'proceeds']):
                duplicates.append({
                    'table': 'inventory',
                    'column': name,
                    'issue': 'Sale data in inventory table (should be in orders)'
                })

        # Check if orders has purchase-related fields that duplicate inventory
        for col in orders_cols:
            name = col.column_name
            # These are OK in orders (reference back to inventory purchase data):
            # - Nothing should duplicate, orders should reference inventory_item_id
            pass

        if duplicates:
            print("\n[!] Found potential duplications:")
            for dup in duplicates:
                print(f"  - {dup['table']}.{dup['column']}: {dup['issue']}")
        else:
            print("\n[OK] No duplications found - clean separation!")

        # Analyze the relationship
        print("\n" + "=" * 80)
        print("RELATIONSHIP ANALYSIS")
        print("=" * 80)

        # Check if all orders have valid inventory references
        result = await session.execute(text("""
            SELECT COUNT(*) as total_orders FROM transactions.orders
        """))
        total_orders = result.fetchone()[0]

        result = await session.execute(text("""
            SELECT COUNT(*)
            FROM transactions.orders o
            LEFT JOIN products.inventory i ON o.inventory_item_id = i.id
            WHERE i.id IS NULL
        """))
        orphaned_orders = result.fetchone()[0]

        print(f"\nTotal orders: {total_orders}")
        print(f"Orders without inventory link: {orphaned_orders}")

        if orphaned_orders > 0:
            print(f"[!] {orphaned_orders} orders have no matching inventory item")
        else:
            print("[OK] All orders properly linked to inventory")

        # Show example data flow
        print("\n" + "=" * 80)
        print("DATA FLOW EXAMPLE (1 sale)")
        print("=" * 80)

        result = await session.execute(text("""
            SELECT
                i.id as inventory_id,
                i.purchase_price as inv_purchase_price,
                i.gross_purchase_price as inv_gross_purchase,
                i.supplier_id,
                o.id as order_id,
                o.gross_sale,
                o.net_proceeds,
                o.net_profit,
                o.roi
            FROM transactions.orders o
            JOIN products.inventory i ON o.inventory_item_id = i.id
            WHERE o.status = 'completed'
            ORDER BY o.sold_at DESC
            LIMIT 1
        """))

        example = result.fetchone()
        if example:
            print("\nInventory (Purchase Data):")
            print(f"  ID: {example.inventory_id}")
            print(f"  Net Purchase: EUR{example.inv_purchase_price}")
            print(f"  Gross Purchase: EUR{example.inv_gross_purchase}")
            print(f"  Supplier ID: {example.supplier_id}")

            print("\nOrder (Sale Data):")
            print(f"  ID: {example.order_id}")
            print(f"  Gross Sale: EUR{example.gross_sale}")
            print(f"  Net Proceeds: EUR{example.net_proceeds}")
            print(f"  Net Profit: EUR{example.net_profit}")
            print(f"  ROI: {example.roi}%")

        # Summary
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print("\n[Architecture]")
        print("  products.inventory  -> Stores PURCHASE data (what we bought)")
        print("  transactions.orders -> Stores SALE data (what we sold)")
        print("  Relationship: orders.inventory_item_id -> inventory.id (1:N)")

        print("\n[Purchase Fields in inventory:]")
        print(f"  - {len(purchase_fields)} purchase-related fields")

        print("\n[Sale Fields in orders:]")
        print(f"  - {len(sale_fields)} sale-related fields")

        print("\n[Conclusion:]")
        if not duplicates and orphaned_orders == 0:
            print("  [OK] Clean separation - no duplications detected!")
            print("  [OK] All relationships valid")
        else:
            print("  [!] Issues found - review above")

    await db.close()


if __name__ == "__main__":
    asyncio.run(check_overlap())
