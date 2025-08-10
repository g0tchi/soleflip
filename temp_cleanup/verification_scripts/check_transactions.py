import asyncio
import asyncpg

async def check_transactions():
    conn = await asyncpg.connect('postgresql://metabaseuser:metabasepass@192.168.2.45:2665/soleflip')
    
    try:
        # Check last batch
        last_batch = await conn.fetchrow(
            "SELECT id, source_type, total_records, processed_records, status, created_at FROM integration.import_batches ORDER BY created_at DESC LIMIT 1"
        )
        print(f'Last batch: {last_batch}')
        
        if last_batch:
            batch_id = str(last_batch['id'])
            
            # Check transactions for this batch
            transactions = await conn.fetch(
                "SELECT COUNT(*) as count FROM sales.transactions WHERE notes LIKE $1",
                f"%batch {batch_id}%"
            )
            print(f'Transactions in batch {batch_id[:8]}: {transactions[0]["count"]}')
            
            # Check products created/updated
            products = await conn.fetch(
                "SELECT COUNT(*) as count FROM products.products"
            )
            print(f'Total products in database: {products[0]["count"]}')
            
            # Check recent transactions
            recent_transactions = await conn.fetch(
                "SELECT COUNT(*) as count FROM sales.transactions WHERE transaction_date >= CURRENT_DATE - INTERVAL '1 day'"
            )
            print(f'Recent transactions (last 24h): {recent_transactions[0]["count"]}')
            
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(check_transactions())