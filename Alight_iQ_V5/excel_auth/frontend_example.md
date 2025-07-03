# Frontend Integration Guide for Structured Comparison Results

## New API Structure Overview

The updated `AddComparisonView` now returns structured data that makes it easy to:
1. Display formatted rows from both files
2. Show match/unmatch status for each row and column
3. Allow frontend editing of match statuses
4. Save modifications back to the database

## Sample Response Structure

```json
{
  "message": "Comparison created successfully",
  "comparison_id": 123,
  "data": {
    "comparison_metadata": {
      "primary_column": "Account_Code",
      "timestamp": "2025-06-26T10:30:00",
      "ranges": {
        "file1": "A6:F31",
        "file2": "A6:F31"
      }
    },
    "file1": {
      "headers": ["Account_Code", "Account_Name", "Amount", "Currency"],
      "rows": [
        {
          "row_number": 1,
          "excel_row": 7,
          "source": "file1",
          "match_status": "matched",
          "has_changes": false,
          "changed_columns": [],
          "data": {
            "Account_Code": {
              "value": "1001",
              "column_index": 0,
              "column_letter": "A",
              "is_changed": false
            },
            "Account_Name": {
              "value": "Cash Account",
              "column_index": 1,
              "column_letter": "B",
              "is_changed": false
            },
            "Amount": {
              "value": 15000,
              "column_index": 2,
              "column_letter": "C",
              "is_changed": false
            }
          }
        }
      ],
      "statistics": {
        "total_rows": 25,
        "matched": 20,
        "changed": 3,
        "added": 0,
        "removed": 2,
        "match_percentage": 80.0,
        "change_percentage": 20.0
      }
    },
    "file2": {
      // Similar structure for file2
    }
  }
}
```

## Frontend Implementation Examples

### 1. Display Comparison Results

```javascript
// React component example
function ComparisonResults({ comparisonData }) {
  const { file1, file2, comparison_metadata } = comparisonData;
  
  return (
    <div>
      <h2>Comparison Results</h2>
      <div className="stats-summary">
        <div>File 1: {file1.statistics.match_percentage}% matched</div>
        <div>File 2: {file2.statistics.match_percentage}% matched</div>
      </div>
      
      <div className="files-comparison">
        <div className="file1-section">
          <h3>File 1 ({file1.total_rows} rows)</h3>
          <ComparisonTable 
            headers={file1.headers}
            rows={file1.rows}
            fileNumber={1}
            comparisonId={comparisonData.comparison_id}
          />
        </div>
        
        <div className="file2-section">
          <h3>File 2 ({file2.total_rows} rows)</h3>
          <ComparisonTable 
            headers={file2.headers}
            rows={file2.rows}
            fileNumber={2}
            comparisonId={comparisonData.comparison_id}
          />
        </div>
      </div>
    </div>
  );
}
```

### 2. Interactive Row Table

```javascript
function ComparisonTable({ headers, rows, fileNumber, comparisonId }) {
  const [editingRow, setEditingRow] = useState(null);
  
  const getRowColor = (status) => {
    const colors = {
      'matched': '#90EE90',
      'changed': '#FFFF00',
      'added': '#ADD8E6',
      'removed': '#FFC7CE',
      'pending': '#FFFFFF'
    };
    return colors[status] || '#FFFFFF';
  };
  
  const updateRowStatus = async (rowId, newStatus) => {
    try {
      const response = await fetch(`/api/comparison/${comparisonId}/file/${fileNumber}/row/${rowId}/update/`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          match_status: newStatus
        })
      });
      
      if (response.ok) {
        // Refresh the comparison data
        refreshComparisonData();
      }
    } catch (error) {
      console.error('Error updating row status:', error);
    }
  };
  
  return (
    <table className="comparison-table">
      <thead>
        <tr>
          <th>Row</th>
          <th>Status</th>
          {headers.map(header => <th key={header}>{header}</th>)}
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        {rows.map(row => (
          <tr key={row.row_number} style={{backgroundColor: getRowColor(row.match_status)}}>
            <td>{row.excel_row}</td>
            <td>
              <select 
                value={row.match_status}
                onChange={(e) => updateRowStatus(row.row_number, e.target.value)}
              >
                <option value="matched">Matched</option>
                <option value="changed">Changed</option>
                <option value="added">Added</option>
                <option value="removed">Removed</option>
              </select>
            </td>
            {headers.map(header => (
              <td key={header} className={row.data[header]?.is_changed ? 'changed-cell' : ''}>
                {row.data[header]?.value}
              </td>
            ))}
            <td>
              <button onClick={() => setEditingRow(row.row_number)}>Edit</button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

### 3. Row Detail Editor

```javascript
function RowEditor({ comparisonId, fileNumber, rowId, onClose }) {
  const [rowData, setRowData] = useState(null);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    fetchRowDetails();
  }, []);
  
  const fetchRowDetails = async () => {
    try {
      const response = await fetch(`/api/comparison/${comparisonId}/file/${fileNumber}/row/${rowId}/`);
      const data = await response.json();
      setRowData(data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching row details:', error);
      setLoading(false);
    }
  };
  
  const updateCellValue = async (columnName, newValue) => {
    try {
      const response = await fetch(`/api/comparison/${comparisonId}/file/${fileNumber}/row/${rowId}/update/`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          updated_columns: {
            [columnName]: newValue
          }
        })
      });
      
      if (response.ok) {
        fetchRowDetails(); // Refresh
      }
    } catch (error) {
      console.error('Error updating cell:', error);
    }
  };
  
  if (loading) return <div>Loading...</div>;
  
  return (
    <div className="row-editor-modal">
      <h3>Edit Row {rowData.row_details.excel_row}</h3>
      <div className="row-comparison">
        <div className="current-row">
          <h4>Current Row</h4>
          {Object.entries(rowData.row_details.data).map(([column, cellData]) => (
            <div key={column} className="cell-editor">
              <label>{column}:</label>
              <input 
                type="text"
                value={cellData.value || ''}
                onChange={(e) => updateCellValue(column, e.target.value)}
                className={cellData.is_changed ? 'changed-cell' : ''}
              />
            </div>
          ))}
        </div>
        
        {rowData.corresponding_row && (
          <div className="corresponding-row">
            <h4>Corresponding Row (Other File)</h4>
            {Object.entries(rowData.corresponding_row.data).map(([column, cellData]) => (
              <div key={column} className="cell-display">
                <label>{column}:</label>
                <span>{cellData.value}</span>
              </div>
            ))}
          </div>
        )}
      </div>
      
      <button onClick={onClose}>Close</button>
    </div>
  );
}
```

### 4. Export Functionality

```javascript
function ExportControls({ comparisonId }) {
  const handleExport = async (format, includeMatched = true, includeUnchanged = false) => {
    try {
      const response = await fetch(
        `/api/comparison/${comparisonId}/export/?format=${format}&include_matched=${includeMatched}&include_unchanged=${includeUnchanged}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );
      
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `comparison_export.${format === 'excel' ? 'xlsx' : format}`;
        a.click();
      }
    } catch (error) {
      console.error('Export failed:', error);
    }
  };
  
  return (
    <div className="export-controls">
      <h4>Export Options</h4>
      <button onClick={() => handleExport('json')}>Export as JSON</button>
      <button onClick={() => handleExport('csv')}>Export as CSV</button>
      <button onClick={() => handleExport('excel')}>Export as Excel</button>
      
      <div className="export-options">
        <label>
          <input type="checkbox" defaultChecked /> Include matched rows
        </label>
        <label>
          <input type="checkbox" /> Include unchanged rows
        </label>
      </div>
    </div>
  );
}
```

## API Endpoints Summary

### New Endpoints:
1. `PUT /api/comparison/{id}/update/` - Update entire comparison data
2. `GET /api/comparison/{id}/file/{file_number}/row/{row_id}/` - Get row details
3. `PUT /api/comparison/{id}/file/{file_number}/row/{row_id}/update/` - Update specific row
4. `GET /api/comparison/{id}/export/?format=json&include_matched=true` - Export results

### Benefits of This Structure:
1. **Clear Data Organization**: Each row contains all necessary information
2. **Frontend Flexibility**: Easy to filter, sort, and display data
3. **Real-time Updates**: Individual row updates without full page refresh
4. **Visual Feedback**: Color-coding and status indicators
5. **Audit Trail**: Track who made changes and when
6. **Export Options**: Multiple formats with filtering options

This structure provides a solid foundation for building an interactive, user-friendly comparison interface.
