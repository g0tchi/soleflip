import asyncio
import asyncpg

async def check_import_records():
    conn = await asyncpg.connect('postgresql://metabaseuser:metabasepass@192.168.2.45:2665/soleflip')
    
    try:
        # Check what import records we actually have
        print("Checking existing import records...")
        
        # Get summary of all batches
        batches = await conn.fetch(
            """SELECT ib.id, ib.source_type, ib.source_file, ib.total_records, ib.processed_records, ib.status, ib.created_at,
                      COUNT(ir.id) as actual_records
               FROM integration.import_batches ib
               LEFT JOIN integration.import_records ir ON ib.id = ir.batch_id
               GROUP BY ib.id, ib.source_type, ib.source_file, ib.total_records, ib.processed_records, ib.status, ib.created_at
               ORDER BY ib.created_at DESC"""
        )
        
        print("\nImport Batches Summary:")
        for batch in batches:
            batch_id = str(batch['id'])[:8]
            print(f"Batch {batch_id}: {batch['status']}")
            print(f"  File: {batch['source_file'] or 'N/A'}")
            print(f"  Records: {batch['actual_records']}/{batch['total_records']} (processed: {batch['processed_records']})")
            print(f"  Created: {batch['created_at']}")
            print()
        
        # Check if we have any records with the specific source file
        stockx_file_records = await conn.fetchval(
            """SELECT COUNT(*) 
               FROM integration.import_records ir
               JOIN integration.import_batches ib ON ir.batch_id = ib.id
               WHERE ib.source_file LIKE '%stockx_historical_seller_sales_report%'"""
        )
        
        print(f"Records from StockX historical file: {stockx_file_records}")
        
        # Check what order numbers we have in the database
        sample_orders = await conn.fetch(
            """SELECT DISTINCT ir.source_data->>'Order Number' as order_number
               FROM integration.import_records ir
               WHERE ir.source_data->>'Order Number' IS NOT NULL
               ORDER BY ir.source_data->>'Order Number'
               LIMIT 10"""
        )
        
        print("\nSample Order Numbers in database:")
        for order in sample_orders:
            print(f"  {order['order_number']}")
            
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(check_import_records())