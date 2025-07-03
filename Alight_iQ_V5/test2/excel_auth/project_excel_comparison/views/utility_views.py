import json
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.db.models import Count
from django.db.models.functions import TruncDay
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes

from ..models import User, FileUpload, Comparison
from ..funtions import get_sheet_names, get_header


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
