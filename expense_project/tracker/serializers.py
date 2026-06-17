from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import EmailOTP
import re

User = get_user_model()

class RegistrationSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    display_name = serializers.CharField(required=True, max_length=150)
    gender = serializers.CharField(required=True, max_length=20)
    password = serializers.CharField(required=True, write_only=True, min_length=8)
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

class OTPVerificationSerializer(serializers.Serializer):
    otp_code = serializers.CharField(required=True, max_length=6, min_length=6)

class ForgotPasswordEmailSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    
    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("We couldn't find an account with that email address.")
        return value

class ResetPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(required=True, write_only=True, min_length=8)
    confirm_password = serializers.CharField(required=True, write_only=True, min_length=8)
    
    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return data
