# Multi-Row Header Detection Guide

## Overview
The Excel comparison tool now automatically detects and combines multi-row headers, making it easier to work with complex Excel files that have headers spanning multiple rows.

## Supported Header Patterns

### 1. Month + Year Pattern
**Example:**
```
Row 1:  | December | December | January | January |
Row 2:  | 2024     | 2025     | 2024    | 2025    |
Row 3:  | Revenue  | Revenue  | Revenue | Revenue |
```
**Combined Headers:** `December 2024`, `December 2025`, `January 2024`, `January 2025`

### 2. Text + Year Pattern
**Example:**
```
Row 1:  | Revenue  | Revenue  | Expenses | Expenses |
Row 2:  | 2024     | 2025     | 2024     | 2025     |
```
**Combined Headers:** `Revenue 2024`, `Revenue 2025`, `Expenses 2024`, `Expenses 2025`

### 3. Category + Subcategory Pattern
**Example:**
```
Row 1:  | Financial | Financial | Operational | Operational |
Row 2:  | Income    | Expenses  | Revenue     | Costs       |
```
**Combined Headers:** `Financial Income`, `Financial Expenses`, `Operational Revenue`, `Operational Costs`

### 4. Three-Row Headers
**Example:**
```
Row 1:  | 2024      | 2024      | 2025      | 2025      |
Row 2:  | Q1        | Q2        | Q1        | Q2        |
Row 3:  | Revenue   | Revenue   | Revenue   | Revenue   |
```
**Combined Headers:** `Revenue Q1 2024`, `Revenue Q2 2024`, `Revenue Q1 2025`, `Revenue Q2 2025`

## How It Works

### Automatic Detection
The system automatically:
1. **Analyzes the first 3 rows** of your specified range
2. **Identifies header patterns** based on content types (text, years, months, numbers)
3. **Combines headers intelligently** using natural language rules
4. **Provides confidence levels** (High, Medium, Low) for the detection

### Detection Logic
- **Year Recognition**: Detects 4-digit numbers between 1900-2100
- **Month Recognition**: Detects full month names (January, February, etc.) and abbreviations (Jan, Feb, etc.)
- **Text Recognition**: Identifies non-numeric text that likely represents categories or labels
- **Pattern Matching**: Uses intelligent rules to combine related header components

### Confidence Levels
- **High Confidence**: Clear patterns like Month+Year or Text+Year combinations
- **Medium Confidence**: Multiple text rows or mixed patterns
- **Low Confidence**: Unclear or inconsistent patterns

## Using the Feature

### 1. Upload Your Files
Upload Excel files with multi-row headers as normal.

### 2. Specify Range
When setting the range (e.g., A1:F99), include all header rows at the top:
- If headers are in rows 1-2, start your range from A1
- If headers are in rows 1-3, start your range from A1
- The system will automatically detect where data begins

### 3. Review Detection Results
After comparison, check the **Header Detection Analysis** section in the Summary tab:
- View the detected pattern
- Check the confidence level
- See how many header rows were used
- Review the combined header names

### 4. Manual Override (if needed)
If the automatic detection doesn't work perfectly:
- The system will show a "Low" confidence warning
- You can adjust your range to include/exclude certain rows
- Or contact support for complex header structures

## Examples from Your Data

Based on the Excel file shown (with "December 2025" and "December 2024"), the system will:

1. **Detect the pattern**: Month in row 1, Year in row 2
2. **Combine intelligently**: "December 2025", "December 2024"
3. **Show high confidence**: This is a well-recognized pattern
4. **Start data from row 3**: Headers end at row 2

## Benefits

### For Users
- **No manual header editing**: System automatically creates meaningful column names
- **Consistent naming**: Headers are combined using standard patterns
- **Clear feedback**: Know exactly how headers were interpreted
- **Flexible**: Works with various multi-row header structures

### For Comparisons
- **Better matching**: Properly combined headers improve row matching accuracy
- **Clearer results**: Combined headers make comparison results easier to understand
- **Reduced errors**: Automatic detection reduces manual configuration errors

## Troubleshooting

### Low Confidence Detection
If you see "Low" confidence:
- **Check your range**: Ensure it includes all header rows
- **Verify data structure**: Make sure headers are in the first few rows
- **Review sample values**: Check if the detected values make sense

### Unexpected Header Names
If headers don't combine as expected:
- **Pattern mismatch**: The system might not recognize your specific pattern
- **Mixed content**: Headers might have inconsistent formatting
- **Contact support**: For complex or unusual header structures

### Data Starting Too Early/Late
If data rows are being treated as headers or vice versa:
- **Adjust range**: Include more or fewer rows at the top
- **Check content**: Ensure clear distinction between headers and data
- **Review detection details**: Use the analysis information to understand the decision

## Technical Details

### Supported File Types
- Excel (.xlsx, .xls)
- Encrypted Excel files (with proper decryption)

### Limitations
- Maximum 3 header rows detected automatically
- Headers must be in consecutive rows
- Complex merged cell structures may need manual handling

### Performance
- Header detection adds minimal processing time
- Analysis results are cached for the comparison session
- No impact on file upload or basic comparison speed
