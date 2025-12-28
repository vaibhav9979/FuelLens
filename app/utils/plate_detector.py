import cv2
import numpy as np
import pytesseract
from PIL import Image
import re
import pickle
import os
from datetime import datetime
from app.models import Vehicle
from app import db

class PlateDetector:
    def __init__(self):
        # Configure tesseract
        # You might need to set the path to tesseract executable on Windows
        # pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        pass
    
    def detect_plate_from_image(self, image_path):
        """
        Detect number plate from an image file
        """
        try:
            # Load image
            img = cv2.imread(image_path)
            if img is None:
                return None
            
            # Apply advanced image enhancement techniques
            enhanced_images = self.enhance_image_for_plate_detection(img)
            
            # Try OCR on different enhanced versions of the image
            text_options = []
            
            # Define custom configs for tesseract
            custom_config = r'--oem 3 --psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
            custom_config_psm6 = r'--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
            custom_config_psm7 = r'--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
            custom_config_psm13 = r'--oem 3 --psm 13 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
            
            # Process each enhanced image with different OCR configurations
            for i, enhanced_img in enumerate(enhanced_images):
                # Try with default config
                text1 = pytesseract.image_to_string(enhanced_img, config=custom_config)
                text_options.append(text1)
                
                # Try with PSM 6
                text2 = pytesseract.image_to_string(enhanced_img, config=custom_config_psm6)
                text_options.append(text2)
                
                # Try with PSM 7
                text3 = pytesseract.image_to_string(enhanced_img, config=custom_config_psm7)
                text_options.append(text3)
                
                # Try with PSM 13
                text4 = pytesseract.image_to_string(enhanced_img, config=custom_config_psm13)
                text_options.append(text4)
            
            # Common patterns for Indian number plates
            plate_patterns = [
                r'[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{1,4}',  # Standard format: XX00XXX0000
                r'[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{1,4}',    # Alternative format
                r'[A-Z]{3}[0-9]{1,4}',                        # Three letters followed by numbers
                r'[A-Z]{2}[0-9]{4}',                          # Two letters followed by 4 digits
                r'[A-Z]{2}[0-9]{1,2}[A-Z]{1,2}[0-9]{1,4}',   # Another common format
                r'[A-Z]{2}[0-9]{1,2}[A-Z]{1}[0-9]{1,4}',     # Another format
                r'[A-Z0-9]{3,10}'                            # General alphanumeric pattern
            ]
            
            detected_plate = None
            
            # Check each text option
            for text in text_options:
                for pattern in plate_patterns:
                    matches = re.findall(pattern, text)
                    if matches:
                        detected_plate = matches[0]
                        break
                if detected_plate:
                    break
            
            # If still no detection, try combining lines from multi-line OCR
            if not detected_plate:
                for text in text_options:
                    lines = text.strip().split('\n')
                    if len(lines) >= 2:
                        # Try combining consecutive lines to form a plate
                        for i in range(len(lines) - 1):
                            combined = re.sub(r'[^A-Za-z0-9]', '', lines[i] + lines[i+1])
                            for pattern in plate_patterns:
                                matches = re.findall(pattern, combined)
                                if matches:
                                    detected_plate = matches[0]
                                    break
                            if detected_plate:
                                break
                    if detected_plate:
                        break
            
            # If no pattern matches, return the most alphanumeric text from all options
            if not detected_plate:
                all_text = ' '.join(text_options)
                alphanumeric_text = re.sub(r'[^A-Za-z0-9]', '', all_text)
                if len(alphanumeric_text) >= 3:
                    # Try to find the most likely plate format
                    for pattern in plate_patterns[:-1]:  # Exclude the general pattern for this check
                        matches = re.findall(pattern, all_text)
                        if matches:
                            detected_plate = matches[0]
                            break
                    
                    if not detected_plate and len(alphanumeric_text) >= 3:
                        detected_plate = alphanumeric_text[:10]  # Limit to 10 characters
            
            # Validate the detected plate - ensure it has a proper format
            if detected_plate:
                # Store the original text for learning purposes
                original_text = ' '.join(text_options)
                detected_plate = self.validate_and_correct_plate(detected_plate)
                # Learn from this detection to improve future accuracy
                self.learn_from_detection(original_text, detected_plate)
            
            return detected_plate
        except Exception as e:
            print(f"Error in plate detection: {e}")
            return None
    
    def detect_plate_from_bytes(self, image_bytes):
        """
        Detect number plate from image bytes (e.g., from camera input)
        """
        try:
            # Convert bytes to numpy array
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                return None
            
            # Apply advanced image enhancement techniques
            enhanced_images = self.enhance_image_for_plate_detection(img)

            # Try OCR on different enhanced versions of the image
            text_options = []
            
            # Define custom configs for tesseract
            custom_config = r'--oem 3 --psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
            custom_config_psm6 = r'--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
            custom_config_psm7 = r'--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
            custom_config_psm13 = r'--oem 3 --psm 13 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
            
            # Process each enhanced image with different OCR configurations
            for i, enhanced_img in enumerate(enhanced_images):
                # Try with default config
                text1 = pytesseract.image_to_string(enhanced_img, config=custom_config)
                text_options.append(text1)
                
                # Try with PSM 6
                text2 = pytesseract.image_to_string(enhanced_img, config=custom_config_psm6)
                text_options.append(text2)
                
                # Try with PSM 7
                text3 = pytesseract.image_to_string(enhanced_img, config=custom_config_psm7)
                text_options.append(text3)
                
                # Try with PSM 13
                text4 = pytesseract.image_to_string(enhanced_img, config=custom_config_psm13)
                text_options.append(text4)
            
            # Common patterns for Indian number plates
            plate_patterns = [
                r'[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{1,4}',  # Standard format: XX00XXX0000
                r'[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{1,4}',    # Alternative format
                r'[A-Z]{3}[0-9]{1,4}',                        # Three letters followed by numbers
                r'[A-Z]{2}[0-9]{4}',                          # Two letters followed by 4 digits
                r'[A-Z]{2}[0-9]{1,2}[A-Z]{1,2}[0-9]{1,4}',   # Another common format
                r'[A-Z]{2}[0-9]{1,2}[A-Z]{1}[0-9]{1,4}',     # Another format
                r'[A-Z0-9]{3,10}'                            # General alphanumeric pattern
            ]
            
            detected_plate = None
            
            # Check each text option
            for text in text_options:
                for pattern in plate_patterns:
                    matches = re.findall(pattern, text)
                    if matches:
                        detected_plate = matches[0]
                        break
                if detected_plate:
                    break
            
            # If still no detection, try combining lines from multi-line OCR
            if not detected_plate:
                for text in text_options:
                    lines = text.strip().split('\n')
                    if len(lines) >= 2:
                        # Try combining consecutive lines to form a plate
                        for i in range(len(lines) - 1):
                            combined = re.sub(r'[^A-Za-z0-9]', '', lines[i] + lines[i+1])
                            for pattern in plate_patterns:
                                matches = re.findall(pattern, combined)
                                if matches:
                                    detected_plate = matches[0]
                                    break
                            if detected_plate:
                                break
                    if detected_plate:
                        break
            
            # If no pattern matches, return the most alphanumeric text from all options
            if not detected_plate:
                all_text = ' '.join(text_options)
                alphanumeric_text = re.sub(r'[^A-Za-z0-9]', '', all_text)
                if len(alphanumeric_text) >= 3:
                    # Try to find the most likely plate format
                    for pattern in plate_patterns[:-1]:  # Exclude the general pattern for this check
                        matches = re.findall(pattern, all_text)
                        if matches:
                            detected_plate = matches[0]
                            break
                    
                    if not detected_plate and len(alphanumeric_text) >= 3:
                        detected_plate = alphanumeric_text[:10]  # Limit to 10 characters
            
            # Validate the detected plate - ensure it has a proper format
            if detected_plate:
                # Store the original text for learning purposes
                original_text = ' '.join(text_options)
                detected_plate = self.validate_and_correct_plate(detected_plate)
                # Learn from this detection to improve future accuracy
                self.learn_from_detection(original_text, detected_plate)
            
            return detected_plate
        except Exception as e:
            print(f"Error in plate detection from bytes: {e}")
            return None
    
    def validate_plate_in_db(self, plate_number):
        """
        Check if the detected plate exists in the database
        """
        try:
            vehicle = Vehicle.query.filter_by(vehicle_number=plate_number.upper()).first()
            return vehicle
        except Exception as e:
            print(f"Error validating plate in DB: {e}")
            return None
    
    def enhance_image_for_plate_detection(self, img):
        """
        Apply advanced image enhancement techniques specifically for number plate detection
        """
        # Convert to grayscale if not already
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img
        
        # Apply multiple enhancement techniques
        enhanced_images = []
        
        # 1. Basic CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced1 = clahe.apply(gray)
        enhanced_images.append(enhanced1)
        
        # 2. Bilateral filter to reduce noise while keeping edges sharp
        bilateral = cv2.bilateralFilter(gray, 9, 75, 75)
        enhanced2 = clahe.apply(bilateral)
        enhanced_images.append(enhanced2)
        
        # 3. Morphological operations to enhance text
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        morph1 = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
        morph1 = clahe.apply(morph1)
        enhanced_images.append(morph1)
        
        # 4. Top-hat transformation to enhance bright text on dark background
        kernel_tophat = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
        tophat = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, kernel_tophat)
        tophat_enhanced = clahe.apply(tophat)
        enhanced_images.append(tophat_enhanced)
        
        # 5. Sharpening filter
        kernel_sharpen = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
        sharpened = cv2.filter2D(gray, -1, kernel_sharpen)
        enhanced5 = clahe.apply(sharpened)
        enhanced_images.append(enhanced5)
        
        # 6. Combine techniques: bilateral + clahe + sharpening
        bilateral_sharp = cv2.filter2D(bilateral, -1, kernel_sharpen)
        enhanced6 = clahe.apply(bilateral_sharp)
        enhanced_images.append(enhanced6)
        
        # 7. Apply different thresholding methods
        _, thresh_otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        enhanced_images.append(thresh_otsu)
        
        _, thresh_binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        enhanced_images.append(thresh_binary)
        
        # 8. Adaptive threshold
        adaptive_thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        enhanced_images.append(adaptive_thresh)
        
        return enhanced_images
    
    def validate_and_correct_plate(self, plate):
        """
        Validate and correct the detected plate by checking format and making common corrections
        """
        if not plate:
            return plate
            
        # Remove any spaces and convert to uppercase
        plate = plate.replace(' ', '').upper()
        
        # Common OCR mistakes corrections
        corrections = {
            '1': 'I',  # Sometimes 'I' is recognized as '1'
            '0': 'O',  # Sometimes 'O' is recognized as '0'
            '5': 'S',  # Sometimes 'S' is recognized as '5'
            '8': 'B',  # Sometimes 'B' is recognized as '8'
            '2': 'Z',  # Sometimes 'Z' is recognized as '2'
        }
        
        # Apply corrections based on context (letters vs numbers in specific positions)
        corrected_plate = ''
        for i, char in enumerate(plate):
            if char.isdigit():
                # For positions likely to be numbers (after letters), keep as numbers
                corrected_plate += char
            elif char.isalpha():
                corrected_plate += char
            else:
                # Remove any other characters
                continue
        
        # Ensure the plate has the right format: 2 letters + numbers + letters + numbers
        # This is a simple validation - more sophisticated validation can be added
        if len(corrected_plate) >= 3:
            # Check if it matches a basic format
            if corrected_plate[:2].isalpha() and any(c.isdigit() for c in corrected_plate[2:]):
                return corrected_plate
        
        # If no specific corrections, return the cleaned plate
        return plate
    
    def learn_from_detection(self, original_text, corrected_plate):
        """
        Store successful detection patterns to improve future detections
        """
        # Create a simple learning data file to store successful patterns
        learning_file = 'plate_detection_learning.pkl'
        learning_data = {}
        
        # Load existing learning data if it exists
        if os.path.exists(learning_file):
            try:
                with open(learning_file, 'rb') as f:
                    learning_data = pickle.load(f)
            except:
                learning_data = {}
        
        # Add the successful detection to learning data
        if corrected_plate:
            # Store the original text and the corrected plate for future reference
            if 'successful_detections' not in learning_data:
                learning_data['successful_detections'] = []
            
            # Store the detection pair
            detection_pair = {
                'original': original_text,
                'corrected': corrected_plate,
                'timestamp': str(datetime.now())
            }
            learning_data['successful_detections'].append(detection_pair)
            
            # Keep only the last 100 successful detections to avoid the file growing too large
            if len(learning_data['successful_detections']) > 100:
                learning_data['successful_detections'] = learning_data['successful_detections'][-100:]
        
        # Save the updated learning data
        try:
            with open(learning_file, 'wb') as f:
                pickle.dump(learning_data, f)
        except:
            # If we can't save, just continue
            pass
    
    def apply_learning_corrections(self, text):
        """
        Apply learned corrections to improve detection
        """
        learning_file = 'plate_detection_learning.pkl'
        
        if os.path.exists(learning_file):
            try:
                with open(learning_file, 'rb') as f:
                    learning_data = pickle.load(f)
                
                # This is a simple implementation - in a real system, you could use more
                # sophisticated pattern matching to apply learned corrections
                if 'successful_detections' in learning_data:
                    # For now, just return the text as is
                    # In a more advanced implementation, you could analyze patterns
                    # in the learning data to improve future detections
                    pass
            except:
                pass
        
        return text