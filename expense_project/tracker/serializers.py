from rest_framework import serializers
from .models import CustomUser

class RegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    security_question = serializers.CharField(required=True)
    security_answer = serializers.CharField(required=True)

    class Meta:
        model = CustomUser
        fields = ['email', 'password', 'display_name', 'gender', 'security_question', 'security_answer']

    def validate_email(self, value):
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def create(self, validated_data):
        user = CustomUser.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            display_name=validated_data['display_name'],
            gender=validated_data.get('gender', ''),
            security_question=validated_data['security_question'],
            security_answer=validated_data['security_answer']
        )
        return user

class ForgotPasswordEmailSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    
    def validate_email(self, value):
        if not CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("We couldn't find an account with that email address.")
        return value

class ResetPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(required=True, write_only=True, min_length=8)
    confirm_password = serializers.CharField(required=True, write_only=True, min_length=8)
    
    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return data
