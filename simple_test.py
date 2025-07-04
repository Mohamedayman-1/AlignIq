#!/usr/bin/env python
import os
import pandas as pd
import tempfile
import shutil

def split_large_csv(input_file, output_dir, header, rows_per_chunk=10000, input_sep=','):
    """Split a large CSV file into smaller chunks with custom headers."""
    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Extract the base name of the input file (without extension)
    base_name = os.path.splitext(os.path.basename(input_file))[0]

    # Read the file in chunks using the provided input separator
    chunk_iter = pd.read_csv(input_file, chunksize=rows_per_chunk, sep=input_sep, header=None)

    chunk_count = 0
    for i, chunk in enumerate(chunk_iter):
        # Assign the provided header to the chunk columns
        chunk.columns = header[:len(chunk.columns)]  # Ensure header matches column count
        # Construct output file path with 1-based index
        output_file = os.path.join(output_dir, f"{base_name}_{i + 1}.csv")
        chunk.to_csv(output_file, index=False, sep=',')
        chunk_count += 1
        print(f"Saved {output_file}")

    return chunk_count

def test_csv_splitter():
    """Test the CSV splitter functionality"""
    try:
        # Create test CSV data
        test_data = {
            'Name': ['John', 'Jane', 'Bob', 'Alice', 'Charlie', 'Diana', 'Eve', 'Frank'] * 2,
            'Age': [25, 30, 35, 28, 32, 27, 29, 31] * 2,
            'Email': ['john@example.com', 'jane@example.com', 'bob@example.com', 'alice@example.com',
                     'charlie@example.com', 'diana@example.com', 'eve@example.com', 'frank@example.com'] * 2
        }
        
        df = pd.DataFrame(test_data)
        
        # Create temporary test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            df.to_csv(f.name, index=False)
            test_file_path = f.name
        
        print(f"Created test file: {test_file_path}")
        print(f"Test file has {len(df)} rows and {len(df.columns)} columns")
        
        # Test the split function
        output_dir = 'test_output'
        headers = ['Name', 'Age', 'Email']
        rows_per_chunk = 5
        
        # Call the split function
        chunk_count = split_large_csv(
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
            
            total_rows = 0
            # Check each file
            for file in files:
                file_path = os.path.join(output_dir, file)
                test_df = pd.read_csv(file_path)
                total_rows += len(test_df)
                print(f"File {file}: {len(test_df)} rows, columns: {list(test_df.columns)}")
                
                # Verify file size
                file_size = os.path.getsize(file_path)
                print(f"  File size: {file_size} bytes ({file_size/1024:.2f} KB)")
        
        print(f"Total rows in all chunks: {total_rows}")
        print(f"Original rows: {len(df)}")
        
        # Clean up
        os.unlink(test_file_path)
        if os.path.exists(output_dir):
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
