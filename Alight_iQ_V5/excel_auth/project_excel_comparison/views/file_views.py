import os
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from ..models import FileUpload
from ..serializers import FileUploadSerializer
from ..permissions import IsAdmin
from ..encryption import encrypt_file


class UploadFileView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        file = request.FILES.get('file')

        if FileUpload.objects.filter(user=request.user, file__icontains=file.name).exists():
            return Response({"message": "File already uploaded."}, status=status.HTTP_400_BAD_REQUEST)

        file_upload = FileUpload.objects.create(user=request.user, file=file)
        file_path = file_upload.file.path
        
        try:
            encrypt_file(file_path)
        except Exception as e:
            file_upload.delete()
            return Response({'error': f'Failed to encrypt file: {str(e)}'}, status=500)
        
        return Response({"message": "Files uploaded and encrypted successfully.", "file_id": file_upload.id}, status=status.HTTP_201_CREATED)

    def delete(self, request, file_id):
        if request.user.role != 'admin' and not request.user.can_delete_files:
            return Response({
                "message": "You don't have permission to delete files."
            }, status=status.HTTP_403_FORBIDDEN)
        
        file_upload = FileUpload.objects.filter(id=file_id).first()
        if not file_upload:
            return Response({"message": "File not found."}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            file_path = file_upload.file.path
            file_upload.delete()
            
            if os.path.exists(file_path):
                os.remove(file_path)
                
            directory = os.path.dirname(file_path)
            if os.path.exists(directory) and not os.listdir(directory):
                os.rmdir(directory)
                
            return Response({"message": "File deleted successfully."}, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                "message": f"Error deleting file: {str(e)}",
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ListUserFilesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        files = FileUpload.objects.filter(user=request.user)
        serializer = FileUploadSerializer(files, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ListAllFilesAdminView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        files = FileUpload.objects.all()
        serializer = FileUploadSerializer(files, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
