# mobile_phone_detector.py - EXAM PROCTORING OPTIMIZED
import torch
import time
import cv2
import numpy as np

class MobilePhoneDetector:
    def __init__(self, device='cpu'):
        self.device = device
        
        # ============ EXAM PROCTORING SETTINGS ============
        print(f"📱 Loading Mobile Phone Detector for Exam Proctoring...")
        
        try:
            self.model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True, verbose=False)
        except Exception as e:
            print(f"Error loading YOLOv5: {e}")
            self.model = None

        if self.model:
            # Only detect mobile phones
            self.model.classes = [67, 77]
            # Lowered slightly to 0.30 for better reliability in varying light
            self.model.conf = 0.30  
            self.model.iou = 0.45   # Standard NMS
            self.model.to(device)
            self.model.eval()
        
        # ============ TRACKING SETTINGS ============
        self.phone_tracker = {}
        self.grace_period = 3  # 3 seconds to remove phone
        self.frame_count = 0
        self.violation_count = 0
        self.consecutive_detections_required = 2  # Must see phone in 2 frames
        
    def detect_phones(self, frame, candidate_id='guest_user'):
        """
        Detect mobile phones for exam proctoring
        - 3 second grace period to remove phone
        - Requires 2 consecutive detections
        - Only triggers on CLEAR phone detections
        """
        if self.model is None:
            return []

        results = []
        current_time = time.time()
        self.frame_count += 1
        
        try:
            # Run detection
            detections = self.model(frame)
            
            for *box, conf, cls in detections.xyxy[0].cpu().numpy():
                if int(cls) in [67, 77]:
                    x1, y1, x2, y2 = map(int, box)
                    width = x2 - x1
                    height = y2 - y1
                    
                    # ============ CHECK FOR BACK CAMERA MODULE ============
                    is_camera, camera_type = self._is_back_camera_module(x1, y1, x2, y2, frame)
                    active_grace = self.grace_period
                    
                    if is_camera:
                        active_grace = 1 # Strict: 1 second
                        print(f"🚨🚨🚨 CHEATING ATTEMPT: BACK CAMERA MODULE detected ({camera_type})")
                    
                    # ============ VALIDATION CHECKS ============
                    # 1. Size check - phone should be reasonable size
                    frame_area = frame.shape[0] * frame.shape[1]
                    area = width * height
                    area_percentage = (area / frame_area) * 100
                    
                    # Too small check - Skip if NOT a camera module
                    if not is_camera and area_percentage < 0.2:
                        continue
                    
                    # Too large (> 50% of frame) - likely too close
                    if area_percentage > 50:
                        continue
                    
                    # 2. Aspect ratio check - Skip if NOT a camera module
                    aspect_ratio = width / height if height > 0 else 0
                    if not is_camera and (aspect_ratio < 0.2 or aspect_ratio > 3.0):
                        continue
                    
                    # 3. Confidence check
                    if conf < 0.30:
                        continue
                    
                    # Generate ID based on proximity
                    phone_id = f"phone_{int(x1/20)}_{int(y1/20)}" 
                    
                    # Track phone across frames
                    if phone_id not in self.phone_tracker:
                        self.phone_tracker[phone_id] = {
                            'first_seen': current_time,
                            'last_seen': current_time,
                            'detection_count': 1,
                            'violation_logged': False,
                            'grace_start': None,
                            'warning_shown': False,
                            'phone_part': camera_type if is_camera else self._identify_phone_part(width, height, area_percentage)
                        }
                    else:
                        self.phone_tracker[phone_id]['last_seen'] = current_time
                        self.phone_tracker[phone_id]['detection_count'] += 1
                        if is_camera: # Keep overriding part if camera is clear
                             self.phone_tracker[phone_id]['phone_part'] = camera_type
                    
                    # Need consecutive detections
                    detection_count = self.phone_tracker[phone_id]['detection_count']
                    
                    # Calculate time visible
                    time_visible = current_time - self.phone_tracker[phone_id]['first_seen']
                    
                    # ============ GRACE PERIOD LOGIC ============
                    violation = False
                    grace_remaining = None
                    warning_message = None
                    tracker = self.phone_tracker[phone_id]  # Initialize tracker here for all code paths
                    
                    if detection_count >= self.consecutive_detections_required:
                        
                        # Start grace period on first valid detection
                        if tracker['grace_start'] is None:
                            tracker['grace_start'] = current_time
                            warning_message = f"⚠️ Phone detected! Remove within {active_grace} seconds"
                            print(f"[{self.frame_count}] {warning_message}")
                        
                        # Calculate grace time remaining
                        elapsed_grace = current_time - tracker['grace_start']
                        grace_remaining = max(0, round(active_grace - elapsed_grace, 1))
                        
                        if grace_remaining > 0 and not tracker['violation_logged']:
                             print(f"⏱️  [CANDIDATE: {candidate_id}] REMOVAL COUNTDOWN: {grace_remaining}s ({tracker['phone_part']})")
                        
                        # Check if grace period expired
                        if elapsed_grace >= active_grace and not tracker['violation_logged']:
                            violation = True
                            tracker['violation_logged'] = True
                            self.violation_count += 1
                            
                            print("\n" + "!"*60)
                            print(f"🚨 EXAM VIOLATION #{self.violation_count} for {candidate_id}")
                            print(f"📸 {tracker['phone_part']} DETECTED AND NOT REMOVED")
                            print(f"⏱️  Visible for: {round(time_visible, 1)} seconds")
                            print(f"🎯 Confidence: {round(float(conf)*100, 1)}%")
                            print("!"*60 + "\n")
                    
                    if not violation and grace_remaining is None:
                         # Solid detection but not yet in grace countdown or just detected
                         print(f"📱 [CANDIDATE: {candidate_id}] DETECTED: {tracker['phone_part']} (Conf: {round(float(conf)*100, 1)}%)")

                    results.append({
                        'bbox': (int(x1), int(y1), int(width), int(height)),
                        'confidence': round(float(conf), 2),
                        'time_visible': round(time_visible, 1),
                        'grace_remaining': grace_remaining,
                        'violation': violation,
                        'warning': warning_message,
                        'detection_count': detection_count,
                        'phone_part': self.phone_tracker[phone_id]['phone_part']
                    })
            
            # Cleanup old detections
            self._cleanup(current_time)
            
            return results
            
        except Exception as e:
            print(f"Detection error: {e}")
            import traceback
            traceback.print_exc()
            return []

    def check_violation(self, phone_detections):
        """
        Returns violation only after grace period expired
        """
        for phone in phone_detections:
            if phone['violation']:
                return {
                    'type': 'mobile_phone',
                    'message': f"Mobile phone detected - Violation recorded",
                    'confidence': phone['confidence'],
                    'time_visible': phone['time_visible'],
                    'grace_period': self.grace_period,
                    'phone_part': phone.get('phone_part', 'Mobile Phone')
                }
        return None

    def get_active_warnings(self, phone_detections):
        """
        Get active grace period warnings for UI
        """
        warnings = []
        for phone in phone_detections:
            if phone['grace_remaining'] is not None and phone['grace_remaining'] > 0:
                warnings.append({
                    'message': f"⚠️ Remove phone in {phone['grace_remaining']}s",
                    'grace_remaining': phone['grace_remaining'],
                    'bbox': phone['bbox'],
                    'phone_part': phone.get('phone_part', 'Mobile Phone')
                })
        return warnings

    def _identify_phone_part(self, width, height, area_percentage):
        """Helper to identify part for the UI"""
        aspect_ratio = width / height if height > 0 else 0
        if area_percentage < 2.0:
            return "Phone Edge/Part"
        elif aspect_ratio > 1.5:
            return "Mobile Phone (Landscape)"
        elif aspect_ratio < 0.7:
            return "Mobile Phone (Portrait)"
        else:
            return "Mobile Phone"

    def _is_back_camera_module(self, x1, y1, x2, y2, frame):
        """
        Detect if the object is a BACK CAMERA MODULE pointing at the screen
        This is the most common cheating method - phone held up to show answers
        """
        width = x2 - x1
        height = y2 - y1
        aspect_ratio = width / height if height > 0 else 0
        
        # ============ BACK CAMERA MODULE SIGNATURES ============
        
        # 1. Modern phones: Square/rectangular camera bump (0.7-1.6 aspect ratio)
        is_camera_bump = (
            0.7 < aspect_ratio < 1.6 and
            20 < width < 80 and
            20 < height < 80
        )
        
        # 2. iPhone style: Square camera module with multiple lenses
        is_iphone_camera = (
            0.9 < aspect_ratio < 1.2 and
            25 < width < 70 and
            25 < height < 70
        )
        
        # 3. Samsung/Android: Rectangular camera bar
        is_camera_bar = (
            1.8 < aspect_ratio < 3.0 and
            40 < width < 100 and
            15 < height < 35
        )
        
        # 4. Small circular camera lens (peeking)
        is_circular_lens = (
            0.9 < aspect_ratio < 1.1 and
            10 < width < 30 and
            10 < height < 30
        )
        
        # 5. Camera flash next to lens
        is_camera_flash = (
            0.5 < aspect_ratio < 1.5 and
            8 < width < 25 and
            8 < height < 25
        )
        
        # ============ POSITION ANALYSIS ============
        frame_height = frame.shape[0]
        frame_width = frame.shape[1]
        
        # Camera module is typically in UPPER half
        is_upper_position = y1 < frame_height * 0.5
        
        # Not too close to edges
        margin = 20
        not_edge = (x1 > margin and y1 > margin and 
                    x2 < frame_width - margin and 
                    y2 < frame_height - margin)
        
        is_back_camera = (
            (is_camera_bump or is_iphone_camera or is_camera_bar or is_circular_lens or is_camera_flash) and
            is_upper_position and
            not_edge
        )
        
        camera_type = None
        if is_back_camera:
            if is_iphone_camera: camera_type = "iPhone Camera Module"
            elif is_camera_bar: camera_type = "Android Camera Bar"
            elif is_circular_lens: camera_type = "Camera Lens (Peeking)"
            elif is_camera_flash: camera_type = "Camera Flash"
            else: camera_type = "Back Camera Module"
            
            print(f"📸 BACK CAMERA DETECTED: {camera_type} at ({x1}, {y1})")
            
        return is_back_camera, camera_type

    def _cleanup(self, current_time):
        """Remove old tracking entries"""
        to_delete = []
        for pid, info in self.phone_tracker.items():
            if current_time - info['last_seen'] > 2.0:
                to_delete.append(pid)
        
        for pid in to_delete:
            del self.phone_tracker[pid]

    def reset(self):
        """Reset for new exam session"""
        self.phone_tracker.clear()
        self.frame_count = 0
        self.violation_count = 0
        print("📱 Phone detector reset for new session")