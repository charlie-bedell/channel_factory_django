from .models import Location
from rest_framework import serializers


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = '__all__'


class AddressSerializer(serializers.Serializer):
    location1 = serializers.CharField(max_length=255)
    location2 = serializers.CharField(max_length=255)
