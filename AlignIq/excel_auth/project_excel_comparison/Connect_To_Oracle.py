import oracledb
from datetime import datetime

def connect_to_db(username, password, dsn, schema=None):
    """Establish a connection to the Oracle database"""
    try:
        connection = oracledb.connect(user=username, password=password, dsn=dsn)
        cursor = connection.cursor()
        if schema:
            cursor.execute(f"ALTER SESSION SET CURRENT_SCHEMA = {schema}")
        return connection, cursor
    except Exception as e:
        raise Exception(f"Failed to connect to database: {str(e)}")

def test_connection(username, password, dsn, schema=None):
    """
    Test if the database connection parameters are valid
    
    Args:
        username (str): Database username
        password (str): Database password
        dsn (str): Data Source Name in format "host:port/service_name"
        schema (str, optional): Schema to test
        
    Returns:
        dict: Connection test result with status and message
    """
    try:
        connection, cursor = connect_to_db(username, password, dsn, schema)
        # Execute a simple query to verify the connection
        cursor.execute("SELECT 1 FROM DUAL")
        result = cursor.fetchone()
        
        # Check if schema exists if provided
        schema_valid = True
        schema_message = ""
        if schema:
            try:
                cursor.execute(f"SELECT 1 FROM DUAL WHERE EXISTS (SELECT 1 FROM ALL_USERS WHERE USERNAME = '{schema}')")
                if not cursor.fetchone():
                    schema_valid = False
                    schema_message = f"Schema '{schema}' does not exist or is not accessible."
            except:
                schema_valid = False
                schema_message = f"Could not verify schema '{schema}'."
        
        close_connection(connection, cursor)
        
        return {
            "status": "connected" if result and schema_valid else "error",
            "message": "Connection successful" + (f", but {schema_message}" if not schema_valid and schema_message else ""),
            "schema_valid": schema_valid
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

def close_connection(connection, cursor):
    """Close the database connection and cursor"""
    if cursor:
        cursor.close()
    if connection:
        connection.close()

def get_all_schemas(username, password, dsn):
    """
    Retrieve all available schemas in the database.
    
    Args:
        username (str): Database username
        password (str): Database password
        dsn (str): Data Source Name
        
    Returns:
        List of dicts containing schema information
    """
    try:
        connection, cursor = connect_to_db(username, password, dsn)
        cursor.execute("""
            SELECT USERNAME AS SCHEMA_NAME 
            FROM ALL_USERS 
            ORDER BY USERNAME
        """)
        schemas = [{"name": row[0]} for row in cursor.fetchall()]
        close_connection(connection, cursor)
        return schemas
    except Exception as e:
        raise Exception(f"Failed to get schemas: {str(e)}")

def get_tables_in_schema(username, password, dsn, schema_name):
    """
    Retrieve all tables in a specific schema.
    
    Args:
        username (str): Database username
        password (str): Database password
        dsn (str): Data Source Name
        schema_name (str): Name of the schema to query
        
    Returns:
        List of dicts containing table information
    """
    try:
        connection, cursor = connect_to_db(username, password, dsn)
        cursor.execute("""
            SELECT TABLE_NAME, NUM_ROWS, LAST_ANALYZED
            FROM ALL_TABLES 
            WHERE OWNER = :schema
            ORDER BY TABLE_NAME
        """, schema=schema_name)
        
        tables = []
        for row in cursor.fetchall():
            table_name = row[0]
            row_count = row[1] if row[1] is not None else "N/A"
            last_analyzed = row[2].strftime('%Y-%m-%d') if row[2] else "Never"
            
            tables.append({
                "name": table_name,
                "rows": row_count,
                "last_analyzed": last_analyzed
            })
        
        close_connection(connection, cursor)
        return tables
    except Exception as e:
        raise Exception(f"Failed to get tables for schema {schema_name}: {str(e)}")

def get_table_columns(username, password, dsn, schema_name, table_name):
    """
    Retrieve column names and their data types for a specific table.
    
    Args:
        username (str): Database username
        password (str): Database password
        dsn (str): Data Source Name
        schema_name (str): Schema name
        table_name (str): Table name
        
    Returns:
        dict: Dictionary with columns information including name and type
    """
    connection = None
    cursor = None
    try:
        connection, cursor = connect_to_db(username, password, dsn)
        
        # Use direct query to get column names AND data types
        query = """
            SELECT COLUMN_NAME, DATA_TYPE, DATA_LENGTH, NULLABLE
            FROM ALL_TAB_COLUMNS 
            WHERE OWNER = :1 AND TABLE_NAME = :2
            ORDER BY COLUMN_ID
        """
        
        try:
            cursor.execute(query, (schema_name, table_name))
            column_objects = []
            for row in cursor.fetchall():
                column_objects.append({
                    'name': row[0],
                    'type': row[1],
                    'length': row[2],
                    'nullable': row[3] == 'Y'
                })
            
            if not column_objects:
                return {
                    'columns': [],
                    'error': f"No columns found for table {schema_name}.{table_name}"
                }
            
            # Return the column objects with their types
            return {
                'columns': column_objects,
                'primary_key_columns': []  # Empty list for compatibility
            }
            
        except Exception as e:
            error_str = str(e)
            print(f"Oracle error when querying columns: {error_str}")
            
            # If it's ORA-01745 (invalid host/bind variable name), try with different approach
            if "ORA-01745" in error_str:
                try:
                    # Try direct dictionary query without using string formatting
                    cursor.execute("""
                        SELECT column_name, data_type, data_length, nullable
                        FROM all_tab_columns 
                        WHERE owner = :owner AND table_name = :table
                        ORDER BY column_id
                    """, owner=schema_name, table=table_name)
                    
                    column_objects = []
                    for row in cursor.fetchall():
                        column_objects.append({
                            'name': row[0],
                            'type': row[1],
                            'length': row[2],
                            'nullable': row[3] == 'Y'
                        })
                    
                    if column_objects:
                        return {
                            'columns': column_objects,
                            'primary_key_columns': []
                        }
                except Exception as e2:
                    return {
                        'columns': [],
                        'error': f"Failed to get columns after retry: {str(e2)}"
                    }
            
            return {
                'columns': [],
                'error': f"Failed to get columns: {error_str}"
            }
            
    except Exception as e:
        error_message = f"Database connection error: {str(e)}"
        print(error_message)
        return {
            'columns': [],
            'error': error_message
        }
    finally:
        if connection and cursor:
            close_connection(connection, cursor)

def get_table_columns_for_comparison(connection, cursor, schema, table):
    """Helper function to reliably get columns for a table during comparison"""
    try:
        try:
            cursor.execute(
                "SELECT COLUMN_NAME FROM ALL_TAB_COLUMNS WHERE OWNER = :owner AND TABLE_NAME = :table ORDER BY COLUMN_ID",
                owner=schema, table=table
            )
            columns = [row[0] for row in cursor.fetchall()]
            if columns:
                return columns
        except Exception as e1:
            # First approach failed, try positional parameters
            pass
            
        try:
            cursor.execute(
                "SELECT COLUMN_NAME FROM ALL_TAB_COLUMNS WHERE OWNER = :1 AND TABLE_NAME = :2 ORDER BY COLUMN_ID",
                (schema, table)
            )
            columns = [row[0] for row in cursor.fetchall()]
            if columns:
                return columns
        except Exception as e2:
            # Second approach failed, try direct string substitution
            pass
            
        try:
            cursor.execute(f"SELECT COLUMN_NAME FROM ALL_TAB_COLUMNS WHERE OWNER = '{schema}' AND TABLE_NAME = '{table}' ORDER BY COLUMN_ID")
            columns = [row[0] for row in cursor.fetchall()]
            if columns:
                return columns
        except Exception as e3:
            # Third approach failed, try user_tab_columns
            pass
            
        try:
            cursor.execute(f"SELECT COLUMN_NAME FROM USER_TAB_COLUMNS WHERE TABLE_NAME = '{table}' ORDER BY COLUMN_ID")
            columns = [row[0] for row in cursor.fetchall()]
            if columns:
                return columns
        except Exception as e4:
            # Fourth approach failed
            pass
            
        try:
            view_name = f"TEMP_VIEW_{table}"
            cursor.execute(f"CREATE OR REPLACE VIEW {view_name} AS SELECT * FROM {schema}.{table} WHERE 1=0")
            cursor.execute(f"SELECT COLUMN_NAME FROM USER_TAB_COLUMNS WHERE TABLE_NAME = '{view_name}'")
            columns = [row[0] for row in cursor.fetchall()]
            cursor.execute(f"DROP VIEW {view_name}")
            if columns:
                return columns
        except Exception as e5:
            # Fifth approach failed
            pass
            
        try:
            cursor.execute(f"SELECT * FROM {schema}.{table} WHERE 1=0")
            columns = [desc[0] for desc in cursor.description]
            return columns
        except Exception as e6:
            pass
            
        raise Exception(f"Could not retrieve columns for table {schema}.{table} after multiple attempts")
            
    except Exception as e:
        raise Exception(f"Failed to get columns for table {schema}.{table}: {str(e)}")

def compare_database_tables(username1, password1, dsn1, schema1, table1, primary_key1, 
                           username2, password2, dsn2, schema2, table2, primary_key2):
    """Compare two database tables and return the differences"""
    connection1 = None
    cursor1 = None
    connection2 = None
    cursor2 = None
    
    try:
        # Connect to databases
        connection1, cursor1 = connect_to_db(username1, password1, dsn1)
        connection2, cursor2 = connect_to_db(username2, password2, dsn2)
        
        # Sanitize inputs to avoid SQL injection
        schema1 = schema1.upper()
        table1 = table1.upper()
        schema2 = schema2.upper()
        table2 = table2.upper()
        
        # Get columns for both tables
        try:
            columns1 = get_table_columns_for_comparison(connection1, cursor1, schema1, table1)
            if not columns1:
                raise Exception(f"No columns found for table {schema1}.{table1}")
        except Exception as e:
            raise Exception(f"Failed to get columns for first table: {str(e)}")
        
        try:
            columns2 = get_table_columns_for_comparison(connection2, cursor2, schema2, table2)
            if not columns2:
                raise Exception(f"No columns found for table {schema2}.{table2}")
        except Exception as e:
            raise Exception(f"Failed to get columns for second table: {str(e)}")
        
        # Find common columns and columns added/removed
        common_columns = list(set(columns1) & set(columns2))
        columns_added = list(set(columns2) - set(columns1))
        columns_removed = list(set(columns1) - set(columns2))
        
        # Fetch all rows from tables
        rows1, column_names1 = fetch_table_data(connection1, cursor1, schema1, table1)
        rows2, column_names2 = fetch_table_data(connection2, cursor2, schema2, table2)
        
        # Find the primary key indices
        try:
            pk_index1 = find_column_index(column_names1, primary_key1)
            pk_index2 = find_column_index(column_names2, primary_key2)
            
            if pk_index1 == -1 or pk_index2 == -1:
                pk_columns1 = ", ".join(column_names1)
                pk_columns2 = ", ".join(column_names2)
                raise Exception(f"Primary key columns not found. Available columns in table 1: {pk_columns1}, table 2: {pk_columns2}")
                
        except Exception as e:
            raise
        
        # Create dictionaries with primary key as key
        data1 = {}
        for row in rows1:
            try:
                key = str(row[pk_index1]) if row[pk_index1] is not None else "NULL"
                data1[key] = {column_names1[i].upper(): row[i] for i in range(len(column_names1))}
            except Exception as e:
                continue
            
        data2 = {}
        for row in rows2:
            try:
                key = str(row[pk_index2]) if row[pk_index2] is not None else "NULL"
                row_dict = {column_names2[i].upper(): row[i] for i in range(len(column_names2))}
                
                if key not in data2:
                    data2[key] = [row_dict]
                else:
                    data2[key].append(row_dict)
            except Exception as e:
                continue
        
        # Find rows added, removed and with value differences
        all_keys = set(data1.keys()) | set(data2.keys())
        rows_added = []
        rows_removed = []
        value_diff = []
        
        for key in all_keys:
            try:
                if key in data1 and key not in data2:
                    rows_removed.append(data1[key])
                elif key in data2 and key not in data1:
                    for row in data2[key]:
                        rows_added.append(row)
                else:
                    # Key exists in both tables
                    first_row = data2[key][0]
                    
                    # Check for value differences
                    for col in common_columns:
                        try:
                            col1 = next((c for c in data1[key].keys() if c.upper() == col.upper()), None)
                            col2 = next((c for c in first_row.keys() if c.upper() == col.upper()), None)
                            
                            if col1 and col2:
                                val1 = data1[key][col1]
                                val2 = first_row[col2]
                                
                                if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
                                    val1 = float(val1)
                                    val2 = float(val2)
                                    if abs(val1 - val2) < 0.00001:
                                        continue
                                
                                if val1 != val2:
                                    val1_str = str(val1) if val1 is not None else "NULL"
                                    val2_str = str(val2) if val2 is not None else "NULL"
                                    
                                    value_diff.append({
                                        "primary_key": key,
                                        "column": col,
                                        "table1_value": val1_str,
                                        "table2_value": val2_str
                                    })
                        except Exception as e:
                            continue
                            
                    # Add any duplicate rows from table2
                    if len(data2[key]) > 1:
                        for row in data2[key][1:]:
                            rows_added.append(row)
            except Exception as e:
                continue
        
        # Prepare summary
        summary = {
            "total_columns_table1": len(columns1),
            "total_columns_table2": len(columns2),
            "common_columns": len(common_columns),
            "added_columns": len(columns_added),
            "removed_columns": len(columns_removed),
            "total_rows_table1": len(rows1),
            "total_rows_table2": len(rows2),
            "added_rows": len(rows_added),
            "removed_rows": len(rows_removed),
            "changed_values": len(value_diff)
        }
        
        return {
            "columns_added": columns_added,
            "columns_removed": columns_removed,
            "rows_added": rows_added,
            "rows_removed": rows_removed,
            "value_diff": value_diff,
            "summary": summary
        }
        
    except Exception as e:
        raise Exception(f"Database comparison failed: {str(e)}")
    finally:
        if connection1 and cursor1:
            close_connection(connection1, cursor1)
        if connection2 and cursor2:
            close_connection(connection2, cursor2)

def fetch_table_data(connection, cursor, schema, table):
    """Helper function to fetch data from a table with better error handling"""
    try:
        # First attempt: try with double quotes
        query = f'SELECT * FROM "{schema}"."{table}"'
        cursor.execute(query)
        rows = cursor.fetchall()
        column_names = [col[0] for col in cursor.description]
        return rows, column_names
    except Exception as e1:
        try:
            # Second attempt: try without quotes
            query = f"SELECT * FROM {schema}.{table}"
            cursor.execute(query)
            rows = cursor.fetchall()
            column_names = [col[0] for col in cursor.description]
            return rows, column_names
        except Exception as e2:
            # Third attempt: use DBMS_METADATA to fetch the correct SQL
            try:
                cursor.execute(
                    "SELECT DBMS_METADATA.GET_DDL('TABLE', :table, :owner) FROM DUAL",
                    table=table, owner=schema
                )
                results = cursor.fetchone()
                if not results:
                    raise Exception(f"Could not fetch metadata for {schema}.{table}")
                
                # Final attempt with fully qualified, parameterized query
                cursor.execute(f"SELECT /*+ PARALLEL(4) */ * FROM {schema}.{table}")
                rows = cursor.fetchall()
                column_names = [col[0] for col in cursor.description]
                return rows, column_names
            except Exception as e3:
                raise Exception(f"Failed to query table {schema}.{table}: {str(e2)}")

def find_column_index(column_names, target_column):
    """Find a column index using case-insensitive matching"""
    # First try exact match
    try:
        return column_names.index(target_column)
    except ValueError:
        # Then try case-insensitive match
        for i, col in enumerate(column_names):
            if col.upper() == target_column.upper():
                return i
        return -1
