from django.contrib.auth.models import Group, User
from rest_framework import serializers
from .models import Company, Contacts, Address, PhoneNumber, Comment


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'email', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        return user


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ['url', 'name']


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ['address', 'verified']


class PhoneNumberSerializer(serializers.ModelSerializer):
    class Meta:
        model = PhoneNumber
        fields = ['number', 'verified', 'description']


class ContactsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contacts
        fields = ['name', 'verified_profile', 'level', 'google_link', 'linkedin_link']

class CommentSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')

    class Meta:
        model = Comment
        fields = ['id', 'user', 'text', 'rating', 'created_at']
        read_only_fields = ['user']

class CompanySerializer(serializers.ModelSerializer):
    address = AddressSerializer(read_only=True)
    contacts = ContactsSerializer(many=True, read_only=True)
    phone_numbers = PhoneNumberSerializer(many=True, read_only=True)

    class Meta:
        model = Company
        fields = [
            'name',
            'slug',
            'is_processed',
            'url',
            'score',
            'address',
            'contacts',
            'phone_numbers',
            'social_urls',
            'comments'
        ]
        read_only_fields = ['slug', 'is_processed']
