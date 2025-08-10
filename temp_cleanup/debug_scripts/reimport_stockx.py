import asyncio
import pandas as pd
from domains.integration.services.import_processor import import_processor, SourceType

async def reimport_stockx():
    print("Re-importing original StockX CSV with destination data...")
    
    # Read original CSV file
    csv_file = 'stockx_historical_seller_sales_report_ab3c4afb-7b84-11eb-a20e-124738b50e12_1751996312862.csv'
    
    try:
        # Read CSV with multiple encoding attempts
        df = None
        for encoding in ['utf-8', 'utf-8-sig', 'latin1', 'cp1252']:
            try:
                df = pd.read_csv(csv_file, encoding=encoding)
                print(f"Successfully read CSV with {encoding} encoding")
                break
            except UnicodeDecodeError:
                continue
        
        if df is None:
            print("Could not read CSV file with any encoding")
            return
        
        print(f"CSV contains {len(df)} records")
        print(f"Columns: {list(df.columns)}")
        
        # Check for destination columns
        if 'Buyer Destination Country' in df.columns:
            print("[OK] Buyer Destination Country column found")
            sample_countries = df['Buyer Destination Country'].dropna().unique()[:5]
            print(f"Sample countries: {list(sample_countries)}")
        else:
            print("[MISSING] Buyer Destination Country column missing")
            
        if 'Buyer Destination City' in df.columns:
            print("[OK] Buyer Destination City column found")
            sample_cities = df['Buyer Destination City'].dropna().unique()[:5]
            print(f"Sample cities: {list(sample_cities)}")
        else:
            print("[MISSING] Buyer Destination City column missing")
        
        # Convert to records
        raw_data = df.to_dict('records')
        
        # Import via processor
        print("\nStarting import process...")
        result = await import_processor.process_import(
            source_type=SourceType.STOCKX,
            data=raw_data,
            metadata={'filename': csv_file, 'batch_size': 100},
            raw_data=raw_data
        )
        
        print(f"\nImport completed:")
        print(f"  Batch ID: {result.batch_id}")
        print(f"  Total Records: {result.total_records}")
        print(f"  Processed: {result.processed_records}")
        print(f"  Errors: {result.error_records}")
        print(f"  Status: {result.status}")
        
        if result.validation_errors:
            print(f"  Validation Errors: {result.validation_errors[:5]}")
        
        # Check if transactions were created with destination data
        if result.processed_records > 0:
            import asyncpg
            conn = await asyncpg.connect('postgresql://metabaseuser:metabasepass@192.168.2.45:2665/soleflip')
            
            try:
                # Check transactions for this batch
                transactions_with_destination = await conn.fetchval(
                    """SELECT COUNT(*) 
                       FROM sales.transactions 
                       WHERE notes LIKE $1 
                       AND (buyer_destination_country IS NOT NULL OR buyer_destination_city IS NOT NULL)""",
                    f"%batch {result.batch_id}%"
                )
                
                total_transactions = await conn.fetchval(
                    """SELECT COUNT(*) 
                       FROM sales.transactions 
                       WHERE notes LIKE $1""",
                    f"%batch {result.batch_id}%"
                )
                
                print(f"\nTransactions created: {total_transactions}")
                print(f"Transactions with destination data: {transactions_with_destination}")
                
                # Show sample transactions with destination data
                if transactions_with_destination > 0:
                    sample_transactions = await conn.fetch(
                        """SELECT external_id, buyer_destination_country, buyer_destination_city
                           FROM sales.transactions 
                           WHERE notes LIKE $1 
                           AND (buyer_destination_country IS NOT NULL OR buyer_destination_city IS NOT NULL)
                           LIMIT 5""",
                        f"%batch {result.batch_id}%"
                    )
                    
                    print("\nSample transactions with destination data:")
                    for txn in sample_transactions:
                        print(f"  {txn['external_id']}: {txn['buyer_destination_country']}, {txn['buyer_destination_city']}")
                        
            finally:
                await conn.close()
        
    except Exception as e:
        print(f"Error during import: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(reimport_stockx())