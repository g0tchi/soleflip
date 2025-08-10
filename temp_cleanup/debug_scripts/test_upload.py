import asyncio
import pandas as pd
from domains.integration.services.import_processor import import_processor, SourceType

async def test_upload():
    print("Testing small upload with transaction creation...")
    
    # Read test CSV
    df = pd.read_csv('test_small.csv')
    raw_data = df.to_dict('records')
    
    print(f"Test data: {raw_data}")
    
    # Process import
    result = await import_processor.process_import(
        source_type=SourceType.STOCKX,
        data=raw_data,
        metadata={'filename': 'test_small.csv', 'batch_size': 10},
        raw_data=raw_data
    )
    
    print(f"Import result: {result}")
    print(f"Batch ID: {result.batch_id}")
    
    # Check if transactions were created
    import asyncpg
    conn = await asyncpg.connect('postgresql://metabaseuser:metabasepass@192.168.2.45:2665/soleflip')
    
    try:
        # Check transactions for this batch
        transactions = await conn.fetchval(
            "SELECT COUNT(*) FROM sales.transactions WHERE notes LIKE $1",
            f"%batch {result.batch_id}%"
        )
        print(f"Transactions created: {transactions}")
        
        if transactions > 0:
            # Show transaction details
            transaction = await conn.fetchrow(
                "SELECT * FROM sales.transactions WHERE notes LIKE $1 LIMIT 1",
                f"%batch {result.batch_id}%"
            )
            print(f"Sample transaction: {dict(transaction)}")
            
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(test_upload())