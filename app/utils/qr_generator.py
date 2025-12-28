import qrcode
import json
from datetime import datetime
import os
from app.models import QRCode as QRCodeModel, Vehicle
from app import db

class QRGenerator:
    def __init__(self):
        pass
    
    def generate_qr_code(self, vehicle_id, vehicle_number, expiry_date, user_id):
        """
        Generate a QR code for a vehicle with compliance information
        """
        try:
            # Create QR code content with vehicle info
            qr_data = {
                'vehicle_id': vehicle_id,
                'vehicle_number': vehicle_number,
                'expiry_date': expiry_date.isoformat() if expiry_date else None,
                'generated_at': datetime.utcnow().isoformat(),
                'status': 'valid',  # This will be checked against database when scanned
                'user_id': user_id
            }
            
            qr_content = json.dumps(qr_data)
            
            # Create QR code image
            qr_img = qrcode.make(qr_content)
            
            # Create filename
            qr_filename = f"qr_{vehicle_id}_{vehicle_number.replace(' ', '_').replace('/', '_')}.png"
            qr_path = os.path.join('app', 'static', 'qr_codes', qr_filename)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(qr_path), exist_ok=True)
            
            # Save QR code image
            qr_img.save(qr_path)
            
            # Create QR code record in database
            qr_code = QRCodeModel(
                vehicle_id=vehicle_id,
                qr_code_path=qr_path,
                qr_content=qr_content
            )
            
            db.session.add(qr_code)
            db.session.commit()
            
            return qr_path, qr_content
        except Exception as e:
            print(f"Error generating QR code: {e}")
            return None, None
    
    def validate_qr_code(self, qr_content):
        """
        Validate QR code content against database
        """
        try:
            # Parse QR content
            qr_data = json.loads(qr_content)
            vehicle_id = qr_data.get('vehicle_id')
            
            # Get vehicle from database
            vehicle = Vehicle.query.get(vehicle_id)
            if not vehicle:
                return {
                    'valid': False,
                    'message': 'Vehicle not found in the system',
                    'vehicle': None
                }
            
            # Check if QR code is still valid
            from app.utils.helpers import calculate_compliance_status
            compliance_status = calculate_compliance_status(vehicle.cng_expiry_date)
            
            # Check if QR code has expired (generated more than 24 hours ago)
            generated_at = datetime.fromisoformat(qr_data['generated_at'])
            if (datetime.utcnow() - generated_at).days > 0:
                # QR code is still valid but generated long ago, update the data
                updated_data = {
                    'vehicle_id': vehicle.id,
                    'vehicle_number': vehicle.vehicle_number,
                    'expiry_date': vehicle.cng_expiry_date.isoformat() if vehicle.cng_expiry_date else None,
                    'generated_at': datetime.utcnow().isoformat(),
                    'status': compliance_status,
                    'user_id': vehicle.user_id
                }
                
                return {
                    'valid': True,
                    'message': 'QR code validated successfully',
                    'vehicle': vehicle,
                    'updated_data': json.dumps(updated_data),
                    'compliance_status': compliance_status
                }
            
            return {
                'valid': True,
                'message': 'QR code validated successfully',
                'vehicle': vehicle,
                'compliance_status': compliance_status
            }
        except json.JSONDecodeError:
            return {
                'valid': False,
                'message': 'Invalid QR code format',
                'vehicle': None
            }
        except Exception as e:
            print(f"Error validating QR code: {e}")
            return {
                'valid': False,
                'message': 'Error validating QR code',
                'vehicle': None
            }
    
    def scan_qr_code_from_image(self, image_path):
        """
        Scan QR code from an image file
        """
        try:
            from pyzbar import pyzbar
            from PIL import Image
            
            # Load image
            img = Image.open(image_path)
            
            # Decode QR codes
            decoded_objects = pyzbar.decode(img)
            
            if decoded_objects:
                # Return the first QR code found
                return decoded_objects[0].data.decode('utf-8')
            else:
                return None
        except ImportError:
            # If pyzbar is not installed, return None
            print("pyzbar not installed. Install it with: pip install pyzbar")
            return None
        except Exception as e:
            print(f"Error scanning QR code from image: {e}")
            return None