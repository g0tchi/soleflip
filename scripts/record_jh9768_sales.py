"""
Record JH9768 (adidas Campus 00s) sales from allike purchase
"""

import asyncio
import os
from datetime import datetime
from decimal import Decimal
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Sales data from StockX API
sales = [
    {
        "inventory_id": "cb6e7555-04ac-4b8c-bb17-32a1b6af2945",  # 39 1/3
        "order_number": "76888647-76788406",
        "size": "39 1/3",
        "sale_price": Decimal("58.00"),
        "sold_at": datetime(2025, 8, 12, 7, 18, 41),
        "purchase_price_gross": Decimal("49.99"),
        "purchase_price_net": Decimal("42.01"),
    },
    {
        "inventory_id": "1c1b4714-5538-4a89-82b2-1676588c2358",  # 38
        "order_number": "77923870-77823629",
        "size": "38",
        "sale_price": Decimal("56.00"),
        "sold_at": datetime(2025, 10, 9, 16, 27, 26),
        "purchase_price_gross": Decimal("49.99"),
        "purchase_price_net": Decimal("42.01"),
    },
]


async def record_sales():
    engine = create_async_engine(os.getenv("DATABASE_URL"), echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Get StockX platform_id
        platform_result = await session.execute(
            text("SELECT id FROM core.platforms WHERE LOWER(name) = 'stockx'")
        )
        platform_id = platform_result.fetchone()[0]

        print("StockX Platform ID:", platform_id)
        print("")

        for sale in sales:
            print(f"Verarbeite: adidas Campus 00s - Size {sale['size']}")
            print("=" * 60)

            # StockX fees: 9.5% + 1.50 EUR processing
            seller_fee = sale["sale_price"] * Decimal("0.095")
            processing_fee = Decimal("1.50")
            total_fees = seller_fee + processing_fee
            net_proceeds = sale["sale_price"] - total_fees

            # Profit calculations
            gross_profit = sale["sale_price"] - sale["purchase_price_gross"]
            net_profit = net_proceeds - sale["purchase_price_gross"]
            roi = (
                (net_profit / sale["purchase_price_gross"]) * 100
                if sale["purchase_price_gross"] > 0
                else 0
            )

            print(f"  Verkaufspreis: {sale['sale_price']} EUR")
            print(f"  Seller Fee (9.5%): {seller_fee:.2f} EUR")
            print(f"  Processing Fee: {processing_fee} EUR")
            print(f"  Net Proceeds: {net_proceeds:.2f} EUR")
            print(f"  Net Profit: {net_profit:.2f} EUR")
            print(f"  ROI: {roi:.2f}%")
            print("")

            # Create order record (NUR transactions.orders - KEINE transactions.transactions!)
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
                """
                ),
                {
                    "inventory_id": sale["inventory_id"],
                    "platform_id": platform_id,
                    "order_number": sale["order_number"],
                    "amount": sale["sale_price"],
                    "platform_fee": total_fees,
                    "stockx_created": sale["sold_at"],
                    "stockx_updated": datetime.now(),
                    "sold_at": sale["sold_at"],
                    "gross_sale": sale["sale_price"],
                    "net_proceeds": net_proceeds,
                    "gross_profit": gross_profit,
                    "net_profit": net_profit,
                    "roi": roi,
                },
            )
            print(f"[OK] Order record erstellt: {sale['order_number']}")

            # Update inventory status
            await session.execute(
                text(
                    """
                    UPDATE products.inventory
                    SET status = :status,
                        roi_percentage = :roi,
                        updated_at = NOW()
                    WHERE id = :inventory_id
                """
                ),
                {"inventory_id": sale["inventory_id"], "roi": roi, "status": "sold"},
            )
            print(f"[OK] Inventory status aktualisiert: sold, ROI: {roi:.2f}%")
            print("")

        await session.commit()
        print("")
        print("[SUCCESS] Beide JH9768 Verkäufe erfolgreich erfasst!")
        print("")
        print("Zusammenfassung:")
        print("-" * 60)
        print(
            "1. Size 39 1/3: 58 EUR - ROI: {:.2f}%".format(
                (sales[0]["sale_price"] - Decimal("6.01") - sales[0]["purchase_price_gross"])
                / sales[0]["purchase_price_gross"]
                * 100
            )
        )
        print(
            "2. Size 38:     56 EUR - ROI: {:.2f}%".format(
                (sales[1]["sale_price"] - Decimal("5.82") - sales[1]["purchase_price_gross"])
                / sales[1]["purchase_price_gross"]
                * 100
            )
        )

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(record_sales())
