import asyncio
import asyncpg

async def check_new_destination_data():
    conn = await asyncpg.connect('postgresql://metabaseuser:metabasepass@192.168.2.45:2665/soleflip')
    
    try:
        # Find the most recent batch (should be our re-import)
        latest_batch = await conn.fetchrow(
            """SELECT id, source_file, total_records, processed_records, status, created_at
               FROM integration.import_batches 
               ORDER BY created_at DESC LIMIT 1"""
        )
        
        if latest_batch:
            batch_id = str(latest_batch['id'])
            print(f"Latest batch: {batch_id[:8]}")
            print(f"  File: {latest_batch['source_file']}")
            print(f"  Records: {latest_batch['processed_records']}/{latest_batch['total_records']}")
            print(f"  Status: {latest_batch['status']}")
            
            # Check transactions with destination data
            transactions_with_destination = await conn.fetchval(
                """SELECT COUNT(*) 
                   FROM sales.transactions 
                   WHERE notes LIKE $1 
                   AND (buyer_destination_country IS NOT NULL OR buyer_destination_city IS NOT NULL)""",
                f"%batch {batch_id}%"
            )
            
            total_transactions = await conn.fetchval(
                """SELECT COUNT(*) 
                   FROM sales.transactions 
                   WHERE notes LIKE $1""",
                f"%batch {batch_id}%"
            )
            
            print(f"\nTransactions created: {total_transactions}")
            print(f"Transactions with destination data: {transactions_with_destination}")
            
            if transactions_with_destination > 0:
                # Show sample transactions with destination data
                sample_transactions = await conn.fetch(
                    """SELECT external_id, buyer_destination_country, buyer_destination_city, sale_price
                       FROM sales.transactions 
                       WHERE notes LIKE $1 
                       AND (buyer_destination_country IS NOT NULL OR buyer_destination_city IS NOT NULL)
                       LIMIT 10""",
                    f"%batch {batch_id}%"
                )
                
                print("\nSample transactions with destination data:")
                for txn in sample_transactions:
                    print(f"  {txn['external_id']}: {txn['buyer_destination_country']}, {txn['buyer_destination_city']} (€{txn['sale_price']})")
            
            # Country statistics
            country_stats = await conn.fetch(
                """SELECT buyer_destination_country, COUNT(*) as count
                   FROM sales.transactions 
                   WHERE notes LIKE $1 
                   AND buyer_destination_country IS NOT NULL
                   GROUP BY buyer_destination_country
                   ORDER BY count DESC
                   LIMIT 10""",
                f"%batch {batch_id}%"
            )
            
            if country_stats:
                print("\nTop destination countries:")
                for stat in country_stats:
                    print(f"  {stat['buyer_destination_country']}: {stat['count']} transactions")
        
        # Overall statistics
        print("\n" + "="*50)
        print("Overall transaction statistics:")
        
        total_transactions = await conn.fetchval("SELECT COUNT(*) FROM sales.transactions")
        transactions_with_destinations = await conn.fetchval(
            "SELECT COUNT(*) FROM sales.transactions WHERE buyer_destination_country IS NOT NULL"
        )
        
        print(f"Total transactions in database: {total_transactions}")
        print(f"Transactions with destination data: {transactions_with_destinations}")
        print(f"Percentage with destination data: {(transactions_with_destinations/total_transactions*100):.1f}%")
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(check_new_destination_data())