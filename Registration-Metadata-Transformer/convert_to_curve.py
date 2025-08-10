#!/usr/bin/env python3
"""
Curve Converter - Transform Master Catalog exports to Curve Work Import format
"""

import argparse
import sys
import re
import yaml
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import unicodedata


class CurveConverter:
    def __init__(self, mapping_file: str, strict: bool = False):
        self.strict = strict
        self.errors = []
        self.load_mapping(mapping_file)
        
    def load_mapping(self, mapping_file: str):
        """Load mapping configuration from YAML file"""
        with open(mapping_file, 'r') as f:
            self.config = yaml.safe_load(f)
        self.columns = self.config['columns']
        self.lookups = self.config.get('lookups', {})
        self.validation_rules = self.config.get('validation_rules', {})
        
    def transform_value(self, value: Any, transform: str, lookups: Dict = None) -> Any:
        """Apply transformation to a value"""
        if pd.isna(value) or value == '':
            return ''
            
        value = str(value).strip()
        
        if transform == "strip":
            return value.strip()
        elif transform == "uppercase":
            return value.upper()
        elif transform == "lowercase":
            return value.lower()
        elif transform == "titlecase":
            return value.title()
        elif transform == "strip_diacritics":
            return self.strip_diacritics(value)
        elif transform.startswith("to_date:"):
            format_str = transform.split(":", 1)[1]
            return self.parse_date(value, format_str)
        elif transform == "percent_0_100":
            return self.convert_to_percent_100(value)
        elif transform == "percent_0_1":
            return self.convert_to_percent_1(value)
        elif transform.startswith("padleft:"):
            parts = transform.split(":")
            width, fill_char = int(parts[1]), parts[2]
            return value.zfill(width) if fill_char == '0' else value.rjust(width, fill_char)
        elif transform.startswith("concat:"):
            separator = transform.split(":", 1)[1]
            # This would need multiple source columns - handled in convert_row
            return value
        elif transform.startswith("split:"):
            separator = transform.split(":", 1)[1]
            return value.split(separator)
        elif transform == "format_iswc":
            return self.format_iswc(value)
        elif transform == "format_isrc":
            return self.format_isrc(value)
        elif transform == "format_ipi":
            return self.format_ipi(value)
        elif transform == "format_duration":
            return self.format_duration(value)
        elif transform == "map_role":
            return self.lookups.get('role_codes', {}).get(value, value)
        elif transform == "map_society":
            return self.lookups.get('society_codes', {}).get(value, value)
        elif transform == "map_territory":
            return self.lookups.get('territories', {}).get(value, value)
        elif transform == "extract_writer_name":
            return self.extract_writer_name(value)
        elif transform == "extract_writer_society":
            return self.extract_writer_society(value)
        elif transform == "extract_writer_ipi":
            return self.extract_writer_ipi(value)
        elif transform == "extract_mechanical_share":
            return self.extract_mechanical_share(value)
        elif transform == "extract_performance_share":
            return self.extract_performance_share(value)
        elif transform == "extract_additional_writer_name":
            return self.extract_additional_writer_name(value)
        elif transform == "extract_additional_writer_society":
            return self.extract_additional_writer_society(value)
        elif transform == "extract_additional_mechanical_share":
            return self.extract_additional_mechanical_share(value)
        elif transform == "extract_additional_performance_share":
            return self.extract_additional_performance_share(value)
        elif transform == "extract_publisher_name":
            return self.extract_publisher_name(value)
        elif transform == "extract_publisher_society":
            return self.extract_publisher_society(value)
        elif transform == "extract_publisher_mechanical_share":
            return self.extract_publisher_mechanical_share(value)
        elif transform == "extract_publisher_performance_share":
            return self.extract_publisher_performance_share(value)
        else:
            return value
    
    def strip_diacritics(self, text: str) -> str:
        """Remove diacritical marks from text"""
        return ''.join(c for c in unicodedata.normalize('NFD', text)
                      if unicodedata.category(c) != 'Mn')
    
    def parse_date(self, date_str: str, output_format: str) -> str:
        """Parse flexible date input and return in specified format"""
        if not date_str or pd.isna(date_str):
            return ''
            
        # Handle pandas Timestamp objects
        if hasattr(date_str, 'strftime'):
            return date_str.strftime(output_format)
            
        # Clean the date string first
        date_str = str(date_str).strip()
        # Remove timestamp part if present
        if ' 00:00:00' in date_str:
            date_str = date_str.replace(' 00:00:00', '')
        
        # Common date formats to try
        formats = [
            '%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d',
            '%m-%d-%Y', '%d-%m-%Y', '%Y.%m.%d', '%m.%d.%Y'
        ]
        
        for fmt in formats:
            try:
                parsed = datetime.strptime(date_str, fmt)
                return parsed.strftime(output_format)
            except ValueError:
                continue
                
        # If no format works, return original
        return date_str
    
    def convert_to_percent_100(self, value: str) -> float:
        """Convert percentage to 0-100 scale"""
        try:
            val = float(str(value).replace('%', ''))
            # If value is between 0-1, convert to 0-100
            if 0 <= val <= 1:
                val *= 100
            return round(val, 2)
        except (ValueError, TypeError):
            return 0.0
    
    def convert_to_percent_1(self, value: str) -> float:
        """Convert percentage to 0-1 scale"""
        try:
            val = float(str(value).replace('%', ''))
            # If value is between 0-100, convert to 0-1
            if val > 1:
                val /= 100
            return round(val, 4)
        except (ValueError, TypeError):
            return 0.0
    
    def format_iswc(self, value: str) -> str:
        """Format ISWC code"""
        if not value or pd.isna(value):
            return ''
        # Remove any existing formatting and re-format
        digits = re.sub(r'[^0-9]', '', str(value))
        if len(digits) == 10:
            return f"T-{digits[:9]}-{digits[9]}"
        return str(value)
    
    def format_isrc(self, value: str) -> str:
        """Format ISRC code"""
        if not value or pd.isna(value):
            return ''
        
        # Handle multiple ISRCs separated by newlines or commas
        value_str = str(value).strip()
        if '\n' in value_str:
            # Take the first ISRC if multiple
            value_str = value_str.split('\n')[0].strip()
        elif ',' in value_str:
            value_str = value_str.split(',')[0].strip()
            
        # Basic ISRC formatting
        value_str = value_str.upper().replace('-', '').replace(' ', '')
        if len(value_str) == 12:
            return f"{value_str[:2]}-{value_str[2:5]}-{value_str[5:7]}-{value_str[7:]}"
        return value_str
    
    def format_ipi(self, value: str) -> str:
        """Format IPI code"""
        if not value or pd.isna(value):
            return ''
        # Keep only digits
        digits = re.sub(r'[^0-9]', '', str(value))
        return digits
    
    def format_duration(self, value: str) -> str:
        """Format duration (MM:SS or seconds)"""
        if not value or pd.isna(value):
            return ''
        # If already in MM:SS format, return as-is
        if ':' in str(value):
            return str(value)
        # If numeric, assume seconds and convert to MM:SS
        try:
            seconds = int(float(value))
            minutes = seconds // 60
            seconds = seconds % 60
            return f"{minutes:02d}:{seconds:02d}"
        except (ValueError, TypeError):
            return str(value)
    
    # MCAT-specific extraction methods
    def extract_writer_name(self, value: str) -> str:
        """Extract writer name from Payday Writers field"""
        if not value or pd.isna(value):
            return ''
        # Look for pattern like "Jorge Omar Barreiro (pka "Jorge Pelegrin") (ASCAP) - 50%"
        # Extract everything before the first '(' or ' - '
        match = re.search(r'^([^(]+?)(?:\s*\(|$)', str(value))
        if match:
            return match.group(1).strip()
        return str(value).split('(')[0].split(' - ')[0].strip()
    
    def extract_writer_society(self, value: str) -> str:
        """Extract writer society from Payday Writers field"""
        if not value or pd.isna(value):
            return ''
        # Look for society codes in parentheses like (ASCAP), (BMI), (SESAC)
        societies = re.findall(r'\((ASCAP|BMI|SESAC|PRS|GEMA|SACEM|SOCAN|APRA)\)', str(value))
        return societies[0] if societies else ''
    
    def extract_writer_ipi(self, value: str) -> str:
        """Extract IPI from Payday Writers' CAE/IPI# field"""
        if not value or pd.isna(value):
            return ''
        # Look for IPI pattern like "Barreiro (ASCAP) - 00002162936"
        match = re.search(r'(\d{9,11})', str(value))
        return match.group(1) if match else ''
    
    def extract_mechanical_share(self, value: str) -> float:
        """Extract mechanical share from Payday Shares field"""
        if not value or pd.isna(value):
            return 0.0
        # Look for "Payday Total: XX%" pattern
        match = re.search(r'Payday Total:\s*(\d+(?:\.\d+)?)%', str(value))
        if match:
            return float(match.group(1))
        # Fallback: look for first percentage
        match = re.search(r'(\d+(?:\.\d+)?)%', str(value))
        return float(match.group(1)) if match else 0.0
    
    def extract_performance_share(self, value: str) -> float:
        """Extract performance share from Payday Shares field (same as mechanical)"""
        return self.extract_mechanical_share(value)
    
    def extract_additional_writer_name(self, value: str) -> str:
        """Extract additional writer name from Add'l Writer field"""
        if not value or pd.isna(value):
            return ''
        # Parse entries like "Khalil Jewell - 50%" or complex multi-line entries
        lines = str(value).split('\n')
        for line in lines:
            if ':' in line:
                # Handle "Dameon Hughes: 1.41%" format
                name = line.split(':')[0].strip()
                if name and not name.replace(' ', '').replace('.', '').isdigit():
                    return name
            elif ' - ' in line and '%' in line:
                # Handle "Khalil Jewell - 50%" format  
                name = line.split(' - ')[0].strip()
                if name:
                    return name
        # Fallback: return first non-empty line
        first_line = lines[0].strip() if lines else ''
        return first_line.split(':')[0].split(' - ')[0].strip()
    
    def extract_additional_writer_society(self, value: str) -> str:
        """Extract society from additional writer info"""
        if not value or pd.isna(value):
            return ''
        # Look for society codes in the additional writer field
        societies = re.findall(r'\b(ASCAP|BMI|SESAC|PRS|GEMA|SACEM|SOCAN|APRA)\b', str(value))
        return societies[0] if societies else ''
    
    def extract_additional_mechanical_share(self, value: str) -> float:
        """Extract mechanical share from Add'l Writer field"""
        if not value or pd.isna(value):
            return 0.0
        # Look for percentage pattern
        percentages = re.findall(r'(\d+(?:\.\d+)?)%', str(value))
        return float(percentages[0]) if percentages else 0.0
    
    def extract_additional_performance_share(self, value: str) -> float:
        """Extract performance share from Add'l Writer field (same as mechanical)"""
        return self.extract_additional_mechanical_share(value)
    
    def extract_publisher_name(self, value: str) -> str:
        """Extract publisher name from Payday Shares field"""
        if not value or pd.isna(value):
            return ''
        # Look for publisher patterns like "Payday Tunes (ASCAP)" or "Payday Empire Music (BMI)"
        # Publishers typically come first in the shares field
        match = re.search(r'^([^-\n]+(?:Payday[^-\n]*?))\s*(?:\(|obo|-)', str(value))
        if match:
            publisher = match.group(1).strip()
            # Clean up the publisher name
            publisher = re.sub(r'\s*\([^)]*\).*$', '', publisher)  # Remove society info
            return publisher.strip()
        return ''
    
    def extract_publisher_society(self, value: str) -> str:
        """Extract publisher society from Payday Shares field"""
        if not value or pd.isna(value):
            return ''
        # Look for society in publisher context
        societies = re.findall(r'\((ASCAP|BMI|SESAC|PRS|GEMA|SACEM|SOCAN|APRA)\)', str(value))
        return societies[0] if societies else ''
    
    def extract_publisher_mechanical_share(self, value: str) -> float:
        """Extract publisher mechanical share from Payday Shares field"""
        if not value or pd.isna(value):
            return 0.0
        # Look for "Payday Total: XX%" pattern first
        match = re.search(r'Payday Total:\s*(\d+(?:\.\d+)?)%', str(value))
        if match:
            return float(match.group(1))
        return 0.0
    
    def extract_publisher_performance_share(self, value: str) -> float:
        """Extract publisher performance share (same as mechanical)"""
        return self.extract_publisher_mechanical_share(value)
    
    def validate_value(self, value: Any, validation: str, column_name: str) -> List[str]:
        """Validate a value according to validation rules"""
        errors = []
        
        if validation == "required" and (not value or pd.isna(value) or str(value).strip() == ''):
            errors.append(f"Required field '{column_name}' is empty")
        elif validation == "date_format":
            if value and not re.match(r'^\d{4}-\d{2}-\d{2}$', str(value)):
                errors.append(f"Invalid date format in '{column_name}': {value}")
        elif validation == "iswc_format":
            pattern = self.validation_rules.get('iswc_pattern', r'^T-\d{9}-\d$')
            if value and not re.match(pattern, str(value)):
                errors.append(f"Invalid ISWC format in '{column_name}': {value}")
        elif validation == "isrc_format":
            pattern = self.validation_rules.get('isrc_pattern', r'^[A-Z]{2}[A-Z0-9]{3}\d{7}$')
            if value and not re.match(pattern, str(value).replace('-', '')):
                errors.append(f"Invalid ISRC format in '{column_name}': {value}")
        elif validation == "ipi_format":
            pattern = self.validation_rules.get('ipi_pattern', r'^\d{9}$|^\d{11}$')
            if value and not re.match(pattern, str(value)):
                errors.append(f"Invalid IPI format in '{column_name}': {value}")
        elif validation == "share_range":
            try:
                val = float(value) if value else 0
                if not (0 <= val <= 100):
                    errors.append(f"Share value out of range (0-100) in '{column_name}': {val}")
            except (ValueError, TypeError):
                if value:  # Only error if there's a value that can't be converted
                    errors.append(f"Invalid share value in '{column_name}': {value}")
        elif validation == "valid_role":
            valid_roles = set(self.lookups.get('role_codes', {}).values())
            if value and value not in valid_roles:
                errors.append(f"Invalid role code in '{column_name}': {value}")
        elif validation == "valid_society":
            valid_societies = set(self.lookups.get('society_codes', {}).values())
            if value and value not in valid_societies:
                errors.append(f"Invalid society code in '{column_name}': {value}")
                
        return errors
    
    def validate_row(self, row: pd.Series, row_idx: int) -> List[Dict]:
        """Validate an entire row"""
        errors = []
        
        # Check required fields
        required_fields = self.validation_rules.get('required_fields', [])
        for field in required_fields:
            if not row.get(field) or pd.isna(row.get(field)) or str(row.get(field)).strip() == '':
                errors.append({
                    'row_index': row_idx,
                    'work_title': row.get('Work Title', 'Unknown'),
                    'error_code': 'REQUIRED_FIELD_MISSING',
                    'error_detail': f"Required field '{field}' is empty"
                })
        
        # Check share totals
        mech_total = 0
        perf_total = 0
        max_participants = self.validation_rules.get('max_participants', 10)
        
        for i in range(1, max_participants + 1):
            mech_col = f"Participant {i} Mechanical Share"
            perf_col = f"Participant {i} Performance Share"
            
            mech_val = row.get(mech_col, 0)
            perf_val = row.get(perf_col, 0)
            
            try:
                if mech_val and not pd.isna(mech_val):
                    mech_total += float(mech_val)
                if perf_val and not pd.isna(perf_val):
                    perf_total += float(perf_val)
            except (ValueError, TypeError):
                continue
        
        # Check if totals equal 100% (with tolerance)
        tolerance = self.validation_rules.get('share_tolerance', 0.01)
        if mech_total > 0 and abs(mech_total - 100) > tolerance:
            errors.append({
                'row_index': row_idx,
                'work_title': row.get('Work Title', 'Unknown'),
                'error_code': 'MECHANICAL_SHARES_INVALID',
                'error_detail': f"Mechanical shares total {mech_total}%, should be 100%"
            })
            
        if perf_total > 0 and abs(perf_total - 100) > tolerance:
            errors.append({
                'row_index': row_idx,
                'work_title': row.get('Work Title', 'Unknown'),
                'error_code': 'PERFORMANCE_SHARES_INVALID',
                'error_detail': f"Performance shares total {perf_total}%, should be 100%"
            })
        
        return errors
    
    def convert_row(self, row: pd.Series, row_idx: int) -> Dict:
        """Convert a single row according to mapping"""
        result = {}
        row_errors = []
        
        for col_config in self.columns:
            dest_col = col_config['dest']
            source_col = col_config.get('source')
            transform = col_config.get('transform', '')
            default = col_config.get('default', '')
            validation = col_config.get('validation')
            
            # Get source value
            if source_col and source_col in row.index:
                value = row[source_col]
            else:
                value = default
            
            # Apply transformation
            if transform:
                try:
                    value = self.transform_value(value, transform, self.lookups)
                except Exception as e:
                    row_errors.append(f"Transform error in {dest_col}: {str(e)}")
                    value = default or ''
            
            # Apply validation
            if validation:
                validation_errors = self.validate_value(value, validation, dest_col)
                row_errors.extend(validation_errors)
            
            result[dest_col] = value
        
        # Validate entire row
        row_validation_errors = self.validate_row(pd.Series(result), row_idx)
        
        # Store errors for this row
        if row_errors or row_validation_errors:
            for error in row_errors:
                self.errors.append({
                    'row_index': row_idx,
                    'work_title': result.get('Work Title', 'Unknown'),
                    'error_code': 'FIELD_ERROR',
                    'error_detail': error
                })
            self.errors.extend(row_validation_errors)
        
        return result
    
    def convert_file(self, input_file: str, output_file: str) -> bool:
        """Convert entire file"""
        try:
            # Read input file
            if input_file.endswith('.xlsx') or input_file.endswith('.xls'):
                df = pd.read_excel(input_file)
            else:
                df = pd.read_csv(input_file)
            
            print(f"Loaded {len(df)} rows from {input_file}")
            
            # Convert each row
            converted_rows = []
            for idx, row in df.iterrows():
                converted_row = self.convert_row(row, idx + 2)  # +2 for 1-based + header
                converted_rows.append(converted_row)
            
            # Create output DataFrame with exact column order from mapping
            column_order = [col['dest'] for col in self.columns]
            result_df = pd.DataFrame(converted_rows, columns=column_order)
            
            # Write output file
            if output_file.endswith('.xlsx'):
                result_df.to_excel(output_file, index=False)
            else:
                result_df.to_csv(output_file, index=False)
            
            print(f"Converted {len(result_df)} rows to {output_file}")
            
            # Write errors file if there are errors
            if self.errors:
                error_file = output_file.replace('.xlsx', '_errors.csv').replace('.csv', '_errors.csv')
                error_df = pd.DataFrame(self.errors)
                error_df.to_csv(error_file, index=False)
                print(f"Found {len(self.errors)} validation errors - see {error_file}")
                
                if self.strict:
                    print("STRICT MODE: Conversion failed due to validation errors")
                    return False
            else:
                print("No validation errors found")
            
            return True
            
        except Exception as e:
            print(f"Conversion failed: {str(e)}")
            return False


def main():
    parser = argparse.ArgumentParser(description='Convert Master Catalog to Curve Work Import format')
    parser.add_argument('--in', dest='input_file', required=True,
                       help='Input Excel/CSV file (Master Catalog)')
    parser.add_argument('--out', dest='output_file', required=True,
                       help='Output Excel/CSV file (Curve format)')
    parser.add_argument('--map', dest='mapping_file', required=True,
                       help='YAML mapping configuration file')
    parser.add_argument('--strict', action='store_true',
                       help='Fail on validation errors')
    
    args = parser.parse_args()
    
    # Validate input files exist
    if not Path(args.input_file).exists():
        print(f"Error: Input file not found: {args.input_file}")
        sys.exit(1)
    
    if not Path(args.mapping_file).exists():
        print(f"Error: Mapping file not found: {args.mapping_file}")
        sys.exit(1)
    
    # Create converter and run conversion
    converter = CurveConverter(args.mapping_file, args.strict)
    success = converter.convert_file(args.input_file, args.output_file)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()