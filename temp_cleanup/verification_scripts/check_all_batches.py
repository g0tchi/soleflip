import asyncio
import asyncpg

async def check_all_batches():
    conn = await asyncpg.connect('postgresql://metabaseuser:metabasepass@192.168.2.45:2665/soleflip')
    
    try:
        # Check all recent batches
        batches = await conn.fetch(
            """SELECT id, source_type, total_records, processed_records, status, created_at 
               FROM integration.import_batches 
               ORDER BY created_at DESC LIMIT 5"""
        )
        
        print("Recent batches:")
        for batch in batches:
            batch_id = str(batch['id'])
            print(f"Batch {batch_id[:8]}: {batch['status']}, {batch['processed_records']}/{batch['total_records']} records")
            
            # Check transactions for this batch
            transactions = await conn.fetchval(
                "SELECT COUNT(*) FROM sales.transactions WHERE notes LIKE $1",
                f"%batch {batch_id}%"
            )
            print(f"  -> Transactions: {transactions}")
        
        # Check the successful batch that created products
        successful_batch = await conn.fetchrow(
            """SELECT id FROM integration.import_batches 
               WHERE status = 'completed' AND processed_records > 0 
               ORDER BY created_at DESC LIMIT 1"""
        )
        
        if successful_batch:
            batch_id = str(successful_batch['id'])
            print(f"\nSuccessful batch {batch_id[:8]}:")
            
            # Check if transactions exist for successful batch
            transactions = await conn.fetchval(
                "SELECT COUNT(*) FROM sales.transactions WHERE notes LIKE $1",
                f"%batch {batch_id}%"
            )
            print(f"  Transactions created: {transactions}")
            
            # Also check without batch reference (maybe different notes format)
            recent_transactions = await conn.fetchval(
                "SELECT COUNT(*) FROM sales.transactions WHERE created_at >= (SELECT created_at FROM integration.import_batches WHERE id = $1)",
                successful_batch['id']
            )
            print(f"  Recent transactions since batch: {recent_transactions}")
            
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(check_all_batches())