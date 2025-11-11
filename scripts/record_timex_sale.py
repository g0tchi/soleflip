"""
Record Timex Camper x Stranger Things sale from StockX order 04-UW2Q0ZAQT8
"""

import asyncio
import os
from datetime import datetime
from decimal import Decimal

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()


async def create_timex_sale():
    engine = create_async_engine(os.getenv("DATABASE_URL"), echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Get the Timex inventory item
        inventory_result = await session.execute(
            text(
                """
                SELECT i.id, i.purchase_price, i.gross_purchase_price, p.id as product_id
                FROM products.inventory i
                JOIN products.products p ON i.product_id = p.id
                WHERE p.sku = 'TW2V50800U8'
                AND i.status = 'in_stock'
                ORDER BY i.created_at DESC
                LIMIT 1
            """
            )
        )
        inventory = inventory_result.fetchone()

        if not inventory:
            print("[ERROR] Timex inventory item not found or already sold")
            return

        inventory_id = inventory[0]
        purchase_price = inventory[1]  # net
        gross_purchase_price = inventory[2]  # gross
        inventory[3]

        print(f"[OK] Found inventory item: {inventory_id}")
        print(f"     Purchase price (net): {purchase_price} EUR")
        print(f"     Purchase price (gross): {gross_purchase_price} EUR")

        # StockX order data
        order_number = "04-UW2Q0ZAQT8"
        sale_price = Decimal("51.00")
        stockx_created_at = datetime(2025, 10, 8, 12, 2, 34)  # From API response

        # Calculate StockX fees (typically 9.5% + processing fee)
        seller_fee = sale_price * Decimal("0.095")  # 9.5%
        processing_fee = Decimal("1.50")  # Estimated processing fee
        total_fees = seller_fee + processing_fee
        net_proceeds = sale_price - total_fees

        # Calculate profit
        gross_profit = sale_price - gross_purchase_price
        net_profit = net_proceeds - gross_purchase_price
        roi = (net_profit / gross_purchase_price * 100) if gross_purchase_price else 0

        print("\n[INFO] Sale details:")
        print(f"     Sale price: {sale_price} EUR")
        print(f"     Seller fee (9.5%): {seller_fee:.2f} EUR")
        print(f"     Processing fee: {processing_fee} EUR")
        print(f"     Net proceeds: {net_proceeds:.2f} EUR")
        print(f"     Gross profit: {gross_profit:.2f} EUR")
        print(f"     Net profit: {net_profit:.2f} EUR")
        print(f"     ROI: {roi:.2f}%")

        # Get StockX platform ID
        platform_result = await session.execute(
            text("SELECT id FROM core.platforms WHERE LOWER(name) = 'stockx'")
        )
        platform = platform_result.fetchone()

        if not platform:
            print("[ERROR] StockX platform not found in database")
            return

        platform_id = platform[0]

        # Create order record
        await session.execute(
            text(
                """
                INSERT INTO transactions.orders (
                    id, inventory_item_id, platform_id, stockx_order_number, status,
                    amount, currency_code, inventory_type, platform_fee,
                    stockx_created_at, last_stockx_updated_at,
                    sold_at, gross_sale, net_proceeds, gross_profit, net_profit, roi,
                    created_at, updated_at
                )
                VALUES (
                    gen_random_uuid(), :inventory_id, :platform_id, :order_number, 'completed',
                    :amount, 'EUR', 'STANDARD', :platform_fee,
                    :stockx_created, :stockx_updated,
                    :sold_at, :gross_sale, :net_proceeds, :gross_profit, :net_profit, :roi,
                    NOW(), NOW()
                )
                RETURNING id
            """
            ),
            {
                "inventory_id": inventory_id,
                "platform_id": platform_id,
                "order_number": order_number,
                "amount": sale_price,
                "platform_fee": total_fees,
                "stockx_created": stockx_created_at,
                "stockx_updated": datetime.now(),
                "sold_at": stockx_created_at,
                "gross_sale": sale_price,
                "net_proceeds": net_proceeds,
                "gross_profit": gross_profit,
                "net_profit": net_profit,
                "roi": roi,
            },
        )
        await session.commit()
        print(f"\n[OK] Created order record: {order_number}")

        # Create transaction record
        await session.execute(
            text(
                """
                INSERT INTO transactions.transactions (
                    id, inventory_id, platform_id, transaction_date,
                    sale_price, platform_fee, shipping_cost, net_profit,
                    status, external_id,
                    created_at, updated_at
                )
                VALUES (
                    gen_random_uuid(), :inventory_id, :platform_id, :transaction_date,
                    :sale_price, :platform_fee, 0, :net_profit,
                    'completed', :external_id,
                    NOW(), NOW()
                )
                RETURNING id
            """
            ),
            {
                "inventory_id": inventory_id,
                "platform_id": platform_id,
                "transaction_date": stockx_created_at,
                "sale_price": sale_price,
                "platform_fee": total_fees,
                "net_profit": net_profit,
                "external_id": order_number,
            },
        )
        await session.commit()
        print("[OK] Created transaction record")

        # Update inventory status to sold
        await session.execute(
            text(
                """
                UPDATE products.inventory
                SET status = 'sold',
                    roi_percentage = :roi,
                    updated_at = NOW()
                WHERE id = :inventory_id
            """
            ),
            {"inventory_id": inventory_id, "roi": roi},
        )
        await session.commit()
        print("[OK] Updated inventory status to 'sold'")

        print(f"\n{'='*60}")
        print("[SUCCESS] Timex sale recorded successfully!")
        print(f"{'='*60}")
        print("\nSummary:")
        print("  Product: Timex Camper x Stranger Things")
        print(f"  Order: {order_number}")
        print(f"  Purchase: {gross_purchase_price} EUR (gross)")
        print(f"  Sale: {sale_price} EUR")
        print(f"  Platform fees: {total_fees:.2f} EUR")
        print(f"  Net proceeds: {net_proceeds:.2f} EUR")
        print(f"  Net profit: {net_profit:.2f} EUR")
        print(f"  ROI: {roi:.2f}%")
        print(f"  Sale date: {stockx_created_at.strftime('%Y-%m-%d')}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_timex_sale())
