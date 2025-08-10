#!/usr/bin/env python3
"""
API Upload Test Script
Tests the StockX CSV upload functionality
"""
import tempfile
import os
from fastapi.testclient import TestClient
from main import app

def test_api_upload():
    """Test the API upload functionality"""
    client = TestClient(app)
    
    print("=" * 60)
    print("API UPLOAD FUNCTIONALITY TEST")
    print("=" * 60)
    
    # 1. Health Check
    print("\n1. Health Check...")
    response = client.get('/health')
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print("   [OK] API is healthy")
    else:
        print("   [FAIL] API health check failed")
        return False
    
    # 2. StockX CSV Upload Test (Validation Only)
    print("\n2. StockX CSV Upload Test (Validation Only)...")
    
    # Create test CSV content
    csv_content = """Item,Sku Size,Order Number,Sale Date,Listing Price,Seller Fee,Total Gross Amount (Total Payout)
Nike Dunk Low Panda,10.5,39224521-39124280,2022-07-07 21:40:06 +00,69,2.07,58.93
Air Jordan 1 High OG,9,39224522-39124281,2022-07-08 15:30:12 +00,150,4.50,130.50
Adidas Yeezy Boost 350,8.5,39224523-39124282,2022-07-09 12:15:30 +00,220,6.60,193.40
"""
    
    # Create temporary CSV file
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8')
    temp_file.write(csv_content)
    temp_file.close()
    
    try:
        with open(temp_file.name, 'rb') as f:
            files = {'file': ('test_stockx.csv', f, 'text/csv')}
            data = {'validate_only': True, 'batch_size': 1000}
            
            response = client.post('/api/v1/integration/webhooks/stockx/upload', 
                                 files=files, data=data)
            
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"   [OK] Validation successful!")
                print(f"   - Status: {result['status']}")
                print(f"   - Total Records: {result['total_records']}")
                print(f"   - Validation Errors: {len(result['validation_errors'])}")
                print(f"   - Filename: {result['filename']}")
            else:
                print(f"   [FAIL] Validation failed: {response.text}")
                return False
                
    finally:
        os.unlink(temp_file.name)
    
    # 3. StockX CSV Upload Test (Full Import)
    print("\n3. StockX CSV Upload Test (Full Import)...")
    
    temp_file2 = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8')
    temp_file2.write(csv_content)
    temp_file2.close()
    
    try:
        with open(temp_file2.name, 'rb') as f:
            files = {'file': ('test_stockx_import.csv', f, 'text/csv')}
            data = {'validate_only': False, 'batch_size': 1000}
            
            response = client.post('/api/v1/integration/webhooks/stockx/upload',
                                 files=files, data=data)
            
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"   [OK] Import successful!")
                print(f"   - Status: {result['status']}")
                print(f"   - Records Processed: {result['total_records']}")
                print(f"   - Imported: {result['imported']}")
                print(f"   - Batch ID: {result['batch_id']}")
            else:
                print(f"   [FAIL] Import failed: {response.text}")
                return False
                
    finally:
        os.unlink(temp_file2.name)
    
    # 4. Error Handling Test - Invalid File Type
    print("\n4. Error Handling Test (Invalid File Type)...")
    response = client.post('/api/v1/integration/webhooks/stockx/upload',
                          files={'file': ('invalid.txt', b'invalid content', 'text/plain')},
                          data={'validate_only': True})
    
    print(f"   Status: {response.status_code}")
    if response.status_code == 400:
        print("   [OK] Correct error handling for invalid file type")
        print(f"   - Error: {response.json()['detail']}")
    else:
        print(f"   [FAIL] Unexpected response: {response.text}")
        return False
    
    # 5. Error Handling Test - Missing Required Columns
    print("\n5. Error Handling Test (Missing Required Columns)...")
    
    invalid_csv = "Wrong,Column,Names\n1,2,3\n"
    temp_file3 = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8')
    temp_file3.write(invalid_csv)
    temp_file3.close()
    
    try:
        with open(temp_file3.name, 'rb') as f:
            files = {'file': ('invalid_columns.csv', f, 'text/csv')}
            data = {'validate_only': True}
            
            response = client.post('/api/v1/integration/webhooks/stockx/upload',
                                 files=files, data=data)
            
            print(f"   Status: {response.status_code}")
            if response.status_code == 400:
                print("   [OK] Correct error handling for missing columns")
                print(f"   - Error: {response.json()['detail']}")
            else:
                print(f"   [FAIL] Unexpected response: {response.text}")
                return False
                
    finally:
        os.unlink(temp_file3.name)
    
    print("\n" + "=" * 60)
    print("[SUCCESS] ALL TESTS PASSED - API UPLOAD FUNCTIONALITY WORKS!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = test_api_upload()
    exit(0 if success else 1)