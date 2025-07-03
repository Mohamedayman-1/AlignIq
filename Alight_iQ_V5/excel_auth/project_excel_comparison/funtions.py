import pandas as pd
import json
import os
import warnings
import tempfile
import time
import gc
import io
import re
import csv
import numpy as np
from datetime import datetime
from pandas.api.types import is_numeric_dtype

# Handle relative imports
try:
    from .encryption import decrypt_file, decrypt_file_to_memory
except ImportError:
    # Fallback for when running as a standalone script
    try:
        from encryption import decrypt_file, decrypt_file_to_memory
    except ImportError:
        # If encryption module is not available, create dummy functions
        def decrypt_file(file_path):
            return file_path
        def decrypt_file_to_memory(file_path):
            with open(file_path, 'rb') as f:
                return f.read()

# Suppress openpyxl warning about default style
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl.styles.stylesheet")

# Constants
COMPARES_CSV_FILE = "Compares.csv"
CSV_DELIMITER = "~"

def safe_delete_file(file_path):
    """Safely delete a file, handling cases where the file might still be in use."""
    if not os.path.exists(file_path):
        return
        
    try:
        gc.collect()
        time.sleep(0.1)
        os.unlink(file_path)
    except PermissionError:
        pass

def ensure_csv_header():
    """Ensure the Compares.csv file has the correct header."""
    if not os.path.exists(COMPARES_CSV_FILE):
        # Create the file with the header if it doesn't exist
        with open(COMPARES_CSV_FILE, mode="w", newline="") as file:
            writer = csv.writer(file, delimiter=CSV_DELIMITER)
            writer.writerow(["ID", "File1ID", "File2ID", "Timestamp", "ComparedBy", "Results"])
    else:
        # Check if the file has a header
        with open(COMPARES_CSV_FILE, mode="r", newline="") as file:
            reader = csv.reader(file, delimiter=CSV_DELIMITER)
            first_row = next(reader, None)
            correct_header = ["ID", "File1ID", "File2ID", "Timestamp", "ComparedBy", "Results"]
            if first_row != correct_header:
                # Rewrite the file with the correct header
                rows = list(reader)
                with open(COMPARES_CSV_FILE, mode="w", newline="") as file:
                    writer = csv.writer(file, delimiter=CSV_DELIMITER)
                    writer.writerow(correct_header)
                    writer.writerows(rows)

# Ensure the header exists when the module is loaded
ensure_csv_header()


def compare(file1, file2, sheet1=None, sheet2=None):
    """Compare two Excel files."""
    decrypted_file1 = decrypt_file(file1)
    decrypted_file2 = decrypt_file(file2)
    
    try:
        df1 = pd.read_excel(decrypted_file1, sheet_name=sheet1) if sheet1 else pd.read_excel(decrypted_file1)
        df2 = pd.read_excel(decrypted_file2, sheet_name=sheet2) if sheet2 else pd.read_excel(decrypted_file2)
        
        result = {
            "columns_added": list(),
            "columns_removed": list(),
            "rows_added": [],
            "rows_removed": [],
            "value_diff": [],
            "summary": {},
        }
        
        return json.dumps(result)
    finally:
        safe_delete_file(decrypted_file1)
        safe_delete_file(decrypted_file2)

def get_sheet_names(encrypted_file_path):
    """Get sheet names from an encrypted Excel file."""
    try:
        # Try the relative import first
        from .encryption import decrypt_file
    except ImportError:
        # Fallback for standalone execution
        try:
            from encryption import decrypt_file
        except ImportError:
            # If no encryption available, assume file is not encrypted
            def decrypt_file(path):
                return path
    
    try:
        decrypted_file = decrypt_file(encrypted_file_path)
        
        try:
            with pd.ExcelFile(decrypted_file) as xls:
                sheet_names = list(xls.sheet_names)
            return sheet_names
        finally:
            safe_delete_file(decrypted_file)
    except Exception as e:
        # Return empty list if there's an error instead of crashing
        return []

def preprocess_results(results):
    """Convert non-serializable objects in the results to JSON-serializable types."""
    if isinstance(results, dict):
        return {k: preprocess_results(v) for k, v in results.items()}
    elif isinstance(results, list):
        return [preprocess_results(item) for item in results]
    elif isinstance(results, pd.DataFrame):
        return results.to_dict(orient="records")
    elif isinstance(results, pd.Series):
        # Convert pandas Series to a readable string or value
        if len(results) == 1:
            return preprocess_results(results.iloc[0])
        else:
            return results.tolist()
    elif pd.isna(results):
        return None
    elif isinstance(results, (pd.Timestamp, datetime)):
        return results.isoformat()
    elif isinstance(results, (np.integer, np.floating, np.ndarray)):
        return results.tolist() if hasattr(results, 'tolist') else float(results)
    else:
        return str(results) if not isinstance(results, (int, float, bool, str, type(None))) else results

def save_comparison(file1_id, file2_id, results, compared_by="Anonymous"):
    """Save the comparison results to the Compares.csv file."""
    comparison_id = str(int(datetime.now().timestamp()))  # Unique ID based on timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    results_serializable = preprocess_results(results)  # Preprocess results
    results_str = json.dumps(results_serializable)  # Serialize results to a JSON string

    # Append the comparison data to the CSV file
    with open(COMPARES_CSV_FILE, mode="a", newline="") as file:
        writer = csv.writer(file, delimiter=CSV_DELIMITER)
        writer.writerow([comparison_id, file1_id, file2_id, timestamp, compared_by, results_str])

def get_comparison(comparison_id):
    """Retrieve a comparison result by its ID."""
    with open(COMPARES_CSV_FILE, mode="r", newline="") as file:
        reader = csv.DictReader(file, delimiter=CSV_DELIMITER)
        for row in reader:
            if row["ID"] == comparison_id:
                # Deserialize the results string back into an object
                row["Results"] = json.loads(row["Results"])
                return row
    raise ValueError(f"Comparison with ID {comparison_id} not found.")

def list_comparisons():
    """List all comparisons from the Compares.csv file."""
    comparisons = []
    with open(COMPARES_CSV_FILE, mode="r", newline="") as file:
        reader = csv.DictReader(file, delimiter=CSV_DELIMITER)
        for row in reader:
            # Skip empty rows
            if not any(row.values()):
                continue
            # Strip whitespace from all fields
            row = {key: value.strip() if value else value for key, value in row.items()}
            comparisons.append(row)
    return comparisons

def open_file(file_path, sheet_name=None):
    """Open a file as a DataFrame."""
    from .encryption import decrypt_file
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File {file_path} does not exist.")

    is_temp = file_path.startswith(tempfile.gettempdir())
    
    try:
        decrypted_file = file_path if is_temp else decrypt_file(file_path)
        
        if sheet_name is None:
            with pd.ExcelFile(decrypted_file) as xls:
                available_sheets = xls.sheet_names
                if not available_sheets:
                    raise ValueError("No sheets found in Excel file")
                sheet_name = available_sheets[0]
        
        df = pd.read_excel(decrypted_file, sheet_name=sheet_name, engine="openpyxl", header=None)
        
        if not is_temp:
            safe_delete_file(decrypted_file)
            
        return df
    except Exception as e:
        if not is_temp:
            safe_delete_file(decrypted_file)
        raise

def combine_column_names(df, start_row, end_row):
    """Combine column names from multiple rows and strip extra spaces."""
    column_rows = df.iloc[start_row -1 : end_row].fillna("").astype(str)
    combined_columns = column_rows.apply(lambda x: " ".join(x).strip(), axis=0)
    return combined_columns.tolist()

def parse_range(range_str):
    """Parse an Excel range string (e.g., "A9:N99") and return start row, end row, start column, and end column."""
    match = re.match(r"([A-Za-z]+)(\d+):([A-Za-z]+)(\d+)", range_str)
    if not match:
        raise ValueError(f"Invalid range format: {range_str}")
    start_col, start_row, end_col, end_row = match.groups()
    return int(start_row), int(end_row), start_col, end_col

def normalize_header_name(header):
    """Normalize header names by removing trailing numbers and extra spaces."""
    normalized = re.sub(r'\s+\d+$', '', str(header).strip())
    return normalized.strip()

def get_header(file_path, sheet_name=None, range="A7:F99"):
    """Get column headers from an Excel file within specified range."""
    from .encryption import decrypt_file
    
    # Decrypt the file before reading
    decrypted_file = decrypt_file(file_path)
    
    try:
        # Parse the range first (outside try/except to get better error messages)
        start_row_file1, end_row_file2, start_col_file1, end_col_fil2 = parse_range(range)
        
        # Make sure we get a DataFrame by specifying the sheet
        if sheet_name is None:
            # If no sheet specified, get the first one
            with pd.ExcelFile(decrypted_file) as xls:
                available_sheets = xls.sheet_names
                if not available_sheets:
                    raise ValueError("No sheets found in Excel file")
                sheet_name = available_sheets[0]
        
        # Now read the specific sheet, so we get a DataFrame, not a dict
        df1 = pd.read_excel(decrypted_file, sheet_name=sheet_name, header=None)
        
        try:
            # Now we can use iloc on the DataFrame
            df1.columns = combine_column_names(
                df1, start_row_file1, start_row_file1 +1
            )

            # cleaned_headers = [normalize_header_name(header) for header in combined_headers]
            # Convert pandas Index to a list before serializing to JSON
            columns_list = df1.columns.tolist()
            return json.dumps(columns_list)
        except Exception as e:
            # Add better error information
            raise ValueError(f"Error processing column headers: {str(e)}")
    finally:
        # Clean up temporary decrypted file
        safe_delete_file(decrypted_file)

def sanitize_column_names(df):
    """
    Sanitize column names while preserving uniqueness.
    """
    sanitized_columns = {}
    seen_names = {}
    
    for col in df.columns:
        # First normalize to remove any duplicate suffixes
        normalized = normalize_header_name(col)
        # Then sanitize by replacing problematic characters
        sanitized = (
            str(normalized)
            .strip()
            .replace("&", "and")
            .replace(":", "_")
            .replace("/", "_")
            .replace("\\", "_")
            .replace(".", "_")
        )
        
        # Ensure uniqueness by adding a suffix if needed
        if sanitized in seen_names:
            seen_names[sanitized] += 1
            sanitized = f"{sanitized}_{seen_names[sanitized]}"
        else:
            seen_names[sanitized] = 0
            
        sanitized_columns[col] = sanitized
    
    # Create a mapping for reverse lookup
    df.columns = [sanitized_columns[col] for col in df.columns]
    
    return df, sanitized_columns


def remove_any_between_endl_characters(s):
    """
    Trims leading and trailing non-alphanumeric characters from the string s, and removes any newline characters between the first and last alphanumeric characters.
    """
    if not isinstance(s, str):
        return s
    match_first = re.search(r'[A-Za-z0-9]', s)
    reversed_s = s[::-1]
    match_last = re.search(r'[A-Za-z0-9]', reversed_s)
    first_pos = match_first.start() if match_first else None
    last_pos = match_last.start() if match_last else None
    # Convert the index from the reversed string back to the original string index
    last_pos = len(s) - 1 - last_pos if last_pos is not None else None
    strr = s[first_pos:last_pos+1] if first_pos is not None and last_pos is not None else ""
    strr = strr.replace('\n', ' ').replace('\r', ' ')
    result = s[:first_pos] + strr + s[last_pos+1:] if first_pos is not None and last_pos is not None else s
    return result

def GetMappingTypes(excel_file_path):
    """Return all sheet names in the given Excel file (encrypted or plain)."""
    try:
        with pd.ExcelFile(excel_file_path) as xls:
            return list(xls.sheet_names)
    except Exception as e:
        return []

def map_epm_to_hfm(MappingDf, MappingEPM, MappingHFM):
    """Returns a dictionary mapping EPM values to HFM values."""
    try:
        if isinstance(MappingHFM, int):
            MappingHFM = MappingDf.columns[MappingHFM]
        if isinstance(MappingEPM, int):
            MappingEPM = MappingDf.columns[MappingEPM]
        return dict(zip(MappingDf[MappingEPM].values, MappingDf[MappingHFM].values))
    except KeyError as e:
        raise KeyError(f"Mapping columns {MappingEPM} or {MappingHFM} not found in the mapping DataFrame: {e}")

def compare_excel_sheets(
    file1_path,
    file2_path,
    sheet_name=None,
    sheet_name2=None,
    PrimaryColumn=None,
    range_file1="A7:F99",
    range_file2="A7:F99",
    mapping_Type="Account",
):
    from .encryption import decrypt_file
    
    decrypted_file1 = decrypt_file(file1_path)
    decrypted_file2 = decrypt_file(file2_path)
    
    try:
        start_row_file1, end_row_file1, _, _ = parse_range(range_file1)
        start_row_file2, end_row_file2, _, _ = parse_range(range_file2)

        df1 = open_file(decrypted_file1, sheet_name=sheet_name)
        df2 = open_file(decrypted_file2, sheet_name=sheet_name2)

        MappingDf = pd.read_excel(
            r"EPM to HFM Mapping V3 2.xlsx",
            sheet_name=mapping_Type
        )
        if mapping_Type == "Master":
            MappingHFM = 1
            MappingEPM = 2
        else:
            MappingHFM = 3
            MappingEPM = 1
        
        df1.columns = combine_column_names(df1, start_row_file1, start_row_file1 + 1)
        df2.columns = combine_column_names(df2, start_row_file2, start_row_file2 + 1)

        df1, cols1_map = sanitize_column_names(df1)
        df2, cols2_map = sanitize_column_names(df2)
        
        reverse_cols1_map = {san: orig for orig, san in cols1_map.items()}
        reverse_cols2_map = {san: orig for orig, san in cols2_map.items()}

        df1 = df1.iloc[start_row_file1 + 1 : end_row_file1].reset_index(drop=True)
        df2 = df2.iloc[start_row_file2 + 1 : end_row_file2].reset_index(drop=True)

        df1["_OriginalRow"] = df1.index + start_row_file1 + 2
        df2["_OriginalRow"] = df2.index + start_row_file2 + 2

        Cols1 = [col.strip() for col in df1.columns]
        Cols2 = [col.strip() for col in df2.columns]

        result = {
            "columns_added": [reverse_cols2_map.get(col, col) for col in set(Cols2) - set(Cols1)],
            "columns_removed": [reverse_cols1_map.get(col, col) for col in set(Cols1) - set(Cols2)],
            "rows_added": [],
            "rows_removed": [],
            "value_diff": [],
            "summary": {},
        }

        if PrimaryColumn is None:
            file1_primary_col = Cols1[0]
            file2_primary_col = Cols2[0]
        else:
            try:
                file1_primary_col = next((san_col for orig_col, san_col in cols1_map.items() 
                                      if normalize_header_name(orig_col) == normalize_header_name(PrimaryColumn[0])), Cols1[0])
                file2_primary_col = next((san_col for orig_col, san_col in cols2_map.items() 
                                      if normalize_header_name(orig_col) == normalize_header_name(PrimaryColumn[0])), Cols2[0])
            except (StopIteration, IndexError):
                file1_primary_col = Cols1[0]
                file2_primary_col = Cols2[0]
                
        common_cols = list(
            (set(Cols1) & set(Cols2)) - {"_OriginalRow"} - {file1_primary_col} - {file2_primary_col}
        )

        epm_to_hfm_dict = map_epm_to_hfm(MappingDf, MappingEPM, MappingHFM)
        HFM_primary_col = set(df1[file1_primary_col].tolist()) 
        EPM_primary_col = set(df2[file2_primary_col].tolist())
        
        Combined_HFM = [epm_to_hfm_dict.get(id, id) for id in EPM_primary_col]
        all_ids = set(Combined_HFM) | set(HFM_primary_col)
        cleaned_ids = []
        for x in all_ids:
            cleaned = remove_any_between_endl_characters(x)
            cleaned_ids.append(cleaned if cleaned else x)
        all_ids = set(cleaned_ids)

        for id in all_ids:
            df1_processed = df1[file1_primary_col].apply(remove_any_between_endl_characters)
            df2_processed = df2[file2_primary_col].apply(remove_any_between_endl_characters).apply(lambda x: epm_to_hfm_dict.get(x, x))
            
            file1_this_id = df1[df1_processed == id]
            file2_this_id = df2[df2_processed == id]
            
            # get added rows
            if file1_this_id.empty and not file2_this_id.empty:
                added_rows = file2_this_id.to_dict(orient="records")
                for row in added_rows:
                    original_row = {reverse_cols2_map.get(k, k): preprocess_results(v) for k, v in row.items()}
                    if original_row.get(reverse_cols2_map.get(file2_primary_col, file2_primary_col)) is None:
                        continue
                    result["rows_added"].append(original_row)
                continue
            # get removed rows
                
            if file2_this_id.empty and not file1_this_id.empty:
                removed_rows = file1_this_id.to_dict(orient="records")
                for row in removed_rows:
                    original_row = {reverse_cols1_map.get(k, k): preprocess_results(v) for k, v in row.items()}
                    if original_row.get(reverse_cols1_map.get(file2_primary_col, file2_primary_col)) is None:
                       continue
                    result["rows_removed"].append(original_row)
                continue
                
            n1 = len(file1_this_id)
            n2 = len(file2_this_id)
            min_n = min(n1, n2)
            
            for i in range(min_n):
                for col in common_cols:
                    row1 = file1_this_id.iloc[i]
                    row2 = file2_this_id.iloc[i]
                    
                    if not is_numeric_dtype(row1[col]):
                        val1 = str(row1[col]).strip()
                        val2 = str(row2[col]).strip()
                    else:
                        val1 = row1[col]
                        val2 = row2[col]
                        
                    if val1 != val2:
                        original_col_name = reverse_cols1_map.get(col, col)
                        result["value_diff"].append(
                            {
                                "excel_row_file1": row1["_OriginalRow"],
                                "excel_row_file2": row2["_OriginalRow"],
                                "column": original_col_name,
                                "file1_value": preprocess_results(val1),
                                "file2_value": preprocess_results(val2),
                            }
                        )
                        
            if n2 > n1:
                extra_rows = file2_this_id.iloc[min_n:]
                added_rows = extra_rows.to_dict(orient="records")
                for row in added_rows:
                    original_row = {reverse_cols2_map.get(k, k): preprocess_results(v) for k, v in row.items()}
                    result["rows_added"].append(original_row)
                    
            if n1 > n2:
                removed_rows = file1_this_id.iloc[min_n:].to_dict(orient="records")
                for row in removed_rows:
                    original_row = {reverse_cols1_map.get(k, k): preprocess_results(v) for k, v in row.items()}
                    result["rows_removed"].append(original_row)
                    
        result["summary"] = {
            "total_columns_file1": len(set(Cols1) - {"_OriginalRow"}),
            "total_columns_file2": len(set(Cols2) - {"_OriginalRow"}),
            "common_columns": len(common_cols),
            "added_columns": len(result["columns_added"]),
            "removed_columns": len(result["columns_removed"]),
            "total_rows_file1": len(df1),
            "total_rows_file2": len(df2),
            "added_rows": len(result["rows_added"]),
            "removed_rows": len(result["rows_removed"]),
            "changed_values": len(result["value_diff"]),
        }
        
        return result
        
    except Exception as e:
        if "014A Tax recogniseed" in str(e) or "&" in str(e):
            return {"error": f"{str(e)} - The error may be related to problematic column names. Try adding more sanitization."}
        return {"error": str(e)}
        
    finally:
        safe_delete_file(decrypted_file1)
        safe_delete_file(decrypted_file2)
