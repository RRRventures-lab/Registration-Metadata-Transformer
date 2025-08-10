# Curve Converter

A robust Python tool to convert Master Catalog exports into Curve Work Import format with comprehensive data validation and transformation capabilities.

## Features

- **Flexible Column Mapping**: YAML-based configuration for easy mapping updates
- **Data Transformations**: 20+ built-in transforms for formatting, dates, percentages, etc.
- **Comprehensive Validation**: Field validation, share totals, format checks
- **Error Reporting**: Detailed error CSV with row-level validation issues
- **Multiple Formats**: Supports Excel (.xlsx) and CSV input/output
- **Strict Mode**: Option to fail on validation errors

## Quick Start

### Prerequisites
- Python 3.10+
- Required packages: `pandas`, `pyyaml`, `openpyxl`

```bash
pip install pandas pyyaml openpyxl
```

### Basic Usage

```bash
python convert_to_curve.py \
  --in "master_catalog.xlsx" \
  --out "curve_import.xlsx" \
  --map "mapping.yaml"
```

### With Strict Validation
```bash
python convert_to_curve.py \
  --in "master_catalog.xlsx" \
  --out "curve_import.xlsx" \
  --map "mapping.yaml" \
  --strict
```

## Configuration

### Mapping File Structure

The `mapping.yaml` file defines how to transform data from the source format to Curve's format:

```yaml
columns:
  - dest: "Work Title"           # Curve column name
    source: "Title"              # Master catalog column name  
    transform: "strip"           # Transformation to apply
    validation: "required"       # Validation rule
    default: ""                  # Default value if source is empty

lookups:
  role_codes:                    # Lookup tables for mapping values
    "Writer": "CA"
    "Composer": "C"
```

### Available Transforms

| Transform | Description | Example |
|-----------|-------------|---------|
| `strip` | Remove leading/trailing whitespace | |
| `uppercase` | Convert to uppercase | `hello` → `HELLO` |
| `lowercase` | Convert to lowercase | `HELLO` → `hello` |
| `titlecase` | Title case conversion | `hello world` → `Hello World` |
| `strip_diacritics` | Remove accents/diacritics | `café` → `cafe` |
| `to_date:%Y-%m-%d` | Parse and format dates | `01/15/2024` → `2024-01-15` |
| `percent_0_100` | Ensure 0-100 percentage scale | `0.5` → `50.0` |
| `percent_0_1` | Convert to 0-1 scale | `50` → `0.5` |
| `format_iswc` | Format ISWC codes | `1234567890` → `T-123456789-0` |
| `format_isrc` | Format ISRC codes | `USRC17607839` → `US-RC1-76-07839` |
| `format_ipi` | Format IPI codes | Clean to digits only |
| `map_role` | Map using role_codes lookup | `Writer` → `CA` |
| `map_society` | Map using society_codes lookup | `ASCAP` → `ASCAP` |
| `map_territory` | Map using territories lookup | `United States` → `US` |
| `padleft:5:0` | Pad left with zeros | `123` → `00123` |

### Validation Rules

| Rule | Description |
|------|-------------|
| `required` | Field cannot be empty |
| `date_format` | Must match YYYY-MM-DD format |
| `iswc_format` | Must match ISWC pattern |
| `isrc_format` | Must match ISRC pattern |
| `ipi_format` | Must be 9 or 11 digits |
| `share_range` | Must be between 0-100 |
| `valid_role` | Must be in role_codes lookup |
| `valid_society` | Must be in society_codes lookup |

### Global Validation

- **Required Fields**: Configurable list of mandatory columns
- **Share Totals**: Mechanical and performance shares must sum to 100% ±0.01%
- **Max Participants**: Configurable limit (default: 10)

## Output

### Success
- Converted file in Curve format
- Console summary of rows processed
- Validation status

### Errors
- `{output_file}_errors.csv` with detailed validation issues
- Columns: `row_index`, `work_title`, `error_code`, `error_detail`

### Error Codes
- `REQUIRED_FIELD_MISSING`: Mandatory field is empty
- `MECHANICAL_SHARES_INVALID`: Mechanical shares don't sum to 100%
- `PERFORMANCE_SHARES_INVALID`: Performance shares don't sum to 100%
- `FIELD_ERROR`: Transformation or validation error

## Advanced Usage

### Custom Lookups
Add organization-specific mappings to the `lookups` section:

```yaml
lookups:
  role_codes:
    "Lead Vocalist": "CA"
    "Background Vocalist": "CA"
  territories:
    "North America": "US-CA"
```

### Multiple Source Columns
For fields requiring data from multiple columns, update the mapping configuration and modify the converter logic.

### Participant Expansion
The system supports up to 10 participants by default. Modify `max_participants` in validation_rules to change this limit.

## Troubleshooting

### Common Issues

1. **File Not Found**: Verify input and mapping file paths
2. **Permission Denied**: Check write permissions for output directory
3. **Memory Issues**: For large files, consider processing in chunks
4. **Encoding Issues**: Ensure CSV files use UTF-8 encoding

### Debug Mode
Add print statements or logging to the converter for detailed processing information.

### Validation Failures
- Check `_errors.csv` for specific validation issues
- Verify lookup tables are complete
- Ensure source data quality

## Development

### Adding New Transforms
1. Add transform logic to `transform_value()` method
2. Update documentation
3. Add test cases

### Adding New Validations
1. Add validation logic to `validate_value()` method  
2. Update validation_rules documentation
3. Add test cases

### Testing
Create test files with various edge cases:
- Missing required fields
- Invalid share totals  
- Malformed codes (ISWC, ISRC, IPI)
- Mixed date formats
- Special characters and Unicode

## License

This project is provided as-is for music rights management workflow automation.