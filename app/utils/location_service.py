from geopy.distance import geodesic
from geopy.geocoders import Nominatim
from app.models import FuelStation
from app import db
from math import radians, cos, sin, asin, sqrt

class LocationService:
    def __init__(self):
        # Initialize geocoder (using Nominatim for open street map data)
        self.geocoder = Nominatim(user_agent="fuellens_app")
    
    def get_coordinates_from_address(self, address):
        """
        Get latitude and longitude from an address
        """
        try:
            location = self.geocoder.geocode(address)
            if location:
                return location.latitude, location.longitude
            return None, None
        except Exception as e:
            print(f"Error geocoding address: {e}")
            return None, None
    
    def calculate_distance(self, lat1, lon1, lat2, lon2):
        """
        Calculate distance between two coordinates in kilometers using haversine formula
        """
        # Convert decimal degrees to radians
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        
        # Radius of earth in kilometers
        r = 6371
        
        return c * r
    
    def find_nearby_stations(self, user_lat, user_lon, radius_km=10):
        """
        Find fuel stations within a given radius from user's location
        """
        nearby_stations = []
        
        # Get all active fuel stations
        stations = FuelStation.query.filter_by(is_active=True).all()
        
        for station in stations:
            if station.latitude and station.longitude:
                distance = self.calculate_distance(
                    user_lat, user_lon, 
                    station.latitude, station.longitude
                )
                
                if distance <= radius_km:
                    station_data = {
                        'id': station.id,
                        'name': station.name,
                        'address': station.get_full_address(),
                        'distance': round(distance, 2),
                        'is_open': station.is_open,
                        'live_load': station.live_load,
                        'fuel_availability': station.fuel_availability,
                        'latitude': station.latitude,
                        'longitude': station.longitude
                    }
                    nearby_stations.append(station_data)
        
        # Sort by distance
        nearby_stations.sort(key=lambda x: x['distance'])
        return nearby_stations
    
    def get_stations_by_city(self, city, state=None):
        """
        Get all fuel stations in a specific city (and optionally state)
        """
        query = FuelStation.query.filter_by(is_active=True)
        
        if state:
            query = query.filter(FuelStation.state.ilike(f'%{state}%'))
        
        stations = query.filter(FuelStation.city.ilike(f'%{city}%')).all()
        
        station_list = []
        for station in stations:
            station_data = {
                'id': station.id,
                'name': station.name,
                'address': station.get_full_address(),
                'is_open': station.is_open,
                'live_load': station.live_load,
                'fuel_availability': station.fuel_availability,
                'latitude': station.latitude,
                'longitude': station.longitude
            }
            station_list.append(station_data)
        
        return station_list
    
    def update_station_location(self, station_id, address):
        """
        Update station location based on address
        """
        try:
            lat, lon = self.get_coordinates_from_address(address)
            if lat and lon:
                station = FuelStation.query.get(station_id)
                if station:
                    station.latitude = lat
                    station.longitude = lon
                    db.session.commit()
                    return True
            return False
        except Exception as e:
            print(f"Error updating station location: {e}")
            return False
    
    def get_optimal_station(self, user_lat, user_lon, station_type='cng'):
        """
        Get the optimal station based on distance, load, and availability
        """
        nearby_stations = self.find_nearby_stations(user_lat, user_lon, radius_km=20)
        
        # Score each station based on distance, load, and availability
        scored_stations = []
        for station in nearby_stations:
            score = 0
            
            # Distance factor (closer is better) - up to 50 points
            distance_score = max(0, 50 - (station['distance'] * 2))
            score += distance_score
            
            # Load factor (less busy is better) - up to 30 points
            if station['live_load'] == 'free':
                score += 30
            elif station['live_load'] == 'normal':
                score += 15
            else:  # busy
                score += 5
            
            # Availability factor (available is better) - up to 20 points
            if station['fuel_availability'] == 'available':
                score += 20
            elif station['fuel_availability'] == 'limited':
                score += 10
            else:  # unavailable
                score += 0
            
            station['score'] = score
            scored_stations.append(station)
        
        # Sort by score (descending)
        scored_stations.sort(key=lambda x: x['score'], reverse=True)
        
        return scored_stations