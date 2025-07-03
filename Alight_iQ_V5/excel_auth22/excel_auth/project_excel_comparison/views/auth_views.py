from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from datetime import timedelta, datetime, timezone as dt_timezone
from django.utils import timezone

from ..models import User
from ..serializers import RegisterSerializer, LoginSerializer


class RegisterView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'data': RegisterSerializer(user).data,
                'message': 'User registered successfully.',
                'token': str(refresh.access_token),
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data
            refresh = RefreshToken.for_user(user)
            return Response({
                'data': RegisterSerializer(user).data,
                'message': 'Login successful.',
                'token': str(refresh.access_token),
            })
        return Response({'message': 'Invalid credentials.'}, status=status.HTTP_401_UNAUTHORIZED)


class TokenExpiredView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        token_created_at = request.auth.payload.get('iat', None)
        if token_created_at:
            expiration_minutes = 1200
            created_time = datetime.fromtimestamp(token_created_at, tz=dt_timezone.utc)
            if timezone.now() > created_time + timedelta(minutes=expiration_minutes):
                return Response({
                    'data': [],
                    'message': 'Token expired.',
                    'token': None
                }, status=status.HTTP_401_UNAUTHORIZED)

        return Response({
            'data': RegisterSerializer(request.user).data,
            'message': 'Token valid.',
            'token': str(request.auth)
        })
