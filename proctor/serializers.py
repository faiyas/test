from rest_framework import serializers
from .models import Question, TestResult, Exam, ExamSession, Violation, Screenshot

class ExamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exam
        fields = '__all__'

class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = '__all__'

class ScreenshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = Screenshot
        fields = ['id', 'image', 'reason', 'captured_at']

class ViolationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Violation
        fields = ['id', 'reason', 'timestamp']

class ExamSessionSerializer(serializers.ModelSerializer):
    violations_list = ViolationSerializer(many=True, read_only=True, source='violation_set')
    screenshots = ScreenshotSerializer(many=True, read_only=True, source='screenshot_set')

    class Meta:
        model = ExamSession
        fields = ['id', 'candidate_id', 'violations', 'terminated', 'started_at', 'violations_list', 'screenshots']

class TestResultSerializer(serializers.ModelSerializer):
    session = ExamSessionSerializer(read_only=True)
    exam_name = serializers.CharField(source='exam.name', read_only=True)
    
    class Meta:
        model = TestResult
        fields = '__all__'
