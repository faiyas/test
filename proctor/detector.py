import cv2
import numpy as np
import torch
import time
from collections import deque, defaultdict
import threading
import os
from .mobile_phone_detector import MobilePhoneDetector


# ============ GLOBAL OBJECT MODEL CACHE ============
_OBJECT_MODEL = None
_OBJECT_MODEL_LOCK = threading.Lock()

def get_object_model(device='cpu'):
    global _OBJECT_MODEL
    if _OBJECT_MODEL is None:
        with _OBJECT_MODEL_LOCK:
            if _OBJECT_MODEL is None:
                print("="*60)
                print(f"⏳ LOADING OBJECT DETECTION MODEL on {device} (this happens once)...")
                print("="*60)
                
                import os
                current_dir = os.path.dirname(os.path.abspath(__file__))
                backend_dir = os.path.dirname(current_dir)
                possible_weights = [
                    os.path.join(current_dir, 'yolov5s.pt'),
                    os.path.join(backend_dir, 'yolov5s.pt'),
                    'yolov5s.pt'
                ]
                
                weights_path = None
                for p in possible_weights:
                    if os.path.exists(p):
                        weights_path = p
                        break
                        
                try:
                    if weights_path:
                        print(f"Found local weights for Object Detection at {weights_path}, loading...")
                        _OBJECT_MODEL = torch.hub.load('ultralytics/yolov5', 'custom', path=weights_path, verbose=False, _verbose=False)
                    else:
                        print("Local weights not found, downloading from hub...")
                        _OBJECT_MODEL = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True, verbose=False, _verbose=False)
                    
                    _OBJECT_MODEL.conf = 0.4
                    _OBJECT_MODEL.iou = 0.45
                    # COCO classes: 0=person, 67=cell phone, 73=laptop, 74=book, 77=cell phone, 84=book
                    _OBJECT_MODEL.classes = [0, 67, 73, 74, 77, 84, 62, 72, 66, 64]
                    _OBJECT_MODEL.to(device)
                    _OBJECT_MODEL.eval()
                    print("✅ OBJECT DETECTION MODEL LOADED SUCCESSFULLY!")
                except Exception as e:
                    print(f"Error loading YOLOv5: {e}")
                    import traceback
                    traceback.print_exc()
                    _OBJECT_MODEL = None
    return _OBJECT_MODEL

class ProctorDetector:
    def __init__(self, device='cpu'):
        self.device = device
        self.frame_count = 0
        self.stable_frames_required = 5

        # Load YOLOv5 for object detection
        self.object_model = get_object_model(device)

        
        # Face detection
        import os
        from django.conf import settings
        
        # Construct absolute paths to model files in the backend root directory
        model_file = os.path.join(settings.BASE_DIR, 'res10_300x300_ssd_iter_140000.caffemodel')
        config_file = os.path.join(settings.BASE_DIR, 'deploy.prototxt')
        
        if os.path.exists(model_file) and os.path.exists(config_file):
            print(f"Loading FaceNet (Caffe) from {model_file}...")
            self.face_net = cv2.dnn.readNetFromCaffe(config_file, model_file)
            self.use_dnn_face = True
        else:
            print(f"Warning: Caffe model files not found at {model_file} or {config_file}. Face detection will fail.")
            self.use_dnn_face = False
            self.face_net = None
        
        self.prev_gray = None
        self.movement_history = deque(maxlen=10)
        
        # Buffering for stable violations - keyed by candidate_id
        # { 'candidate_id': {'no_face': 0, 'multiple_faces': 0} }
        self.buffers = defaultdict(lambda: {'no_face': 0, 'multiple_faces': 0})
        
        self.frame_skip = 1
        self.resize_dim = (416, 416)
        
        self.prohibited_items = {
            73: {'name': '💻 Laptop', 'priority': 2, 'grace_period': 5},
            84: {'name': '📚 Book/Notes', 'priority': 2, 'grace_period': 5},
            74: {'name': '📚 Book', 'priority': 2, 'grace_period': 5},
            62: {'name': '📺 TV/Monitor', 'priority': 3, 'grace_period': 8},
            72: {'name': '📺 TV/Monitor', 'priority': 3, 'grace_period': 8},
            65: {'name': '⌨️ Keyboard', 'priority': 3, 'grace_period': 8},
            66: {'name': '⌨️ Keyboard', 'priority': 3, 'grace_period': 8},
            64: {'name': '🖱️ Remote', 'priority': 3, 'grace_period': 8},
            67: {'name': 'Mobile Phone', 'priority': 1, 'grace_period': 3}, # Re-adding for redundancy if needed, but primary check is specialized
        }
        
        self.object_tracker = defaultdict(lambda: {
            'first_seen': 0,
            'last_seen': 0,
            'confidence_scores': [],
            'violation_logged': False,
            'correction_start_time': None,
            'grace_remaining': 0
        })
        
        self.current_violations = []
        self.correction_timer = {}

        self.mobile_phone_detector = MobilePhoneDetector(device=device)
        
        self.lock = threading.Lock()
        
    def analyze_frame(self, frame, candidate_id='guest_user'):
        if not self.lock.acquire(blocking=False):
            # PROCTORING NEUTRAL: If busy, don't trigger violations
            return {
                "face_detected": True,
                "multiple_faces": False,
                "heavy_movement": False,
                "object_detected": False,
                "mobile_phone_detected": False,
                "processing_time": 0,
                "skipped": True
            }
            
        start_time = time.time()
        current_time = start_time
        # Initialize results
        result = {
            "face_count": 0,
            "face_detected": True, # Neutral until buffer says otherwise
            "multiple_faces": False,
            "heavy_movement": False,
            "movement_score": 0.0,
            "object_detected": False,
            "object_violation": False,
            "violation_type": None,
            "violation_severity": None,
            "violation_details": [],
            "mobile_phone_detected": False,
            "mobile_phone_count": 0,
            "mobile_phone_details": []
        }
        
        try:
            try:
                frame_resized = cv2.resize(frame, self.resize_dim)
            except Exception:
                return result
                
            h, w = frame_resized.shape[:2]
        
            faces = []
            if self.use_dnn_face and self.face_net:
                try:
                    blob = cv2.dnn.blobFromImage(frame_resized, 1.0, (300, 300), 
                                                [104, 117, 123], False, False)
                    self.face_net.setInput(blob)
                    detections = self.face_net.forward()
                    
                    for i in range(detections.shape[2]):
                        confidence = detections[0, 0, i, 2]
                        # Set to 0.65 for strict proctoring (less ghost detection)
                        if confidence > 0.65:
                            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                            x1, y1, x2, y2 = box.astype(int)
                            
                            scale_x = frame.shape[1] / self.resize_dim[0]
                            scale_y = frame.shape[0] / self.resize_dim[1]
                            
                            faces.append((
                                int(x1 * scale_x),
                                int(y1 * scale_y),
                                int((x2 - x1) * scale_x),
                                int((y2 - y1) * scale_y),
                                float(confidence)
                            ))
                except Exception as e:
                    print(f"Face Detection Error: {e}")

            result["face_count"] = len(faces)
            
            # --- Buffer Logic for Stable Results (Candidate Isolated) ---
            buffer = self.buffers[candidate_id]
            
            if len(faces) == 0:
                buffer['no_face'] += 1
                buffer['multiple_faces'] = 0
            elif len(faces) > 1:
                # Check for overlap to merge faces? (self._are_faces_overlapping)
                if self._are_faces_overlapping([f[:4] for f in faces]):
                    buffer['no_face'] = 0
                    buffer['multiple_faces'] = 0
                else:
                    buffer['multiple_faces'] += 1
                    buffer['no_face'] = 0
            else: # Exactly 1 face
                buffer['no_face'] = 0
                buffer['multiple_faces'] = 0

            # Determine final status based on buffers (Reduced threshold for better response)
            if buffer['no_face'] >= 2:
                if result["face_detected"]: # If it was True, log the change
                    print(f"⚠️ [CANDIDATE: {candidate_id}] FACE MISSING for {buffer['no_face']} frames!")
                result["face_detected"] = False
                result["multiple_faces"] = False
            elif buffer['multiple_faces'] >= 2:
                if not result["multiple_faces"]: # If it was False, log the change
                    print(f"⚠️ [CANDIDATE: {candidate_id}] MULTIPLE FACES ({len(faces)}) for {buffer['multiple_faces']} frames!")
                result["face_detected"] = True 
                result["multiple_faces"] = True
            else:
                # Default state (assume normal unless buffer triggers)
                result["face_detected"] = True
                result["multiple_faces"] = False

            # --- FRAME STATUS LOG ---
            status_line = f"[Frame {self.frame_count}] Faces: {len(faces)} | Buffer: (NF:{buffer['no_face']}, MF:{buffer['multiple_faces']})"
            
            gray = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (5, 5), 0)
            
            if self.prev_gray is not None and self.frame_count > self.stable_frames_required:
                diff = cv2.absdiff(self.prev_gray, gray)
                _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
                movement = (np.count_nonzero(thresh) / thresh.size) * 100
                result["movement_score"] = float(round(movement, 2))
                status_line += f" | Movement: {result['movement_score']}%"
                self.movement_history.append(movement)
                
                if len(self.movement_history) > 5:
                    avg_movement = np.mean(self.movement_history)
                    result["heavy_movement"] = bool(movement > max(35, avg_movement * 1.8))
                    if result["heavy_movement"]:
                        status_line += " [!] HEAVY MOVEMENT"
            
            print(status_line)
            
            self.prev_gray = gray.copy()

            if self.mobile_phone_detector:
                mobile_phones = self.mobile_phone_detector.detect_phones(frame, candidate_id=candidate_id)
                if mobile_phones:
                    result["mobile_phone_detected"] = True
                    result["mobile_phone_count"] = len(mobile_phones)
                    result["mobile_phone_details"] = mobile_phones
                    
                    # New: Get grace period warnings/status
                    warnings = self.mobile_phone_detector.get_active_warnings(mobile_phones)
                    if warnings:
                        result["phone_warnings"] = warnings
                        result["grace_remaining"] = warnings[0]['grace_remaining']
                    
                    phone_violation = self.mobile_phone_detector.check_violation(mobile_phones)
                    if phone_violation:
                        result["object_violation"] = True
                        result["violation_type"] = "Mobile Phone"
                        result["violation_severity"] = "HIGH"
                        result["violation_details"].append({
                            "type": "📱 Mobile Phone",
                            "severity": "HIGH",
                            "time_visible": phone_violation['time_visible'],
                            "grace_remaining": 0,
                            "bbox": phone_violation.get('bbox'),
                            "confidence": phone_violation['confidence']
                        })
            
            if self.object_model and self.frame_count > self.stable_frames_required:
                try:
                    results = self.object_model(frame)
                    
                    objects_detected = []
                    current_object_ids = set()
                    
                    for *box, conf, cls in results.xyxy[0].cpu().numpy():
                        cls_id = int(cls)
                        
                        if cls_id in self.prohibited_items:
                            x1, y1, x2, y2 = map(int, box)
                            item_info = self.prohibited_items[cls_id]
                            
                            near_face = self._is_near_face((x1, y1, x2-x1, y2-y1), faces)
                            
                            obj_id = f"{cls_id}_{x1}_{y1}_{x2}_{y2}"
                            current_object_ids.add(obj_id)
                            
                            if obj_id not in self.object_tracker:
                                self.object_tracker[obj_id]['first_seen'] = current_time
                                self.object_tracker[obj_id]['grace_remaining'] = item_info['grace_period']
                            
                            self.object_tracker[obj_id]['last_seen'] = current_time
                            self.object_tracker[obj_id]['confidence_scores'].append(float(conf))
                            
                            time_visible = current_time - self.object_tracker[obj_id]['first_seen']
                            
                            violation_triggered = False
                            grace_remaining = None
                            
                            if not self.object_tracker[obj_id]['violation_logged']:
                                if item_info['priority'] == 1:  # Mobile phones - immediate (handled by separate detector now)
                                    pass 
                                elif item_info['priority'] == 2:  # Books/Laptops
                                    if time_visible > 1.0:  # Visible for 1 second
                                        violation_triggered = True
                                        grace_remaining = 2  # 2 seconds to correct
                                else:  # Other items
                                    if time_visible > 1.5:  # Visible for 1.5 seconds
                                        violation_triggered = True
                                        grace_remaining = 3  # 3 seconds to correct
                            
                            if self.object_tracker[obj_id]['correction_start_time']:
                                elapsed = current_time - self.object_tracker[obj_id]['correction_start_time']
                                grace_remaining = max(0, item_info['grace_period'] - elapsed)
                            
                            object_detail = {
                                "id": obj_id,
                                "type": item_info['name'],
                                "class_id": int(cls_id),
                                "confidence": round(float(conf), 2),
                                "bbox": (int(x1), int(y1), int(x2-x1), int(y2-y1)),
                                "near_face": bool(near_face),
                                "time_visible": round(float(time_visible), 1),
                                "violation": bool(violation_triggered),
                                "grace_remaining": round(float(grace_remaining), 1) if grace_remaining is not None else None,
                                "priority": int(item_info['priority'])
                            }
                            
                            objects_detected.append(object_detail)
                            
                            if violation_triggered:
                                result["object_violation"] = True
                                result["violation_type"] = item_info['name']
                                result["violation_severity"] = "HIGH" if item_info['priority'] == 1 else "MEDIUM"
                                result["correction_time_remaining"] = round(float(grace_remaining), 2) if grace_remaining is not None else 0
                                
                                result["violation_details"].append({
                                    "type": item_info['name'],
                                    "severity": "HIGH" if item_info['priority'] == 1 else "MEDIUM",
                                    "time_visible": round(float(time_visible), 1),
                                    "grace_remaining": round(float(grace_remaining), 1) if grace_remaining is not None else None,
                                    "bbox": (int(x1), int(y1), int(x2-x1), int(y2-y1)),
                                    "confidence": round(float(conf), 2),
                                    "near_face": bool(near_face)
                                })
                                
                                self.object_tracker[obj_id]['violation_logged'] = True
                                
                                if not self.object_tracker[obj_id]['correction_start_time']:
                                    self.object_tracker[obj_id]['correction_start_time'] = current_time
                    
                    objects_to_remove = []
                    for obj_id, track_info in self.object_tracker.items():
                        if current_time - track_info['last_seen'] > 2.0:
                            objects_to_remove.append(obj_id)
                    
                    for obj_id in objects_to_remove:
                        del self.object_tracker[obj_id]
                    
                    # Update result
                    if objects_detected:
                        result["object_detected"] = True
                        result["object_details"] = objects_detected
                        
                except Exception as e:
                    print(f"YOLO Object Detection Error: {e}")
                    import traceback
                    traceback.print_exc()
            
            self.frame_count += 1
            result["processing_time"] = round((time.time() - start_time) * 1000, 2)
            
            return result
        finally:
            self.lock.release()
    
    def _is_near_face(self, obj_bbox, faces):
        """Check if object is near face (within 1.5x face width)"""
        ox, oy, ow, oh = obj_bbox
        obj_center = (ox + ow//2, oy + oh//2)
        
        for (fx, fy, fw, fh, _) in faces:
            face_center = (fx + fw//2, fy + fh//2)
            distance = np.sqrt((obj_center[0] - face_center[0])**2 + 
                              (obj_center[1] - face_center[1])**2)
            
            if distance < fw * 1.5:
                return True
        return False
    
    def _are_faces_overlapping(self, faces):
        """Check if faces overlap significantly"""
        if len(faces) <= 1:
            return False
        
        for i in range(len(faces)):
            for j in range(i + 1, len(faces)):
                x1, y1, w1, h1 = faces[i]
                x2, y2, w2, h2 = faces[j]
                
                x_left = max(x1, x2)
                y_top = max(y1, y2)
                x_right = min(x1 + w1, x2 + w2)
                y_bottom = min(y1 + h1, y2 + h2)
                
                if x_right < x_left or y_bottom < y_top:
                    continue
                
                intersection = (x_right - x_left) * (y_bottom - y_top)
                area1 = w1 * h1
                area2 = w2 * h2
                smaller = min(area1, area2)
                
                if intersection > 0.3 * smaller:  # 30% overlap
                    return True
        
        return False
    
    def reset(self):
        self.prev_gray = None
        self.frame_count = 0
        self.movement_history.clear()
        self.object_tracker.clear()
        self.current_violations.clear()
        self.correction_timer.clear()
        if self.mobile_phone_detector:
            self.mobile_phone_detector.reset()