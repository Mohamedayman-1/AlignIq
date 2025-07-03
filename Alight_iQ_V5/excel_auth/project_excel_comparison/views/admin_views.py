from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from ..models import User
from ..permissions import IsAdmin


class ListUsersView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request):
        users = User.objects.exclude(id=request.user.id)
        data = []
        for user in users:
            data.append({
                'id': user.id,
                'username': user.username,
                'role': user.role,
                'can_delete_files': user.can_delete_files
            })
        return Response(data)


class UpdateUserPermissionView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def put(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            can_delete_files = request.data.get('can_delete_files', False)
            
            user.can_delete_files = can_delete_files
            user.save()
            
            return Response({
                "message": f"Permissions updated for user {user.username}",
                "can_delete_files": user.can_delete_files
            })
        except User.DoesNotExist:
            return Response({"message": "User not found."}, status=status.HTTP_404_NOT_FOUND)
