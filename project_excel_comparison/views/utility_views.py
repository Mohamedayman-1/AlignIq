import json
import os
import tempfile
import datetime
from datetime import datetime, timedelta
from django.http import JsonResponse, HttpResponse, Http404
from django.db.models import Count
from django.db.models.functions import TruncDay
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes

from ..models import User, FileUpload, Comparison
from ..funtions import get_sheet_names, get_header
import pandas as pd
import zipfile
import shutil

class GetSheetNamesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, file_id):
        try:
            file_obj = FileUpload.objects.get(id=file_id, user=request.user)
            names = get_sheet_names(file_obj.file.path)
            return JsonResponse({"sheet_names": names}, status=200)
        except FileUpload.DoesNotExist:
            return JsonResponse({"error": "File not found or not authorized."}, status=404)


class GetFileHeaderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, file_id):
        range_value = request.data.get('range', 'A7:F99')
        
        file_upload = FileUpload.objects.filter(id=file_id, user=request.user).first()
        if not file_upload:
            return Response({"error": "File not found or not yours."}, status=status.HTTP_404_NOT_FOUND)
        
        columns = get_header(file_upload.file.path, range=range_value)
        return Response({"columns": columns}, status=status.HTTP_200_OK)

class split_Lcsvs_View(APIView):
    permission_classes = [IsAuthenticated]
    
    # Class variable to store the last processed file data for reuse
    last_processed_file = {}

    @staticmethod
    def split_large_csv(input_file, output_dir, header, rows_per_chunk=10000, input_sep=',', filename=None):
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
            output_file = os.path.join(output_dir, f"{filename}_{i + 1}.csv")
            chunk.to_csv(output_file, index=False, sep=',')
            chunk_count += 1
            print(f"Saved {output_file}")
    
        return chunk_count

    def post(self, request, file_id=None):
        try:
            user_id = request.user.id
            
            # Check if we should reuse the last processed file
            reuse_file = request.POST.get('reuse_file', 'false').lower() == 'true'
            
            if reuse_file and user_id in self.last_processed_file:
                # Reuse the last processed file
                file_path = self.last_processed_file[user_id]['file_path']
                
                # Verify file still exists
                if not os.path.exists(file_path):
                    return Response({"error": "Previously uploaded file no longer exists. Please upload a new file."}, 
                                  status=status.HTTP_400_BAD_REQUEST)
                
                original_filename = self.last_processed_file[user_id]['original_filename']
                print(f"Reusing file: {original_filename}")
                
            elif 'file' in request.FILES:
                # Handle new file upload
                uploaded_file = request.FILES['file']
                
                # Validate file type
                if not uploaded_file.name.lower().endswith('.csv'):
                    return Response({"error": "Please upload a CSV file."}, status=status.HTTP_400_BAD_REQUEST)
                
                # Save file temporarily
                with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp_file:
                    for chunk in uploaded_file.chunks():
                        temp_file.write(chunk)
                    temp_file_path = temp_file.name
                
                file_path = temp_file_path
                original_filename = uploaded_file.name
                
                # Store for potential reuse
                self.last_processed_file[user_id] = {
                    'file_path': file_path,
                    'original_filename': original_filename,
                    'upload_time': datetime.now()
                }
                
                print(f"New file uploaded: {original_filename}")
                
            elif file_id:
                # Use existing uploaded file from database
                file_upload = FileUpload.objects.get(id=file_id, user=request.user)
                if not file_upload.file.name.endswith('.csv'):
                    return Response({"error": "File is not a CSV."}, status=status.HTTP_400_BAD_REQUEST)
                file_path = file_upload.file.path
                original_filename = file_upload.file.name
                
            else:
                return Response({"error": "No file provided."}, status=status.HTTP_400_BAD_REQUEST)

            # Get parameters from request
            if 'file' in request.FILES or reuse_file:
                # Handle form data
                output_dir = request.POST.get('output_dir', 'output_chunks')
                header_str = request.POST.get('header', '')
                
                # Parse comma-separated headers
                if header_str:
                    header = [h.strip() for h in header_str.split(',') if h.strip()]
                else:
                    header = []
                    
                rows_per_chunk = int(request.POST.get('chunk_size', 10000))
                input_sep = request.POST.get('input_sep', ',')
            else:
                # Handle JSON data
                output_dir = request.data.get('output_dir', 'output_chunks')
                header = request.data.get('header', [])
                rows_per_chunk = int(request.data.get('chunk_size', 10000))
                input_sep = request.data.get('input_sep', ',')

            if not header:
                return Response({"error": "Header is required."}, status=status.HTTP_400_BAD_REQUEST)

            # Create unique output directory
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_output_dir = f"{output_dir}_{timestamp}"

            # Call the static method to split the CSV
            chunk_count = self.split_large_csv(
                input_file=file_path,
                output_dir=unique_output_dir,
                header=header,
                rows_per_chunk=rows_per_chunk,
                input_sep=input_sep,
                filename=original_filename
            )

            # Get list of created CSV files
            csv_files = []
            if os.path.exists(unique_output_dir):
                for root, dirs, files in os.walk(unique_output_dir):
                    for file in files:
                        if file.lower().endswith('.csv'):
                            file_path_full = os.path.join(root, file)
                            file_size = os.path.getsize(file_path_full) if os.path.exists(file_path_full) else 0
                            
                            csv_files.append({
                                'filename': file,
                                'full_path': file_path_full,
                                'relative_path': os.path.relpath(file_path_full, unique_output_dir),
                                'size': file_size
                            })
                            
                            print(f"DEBUG: Found CSV file: {file} ({file_size} bytes)")
            
            # Sort CSV files by filename for consistent ordering
            csv_files.sort(key=lambda x: x['filename'])
            
            print(f"DEBUG: Total CSV files found: {len(csv_files)}")
            
            return Response({
                "csv_files": csv_files,
                "message": "CSV split successfully",
                "output_directory": unique_output_dir,
                "chunks_created": chunk_count,
                "original_filename": original_filename if 'original_filename' in locals() else "Unknown"
            }, status=status.HTTP_200_OK)
            
        except FileUpload.DoesNotExist:
            return Response({"error": "File not found or not yours."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(f"Error in split_Lcsvs_View: {str(e)}")
            return Response({"error": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            return Response({"error": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CSVDownloadView(APIView):
    """Download individual CSV files from split results."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, file_path):
        try:
            # Decode the file path (it's base64 encoded)
            import base64
            try:
                decoded_path = base64.b64decode(file_path).decode('utf-8')
                print(f"DEBUG: Decoded file path: {decoded_path}")
            except Exception as e:
                print(f"DEBUG: Failed to decode path: {e}")
                decoded_path = file_path
            
            # Security check: ensure file exists and is within expected directory
            if not os.path.exists(decoded_path):
                print(f"DEBUG: File not found: {decoded_path}")
                raise Http404("File not found")
            
            # Additional security: ensure path doesn't contain directory traversal
            if '..' in decoded_path:
                print(f"DEBUG: Directory traversal detected: {decoded_path}")
                raise Http404("Invalid file path")
            
            # Check if file is a CSV
            if not decoded_path.lower().endswith('.csv'):
                print(f"DEBUG: Not a CSV file: {decoded_path}")
                raise Http404("Invalid file type")
            
            print(f"DEBUG: Serving file: {decoded_path}")
            
            with open(decoded_path, 'rb') as f:
                response = HttpResponse(f.read(), content_type='text/csv')
                response['Content-Disposition'] = f'attachment; filename="{os.path.basename(decoded_path)}"'
                return response
                
        except Exception as e:
            print(f"Error in CSVDownloadView: {str(e)}")
            raise Http404("File not found")


class CSVZipDownloadView(APIView):
    """Download selected CSV files as a ZIP archive."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            selected_files = request.data.get('selected_files', [])
            zip_name = request.data.get('zip_name', 'selected_files.zip')
            
            print(f"DEBUG: Received request to zip {len(selected_files)} files")
            print(f"DEBUG: Selected files: {selected_files}")
            
            if not selected_files:
                return Response({"error": "No files selected"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Create a temporary ZIP file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_zip:
                with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for file_path in selected_files:
                        print(f"DEBUG: Processing file: {file_path}")
                        
                        # Security checks
                        if not os.path.exists(file_path):
                            print(f"DEBUG: File not found: {file_path}")
                            continue
                        
                        if '..' in file_path:
                            print(f"DEBUG: Directory traversal detected: {file_path}")
                            continue
                        
                        if not file_path.lower().endswith('.csv'):
                            print(f"DEBUG: Not a CSV file: {file_path}")
                            continue
                        
                        # Add file to ZIP
                        arcname = os.path.basename(file_path)
                        zipf.write(file_path, arcname)
                        print(f"DEBUG: Added to ZIP: {arcname}")
                
                # Return the ZIP file
                with open(temp_zip.name, 'rb') as f:
                    response = HttpResponse(f.read(), content_type='application/zip')
                    response['Content-Disposition'] = f'attachment; filename="{zip_name}"'
                
                # Clean up temp file
                try:
                    os.unlink(temp_zip.name)
                except:
                    pass
                
                print(f"DEBUG: ZIP file created and sent: {zip_name}")
                return response
                
        except Exception as e:
            print(f"Error in CSVZipDownloadView: {str(e)}")
            return Response({"error": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_analytics(request):
    """Returns analytics data for the dashboard, including user and admin stats."""
    try:
        user = request.user
        is_admin = (getattr(user, 'role', None) == 'admin')

        # User-specific stats
        user_files = FileUpload.objects.filter(user=user)
        user_file_count = user_files.count()
        user_comparisons = Comparison.objects.filter(user=user)
        user_comparison_count = user_comparisons.count()

        # Simple file-types breakdown for user
        user_file_types = {}
        for f in user_files:
            try:
                ext = f.file.name.split('.')[-1].lower() if '.' in f.file.name else 'unknown'
                user_file_types[ext] = user_file_types.get(ext, 0) + 1
            except Exception:
                user_file_types['unknown'] = user_file_types.get('unknown', 0) + 1

        # Recent comparisons
        recent_comps = user_comparisons.order_by('-timestamp')[:5]

        # Activity by day (last 30 days)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        daily_activity = user_comparisons.filter(timestamp__gte=thirty_days_ago).annotate(
            day=TruncDay('timestamp')
        ).values('day').annotate(count=Count('id')).order_by('day')
        
        activity_data = {}
        for item in daily_activity:
            try:
                day_str = item['day'].strftime('%Y-%m-%d')
                activity_data[day_str] = item['count']
            except Exception:
                continue

        data = {
            "user_stats": {
                "total_files": user_file_count,
                "total_comparisons": user_comparison_count,
                "file_types": user_file_types,
                "recent_comparisons": [],
                "activity_by_day": activity_data
            }
        }

        # Add recent comparisons safely
        for comp in recent_comps:
            try:
                data["user_stats"]["recent_comparisons"].append({
                    "file1": comp.file1.file.name.split('/')[-1] if comp.file1 and comp.file1.file else "Unknown",
                    "file2": comp.file2.file.name.split('/')[-1] if comp.file2 and comp.file2.file else "Unknown",
                    "timestamp": comp.timestamp.isoformat() if comp.timestamp else None,
                })
            except Exception:
                continue

        # Admin stats
        if is_admin:
            try:
                total_users = User.objects.count()
                total_files = FileUpload.objects.count()
                total_comparisons = Comparison.objects.count()

                top_users_query = Comparison.objects.values('user__username').annotate(
                    comparison_count=Count('id')
                ).order_by('-comparison_count')[:5]

                system_file_types = {}
                for f in FileUpload.objects.all():
                    try:
                        ext = f.file.name.split('.')[-1].lower() if '.' in f.file.name else 'unknown'
                        system_file_types[ext] = system_file_types.get(ext, 0) + 1
                    except Exception:
                        system_file_types['unknown'] = system_file_types.get('unknown', 0) + 1

                recent_sys_activity = Comparison.objects.order_by('-timestamp')[:10]
                sys_daily_activity = Comparison.objects.filter(timestamp__gte=thirty_days_ago).annotate(
                    day=TruncDay('timestamp')
                ).values('day').annotate(count=Count('id')).order_by('day')
                
                sys_activity_data = {}
                for item in sys_daily_activity:
                    try:
                        day_str = item['day'].strftime('%Y-%m-%d')
                        sys_activity_data[day_str] = item['count']
                    except Exception:
                        continue

                admin_recent_activity = []
                for comp in recent_sys_activity:
                    try:
                        admin_recent_activity.append({
                            "user": comp.user.username if comp.user else "Unknown",
                            "file1": comp.file1.file.name.split('/')[-1] if comp.file1 and comp.file1.file else "Unknown",
                            "file2": comp.file2.file.name.split('/')[-1] if comp.file2 and comp.file2.file else "Unknown",
                            "timestamp": comp.timestamp.isoformat() if comp.timestamp else None,
                        })
                    except Exception:
                        continue

                data["admin_stats"] = {
                    "total_users": total_users,
                    "total_files": total_files,
                    "total_comparisons": total_comparisons,
                    "top_users": [
                        {
                            "username": item['user__username'] or "Unknown",
                            "comparison_count": item['comparison_count']
                        }
                        for item in top_users_query
                    ],
                    "system_file_types": system_file_types,
                    "recent_system_activity": admin_recent_activity,
                    "system_activity_by_day": sys_activity_data
                }
            except Exception as e:
                # If admin stats fail, still return user stats
                data["admin_stats_error"] = f"Failed to load admin stats: {str(e)}"

        return Response(data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            "error": f"Failed to fetch analytics: {str(e)}",
            "user_stats": {
                "total_files": 0,
                "total_comparisons": 0,
                "file_types": {},
                "recent_comparisons": [],
                "activity_by_day": {}
            }
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

