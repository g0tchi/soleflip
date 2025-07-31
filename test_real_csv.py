#!/usr/bin/env python3
"""
Test API with real CSV files in the project
"""
import os
from fastapi.testclient import TestClient
from main import app

def test_with_real_csv_files():
    """Test with real CSV files from the project"""
    client = TestClient(app)
    
    print("=" * 60)
    print("TESTING WITH REAL CSV FILES")
    print("=" * 60)
    
    # Find CSV files in the project
    csv_files = [f for f in os.listdir('.') if f.endswith('.csv')]
    
    print(f"Found {len(csv_files)} CSV files:")
    for csv_file in csv_files:
        print(f"  - {csv_file}")
    
    # Test each CSV file
    for csv_file in csv_files:
        print(f"\nTesting {csv_file}...")
        print("-" * 40)
        
        try:
            with open(csv_file, 'rb') as f:
                files = {'file': (csv_file, f, 'text/csv')}
                data = {'validate_only': True, 'batch_size': 1000}
                
                response = client.post('/api/v1/integration/webhooks/stockx/upload', 
                                     files=files, data=data)
                
                print(f"   Status: {response.status_code}")
                if response.status_code == 200:
                    result = response.json()
                    print(f"   [OK] File processed successfully!")
                    print(f"   - Status: {result['status']}")
                    print(f"   - Total Records: {result['total_records']}")
                    print(f"   - Validation Errors: {len(result['validation_errors'])}")
                    
                    if result['validation_errors']:
                        print("   - First few errors:")
                        for error in result['validation_errors'][:3]:
                            print(f"     * {error}")
                        if len(result['validation_errors']) > 3:
                            print(f"     * ... and {len(result['validation_errors']) - 3} more")
                else:
                    print(f"   [FAIL] Processing failed")
                    print(f"   - Error: {response.text}")
                    
        except Exception as e:
            print(f"   [ERROR] Exception occurred: {e}")
    
    print(f"\n" + "=" * 60)
    print("REAL CSV FILE TESTING COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    test_with_real_csv_files()