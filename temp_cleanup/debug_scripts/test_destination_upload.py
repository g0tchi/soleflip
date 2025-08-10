import asyncio
import pandas as pd
from domains.integration.services.import_processor import import_processor, SourceType

async def test_destination_upload():
    print("Testing destination data upload...")
    
    # Read test CSV
    df = pd.read_csv('test_destination.csv')
    raw_data = df.to_dict('records')
    
    print(f"Test data: {raw_data}")
    
    # Process import
    result = await import_processor.process_import(
        source_type=SourceType.STOCKX,
        data=raw_data,
        metadata={'filename': 'test_destination.csv', 'batch_size': 10},
        raw_data=raw_data
    )
    
    print(f"Import result: {result}")
    print(f"Batch ID: {result.batch_id}")
    
    # Check if transactions were created with destination data
    import asyncpg
    conn = await asyncpg.connect('postgresql://metabaseuser:metabasepass@192.168.2.45:2665/soleflip')
    
    try:
        # Check transactions for this batch
        transaction = await conn.fetchrow(
            """SELECT id, external_id, buyer_destination_country, buyer_destination_city, notes 
               FROM sales.transactions 
               WHERE notes LIKE $1 LIMIT 1""",
            f"%batch {result.batch_id}%"
        )
        
        if transaction:
            print(f"Transaction found:")
            print(f"  ID: {transaction['id']}")
            print(f"  External ID: {transaction['external_id']}")
            print(f"  Destination Country: {transaction['buyer_destination_country']}")
            print(f"  Destination City: {transaction['buyer_destination_city']}")
        else:
            print("No transaction found!")
            
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(test_destination_upload())