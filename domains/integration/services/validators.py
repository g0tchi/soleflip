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
    
    def extract_brand_from_name(self, product_name: str) -> Optional[str]:
        """Universal brand extraction from product names"""
        if not product_name:
            return None
        
        # Common brand patterns in sneaker/fashion names
        brand_patterns = {
            # Nike and Jordan brands
            r'^Nike\s': 'Nike',
            r'^Air\s': 'Nike',
            r'^Wmns\s': 'Nike',
            r'Jordan\s': 'Nike Jordan',
            r'Travis Scott x': 'Nike Jordan',
            r'Air Max': 'Nike',
            r'Air Force': 'Nike',
            r'Dunk': 'Nike',
            r'Blazer': 'Nike',
            r'Cortez': 'Nike',
            r'P-6000': 'Nike',
            r'React': 'Nike',
            r'Zoom': 'Nike',
            r'Vapormax': 'Nike',
            r'Presto': 'Nike',
            
            # Adidas
            r'^adidas': 'Adidas',
            r'^Yeezy': 'Adidas',
            r'Campus': 'Adidas',
            r'Gazelle': 'Adidas',
            r'Forum': 'Adidas',
            r'Question': 'Adidas',
            r'UltraBoost': 'Adidas',
            r'Bad Bunny x': 'Adidas',
            r'Gucci x': 'Adidas',
            r'Samba': 'Adidas',
            r'Stan Smith': 'Adidas',
            r'Superstar': 'Adidas',
            r'NMD': 'Adidas',
            r'Originals': 'Adidas',
            
            # New Balance
            r'^\d{3,4}[RV]?\s': 'New Balance',  # Model numbers like 2002R, 574, etc.
            r'^Wmns \d{3}': 'New Balance',
            r'^New Balance': 'New Balance',
            
            # ASICS
            r'Gel\s': 'ASICS',
            r'GmbH x': 'ASICS',
            r'HAL STUDIOS x': 'ASICS',
            r'Kiko Kostadinov x': 'ASICS',
            r'^ASICS': 'ASICS',
            
            # Converse
            r'Chuck Taylor': 'Converse',
            r'All Star': 'Converse',
            r'^Converse': 'Converse',
            r'Chuck 70': 'Converse',
            r'One Star': 'Converse',
            
            # Puma
            r'^Puma': 'Puma',
            r'Suede': 'Puma',
            r'Palermo': 'Puma',
            r'Speedcat': 'Puma',
            r'RS-X': 'Puma',
            
            # Vans
            r'^Vans': 'Vans',
            r'Old Skool': 'Vans',
            r'Authentic': 'Vans',
            r'Era': 'Vans',
            r'Slip-On': 'Vans',
            r'Sk8-Hi': 'Vans',
            
            # Stone Island
            r'Stone Island': 'Stone Island',
            
            # Off-White
            r'Off-White': 'Off-White',
            r'OFF-WHITE': 'Off-White',
            
            # Fear of God
            r'Fear of God': 'Fear of God',
            r'FOG': 'Fear of God',
            r'Essentials': 'Fear of God',
            
            # UGG
            r'UGG': 'UGG',
            r'Classic Ultra Mini': 'UGG',
            r'Classic Short': 'UGG',
            r'Tasman': 'UGG',
            r'Scuffette': 'UGG',
            
            # Timberland  
            r'Timberland': 'Timberland',
            r'6-Inch Premium': 'Timberland',
            
            # Crocs
            r'Crocs': 'Crocs',
            r'Classic Clog': 'Crocs',
            
            # Dr. Martens
            r'Dr\. Martens': 'Dr. Martens',
            r'1460': 'Dr. Martens',
            r'1461': 'Dr. Martens',
            
            # Salomon
            r'Salomon': 'Salomon',
            r'^Salomon': 'Salomon',
            r'XT-6': 'Salomon',
            r'XT-4': 'Salomon',
            r'XT-Wings': 'Salomon',
            r'Speedcross': 'Salomon',
            r'S/LAB': 'Salomon',
            r'ACS Pro': 'Salomon',  # ACS Pro Serie hinzugefügt
            r'ACS+': 'Salomon',
            
            # Hoka
            r'Hoka': 'Hoka',
            r'Clifton': 'Hoka',
            r'Bondi': 'Hoka',
            
            # On Running
            r'^On\s': 'On Running',
            r'Cloud': 'On Running',
            
            # Golden Goose
            r'Golden Goose': 'Golden Goose',
            r'Super-Star': 'Golden Goose',
            
            # Fashion/Streetwear Brands  
            r'Telfar': 'Telfar',
            r'Palace': 'Palace',
            r'Supreme': 'Supreme',
            r'Stussy|Stüssy': 'Stussy',
            r'Kith': 'Kith',
            r'Essentials': 'Fear of God Essentials',
            
            # Luxury/High Fashion
            r'Louis Vuitton': 'Louis Vuitton',
            r'Balenciaga': 'Balenciaga',
            r'Gucci': 'Gucci',
            r'Bottega Veneta': 'Bottega Veneta',
            r'Margiela': 'Maison Margiela',
            r'Maison Margiela': 'Maison Margiela',
            r'Rick Owens': 'Rick Owens',
            r'Comme des Garcons': 'Comme des Garcons',
            r'CDG': 'Comme des Garcons',
            
            # Accessories/Bags
            r'Eastpak': 'Eastpak',
            r'JanSport': 'JanSport',
            r'Taschen': 'Taschen',
            
            # Toy/Collectibles (wie Mattel aus deinen Daten)
            r'Mattel': 'Mattel',
            r'Hot Wheels': 'Mattel',
            r'Cybertruck': 'Mattel',
            r'MEGA Construx': 'Mattel',
            
            # KAWS Collaborations
            r'KAWS': 'KAWS',
            
            # Artist/Designer Collaborations
            r'Takashi Murakami': 'Murakami',
            r'Field Boot': 'Timberland',
            r'Earthkeepers': 'Timberland',
            
            # Telfar
            r'Telfar': 'Telfar',
            r'Shopping Bag': 'Telfar',
            
            # Eastpak
            r'Eastpak': 'Eastpak',
            r'Padded Pak\'r': 'Eastpak',
            r'Wyoming': 'Eastpak',
            
            # The North Face
            r'The North Face': 'The North Face',
            r'TNF': 'The North Face',
            r'North Face': 'The North Face',
            r'Nuptse': 'The North Face',
            r'Denali': 'The North Face',
            r'Base Camp': 'The North Face',
            
            # Palace
            r'Palace': 'Palace',
            r'P-Cap': 'Palace',
            
            # Y-3 (Yohji Yamamoto x Adidas)
            r'Y-3': 'Y-3',
            r'Yohji Yamamoto': 'Y-3',
            r'Kusari': 'Y-3',
            r'Kaiwa': 'Y-3',
            r'Runner 4D': 'Y-3',
            
            # Salomon
            r'XT-4': 'Salomon',
            r'XT-6': 'Salomon',
            r'Salomon': 'Salomon',
            r'Speedcross': 'Salomon',
            
            # Other brands
            r'Crocs': 'Crocs',
            r'Classic Clog': 'Crocs',
            r'Salehe Bembury x': 'Crocs',
            r'Tom Sachs x': 'Nike',
            r'Clifton': 'HOKA',
            r'Classic Cowboy Boot': 'Dr. Martens',
            r'Converse': 'Converse',
            r'Chuck': 'Converse',
            r'Reebok': 'Reebok',
            r'Club C': 'Reebok'
        }
        
        # Try to match brand patterns
        for pattern, brand in brand_patterns.items():
            if re.search(pattern, product_name, re.IGNORECASE):
                return brand
        
        # If no pattern matches, try to extract first word as potential brand
        first_word = product_name.split()[0] if product_name.split() else None
        if first_word and len(first_word) > 2:
            # Common brand names that might appear as first word
            known_brands = [
                'Nike', 'Adidas', 'Yeezy', 'Jordan', 'Converse', 'Vans', 
                'Puma', 'Reebok', 'ASICS', 'Salomon', 'HOKA', 'Crocs',
                'UGG', 'Timberland', 'Telfar', 'Eastpak', 'Palace'
            ]
            if first_word in known_brands:
                return first_word
        
        return None  # Unable to determine brand
    
    def normalize_currency(self, value: Any) -> Optional[Decimal]:
        """Normalize currency values from various string formats."""
        if value is None:
            return None

        if isinstance(value, float):
            import math
            if math.isnan(value) or math.isinf(value):
                return None
        
        value_str = str(value).strip()
        if not value_str or value_str.lower() in ['nan', 'inf', '-inf']:
            return None

        # Remove currency symbols and whitespace
        cleaned_str = re.sub(r'[€$£¥\s]', '', value_str)

        # Determine if comma or dot is the decimal separator
        last_dot = cleaned_str.rfind('.')
        last_comma = cleaned_str.rfind(',')

        if last_comma > last_dot:
            # Format is likely "1.234,56". Remove dots, replace comma with dot.
            cleaned_str = cleaned_str.replace('.', '').replace(',', '.')
        elif last_dot > last_comma:
            # Format is likely "1,234.56". Remove commas.
            cleaned_str = cleaned_str.replace(',', '')
        else:
            # No separators or only one type, e.g., "1234.56" or "1234,56"
            cleaned_str = cleaned_str.replace(',', '.')

        try:
            return Decimal(cleaned_str)
        except InvalidOperation:
            raise ValidationError([f"Invalid currency format: {value}"])

    def normalize_date(self, value: Any, formats: List[str] = None) -> Optional[datetime]:
        """Normalize date values from various string formats."""
        if value is None:
            return None

        value_str = str(value).strip()
        if not value_str:
            return None

        # Handle special cases like German months before trying standard formats
        german_months = {
            'Januar': 'January', 'Februar': 'February', 'März': 'March',
            'April': 'April', 'Mai': 'May', 'Juni': 'June', 'Juli': 'July',
            'August': 'August', 'September': 'September', 'Oktober': 'October',
            'November': 'November', 'Dezember': 'December'
        }
        for de, en in german_months.items():
            value_str = value_str.replace(de, en)

        # Handle StockX timezone format
        if ' +' in value_str and value_str.endswith(' +00'):
            value_str = value_str.replace(' +00', ' +0000')

        # Use dateutil.parser for robust parsing
        try:
            from dateutil import parser
            return parser.parse(value_str)
        except (ValueError, TypeError):
            # Fallback to trying specific formats if dateutil fails
            pass

        default_formats = [
            '%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y', '%m/%d/%Y',
            '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%SZ', '%d. %B %Y'
        ]
        
        for fmt in formats or default_formats:
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

class AliasValidator(BaseValidator):
    """Validator for Alias export data (Alias = GOAT's selling platform)"""
    
    def __init__(self):
        super().__init__()
        self.required_fields = [
            'ORDER_NUMBER',
            'NAME',
            'PRODUCT_PRICE_CENTS_SALE_PRICE',
            'CREDIT_DATE'
        ]
        self.optional_fields = [
            'USERNAME',
            'SKU', 
            'SIZE',
            'PURCHASED_DATE'
        ]
    
    async def normalize_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize Alias record"""
        normalized = {}
        
        # Basic field mapping
        normalized['order_number'] = str(record.get('ORDER_NUMBER', '')).strip()
        normalized['item_name'] = str(record.get('NAME', '')).strip()
        normalized['sku'] = str(record.get('SKU', '')).strip()
        normalized['size'] = self._normalize_size(record.get('SIZE'))
        normalized['supplier'] = str(record.get('USERNAME', '')).strip()
        
        # Brand extraction from product name (Alias doesn't have separate brand columns)
        normalized['brand'] = self._extract_brand_from_name(normalized['item_name'])
        
        # Date normalization - Alias uses DD/MM/YY format
        normalized['sale_date'] = self.normalize_date(
            record.get('CREDIT_DATE'),
            ['%d/%m/%y', '%d/%m/%Y', '%d.%m.%y', '%d.%m.%Y']
        )
        
        normalized['purchase_date'] = self.normalize_date(
            record.get('PURCHASED_DATE'),
            ['%d/%m/%y', '%d/%m/%Y', '%d.%m.%y', '%d.%m.%Y']
        )
        
        # Currency normalization - Alias PRODUCT_PRICE_CENTS_SALE_PRICE contains full USD amounts
        sale_price = record.get('PRODUCT_PRICE_CENTS_SALE_PRICE')
        if sale_price is not None:
            try:
                normalized['sale_price'] = Decimal(str(sale_price))  # Direct USD amount, no conversion needed
            except (InvalidOperation, ValueError):
                raise ValidationError([f"Invalid price format: {sale_price}"])
        else:
            normalized['sale_price'] = None
        
        # Alias doesn't provide fees - set defaults
        normalized['platform_fee'] = None
        normalized['shipping_fee'] = None
        normalized['net_profit'] = normalized['sale_price']  # No fees to subtract
        
        # Platform identification
        normalized['platform'] = 'alias'  # Alias = GOAT's selling platform
        normalized['source_type'] = 'alias'
        
        # Generate unique transaction ID for database
        normalized['external_id'] = f"alias_{normalized['order_number']}"
        
        # Additional metadata
        normalized['status'] = 'completed'  # Alias exports are completed sales
        
        # Flag for StockX name prioritization in product matching
        normalized['_requires_stockx_name_priority'] = True
        
        return normalized
    
    def _normalize_size(self, size_value: Any) -> Optional[str]:
        """Normalize size values for Alias"""
        if size_value is None:
            return None
        
        size_str = str(size_value).strip()
        if not size_str or size_str.lower() in ['n/a', 'none', '']:
            return None
        
        # Handle clothing sizes (like 106 for pants)
        if size_str.isdigit() and len(size_str) >= 2:
            # Could be clothing size or shoe size
            size_int = int(size_str)
            if size_int > 50:  # Likely clothing size
                return f"Size {size_str}"
            else:
                return size_str  # Shoe size
        
        # Handle decimal shoe sizes
        try:
            size_float = float(size_str)
            if 3 <= size_float <= 20:  # Typical shoe size range
                return str(size_float)
        except ValueError:
            pass
        
        return size_str  # Return as-is if can't categorize
    
    def _extract_brand_from_name(self, product_name: str) -> Optional[str]:
        """Extract brand from product name for Alias imports"""
        return self.extract_brand_from_name(product_name)

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
            'Style',     # The actual SKU from StockX exports
            'Sku Size',  # Size is optional for non-shoes
            'Size',      # Alternative size field
            'Seller Fee',
            'Payment Processing',
            'Shipping Fee',
            'Total Payout',
            'Total Gross Amount (Total Payout)',  # StockX format
            'Seller Name',
            'Buyer Country',
            'Buyer Destination Country',
            'Buyer Destination City',
            'Invoice Number'
        ]
    
    async def normalize_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize StockX record"""
        normalized = {}
        
        # Basic field mapping
        normalized['order_number'] = str(record.get('Order Number', '')).strip()
        normalized['item_name'] = str(record.get('Item', '')).strip()
        # Try Style first (actual StockX SKU), then fall back to SKU field
        normalized['sku'] = str(record.get('Style', record.get('SKU', ''))).strip()
        # Try multiple size field names (StockX uses 'Sku Size')
        size_value = record.get('Sku Size') or record.get('Size')  
        normalized['size'] = self._normalize_size(size_value)
        
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
        
        # Brand extraction from product name (StockX doesn't have separate brand column)
        normalized['brand'] = self.extract_brand_from_name(normalized['item_name'])
        
        # Additional fields
        normalized['seller_name'] = str(record.get('Seller Name', '')).strip()
        normalized['buyer_country'] = str(record.get('Buyer Country', '')).strip()
        normalized['buyer_destination_country'] = str(record.get('Buyer Destination Country', '')).strip()
        normalized['buyer_destination_city'] = str(record.get('Buyer Destination City', '')).strip()
        normalized['invoice_number'] = str(record.get('Invoice Number', '')).strip()
        
        # Metadata
        normalized['source'] = 'stockx'
        normalized['imported_at'] = datetime.now()
        
        return normalized
    
    def _normalize_size(self, size_value: Any) -> str:
        """Normalize shoe sizes"""
        if size_value is None:
            return "Unknown"
        
        # Handle NaN values from pandas
        if isinstance(size_value, float):
            import math
            if math.isnan(size_value):
                return "One Size"  # NaN often means "not applicable" for size
        
        size_str = str(size_value).strip().upper()
        
        # Handle common size formats
        if size_str in ['N/A', '', 'NULL', 'NAN']:
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
            'Product Name',
            'Brand',
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
        
        # Brand extraction - try Brand column first, then extract from Product Name
        normalized['brand'] = str(record.get('Brand', '')).strip() or None
        if not normalized['brand']:
            product_name = record.get('Product Name')
            if product_name:
                normalized['brand'] = self.extract_brand_from_name(str(product_name).strip())
        
        # Platform
        normalized['platform'] = str(record.get('Platform', 'Manual')).strip()
        
        # Metadata
        normalized['source'] = 'sales'
        normalized['imported_at'] = datetime.now()
        
        return normalized