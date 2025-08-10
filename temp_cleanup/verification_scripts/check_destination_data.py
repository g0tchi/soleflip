import asyncio
import asyncpg
import json

async def check_destination_data():
    conn = await asyncpg.connect('postgresql://metabaseuser:metabasepass@192.168.2.45:2665/soleflip')
    
    try:
        # Check if original import records have destination data
        print("Checking import records for destination data...")
        
        # Check a few records from recent batches
        records = await conn.fetch(
            """SELECT id, source_data, processed_data 
               FROM integration.import_records 
               WHERE batch_id IN (
                   SELECT id FROM integration.import_batches 
                   WHERE status = 'completed' AND processed_records > 0 
                   ORDER BY created_at DESC LIMIT 1
               )
               LIMIT 3"""
        )
        
        for record in records:
            print(f"\nRecord {str(record['id'])[:8]}:")
            
            # Check source_data
            source_data = record['source_data']
            if source_data:
                print("Source data keys:", list(source_data.keys()))
                if 'Buyer Destination Country' in source_data:
                    print(f"  Source Destination Country: {source_data.get('Buyer Destination Country')}")
                if 'Buyer Destination City' in source_data:
                    print(f"  Source Destination City: {source_data.get('Buyer Destination City')}")
            
            # Check processed_data
            processed_data = record['processed_data']
            if processed_data:
                print("Processed data keys:", list(processed_data.keys()))
                if 'buyer_destination_country' in processed_data:
                    print(f"  Processed Destination Country: {processed_data.get('buyer_destination_country')}")
                if 'buyer_destination_city' in processed_data:
                    print(f"  Processed Destination City: {processed_data.get('buyer_destination_city')}")
        
        # Check our test records
        print("\n" + "="*50)
        print("Checking our test records...")
        
        test_records = await conn.fetch(
            """SELECT t.external_id, t.buyer_destination_country, t.buyer_destination_city
               FROM sales.transactions t 
               WHERE t.external_id LIKE 'stockx_TEST-%'
               ORDER BY t.created_at DESC"""
        )
        
        for record in test_records:
            print(f"Test Transaction {record['external_id']}:")
            print(f"  Country: {record['buyer_destination_country']}")
            print(f"  City: {record['buyer_destination_city']}")
            
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(check_destination_data())