#!/usr/bin/env python3
"""
Unit tests for Curve Converter
"""

import unittest
import sys
import os
import tempfile
import pandas as pd
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path to import converter
sys.path.append(str(Path(__file__).parent.parent))
from convert_to_curve import CurveConverter, ConfigurationError, ValidationError, TransformError


class TestCurveConverter(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        # Create a minimal mapping configuration for testing
        self.test_mapping = {
            'columns': [
                {'dest': 'Work Title', 'source': 'Title', 'transform': 'strip', 'validation': 'required'},
                {'dest': 'Participant 1 Name', 'source': 'Writer 1', 'transform': 'strip'},
                {'dest': 'Participant 1 Role', 'source': 'Writer 1 Role', 'transform': 'map_role', 'default': 'CA'},
                {'dest': 'Participant 1 Mechanical Share', 'source': 'Writer 1 Mech Share', 'transform': 'percent_0_100'},
                {'dest': 'Participant 1 Performance Share', 'source': 'Writer 1 Perf Share', 'transform': 'percent_0_100'},
            ],
            'lookups': {
                'role_codes': {'Writer': 'CA', 'Composer': 'C', 'Publisher': 'E'},
                'society_codes': {'ASCAP': 'ASCAP', 'BMI': 'BMI'},
                'territories': {'World': 'WW', 'United States': 'US'}
            },
            'validation_rules': {
                'required_fields': ['Work Title'],
                'share_tolerance': 0.01,
                'max_participants': 10
            }
        }
        
        # Create temporary mapping file
        self.temp_mapping = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        import yaml
        yaml.dump(self.test_mapping, self.temp_mapping)
        self.temp_mapping.close()
        
        self.converter = CurveConverter(self.temp_mapping.name)
    
    def tearDown(self):
        """Clean up test fixtures"""
        os.unlink(self.temp_mapping.name)
    
    def test_strip_transform(self):
        """Test strip transformation"""
        result = self.converter.transform_value('  Hello World  ', 'strip')
        self.assertEqual(result, 'Hello World')
    
    def test_uppercase_transform(self):
        """Test uppercase transformation"""
        result = self.converter.transform_value('hello world', 'uppercase')
        self.assertEqual(result, 'HELLO WORLD')
    
    def test_percent_0_100_transform(self):
        """Test percentage conversion to 0-100 scale"""
        # Test 0-1 to 0-100 conversion
        result = self.converter.transform_value('0.5', 'percent_0_100')
        self.assertEqual(result, 50.0)
        
        # Test already in 0-100 scale
        result = self.converter.transform_value('75', 'percent_0_100')
        self.assertEqual(result, 75.0)
        
        # Test percentage string
        result = self.converter.transform_value('25%', 'percent_0_100')
        self.assertEqual(result, 25.0)
    
    def test_percent_0_1_transform(self):
        """Test percentage conversion to 0-1 scale"""
        # Test 0-100 to 0-1 conversion
        result = self.converter.transform_value('50', 'percent_0_1')
        self.assertEqual(result, 0.5)
        
        # Test already in 0-1 scale
        result = self.converter.transform_value('0.25', 'percent_0_1')
        self.assertEqual(result, 0.25)
    
    def test_date_parsing(self):
        """Test date parsing and formatting"""
        # Test MM/DD/YYYY format
        result = self.converter.parse_date('01/15/2024', '%Y-%m-%d')
        self.assertEqual(result, '2024-01-15')
        
        # Test YYYY-MM-DD format (already correct)
        result = self.converter.parse_date('2024-01-15', '%Y-%m-%d')
        self.assertEqual(result, '2024-01-15')
    
    def test_iswc_formatting(self):
        """Test ISWC formatting"""
        result = self.converter.format_iswc('1234567890')
        self.assertEqual(result, 'T-123456789-0')
        
        # Test already formatted
        result = self.converter.format_iswc('T-123456789-0')
        self.assertEqual(result, 'T-123456789-0')
    
    def test_isrc_formatting(self):
        """Test ISRC formatting"""
        result = self.converter.format_isrc('USRC17607839')
        self.assertEqual(result, 'US-RC1-76-07839')
    
    def test_role_mapping(self):
        """Test role code mapping"""
        result = self.converter.transform_value('Writer', 'map_role')
        self.assertEqual(result, 'CA')
        
        # Test unmapped role (should return original)
        result = self.converter.transform_value('Unknown Role', 'map_role')
        self.assertEqual(result, 'Unknown Role')
    
    def test_duration_formatting(self):
        """Test duration formatting"""
        # Test seconds to MM:SS conversion
        result = self.converter.format_duration('225')  # 3:45
        self.assertEqual(result, '03:45')
        
        # Test already formatted duration
        result = self.converter.format_duration('3:45')
        self.assertEqual(result, '3:45')
    
    def test_validation_required_field(self):
        """Test required field validation"""
        errors = self.converter.validate_value('', 'required', 'Work Title')
        self.assertEqual(len(errors), 1)
        self.assertIn('Required field', errors[0])
        
        # Test non-empty value
        errors = self.converter.validate_value('Test Title', 'required', 'Work Title')
        self.assertEqual(len(errors), 0)
    
    def test_validation_share_range(self):
        """Test share range validation"""
        # Valid share
        errors = self.converter.validate_value('50.0', 'share_range', 'Share')
        self.assertEqual(len(errors), 0)
        
        # Invalid share (over 100)
        errors = self.converter.validate_value('150.0', 'share_range', 'Share')
        self.assertEqual(len(errors), 1)
        self.assertIn('out of range', errors[0])
        
        # Invalid share (negative)
        errors = self.converter.validate_value('-10.0', 'share_range', 'Share')
        self.assertEqual(len(errors), 1)
    
    def test_row_conversion(self):
        """Test converting a complete row"""
        test_row = pd.Series({
            'Title': '  Test Song  ',
            'Writer 1': 'John Doe',
            'Writer 1 Role': 'Writer',
            'Writer 1 Mech Share': '50',
            'Writer 1 Perf Share': '0.5'  # Test conversion from 0-1 to 0-100
        })
        
        result = self.converter.convert_row(test_row, 1)
        
        self.assertEqual(result['Work Title'], 'Test Song')
        self.assertEqual(result['Participant 1 Name'], 'John Doe')
        self.assertEqual(result['Participant 1 Role'], 'CA')
        self.assertEqual(result['Participant 1 Mechanical Share'], 50.0)
        self.assertEqual(result['Participant 1 Performance Share'], 50.0)
    
    def test_strip_diacritics(self):
        """Test diacritic removal"""
        result = self.converter.strip_diacritics('café naïve résumé')
        self.assertEqual(result, 'cafe naive resume')
    
    def test_empty_and_null_values(self):
        """Test handling of empty and null values"""
        # Test None/NaN values
        result = self.converter.transform_value(None, 'strip')
        self.assertEqual(result, '')
        
        result = self.converter.transform_value(pd.NA, 'uppercase')
        self.assertEqual(result, '')
        
        # Test empty string
        result = self.converter.transform_value('', 'strip')
        self.assertEqual(result, '')


class TestValidationRules(unittest.TestCase):
    """Test validation rules and error handling"""
    
    def setUp(self):
        self.test_mapping = {
            'columns': [
                {'dest': 'Work Title', 'source': 'Title', 'validation': 'required'},
                {'dest': 'ISWC', 'source': 'ISWC', 'validation': 'iswc_format'},
                {'dest': 'ISRC', 'source': 'ISRC', 'validation': 'isrc_format'},
                {'dest': 'Participant 1 IPI', 'source': 'IPI', 'validation': 'ipi_format'},
                {'dest': 'Registration Date', 'source': 'Date', 'validation': 'date_format'},
                {'dest': 'Participant 1 Mechanical Share', 'source': 'Share', 'validation': 'share_range'},
            ],
            'validation_rules': {
                'iswc_pattern': r'^T-\d{9}-\d$',
                'isrc_pattern': r'^[A-Z]{2}[A-Z0-9]{3}\d{7}$',
                'ipi_pattern': r'^\d{9}$|^\d{11}$'
            }
        }
        
        self.temp_mapping = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        import yaml
        yaml.dump(self.test_mapping, self.temp_mapping)
        self.temp_mapping.close()
        
        self.converter = CurveConverter(self.temp_mapping.name)
    
    def tearDown(self):
        os.unlink(self.temp_mapping.name)
    
    def test_iswc_validation(self):
        """Test ISWC format validation"""
        # Valid ISWC
        errors = self.converter.validate_value('T-123456789-0', 'iswc_format', 'ISWC')
        self.assertEqual(len(errors), 0)
        
        # Invalid ISWC
        errors = self.converter.validate_value('INVALID', 'iswc_format', 'ISWC')
        self.assertEqual(len(errors), 1)
        self.assertIn('Invalid ISWC format', errors[0])
    
    def test_isrc_validation(self):
        """Test ISRC format validation"""
        # Valid ISRC (without hyphens)
        errors = self.converter.validate_value('USRC17607839', 'isrc_format', 'ISRC')
        self.assertEqual(len(errors), 0)
        
        # Valid ISRC (with hyphens - should be stripped)
        errors = self.converter.validate_value('US-RC1-76-07839', 'isrc_format', 'ISRC')
        self.assertEqual(len(errors), 0)
        
        # Invalid ISRC
        errors = self.converter.validate_value('INVALID', 'isrc_format', 'ISRC')
        self.assertEqual(len(errors), 1)
    
    def test_ipi_validation(self):
        """Test IPI format validation"""
        # Valid 9-digit IPI
        errors = self.converter.validate_value('123456789', 'ipi_format', 'IPI')
        self.assertEqual(len(errors), 0)
        
        # Valid 11-digit IPI
        errors = self.converter.validate_value('12345678901', 'ipi_format', 'IPI')
        self.assertEqual(len(errors), 0)
        
        # Invalid IPI (wrong length)
        errors = self.converter.validate_value('12345', 'ipi_format', 'IPI')
        self.assertEqual(len(errors), 1)
    
    def test_date_validation(self):
        """Test date format validation"""
        # Valid date
        errors = self.converter.validate_value('2024-01-15', 'date_format', 'Date')
        self.assertEqual(len(errors), 0)
        
        # Invalid date format
        errors = self.converter.validate_value('01/15/2024', 'date_format', 'Date')
        self.assertEqual(len(errors), 1)
        self.assertIn('Invalid date format', errors[0])


class TestErrorHandling(unittest.TestCase):
    """Test error handling and edge cases"""
    
    def setUp(self):
        # Create a minimal valid mapping for error testing
        self.test_mapping = {
            'columns': [
                {'dest': 'Work Title', 'source': 'Title', 'validation': 'required'}
            ],
            'validation_rules': {}
        }
        
        self.temp_mapping = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        import yaml
        yaml.dump(self.test_mapping, self.temp_mapping)
        self.temp_mapping.close()
    
    def tearDown(self):
        os.unlink(self.temp_mapping.name)
    
    def test_missing_mapping_file(self):
        """Test handling of missing mapping file"""
        with self.assertRaises(ConfigurationError):
            CurveConverter('nonexistent_file.yaml')
    
    def test_empty_mapping_file(self):
        """Test handling of empty mapping file"""
        empty_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        empty_file.write('')
        empty_file.close()
        
        try:
            with self.assertRaises(ConfigurationError):
                CurveConverter(empty_file.name)
        finally:
            os.unlink(empty_file.name)


class TestIntegration(unittest.TestCase):
    """Integration tests for full conversion workflows"""
    
    def setUp(self):
        self.test_mapping = {
            'columns': [
                {'dest': 'Work Title', 'source': 'Title', 'transform': 'strip', 'validation': 'required'},
                {'dest': 'Artist Name', 'source': 'Artist', 'transform': 'strip'},
            ],
            'validation_rules': {
                'required_fields': ['Work Title']
            }
        }
        
        self.temp_mapping = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        import yaml
        yaml.dump(self.test_mapping, self.temp_mapping)
        self.temp_mapping.close()
    
    def tearDown(self):
        os.unlink(self.temp_mapping.name)
    
    def test_csv_conversion(self):
        """Test full CSV conversion workflow"""
        converter = CurveConverter(self.temp_mapping.name, log_level='ERROR')  # Suppress logs
        
        # Create test CSV
        test_data = pd.DataFrame({
            'Title': ['Song 1', 'Song 2'],
            'Artist': ['Artist A', 'Artist B']
        })
        
        input_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        test_data.to_csv(input_file.name, index=False)
        input_file.close()
        
        output_file = tempfile.NamedTemporaryFile(suffix='.csv', delete=False)
        output_file.close()
        
        try:
            result = converter.convert_file(input_file.name, output_file.name)
            self.assertTrue(result)
            self.assertTrue(Path(output_file.name).exists())
            
        finally:
            os.unlink(input_file.name)
            if Path(output_file.name).exists():
                os.unlink(output_file.name)


if __name__ == '__main__':
    # Make sure required packages are available
    try:
        import pandas
        import yaml
    except ImportError as e:
        print(f"Missing required package: {e}")
        print("Install with: pip install pandas pyyaml openpyxl")
        sys.exit(1)
    
    unittest.main()