#!/usr/bin/env python
import os
import sys
import pandas as pd
import tempfile

# Add the project directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_csv_splitter():
    """Test the CSV splitter functionality"""
    try:
        # Create test CSV data
        test_data = {
            'Name': ['John', 'Jane', 'Bob', 'Alice', 'Charlie', 'Diana', 'Eve', 'Frank'],
            'Age': [25, 30, 35, 28, 32, 27, 29, 31],
            'Email': ['john@example.com', 'jane@example.com', 'bob@example.com', 'alice@example.com',
                     'charlie@example.com', 'diana@example.com', 'eve@example.com', 'frank@example.com']
        }
        
        df = pd.DataFrame(test_data)
        
        # Create temporary test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            df.to_csv(f.name, index=False)
            test_file_path = f.name
        
        print(f"Created test file: {test_file_path}")
        
        # Test the split function
        from project_excel_comparison.views.utility_views import split_Lcsvs_View
        
        # Test parameters
        output_dir = 'test_output'
        headers = ['Name', 'Age', 'Email']
        rows_per_chunk = 3
        
        # Call the split function
        chunk_count = split_Lcsvs_View.split_large_csv(
            input_file=test_file_path,
            output_dir=output_dir,
            header=headers,
            rows_per_chunk=rows_per_chunk
        )
        
        print(f"Split into {chunk_count} chunks")
        
        # Verify output files
        if os.path.exists(output_dir):
            files = [f for f in os.listdir(output_dir) if f.endswith('.csv')]
            print(f"Created files: {files}")
            
            # Check each file
            for file in files:
                file_path = os.path.join(output_dir, file)
                test_df = pd.read_csv(file_path)
                print(f"File {file}: {len(test_df)} rows, columns: {list(test_df.columns)}")
        
        # Clean up
        os.unlink(test_file_path)
        if os.path.exists(output_dir):
            import shutil
            shutil.rmtree(output_dir)
        
        print("Test completed successfully!")
        return True
        
    except Exception as e:
        print(f"Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_csv_splitter()
