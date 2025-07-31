"""
Data Validation System
Replaces chaotic SQL validation with clean, testable Python validators
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import re
from decimal import Decimal, InvalidOperation
from dataclasses import dataclass
import structlog

logger = structlog.get_logger(__name__)

@dataclass
class ValidationResult:
    """Result of data validation"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    normalized_data: List[Dict[str, Any]]

class BaseValidator:
    """Base class for all data validators"""
    
    def __init__(self):
        self.required_fields = []
        self.optional_fields = []
        self.field_types = {}
        self.field_patterns = {}
    
    async def validate_batch(self, data: List[Dict[str, Any]]) -> ValidationResult:
        """Validate a batch of records"""
        errors = []
        warnings = []
        normalized_data = []
        
        for idx, record in enumerate(data):
            try:
                normalized_record = await self.validate_record(record, idx)
                normalized_data.append(normalized_record)
            except ValidationError as e:
                errors.extend([f"Row {idx + 1}: {error}" for error in e.errors])
                # Add original record with error flag
                normalized_data.append({**record, "_validation_error": True})
            except Exception as e:
                errors.append(f"Row {idx + 1}: Unexpected validation error: {str(e)}")
                normalized_data.append({**record, "_validation_error": True})
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            normalized_data=normalized_data
        )
    
    async def validate_record(self, record: Dict[str, Any], row_idx: int) -> Dict[str, Any]:
        """Validate and normalize a single record"""
        errors = []
        
        # Check required fields
        for field in self.required_fields:
            if field not in record or record[field] is None or str(record[field]).strip() == "":
                errors.append(f"Missing required field: {field}")
        
        if errors:
            raise ValidationError(errors)
        
        # Normalize the record
        normalized = await self.normalize_record(record)
        
        return normalized
    
    async def normalize_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize record data - to be implemented by subclasses"""
        return record
    
    def normalize_currency(self, value: Any) -> Optional[Decimal]:
        """Normalize currency values"""
        if value is None:
            return None
        
        # Handle NaN values from pandas
        if isinstance(value, float):
            import math
            if math.isnan(value) or math.isinf(value):
                return None
        
        # Convert to string and clean
        value_str = str(value).strip()
        if not value_str or value_str.lower() in ['nan', 'inf', '-inf']:
            return None
        
        # Remove currency symbols and spaces
        cleaned = re.sub(r'[€$£¥,\s]', '', value_str)
        
        # Handle European decimal format (comma as decimal separator)
        if ',' in cleaned and '.' not in cleaned:
            cleaned = cleaned.replace(',', '.')
        elif ',' in cleaned and '.' in cleaned:
            # Both comma and dot - assume comma is thousands separator
            cleaned = cleaned.replace(',', '')
        
        try:
            return Decimal(cleaned)
        except (InvalidOperation, ValueError):
            raise ValidationError([f"Invalid currency format: {value}"])
    
    def normalize_date(self, value: Any, formats: List[str] = None) -> Optional[datetime]:
        """Normalize date values"""
        if value is None:
            return None
        
        value_str = str(value).strip()
        if not value_str:
            return None
        
        # Handle StockX timezone format: convert "+00" to "+0000"
        if ' +' in value_str and value_str.endswith(' +00'):
            value_str = value_str.replace(' +00', ' +0000')
        
        # Default date formats to try
        if formats is None:
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d',
                '%d.%m.%Y',
                '%d/%m/%Y',
                '%m/%d/%Y',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M:%SZ'
            ]
        
        for fmt in formats:
            try:
                return datetime.strptime(value_str, fmt)
            except ValueError:
                continue
        
        raise ValidationError([f"Invalid date format: {value}"])

class ValidationError(Exception):
    """Custom validation error"""
    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__(f"Validation failed: {'; '.join(errors)}")

class StockXValidator(BaseValidator):
    """Validator for StockX export data"""
    
    def __init__(self):
        super().__init__()
        self.required_fields = [
            'Order Number',
            'Sale Date', 
            'Item',
            'Listing Price'
        ]
        self.optional_fields = [
            'SKU',
            'Sku Size',  # Size is optional for non-shoes
            'Size',      # Alternative size field
            'Seller Fee',
            'Payment Processing',
            'Shipping Fee',
            'Total Payout',
            'Total Gross Amount (Total Payout)',  # StockX format
            'Seller Name',
            'Buyer Country',
            'Invoice Number'
        ]
    
    async def normalize_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize StockX record"""
        normalized = {}
        
        # Basic field mapping
        normalized['order_number'] = str(record.get('Order Number', '')).strip()
        normalized['item_name'] = str(record.get('Item', '')).strip()
        normalized['sku'] = str(record.get('SKU', '')).strip()
        normalized['size'] = self._normalize_size(record.get('Size'))
        
        # Date normalization - StockX uses UTC timezone format
        normalized['sale_date'] = self.normalize_date(
            record.get('Sale Date'),
            ['%Y-%m-%d %H:%M:%S %z', '%Y-%m-%d %H:%M:%S', '%m/%d/%Y %H:%M:%S', '%m/%d/%Y']
        )
        
        # Currency normalization
        normalized['listing_price'] = self.normalize_currency(record.get('Listing Price'))
        normalized['seller_fee'] = self.normalize_currency(record.get('Seller Fee'))
        normalized['payment_processing'] = self.normalize_currency(record.get('Payment Processing'))
        normalized['shipping_fee'] = self.normalize_currency(record.get('Shipping Fee'))
        normalized['total_payout'] = self.normalize_currency(record.get('Total Payout'))
        
        # Calculate net profit if not provided
        if all(x is not None for x in [normalized['listing_price'], normalized['seller_fee'], 
                                      normalized['payment_processing'], normalized['shipping_fee']]):
            normalized['net_profit'] = (
                normalized['listing_price'] - 
                normalized['seller_fee'] - 
                normalized['payment_processing'] - 
                normalized['shipping_fee']
            )
        
        # Additional fields
        normalized['seller_name'] = str(record.get('Seller Name', '')).strip()
        normalized['buyer_country'] = str(record.get('Buyer Country', '')).strip()
        normalized['invoice_number'] = str(record.get('Invoice Number', '')).strip()
        
        # Metadata
        normalized['source'] = 'stockx'
        normalized['imported_at'] = datetime.now()
        
        return normalized
    
    def _normalize_size(self, size_value: Any) -> str:
        """Normalize shoe sizes"""
        if size_value is None:
            return "Unknown"
        
        size_str = str(size_value).strip().upper()
        
        # Handle common size formats
        if size_str in ['N/A', '', 'NULL']:
            return "One Size"
        
        # Add US prefix if it's just a number
        if re.match(r'^\d+\.?\d*$', size_str):
            return f"US {size_str}"
        
        return size_str

class NotionValidator(BaseValidator):
    """Validator for Notion export data"""
    
    def __init__(self):
        super().__init__()
        self.required_fields = [
            'id',
            'name'
        ]
        self.optional_fields = [
            'database_id',
            'properties',
            'last_edited_time',
            'created_time'
        ]
    
    async def normalize_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize Notion record"""
        normalized = {}
        
        # Basic fields
        normalized['notion_page_id'] = str(record.get('id', '')).strip()
        normalized['notion_database_id'] = str(record.get('database_id', '')).strip()
        normalized['item_name'] = str(record.get('name', '')).strip()
        
        # Extract properties if available
        properties = record.get('properties', {})
        if isinstance(properties, dict):
            # Extract common properties
            normalized['brand'] = self._extract_property(properties, 'brand')
            normalized['size'] = self._extract_property(properties, 'size')
            normalized['purchase_price'] = self._extract_currency_property(properties, 'purchase_price')
            normalized['target_price'] = self._extract_currency_property(properties, 'target_price')
            normalized['status'] = self._extract_property(properties, 'status')
            
            # Extract order references
            normalized['stockx_order_number'] = self._extract_property(properties, 'stockx_order')
            normalized['alias_order_number'] = self._extract_property(properties, 'alias_order')
        
        # Dates
        if 'last_edited_time' in record:
            normalized['last_edited'] = self.normalize_date(
                record['last_edited_time'],
                ['%Y-%m-%dT%H:%M:%S.%fZ']
            )
        
        # Metadata
        normalized['source'] = 'notion'
        normalized['imported_at'] = datetime.now()
        
        return normalized
    
    def _extract_property(self, properties: Dict, prop_name: str) -> Optional[str]:
        """Extract string property from Notion properties"""
        prop_data = properties.get(prop_name, {})
        
        # Handle different property types
        if isinstance(prop_data, dict):
            # Rich text property
            if 'rich_text' in prop_data and prop_data['rich_text']:
                return prop_data['rich_text'][0].get('text', {}).get('content', '')
            
            # Title property
            if 'title' in prop_data and prop_data['title']:
                return prop_data['title'][0].get('text', {}).get('content', '')
            
            # Select property
            if 'select' in prop_data and prop_data['select']:
                return prop_data['select'].get('name', '')
        
        return None
    
    def _extract_currency_property(self, properties: Dict, prop_name: str) -> Optional[Decimal]:
        """Extract currency property from Notion properties"""
        prop_data = properties.get(prop_name, {})
        
        if isinstance(prop_data, dict) and 'number' in prop_data:
            try:
                return Decimal(str(prop_data['number']))
            except (InvalidOperation, ValueError, TypeError):
                pass
        
        return None

class SalesValidator(BaseValidator):
    """Validator for manual sales CSV data"""
    
    def __init__(self):
        super().__init__()
        self.required_fields = [
            'SKU',
            'Sale Date',
            'Status'
        ]
        self.optional_fields = [
            'Gross Buy',
            'Net Buy', 
            'Gross Sale',
            'Net Sale',
            'Platform'
        ]
    
    async def normalize_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize sales record"""
        normalized = {}
        
        # Basic fields
        normalized['sku'] = str(record.get('SKU', '')).strip()
        normalized['status'] = str(record.get('Status', '')).strip().lower()
        
        # Date - try German format first
        try:
            normalized['sale_date'] = self.normalize_date(
                record.get('Sale Date'),
                ['%d. %B %Y', '%d.%m.%Y', '%Y-%m-%d']
            )
        except ValidationError as e:
            # Fallback to standard formats
            normalized['sale_date'] = self.normalize_date(record.get('Sale Date'))
        
        # Financial data
        normalized['gross_buy'] = self.normalize_currency(record.get('Gross Buy'))
        normalized['net_buy'] = self.normalize_currency(record.get('Net Buy'))
        normalized['gross_sale'] = self.normalize_currency(record.get('Gross Sale'))
        normalized['net_sale'] = self.normalize_currency(record.get('Net Sale'))
        
        # Calculate profit if possible
        if normalized['net_sale'] and normalized['net_buy']:
            normalized['profit'] = normalized['net_sale'] - normalized['net_buy']
        
        # Platform
        normalized['platform'] = str(record.get('Platform', 'Manual')).strip()
        
        # Metadata
        normalized['source'] = 'sales'
        normalized['imported_at'] = datetime.now()
        
        return normalized