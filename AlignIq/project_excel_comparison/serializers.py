from rest_framework import serializers
from .models import User, FileUpload , Comparison , Database_Connection
from django.contrib.auth import authenticate
 
class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'password', 'role', 'can_delete_files']
        extra_kwargs = {'password': {'write_only': True}}
 
    def create(self, validated_data):
        return User.objects.create_user(**validated_data)
 
class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
 
    def validate(self, data):
        user = authenticate(**data)
        if user and user.is_active:
            return user
        raise serializers.ValidationError("Invalid credentials")
 
class FileUploadSerializer(serializers.ModelSerializer):
    uploaded_by = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = FileUpload
        fields = ['id', 'file', 'uploaded_at', 'uploaded_by']
 
class UserWithFilesSerializer(serializers.ModelSerializer):
    files = FileUploadSerializer(many=True, read_only=True)
 
    class Meta:
        model = User
        fields = ['id', 'username', 'role', 'files']


class ComparisonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comparison
        fields = '__all__'

class DatabaseConnectionSerializer(serializers.ModelSerializer):
    username_display = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = Database_Connection
        fields = ['id', 'user', 'username_display', 'username', 'password', 'DSN', 'created_at']
        extra_kwargs = {
            'password': {'write_only': True},
            'user': {'required': False}
        }
