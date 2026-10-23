from rest_framework import serializers
from .models import User


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'country', 'role', 'info', 'photo', 'password']

    def validate_role(self, value):
        if value == 'admin':
            raise serializers.ValidationError('You cannot register as admin.')
        return value

    def create(self, data):
        password = data.pop('password')
        user = User(**data)
        user.username = data['email']
        user.set_password(password)
        user.save()
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email', 'phone', 'country', 'role', 'info', 'photo']