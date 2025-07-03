from datetime import datetime, timedelta
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination

from ..models import Database_Connection, Database_Comparison
from ..serializers import DatabaseConnectionSerializer
from ..permissions import IsAdmin
from ..Connect_To_Oracle import (
    test_connection, get_all_schemas, get_tables_in_schema, 
    get_table_columns, compare_database_tables
)


class CreateDatabaseConnectionView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        data = request.data.copy()
        serializer = DatabaseConnectionSerializer(data=data)
        
        if serializer.is_valid():
            connection = serializer.save(user=request.user)
            return Response({
                'message': 'Database connection created successfully.',
                'data': DatabaseConnectionSerializer(connection).data
            }, status=status.HTTP_201_CREATED)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ListUserDatabaseConnectionsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        connections = Database_Connection.objects.filter(user=request.user)
        serializer = DatabaseConnectionSerializer(connections, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ListAllDatabaseConnectionsView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request):
        connections = Database_Connection.objects.all()
        serializer = DatabaseConnectionSerializer(connections, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UpdateDatabaseConnectionView(APIView):
    permission_classes = [IsAuthenticated]
    
    def put(self, request, connection_id):
        try:
            connection = Database_Connection.objects.get(id=connection_id, user=request.user)
            serializer = DatabaseConnectionSerializer(connection, data=request.data, partial=True)
            
            if serializer.is_valid():
                serializer.save()
                return Response({
                    'message': 'Database connection updated successfully.',
                    'data': serializer.data
                }, status=status.HTTP_200_OK)
                
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        except Database_Connection.DoesNotExist:
            return Response(
                {'message': 'Database connection not found or you do not have permission to modify it.'},
                status=status.HTTP_404_NOT_FOUND
            )


class DeleteDatabaseConnectionView(APIView):
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, connection_id):
        try:
            connection = Database_Connection.objects.get(id=connection_id, user=request.user)
            connection.delete()
            
            return Response(
                {'message': 'Database connection deleted successfully.'},
                status=status.HTTP_200_OK
            )
            
        except Database_Connection.DoesNotExist:
            return Response(
                {'message': 'Database connection not found or you do not have permission to delete it.'},
                status=status.HTTP_404_NOT_FOUND
            )


class TestDatabaseConnectionView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, connection_id=None):
        try:
            if connection_id:
                connection = Database_Connection.objects.get(id=connection_id, user=request.user)
                username = connection.username
                password = connection.password
                dsn = connection.DSN
                schema = getattr(connection, 'SCHEMA', None)
            else:
                username = request.data.get('username')
                password = request.data.get('password')
                dsn = request.data.get('DSN')
                schema = request.data.get('SCHEMA', None)
                
                if not username or not password or not dsn:
                    return Response({
                        'message': 'Username, password, and DSN are required.',
                        'status': 'failed'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                result = test_connection(username, password, dsn, schema)
                
                if result["status"] == "connected":
                    return Response({
                        'message': result["message"],
                        'status': 'connected',
                        'schema_valid': result.get("schema_valid", True)
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({
                        'message': result["message"],
                        'status': 'failed'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
            except Exception as e:
                return Response({
                    'message': f'Failed to connect to the database: {str(e)}',
                    'status': 'failed'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Database_Connection.DoesNotExist:
            return Response({
                'message': 'Database connection not found or you do not have permission to access it.',
                'status': 'failed'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'message': f'Error: {str(e)}',
                'status': 'failed'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TestDatabaseConnectionByIdView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, connection_id):
        return TestDatabaseConnectionView().post(request, connection_id)


class GetAvailableSchemasView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, connection_id=None):
        try:
            if connection_id:
                if request.user.role == 'admin':
                    connection = Database_Connection.objects.get(id=connection_id)
                else:
                    connection = Database_Connection.objects.get(id=connection_id, user=request.user)
                
                username = connection.username
                password = connection.password
                dsn = connection.DSN
            else:
                username = request.data.get('username')
                password = request.data.get('password')
                dsn = request.data.get('DSN')
                
                if not username or not password or not dsn:
                    return Response({
                        'message': 'Username, password, and DSN are required.',
                        'status': 'error'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                schemas = get_all_schemas(username, password, dsn)
                return Response({
                    'status': 'success',
                    'schemas': schemas
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                return Response({
                    'message': f'Failed to retrieve schemas: {str(e)}',
                    'status': 'error'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Database_Connection.DoesNotExist:
            return Response({
                'message': 'Database connection not found or you do not have permission to access it.',
                'status': 'error'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'message': f'Error: {str(e)}',
                'status': 'error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetSchemaTablesView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, connection_id=None):
        try:
            schema_name = request.data.get('schema')
            if not schema_name:
                return Response({
                    'message': 'Schema name is required.',
                    'status': 'error'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if connection_id:
                if request.user.role == 'admin':
                    connection = Database_Connection.objects.get(id=connection_id)
                else:
                    connection = Database_Connection.objects.get(id=connection_id, user=request.user)
                    
                username = connection.username
                password = connection.password
                dsn = connection.DSN
            else:
                username = request.data.get('username')
                password = request.data.get('password')
                dsn = request.data.get('DSN')
                
                if not username or not password or not dsn:
                    return Response({
                        'message': 'Username, password, and DSN are required.',
                        'status': 'error'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                tables = get_tables_in_schema(username, password, dsn, schema_name)
                return Response({
                    'status': 'success',
                    'schema': schema_name,
                    'tables': tables
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                return Response({
                    'message': f'Failed to retrieve tables for schema {schema_name}: {str(e)}',
                    'status': 'error'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Database_Connection.DoesNotExist:
            return Response({
                'message': 'Database connection not found or you do not have permission to access it.',
                'status': 'error'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'message': f'Error: {str(e)}',
                'status': 'error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetTableColumnsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, connection_id=None):
        try:
            schema_name = request.data.get('schema')
            table_name = request.data.get('table')
            
            if not schema_name or not table_name:
                return Response({
                    'message': 'Schema name and table name are required.',
                    'status': 'error'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if connection_id:
                if request.user.role == 'admin':
                    connection = Database_Connection.objects.get(id=connection_id)
                else:
                    connection = Database_Connection.objects.get(id=connection_id, user=request.user)
                    
                username = connection.username
                password = connection.password
                dsn = connection.DSN
            else:
                username = request.data.get('username')
                password = request.data.get('password')
                dsn = request.data.get('DSN')
                
                if not username or not password or not dsn:
                    return Response({
                        'message': 'Username, password, and DSN are required.',
                        'status': 'error'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                columns_result = get_table_columns(username, password, dsn, schema_name, table_name)
                
                if 'error' in columns_result:
                    return Response({
                        'message': columns_result['error'],
                        'status': 'error'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                return Response({
                    'status': 'success',
                    'columns': columns_result['columns']
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                return Response({
                    'message': f'Failed to retrieve columns for table {schema_name}.{table_name}: {str(e)}',
                    'status': 'error'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Database_Connection.DoesNotExist:
            return Response({
                'message': 'Database connection not found or you do not have permission to access it.',
                'status': 'error'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'message': f'Error: {str(e)}',
                'status': 'error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CompareDatabaseTablesView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        connection_id1 = request.data.get('connection1')
        connection_id2 = request.data.get('connection2')
        schema1 = request.data.get('schema1')
        schema2 = request.data.get('schema2')
        table1 = request.data.get('table1')
        table2 = request.data.get('table2')
        primary_key1 = request.data.get('column1')
        primary_key2 = request.data.get('column2')
        
        if not all([connection_id1, connection_id2, schema1, schema2, table1, table2, primary_key1, primary_key2]):
            return Response({
                'message': 'All parameters are required: connection1, connection2, schema1, schema2, table1, table2, column1, column2',
                'status': 'error'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            connection1 = Database_Connection.objects.get(id=connection_id1)
            connection2 = Database_Connection.objects.get(id=connection_id2)
            
            username1 = connection1.username
            password1 = connection1.password
            dsn1 = connection1.DSN
            
            username2 = connection2.username
            password2 = connection2.password
            dsn2 = connection2.DSN
            
            results = compare_database_tables(
                username1, password1, dsn1, schema1, table1, primary_key1,
                username2, password2, dsn2, schema2, table2, primary_key2
            )
            
            save_comparison = request.data.get('save_comparison', False)
            comparison_id = None
            
            if save_comparison:
                db_comparison = Database_Comparison.objects.create(
                    user=request.user,
                    connection1=connection1,
                    connection2=connection2,
                    schema1=schema1,
                    schema2=schema2,
                    table1=table1,
                    table2=table2,
                    primary_key1=primary_key1,
                    primary_key2=primary_key2,
                    results=results
                )
                comparison_id = db_comparison.id
            
            return Response({
                'status': 'success',
                'message': 'Tables compared successfully',
                'results': results,
                'saved': save_comparison,
                'comparison_id': comparison_id
            }, status=status.HTTP_200_OK)
            
        except Database_Connection.DoesNotExist:
            return Response({
                'message': 'One or both database connections not found or unauthorized access',
                'status': 'error'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'message': f'Error comparing tables: {str(e)}',
                'status': 'error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ListUserDatabaseComparisonsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if request.user.role == 'admin' and request.GET.get('all', '').lower() == 'true':
            comparisons = Database_Comparison.objects.all()
        else:
            comparisons = Database_Comparison.objects.filter(user=request.user)
        
        search_query = request.GET.get('search', '').strip()
        if search_query:
            comparisons = comparisons.filter(
                Q(schema1__icontains=search_query) | 
                Q(schema2__icontains=search_query) |
                Q(table1__icontains=search_query) |
                Q(table2__icontains=search_query)
            )
        
        # Date filtering
        date_filter_type = request.GET.get('date_filter_type', '')
        if date_filter_type == 'range':
            start_date = request.GET.get('start_date')
            end_date = request.GET.get('end_date')
            if start_date and end_date:
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
                end_date = end_date_obj.strftime('%Y-%m-%d')
                comparisons = comparisons.filter(timestamp__range=[start_date, end_date])
        elif date_filter_type == 'day' and request.GET.get('filter_date'):
            filter_date = request.GET.get('filter_date')
            comparisons = comparisons.filter(timestamp__date=filter_date)
        elif date_filter_type == 'month' and request.GET.get('filter_date'):
            filter_date = datetime.strptime(request.GET.get('filter_date'), '%Y-%m-%d')
            comparisons = comparisons.filter(
                timestamp__year=filter_date.year,
                timestamp__month=filter_date.month
            )
        elif date_filter_type == 'year' and request.GET.get('filter_date'):
            filter_date = datetime.strptime(request.GET.get('filter_date'), '%Y-%m-%d')
            comparisons = comparisons.filter(timestamp__year=filter_date.year)
        
        comparisons = comparisons.order_by('-timestamp')
        
        paginator = PageNumberPagination()
        paginator.page_size = 10
        page = paginator.paginate_queryset(comparisons, request)
        
        if page is not None:
            data = []
            for comp in page:
                try:
                    connection1_username = comp.connection1.username
                    connection2_username = comp.connection2.username
                except:
                    connection1_username = "Unknown"
                    connection2_username = "Unknown"
                
                data.append({
                    'id': comp.id,
                    'source': f"{comp.schema1}.{comp.table1}",
                    'target': f"{comp.schema2}.{comp.table2}",
                    'connection1_name': f"{connection1_username}@{comp.connection1.DSN}",
                    'connection2_name': f"{connection2_username}@{comp.connection2.DSN}",
                    'timestamp': comp.timestamp,
                    'summary': {
                        'total_columns_table1': comp.results.get('summary', {}).get('total_columns_table1', 0),
                        'total_columns_table2': comp.results.get('summary', {}).get('total_columns_table2', 0),
                        'added_rows': comp.results.get('summary', {}).get('added_rows', 0),
                        'removed_rows': comp.results.get('summary', {}).get('removed_rows', 0),
                        'changed_values': comp.results.get('summary', {}).get('changed_values', 0),
                    }
                })
            
            return Response({
                'results': data,
                'current_page': paginator.page.number,
                'total_pages': paginator.page.paginator.num_pages
            })
        
        return Response([])


class DeleteDatabaseComparisonView(APIView):
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, comparison_id):
        try:
            if request.user.role == 'admin':
                comparison = Database_Comparison.objects.get(id=comparison_id)
            else:
                comparison = Database_Comparison.objects.get(id=comparison_id, user=request.user)
            
            comparison.delete()
            return Response({
                'message': 'Database comparison deleted successfully',
                'status': 'success'
            }, status=status.HTTP_200_OK)
        except Database_Comparison.DoesNotExist:
            return Response({
                'message': 'Comparison not found or you do not have permission to delete it',
                'status': 'error'
            }, status=status.HTTP_404_NOT_FOUND)


class GetDatabaseComparisonView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, comparison_id):
        try:
            if request.user.role == 'admin':
                comparison = Database_Comparison.objects.get(id=comparison_id)
            else:
                comparison = Database_Comparison.objects.get(id=comparison_id, user=request.user)
                
            return Response({
                'id': comparison.id,
                'connection1': comparison.connection1.id,
                'connection2': comparison.connection2.id,
                'schema1': comparison.schema1,
                'schema2': comparison.schema2,
                'table1': comparison.table1,
                'table2': comparison.table2,
                'primary_key1': comparison.primary_key1,
                'primary_key2': comparison.primary_key2,
                'timestamp': comparison.timestamp,
                'results': comparison.results,
            }, status=status.HTTP_200_OK)
        except Database_Comparison.DoesNotExist:
            return Response({
                'message': 'Comparison not found or you do not have permission to view it',
                'status': 'error'
            }, status=status.HTTP_404_NOT_FOUND)
