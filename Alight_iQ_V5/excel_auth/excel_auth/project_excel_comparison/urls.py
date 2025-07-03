from django.urls import path
from django.views.generic.base import TemplateView

# Auth views
from .views.auth_views import RegisterView, LoginView, TokenExpiredView

# File views
from .views.file_views import UploadFileView, ListUserFilesView, ListAllFilesAdminView

# Comparison views
from .views.comparison_views import (
    AddComparisonView, DeleteComparisonView, ListUserComparisonView, 
    ListAllComparisonView, ComparisonDetailView, DownloadComparisonExcelView,
    AnalyzeExcelTableView
)

# Database views
from .views.database_views import (
    CreateDatabaseConnectionView, ListUserDatabaseConnectionsView, 
    ListAllDatabaseConnectionsView, UpdateDatabaseConnectionView,
    DeleteDatabaseConnectionView, TestDatabaseConnectionView, 
    TestDatabaseConnectionByIdView, GetAvailableSchemasView, 
    GetSchemaTablesView, GetTableColumnsView, CompareDatabaseTablesView,
    ListUserDatabaseComparisonsView, DeleteDatabaseComparisonView, 
    GetDatabaseComparisonView
)

# Admin views
from .views.admin_views import ListUsersView, UpdateUserPermissionView

# Utility views
from .views.utility_views import GetSheetNamesView, GetFileHeaderView, dashboard_analytics

urlpatterns = [
    # Authentication endpoints
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('token-expired/', TokenExpiredView.as_view(), name='token-expired'),
    
    # File management endpoints
    path('upload-file/', UploadFileView.as_view(), name='upload-file'),
    path('delete-file/<int:file_id>/', UploadFileView.as_view(), name='delete-file'),
    path('user-files/', ListUserFilesView.as_view(), name='user-files'),
    path('my-files/', ListUserFilesView.as_view(), name='my-files'),
    path('all-files/', ListAllFilesAdminView.as_view(), name='all-files'),
    
    # Excel comparison endpoints
    path('add-comparison/<int:file1_id>/<int:file2_id>/', AddComparisonView.as_view(), name='add-comparison'),
    path('delete-comparison/<int:comparison_id>/', DeleteComparisonView.as_view(), name='delete-comparison'),
    path('user-comparisons/', ListUserComparisonView.as_view(), name='user-comparisons'),
    path('list_user_comparison/', ListUserComparisonView.as_view(), name='list_user_comparison'),
    path('all-comparisons/', ListAllComparisonView.as_view(), name='all-comparisons'),
    path('comparison/<int:comparison_id>/', ComparisonDetailView.as_view(), name='comparison-detail'),
    path('download-excel/<int:comparison_id>/<int:file_number>/', DownloadComparisonExcelView.as_view(), name='download-excel'),
    path('analyze-excel/<int:comparison_id>/<int:file_number>/', AnalyzeExcelTableView.as_view(), name='analyze-excel'),
    
    # Database connection endpoints
    path('database-connections/', CreateDatabaseConnectionView.as_view(), name='create-database-connection'),
    path('database-connections/list/', ListUserDatabaseConnectionsView.as_view(), name='list-database-connections'),
    path('database-connections/all/', ListAllDatabaseConnectionsView.as_view(), name='all-database-connections'),
    path('database-connections/<int:connection_id>/', UpdateDatabaseConnectionView.as_view(), name='update-database-connection'),
    path('database-connections/<int:connection_id>/delete/', DeleteDatabaseConnectionView.as_view(), name='delete-database-connection'),
    path('database-connections/test/', TestDatabaseConnectionView.as_view(), name='test-database-connection'),
    path('database-connections/<int:connection_id>/test/', TestDatabaseConnectionByIdView.as_view(), name='test-database-connection-by-id'),
    
    # Database schema and table endpoints
    path('database-schemas/', GetAvailableSchemasView.as_view(), name='get-schemas'),
    path('database-schemas/<int:connection_id>/', GetAvailableSchemasView.as_view(), name='get-schemas-by-id'),
    path('database-tables/', GetSchemaTablesView.as_view(), name='get-tables'),
    path('database-tables/<int:connection_id>/', GetSchemaTablesView.as_view(), name='get-tables-by-id'),
    path('database-columns/', GetTableColumnsView.as_view(), name='get-columns'),
    path('database-columns/<int:connection_id>/', GetTableColumnsView.as_view(), name='get-columns-by-id'),
    
    # Database comparison endpoints
    path('database-comparisons/', CompareDatabaseTablesView.as_view(), name='compare-database-tables'),
    path('database-comparisons/list/', ListUserDatabaseComparisonsView.as_view(), name='list-database-comparisons'),
    path('database-comparisons/<int:comparison_id>/', GetDatabaseComparisonView.as_view(), name='get-database-comparison'),
    path('database-comparisons/<int:comparison_id>/delete/', DeleteDatabaseComparisonView.as_view(), name='delete-database-comparison'),
    
    # Admin endpoints
    path('admin/users/', ListUsersView.as_view(), name='list-users'),
    path('admin/users/<int:user_id>/permissions/', UpdateUserPermissionView.as_view(), name='update-user-permission'),
    
    # Utility endpoints
    path('files/<int:file_id>/sheets/', GetSheetNamesView.as_view(), name='get-sheet-names'),
    path('files/<int:file_id>/headers/', GetFileHeaderView.as_view(), name='get-file-header'),
    path('dashboard/analytics/', dashboard_analytics, name='dashboard-analytics'),
    
    # Template endpoints
    path('database-comparison-history/', TemplateView.as_view(template_name='database_comparison_history.html'), name='database-comparison-history'),
]