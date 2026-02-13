from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import QuestionViewSet, TestResultViewSet, ExamViewSet, analyze_frame, reset_session, log_violation, check_exam_access, request_retake, student_login

router = DefaultRouter()
router.register(r'questions', QuestionViewSet)
router.register(r'results', TestResultViewSet)
router.register(r'exams', ExamViewSet)

urlpatterns = [
    path("analyze/", analyze_frame, name="analyze_frame"),
    path("reset/", reset_session, name="reset_session"),
    path("log_violation/", log_violation, name="log_violation"),
    path("check_exam_access/", check_exam_access, name="check_exam_access"),
    path("request_retake/", request_retake, name="request_retake"),
    path("student_login/", student_login, name="student_login"),
]

urlpatterns += router.urls