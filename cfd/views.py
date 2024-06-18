from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import Http404
from .serializers import LocationSerializer, AddressSerializer
from .models import Location
import requests

from math import radians, cos, sin, sqrt, atan2

# TODO: remove lazy env imports
from pathlib import Path
import environ
import os
BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))


# Create your views here.


class DistanceView(APIView):
    def get(self, request):
        return Response({"get": "looks good"}, status=status.HTTP_200_OK)

    def post(self, request):

        address_serializer = AddressSerializer(data=request.data)

        if address_serializer.is_valid():
            location1 = address_serializer.validated_data['location1']
            location2 = address_serializer.validated_data['location2']

            loc1 = self.get_or_create_location(location1)
            loc2 = self.get_or_create_location(location2)

            if loc1 and loc2:
                distance = self.calculate_distance(loc1.lat, loc1.lng, loc2.lat, loc2.lng)
                return Response({'distance(KM)': distance,
                                 'distance(MI)': self.to_mi(distance)}, status=status.HTTP_200_OK)
            else:
                return Response({'error': 'Unable to process locations'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(address_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def to_mi(self, distance):
        return distance * 0.6214

    def get_or_create_location(self, address):

        address_parts = address.split(', ')
        address_struct = {}

        for i in address_parts:
            if ((i.isalpha()) & (len(i) == 2)):
                address_struct['state'] = i

        if address_struct['state']:
            location = Location.objects.filter(state=address_struct['state'])
            location = location.filter(full_address__contains=address_parts[0]).first()
        else:
            location = Location.objects.filter(full_address__contains=address_parts[0]).first(0)

        if location:
            print("FOUND LOCATION!")
            return location

        google_maps_api_key = env("GOOGLE_MAPS_API_KEY")
        response = requests.get(f'https://maps.googleapis.com/maps/api/geocode/json?address={address}&key={google_maps_api_key}')
        data = response.json()

        if data['status'] == 'OK':
            result = data['results'][0]
            lat = result['geometry']['location']['lat']
            lng = result['geometry']['location']['lng']
            full_address = result['formatted_address']
            state = None
            country = None

            loc_match = Location.objects.filter(full_address=full_address).first()
            if loc_match:
                # TODO write poor matches (user_data:existing_record) to log,
                # where user input was unable to be parsed from location
                # the first time. use logs to iterate on search algorithm
                return loc_match

            for component in result['address_components']:
                if 'administrative_area_level_1' in component['types']:
                    state = component['short_name']
                    if 'country' in component['types']:
                        country = component['long_name']

            location_serializer = LocationSerializer(data={
                'full_address': full_address,
                'lat': lat,
                'lng': lng,
                'state': state if state else "NA",
                'country': country if country else "NA"
            })

            if location_serializer.is_valid():
                location = location_serializer.save()
                return location
            else:
                print(location_serializer.errors)
                return None
        else:
            return None

    def calculate_distance(self, lat1, lng1, lat2, lng2):
        # in kilometers

        R = 6371.0  # earth radius in km

        lat1 = radians(lat1)
        lng1 = radians(lng1)
        lat2 = radians(lat2)
        lng2 = radians(lng2)

        dlat = lat2 - lat1
        dlng = lng2 - lng1

        a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) + sin(dlng / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        distance = R * c

        return distance
