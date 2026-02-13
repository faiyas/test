import openpyxl
import os
import warnings
import traceback

# Suppress YOLOv5 deprecation warnings
warnings.filterwarnings("ignore", category=FutureWarning)
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Question, TestResult, Exam, ExamSession, Violation, Screenshot, Student
from .serializers import QuestionSerializer, TestResultSerializer, ExamSerializer
from django.shortcuts import get_object_or_404

class ExamViewSet(viewsets.ModelViewSet):
    queryset = Exam.objects.all()
    serializer_class = ExamSerializer

    def dispatch(self, request, *args, **kwargs):
        print(f"🔍 [ExamViewSet] Incoming request: {request.method} {request.path}")
        return super().dispatch(request, *args, **kwargs)

class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer

    def get_queryset(self):
        # Optional: Filter by specific exam if 'exam_id' passed in query params
        exam_id = self.request.query_params.get('exam_id')
        if exam_id:
             return Question.objects.filter(exam_id=exam_id)
        # Default: return questions for the first active exam found (for student view compatibility)
        active_exam = Exam.objects.filter(is_active=True).first()
        if active_exam:
            return Question.objects.filter(exam=active_exam)
        return Question.objects.all()

    @action(detail=False, methods=['post'])
    def upload_excel(self, request):
        file_obj = request.FILES.get('file')
        exam_id = request.data.get('exam_id')
        
        if not file_obj:
            return Response({'error': 'No file uploaded'}, status=status.HTTP_400_BAD_REQUEST)

        # Get the exam to associate questions with
        exam = None
        if exam_id:
            try:
                exam = Exam.objects.get(id=exam_id)
            except Exam.DoesNotExist:
                return Response({'error': 'Exam not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # If no exam specified, create a default one or use existing active one
        if not exam:
            exam, _ = Exam.objects.get_or_create(name="Default Exam", defaults={'duration_minutes': 30, 'is_active': True})

        try:
            wb = openpyxl.load_workbook(file_obj)
            sheet = wb.active
            questions_created = 0
            
            # Headers: Text, Option A, Option B, Option C, Option D, Correct Answer
            for row in sheet.iter_rows(min_row=2, values_only=True):
                if not row or not row[0]: continue
                
                Question.objects.create(
                    exam=exam,
                    text=row[0],
                    option_a=row[1],
                    option_b=row[2],
                    option_c=row[3],
                    option_d=row[4],
                    correct_answer=row[5]
                )
                questions_created += 1
                
            return Response({'message': f'{questions_created} questions uploaded to {exam.name}'}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ... (imports and get_detector code remain same) ...
import cv2
import numpy as np
import base64
from django.http import JsonResponse
from rest_framework.decorators import api_view
from .detector import ProctorDetector

import threading

# Global detector instance
detector = None
detector_lock = threading.Lock()

def get_detector():
    global detector
    if detector is None:
        with detector_lock:
            if detector is None:
                detector = ProctorDetector()
    return detector

@api_view(['POST'])
def analyze_frame(request):
    try:
        image_data = request.data.get('image')
        candidate_id = request.data.get('candidate_id', 'unknown_candidate')
        mode = request.data.get('mode', 'test')  # 'test' or 'verification'
        
        if not image_data:
            print("Analyze Frame: Error - No image provided")
            return Response({'error': 'No image provided'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            if ';base64,' not in image_data:
                print(f"Analyze Frame: Error - Invalid image format (missing ;base64,). Data prefix: {image_data[:50]}")
                return Response({'error': 'Invalid image format'}, status=status.HTTP_400_BAD_REQUEST)
                
            format, imgstr = image_data.split(';base64,') 
            nparr = np.frombuffer(base64.b64decode(imgstr), np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        except Exception as e:
             print(f"Analyze Frame: Error decoding image: {e}")
             return Response({'error': f'Invalid image format: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

        if frame is None:
            print("Analyze Frame: Error - Failed to decode image (frame is None)")
            return Response({'error': 'Failed to decode image'}, status=status.HTTP_400_BAD_REQUEST)

        # Get or create active session
        session, created = ExamSession.objects.get_or_create(
            candidate_id=candidate_id,
            terminated=False,
            defaults={'violations': 0}
        )

        if session.terminated and mode != 'verification':
             return Response({'error': 'Session terminated'}, status=status.HTTP_403_FORBIDDEN)

        detector_instance = get_detector()
        result = detector_instance.analyze_frame(frame, candidate_id=candidate_id)
        
        # If the frame was skipped (lock busy), don't process violations
        if result.get('skipped'):
            print(f"⏩ Skipping violation analysis for {candidate_id} (Busy)")
            result['session_violations'] = session.violations
            return Response(result)

        # If in verification mode, just return the result without saving violations
        if mode == 'verification':
            result['session_violations'] = session.violations
            return Response(result)

        # Persist Violations - Robust atomic counting
        from django.db.models import F
        new_violations = 0

        # 1. Mobile Phone (High Priority)
        if result.get('mobile_phone_detected'):
            # Check for actual violation (after grace period triggers object_violation)
            phone_violation = result.get('object_violation') and result.get('violation_type') == 'Mobile Phone'
            if phone_violation:
                details = "Mobile Phone Detected"
                if result.get('mobile_phone_details'):
                    part = result['mobile_phone_details'][0].get('phone_part', 'Mobile Phone')
                    details = f"Mobile Phone Detected: {part}"
                
                Violation.objects.create(session=session, reason=details)
                Screenshot.objects.create(session=session, image=image_data, reason="Mobile Phone")
                new_violations += 1
                print(f"🚨 PHONE VIOLATION: {details} for {candidate_id}")
            
        # 2. Multiple faces detected
        if result.get('multiple_faces'):
            Violation.objects.create(session=session, reason="Multiple faces detected")
            Screenshot.objects.create(session=session, image=image_data, reason="Multiple Faces")
            new_violations += 1
            print(f"🚨 VIOLATION: Multiple faces for {candidate_id}")

        # 3. Face is not visible (Strict independent check)
        if not result.get('face_detected'):
            Violation.objects.create(session=session, reason="Face is not visible")
            Screenshot.objects.create(session=session, image=image_data, reason="No Face Detected")
            new_violations += 1
            print(f"🚨 VIOLATION: Face not visible for {candidate_id}")
            
        # 4. Other Prohibited Objects
        if result.get('object_violation') and result.get('violation_type') != 'Mobile Phone':
            v_type = result.get('violation_type', 'Prohibited Object')
            Violation.objects.create(session=session, reason=f"Prohibited Object: {v_type}")
            Screenshot.objects.create(session=session, image=image_data, reason=f"Object: {v_type}")
            new_violations += 1
            print(f"🚨 VIOLATION: Object ({v_type}) for {candidate_id}")

        if new_violations > 0:
            # Use atomic update on the queryset for maximum reliability
            ExamSession.objects.filter(id=session.id).update(violations=F('violations') + new_violations)
            print(f"✅ Successfully incremented violations by {new_violations} for {candidate_id}")
            
        # ALWAYS refresh to get any concurrent updates (e.g. tab switching)
        session.refresh_from_db()
            
        # ============ ENHANCED VIOLATION DASHBOARD ============
        print("\n" + "="*65)
        print(f"🎓 PROCTORING DASHBOARD | {candidate_id}")
        print(f"🚫 TOTAL VIOLATIONS: {session.violations}/3")
        
        status_text = "✅ STABLE"
        if new_violations > 0:
            status_text = "🚨 VIOLATION RECORDED"
        elif result.get('phone_warnings'):
            status_text = "⚠️ WARNING (GRACE PERIOD)"
        elif not result.get('face_detected'):
            status_text = "⚠️ STABILIZING (NO FACE)"
            
        print(f"📊 STATUS: {status_text}")
        print("="*65 + "\n")
            
        result['session_violations'] = session.violations
        return Response(result)
        
    except Exception as e:
        print(f"❌ CRITICAL ERROR analyzing frame for {candidate_id}: {e}")
        import traceback
        traceback.print_exc()
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def reset_session(request):
    candidate_id = request.data.get('candidate_id')
    if candidate_id:
        # Important: Mark all existing active sessions as terminated
        ExamSession.objects.filter(candidate_id=candidate_id, terminated=False).update(terminated=True)
        print(f"🔄 SESSIONS RESET for {candidate_id}")
        return Response({'message': f'Active sessions for {candidate_id} terminated.'})
    return Response({'error': 'Candidate ID required'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def log_violation(request):
    candidate_id = request.data.get('candidate_id')
    reason = request.data.get('reason', 'Browser Violation')
    
    if not candidate_id:
        return Response({'error': 'Candidate ID required'}, status=status.HTTP_400_BAD_REQUEST)
        
    session = ExamSession.objects.filter(candidate_id=candidate_id, terminated=False).order_by('-started_at').first()
    if not session:
        return Response({'error': 'No active session found'}, status=status.HTTP_404_NOT_FOUND)
        
    Violation.objects.create(session=session, reason=reason)
    # Optional: Save a screenshot placeholder or null if needed
    from django.db.models import F
    session.violations = F('violations') + 1
    session.save()
    session.refresh_from_db()
    
    print(f"🚨 MANUAL VIOLATION LOGGED: {reason}. Total for {candidate_id}: {session.violations}")
    return Response({'session_violations': session.violations})

class TestResultViewSet(viewsets.ModelViewSet):
    queryset = TestResult.objects.all().order_by('-date_taken')
    serializer_class = TestResultSerializer

    def create(self, request, *args, **kwargs):
        # Custom create to link ExamSession
        candidate_id = request.data.get('student_name') # Using email as ID for now
        
        try:
            # Try to find the active session for this candidate
            session = ExamSession.objects.filter(candidate_id=candidate_id, terminated=False).order_by('-started_at').first()
            
            # Create Result
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            test_result = serializer.save(session=session)
            
            # Mark session as terminated and completed
            if session:
                session.terminated = True
                session.completed = True
                session.save()
                
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
            
        except Exception as e:
            print(f"❌ ERROR in TestResult creation for {candidate_id}: {e}")
            import traceback
            traceback.print_exc()
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def check_exam_access(request):
    """Check if student can take the exam"""
    candidate_id = request.query_params.get('candidate_id')
    
    if not candidate_id:
        return Response({'error': 'Candidate ID required'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if student has completed exam
    completed_session = ExamSession.objects.filter(
        candidate_id=candidate_id,
        completed=True
    ).order_by('-started_at').first()
    
    if completed_session and not completed_session.can_retake:
        return Response({
            'can_take_exam': False,
            'reason': 'already_completed',
            'retake_requested': completed_session.retake_requested,
            'session_id': completed_session.id
        })
    
    return Response({'can_take_exam': True})


@api_view(['POST'])
def request_retake(request):
    """Student requests permission to retake exam"""
    candidate_id = request.data.get('candidate_id')
    reason = request.data.get('reason', '')
    
    if not candidate_id:
        return Response({'error': 'Candidate ID required'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Find the most recent completed session
    session = ExamSession.objects.filter(
        candidate_id=candidate_id,
        completed=True
    ).order_by('-started_at').first()
    
    if not session:
        return Response({'error': 'No completed session found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Update retake request
    session.retake_requested = True
    session.retake_reason = reason
    session.save()
    
    print(f"📝 RETAKE REQUEST from {candidate_id}: {reason}")
    
    return Response({
        'message': 'Retake request submitted successfully',
        'session_id': session.id
    })


@api_view(['POST'])
def student_login(request):
    """Authenticate student or admin with email and password"""
    from django.contrib.auth.hashers import check_password
    from django.contrib.auth import get_user_model
    
    email = request.data.get('email')
    password = request.data.get('password')
    
    if not email or not password:
        return Response({'error': 'Email and password required'}, status=status.HTTP_400_BAD_REQUEST)
    
    # First, check if it's a Django admin/superuser
    User = get_user_model()
    try:
        admin_user = User.objects.get(email=email)
        if admin_user.check_password(password) and (admin_user.is_staff or admin_user.is_superuser):
            return Response({
                'success': True,
                'is_admin': True,
                'user': {
                    'id': str(admin_user.id),
                    'email': admin_user.email,
                    'name': admin_user.get_full_name() or admin_user.username
                }
            })
    except User.DoesNotExist:
        pass
    
    # If not admin, check if it's a student
    try:
        student = Student.objects.get(email=email, is_active=True)
        
        if check_password(password, student.password):
            return Response({
                'success': True,
                'is_admin': False,
                'user': {
                    'id': student.student_id,
                    'email': student.email,
                    'name': student.name
                }
            })
        else:
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
            
    except Student.DoesNotExist:
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
