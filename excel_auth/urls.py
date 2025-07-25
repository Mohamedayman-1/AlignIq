"""
URL configuration for excel_auth project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

# Create a view that can serve any template from the templates directory
def serve_template(request, template_name):
    return TemplateView.as_view(template_name=f'{template_name}.html')(request)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('project_excel_comparison.urls')),
    path('', TemplateView.as_view(template_name='index.html'), name='login'),
    path('login/', TemplateView.as_view(template_name='index.html'), name='login-page'),
    path('dashboard/', TemplateView.as_view(template_name='dashboard.html'), name='dashboard'),
    # Add this line for the database comparison history page
    path('database-comparison-history/', TemplateView.as_view(template_name='database_comparison_history.html'), name='database-comparison-history'),
    # Add CSV Splitter page
    path('csv-splitter/', TemplateView.as_view(template_name='csv_splitter.html'), name='csv-splitter'),
    # Path to serve any template
    path('template/<str:template_name>/', serve_template, name='serve_template'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

