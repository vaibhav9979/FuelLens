from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import FuelStation, User, StationRating
from app.utils.location_service import LocationService
from app.utils.helpers import send_notification
import json

stations_bp = Blueprint('stations', __name__)

@stations_bp.route('/nearby-stations')
@login_required
def nearby_stations():
    # Get user's location from request or session
    user_lat = request.args.get('lat', type=float)
    user_lon = request.args.get('lon', type=float)
    
    if not user_lat or not user_lon:
        # If no location provided, show a form to enter location
        return render_template('stations/find_nearby.html')
    
    location_service = LocationService()
    nearby_stations = location_service.find_nearby_stations(user_lat, user_lon)
    
    return render_template('stations/nearby.html', 
                          stations=nearby_stations, 
                          user_lat=user_lat, 
                          user_lon=user_lon)

@stations_bp.route('/find-stations', methods=['GET', 'POST'])
@login_required
def find_stations():
    if request.method == 'POST':
        city = request.form.get('city', '').strip()
        state = request.form.get('state', '').strip()
        
        location_service = LocationService()
        stations = location_service.get_stations_by_city(city, state if state else None)
        
        return render_template('stations/results.html', 
                              stations=stations, 
                              city=city, 
                              state=state)
    
    return render_template('stations/find.html')

@stations_bp.route('/station/<int:station_id>')
@login_required
def station_details(station_id):
    station = FuelStation.query.get_or_404(station_id)
    
    # Get ratings for this station
    ratings = StationRating.query.filter_by(station_id=station_id).all()
    
    # Calculate average ratings
    if ratings:
        avg_compliance = sum(r.compliance_strictness for r in ratings) / len(ratings)
        avg_waiting = sum(r.waiting_time for r in ratings) / len(ratings)
        avg_service = sum(r.service_quality for r in ratings) / len(ratings)
        avg_overall = sum(r.overall_rating for r in ratings) / len(ratings)
    else:
        avg_compliance = avg_waiting = avg_service = avg_overall = 0
    
    return render_template('stations/detail.html', 
                          station=station, 
                          ratings=ratings,
                          avg_compliance=round(avg_compliance, 1),
                          avg_waiting=round(avg_waiting, 1),
                          avg_service=round(avg_service, 1),
                          avg_overall=round(avg_overall, 1))

@stations_bp.route('/station/<int:station_id>/rate', methods=['POST'])
@login_required
def rate_station(station_id):
    station = FuelStation.query.get_or_404(station_id)
    
    compliance_strictness = request.form.get('compliance_strictness', type=int)
    waiting_time = request.form.get('waiting_time', type=int)
    service_quality = request.form.get('service_quality', type=int)
    review = request.form.get('review', '').strip()
    
    if not all([compliance_strictness, waiting_time, service_quality]):
        flash('All rating fields are required!', 'error')
        return redirect(url_for('stations.station_details', station_id=station_id))
    
    if not (1 <= compliance_strictness <= 5 and 1 <= waiting_time <= 5 and 1 <= service_quality <= 5):
        flash('Ratings must be between 1 and 5!', 'error')
        return redirect(url_for('stations.station_details', station_id=station_id))
    
    # Calculate overall rating
    overall_rating = (compliance_strictness + waiting_time + service_quality) / 3
    
    try:
        # Check if user has already rated this station
        existing_rating = StationRating.query.filter_by(
            station_id=station_id, 
            rater_id=current_user.id
        ).first()
        
        if existing_rating:
            # Update existing rating
            existing_rating.compliance_strictness = compliance_strictness
            existing_rating.waiting_time = waiting_time
            existing_rating.service_quality = service_quality
            existing_rating.overall_rating = overall_rating
            existing_rating.review = review
        else:
            # Create new rating
            rating = StationRating(
                station_id=station_id,
                rater_id=current_user.id,
                compliance_strictness=compliance_strictness,
                waiting_time=waiting_time,
                service_quality=service_quality,
                overall_rating=overall_rating,
                review=review
            )
            db.session.add(rating)
        
        db.session.commit()
        flash('Station rated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error rating station. Please try again.', 'error')
    
    return redirect(url_for('stations.station_details', station_id=station_id))

@stations_bp.route('/api/nearby-stations')
@login_required
def api_nearby_stations():
    user_lat = request.args.get('lat', type=float)
    user_lon = request.args.get('lon', type=float)
    radius = request.args.get('radius', default=10, type=int)
    
    if not user_lat or not user_lon:
        return jsonify({'error': 'Latitude and longitude are required'}), 400
    
    location_service = LocationService()
    nearby_stations = location_service.find_nearby_stations(user_lat, user_lon, radius)
    
    return jsonify({'stations': nearby_stations})

@stations_bp.route('/api/optimal-station')
@login_required
def api_optimal_station():
    user_lat = request.args.get('lat', type=float)
    user_lon = request.args.get('lon', type=float)
    
    if not user_lat or not user_lon:
        return jsonify({'error': 'Latitude and longitude are required'}), 400
    
    location_service = LocationService()
    optimal_stations = location_service.get_optimal_station(user_lat, user_lon)
    
    # Return the top 3 optimal stations
    return jsonify({'stations': optimal_stations[:3]})

@stations_bp.route('/station/<int:station_id>/get-directions')
@login_required
def get_directions(station_id):
    station = FuelStation.query.get_or_404(station_id)
    
    # In a real implementation, you would calculate directions
    # For now, we'll just return the station location
    return jsonify({
        'station_name': station.name,
        'station_address': station.get_full_address(),
        'station_lat': station.latitude,
        'station_lon': station.longitude
    })