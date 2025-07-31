"""
Data Parsers for Import Processing
Handles CSV, JSON, and Excel file parsing with robust error handling
and data normalization for different source formats.
"""
from typing import List, Dict, Any, Optional, Union
import pandas as pd
import json
import io
from pathlib import Path
from abc import ABC, abstractmethod
import structlog
from dataclasses import dataclass
from enum import Enum

logger = structlog.get_logger(__name__)

class ParseError(Exception):
    """Custom exception for parsing errors"""
    pass

class FileFormat(Enum):
    CSV = "csv"
    JSON = "json" 
    EXCEL = "excel"
    UNKNOWN = "unknown"

@dataclass
class ParseResult:
    """Result of parsing operation"""
    data: List[Dict[str, Any]]
    format_detected: FileFormat
    encoding_used: Optional[str] = None
    rows_parsed: int = 0
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
        self.rows_parsed = len(self.data)

class BaseParser(ABC):
    """Abstract base parser class"""
    
    @abstractmethod
    def parse(self, content: Union[bytes, str, io.IOBase], **kwargs) -> ParseResult:
        """Parse content and return structured data"""
        pass
    
    @abstractmethod
    def can_handle(self, content: Union[bytes, str], filename: str = None) -> bool:
        """Check if this parser can handle the given content"""
        pass

class CSVParser(BaseParser):
    """CSV file parser with multiple encoding and delimiter support"""
    
    SUPPORTED_ENCODINGS = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1']
    SUPPORTED_DELIMITERS = [',', ';', '\t', '|']
    
    def can_handle(self, content: Union[bytes, str], filename: str = None) -> bool:
        """Check if content appears to be CSV"""
        if filename and not filename.lower().endswith('.csv'):
            return False
            
        # Try to detect CSV structure
        try:
            sample = content[:1000] if isinstance(content, bytes) else content[:1000]
            if isinstance(sample, bytes):
                sample = sample.decode('utf-8', errors='ignore')
            
            # Look for common CSV indicators
            has_commas = ',' in sample
            has_quotes = '"' in sample
            has_newlines = '\n' in sample
            
            return has_commas and has_newlines
        except:
            return False
    
    def parse(self, content: Union[bytes, str, io.IOBase], **kwargs) -> ParseResult:
        """
        Parse CSV content with multiple strategies for maximum compatibility
        
        Args:
            content: CSV content as bytes, string, or file-like object
            **kwargs: Additional parsing options
                - delimiter: Force specific delimiter
                - encoding: Force specific encoding
                - max_rows: Limit number of rows to parse
        """
        logger.info("Starting CSV parsing")
        
        # Convert content to string if needed
        if isinstance(content, bytes):
            decoded_content = self._decode_content(content)
        elif hasattr(content, 'read'):
            raw_content = content.read()
            if isinstance(raw_content, bytes):
                decoded_content = self._decode_content(raw_content)
            else:
                decoded_content = raw_content
        else:
            decoded_content = content
            
        # Parse with multiple strategies
        df, encoding_used, warnings = self._parse_with_strategies(decoded_content, **kwargs)
        
        if df is None or len(df) == 0:
            raise ParseError("Could not parse CSV file or file is empty")
        
        # Convert to list of dictionaries
        data = df.to_dict('records')
        
        logger.info(f"CSV parsing completed", rows=len(data), encoding=encoding_used)
        
        return ParseResult(
            data=data,
            format_detected=FileFormat.CSV,
            encoding_used=encoding_used,
            warnings=warnings
        )
    
    def _decode_content(self, content: bytes) -> str:
        """Try multiple encodings to decode content"""
        for encoding in self.SUPPORTED_ENCODINGS:
            try:
                return content.decode(encoding)
            except UnicodeDecodeError:
                continue
        
        # Fallback with error handling
        return content.decode('utf-8', errors='replace')
    
    def _parse_with_strategies(self, content: str, **kwargs) -> tuple:
        """Try multiple parsing strategies"""
        warnings = []
        encoding_used = kwargs.get('encoding', 'utf-8')
        
        # Strategy 1: pandas with auto-detection
        strategies = [
            # Standard CSV
            {'sep': None, 'engine': 'python'},
            # Common delimiters
            *[{'sep': delim, 'quotechar': '"', 'skipinitialspace': True} 
              for delim in self.SUPPORTED_DELIMITERS],
            # Lenient parsing
            {'sep': ',', 'quoting': 1, 'on_bad_lines': 'skip'},
            {'sep': ',', 'engine': 'python', 'on_bad_lines': 'skip'},
        ]
        
        for strategy in strategies:
            try:
                # Apply max_rows limit if specified
                if kwargs.get('max_rows'):
                    strategy['nrows'] = kwargs['max_rows']
                
                df = pd.read_csv(io.StringIO(content), **strategy)
                
                if len(df) > 0 and len(df.columns) > 1:
                    # Clean column names
                    df.columns = df.columns.str.strip()
                    
                    logger.debug(f"CSV parsing successful with strategy", 
                               strategy=strategy, rows=len(df), cols=len(df.columns))
                    return df, encoding_used, warnings
                    
            except Exception as e:
                warnings.append(f"Strategy failed: {str(e)[:100]}")
                continue
        
        return None, encoding_used, warnings

class JSONParser(BaseParser):
    """JSON file parser with schema flexibility"""
    
    def can_handle(self, content: Union[bytes, str], filename: str = None) -> bool:
        """Check if content appears to be JSON"""
        if filename and not filename.lower().endswith('.json'):
            return False
            
        try:
            test_content = content[:100] if isinstance(content, bytes) else content[:100]
            if isinstance(test_content, bytes):
                test_content = test_content.decode('utf-8', errors='ignore')
            
            # Look for JSON indicators
            stripped = test_content.strip()
            return stripped.startswith('{') or stripped.startswith('[')
        except:
            return False
    
    def parse(self, content: Union[bytes, str, io.IOBase], **kwargs) -> ParseResult:
        """
        Parse JSON content with flexible schema handling
        
        Args:
            content: JSON content
            **kwargs: Additional options
                - flatten_nested: Whether to flatten nested objects
                - array_field: Field name containing the array data
        """
        logger.info("Starting JSON parsing")
        
        # Convert to string if needed  
        if isinstance(content, bytes):
            content_str = content.decode('utf-8')
        elif hasattr(content, 'read'):
            raw = content.read()
            content_str = raw.decode('utf-8') if isinstance(raw, bytes) else raw
        else:
            content_str = content
            
        try:
            # Parse JSON
            json_data = json.loads(content_str)
            
            # Handle different JSON structures
            if isinstance(json_data, list):
                data = json_data
            elif isinstance(json_data, dict):
                # Check for common array fields
                array_field = kwargs.get('array_field')
                if array_field and array_field in json_data:
                    data = json_data[array_field]
                elif 'results' in json_data:
                    data = json_data['results']
                elif 'data' in json_data:
                    data = json_data['data']
                elif 'items' in json_data:
                    data = json_data['items']
                else:
                    # Single object - wrap in list
                    data = [json_data]
            else:
                raise ParseError(f"Unsupported JSON structure: {type(json_data)}")
            
            # Flatten nested objects if requested
            if kwargs.get('flatten_nested', False):
                data = self._flatten_objects(data)
            
            logger.info(f"JSON parsing completed", records=len(data))
            
            return ParseResult(
                data=data,
                format_detected=FileFormat.JSON
            )
            
        except json.JSONDecodeError as e:
            raise ParseError(f"Invalid JSON format: {str(e)}")
        except Exception as e:
            raise ParseError(f"JSON parsing error: {str(e)}")
    
    def _flatten_objects(self, data: List[Dict]) -> List[Dict]:
        """Flatten nested objects in JSON data"""
        flattened = []
        
        for item in data:
            flat_item = {}
            self._flatten_dict(item, flat_item)
            flattened.append(flat_item)
            
        return flattened
    
    def _flatten_dict(self, obj: Dict, parent: Dict, prefix: str = ''):
        """Recursively flatten dictionary"""
        for key, value in obj.items():
            new_key = f"{prefix}.{key}" if prefix else key
            
            if isinstance(value, dict):
                self._flatten_dict(value, parent, new_key)
            elif isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
                # Handle array of objects - take first item or join
                parent[new_key] = json.dumps(value)
            else:
                parent[new_key] = value

class ExcelParser(BaseParser):
    """Excel file parser (.xlsx, .xls)"""
    
    def can_handle(self, content: Union[bytes, str], filename: str = None) -> bool:
        """Check if content appears to be Excel"""
        if filename:
            return filename.lower().endswith(('.xlsx', '.xls'))
        return False
    
    def parse(self, content: Union[bytes, str, io.IOBase], **kwargs) -> ParseResult:
        """
        Parse Excel content
        
        Args:
            content: Excel content
            **kwargs: Additional options
                - sheet_name: Specific sheet to parse
                - header_row: Row number containing headers
        """
        logger.info("Starting Excel parsing")
        
        try:
            # Handle different input types
            if isinstance(content, bytes):
                excel_data = pd.read_excel(io.BytesIO(content), 
                                         sheet_name=kwargs.get('sheet_name', 0),
                                         header=kwargs.get('header_row', 0))
            elif hasattr(content, 'read'):
                excel_data = pd.read_excel(content,
                                         sheet_name=kwargs.get('sheet_name', 0), 
                                         header=kwargs.get('header_row', 0))
            else:
                raise ParseError("Invalid Excel content format")
            
            if len(excel_data) == 0:
                raise ParseError("Excel file is empty")
            
            # Clean column names
            excel_data.columns = excel_data.columns.str.strip()
            
            # Convert to records
            data = excel_data.to_dict('records')
            
            logger.info(f"Excel parsing completed", rows=len(data), cols=len(excel_data.columns))
            
            return ParseResult(
                data=data,
                format_detected=FileFormat.EXCEL
            )
            
        except Exception as e:
            raise ParseError(f"Excel parsing error: {str(e)}")

class UniversalParser:
    """Universal parser that auto-detects format and uses appropriate parser"""
    
    def __init__(self):
        self.parsers = {
            FileFormat.CSV: CSVParser(),
            FileFormat.JSON: JSONParser(),
            FileFormat.EXCEL: ExcelParser(),
        }
    
    def detect_format(self, content: Union[bytes, str], filename: str = None) -> FileFormat:
        """Auto-detect file format"""
        logger.debug("Detecting file format", filename=filename)
        
        # Try each parser's detection method
        for format_type, parser in self.parsers.items():
            if parser.can_handle(content, filename):
                logger.info(f"Format detected", format=format_type.value, filename=filename)
                return format_type
        
        logger.warning("Could not detect file format", filename=filename)
        return FileFormat.UNKNOWN
    
    def parse(self, content: Union[bytes, str, io.IOBase], 
              filename: str = None, format_hint: FileFormat = None, **kwargs) -> ParseResult:
        """
        Parse content with automatic format detection
        
        Args:
            content: File content
            filename: Original filename for format detection
            format_hint: Hint about expected format
            **kwargs: Parser-specific options
        """
        logger.info("Starting universal parsing", filename=filename, format_hint=format_hint)
        
        # Use format hint if provided, otherwise detect
        if format_hint and format_hint in self.parsers:
            detected_format = format_hint
        else:
            detected_format = self.detect_format(content, filename)
        
        if detected_format == FileFormat.UNKNOWN:
            raise ParseError(f"Unsupported file format for file: {filename}")
        
        # Use appropriate parser
        parser = self.parsers[detected_format]
        result = parser.parse(content, **kwargs)
        
        logger.info("Universal parsing completed", 
                   format=detected_format.value, rows=result.rows_parsed)
        
        return result

# Convenience function for easy usage
def parse_file(content: Union[bytes, str, io.IOBase], 
               filename: str = None, **kwargs) -> ParseResult:
    """
    Convenience function to parse any supported file format
    
    Args:
        content: File content
        filename: Original filename
        **kwargs: Parser options
    
    Returns:
        ParseResult with parsed data
    
    Example:
        result = parse_file(csv_bytes, 'data.csv')
        records = result.data
    """
    parser = UniversalParser()
    return parser.parse(content, filename, **kwargs)