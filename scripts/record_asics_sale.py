"""
Record Asics Gel-Kayano 20 sale from allike purchase
US W 5.5 = EU 38 bei Asics
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

# Sale data from StockX API
sale = {
    "inventory_id": "96874a85-decc-457e-8ea8-74556efa6e9a",  # EU 38
    "order_number": "77633803-77533562",
    "size_stockx": "5.5",  # US W 5.5 = EU 38
    "size_eu": "38",
    "sale_price": Decimal("94.00"),
    "sold_at": datetime(2025, 9, 18, 10, 14, 53),
    "purchase_price_gross": Decimal("104.99"),
    "purchase_price_net": Decimal("88.23"),
}


async def record_asics_sale():
    engine = create_async_engine(os.getenv("DATABASE_URL"), echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Get StockX platform_id
        platform_result = await session.execute(
            text("SELECT id FROM core.platforms WHERE LOWER(name) = 'stockx'")
        )
        platform_id = platform_result.fetchone()[0]

        print("Asics Gel-Kayano 20 Verkauf")
        print("=" * 60)
        print(f"StockX Size: US W {sale['size_stockx']} (= EU {sale['size_eu']})")
        print("")

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

        print(f"Verkaufspreis: {sale['sale_price']} EUR")
        print(f"Seller Fee (9.5%): {seller_fee:.2f} EUR")
        print(f"Processing Fee: {processing_fee} EUR")
        print(f"Net Proceeds: {net_proceeds:.2f} EUR")
        print(f"Gross Profit: {gross_profit:.2f} EUR")
        print(f"Net Profit: {net_profit:.2f} EUR")
        print(f"ROI: {roi:.2f}%")
        print("")

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

        print("[SUCCESS] Asics Gel-Kayano 20 Verkauf erfolgreich erfasst!")
        print("")
        print("Hinweis: US W 5.5 wurde korrekt als EU 38 erkannt")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(record_asics_sale())
