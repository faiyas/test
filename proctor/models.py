from django.db import models

class ExamSession(models.Model):
    candidate_id = models.CharField(max_length=100, db_index=True)
    violations = models.IntegerField(default=0)
    terminated = models.BooleanField(default=False, db_index=True)
    started_at = models.DateTimeField(auto_now_add=True, db_index=True)
    completed = models.BooleanField(default=False, db_index=True)
    can_retake = models.BooleanField(default=False)
    retake_requested = models.BooleanField(default=False, db_index=True)
    retake_reason = models.TextField(blank=True, null=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['candidate_id', 'terminated']),
            models.Index(fields=['candidate_id', 'completed']),
        ]
    
    def __str__(self):
        return f"Session {self.candidate_id}"

class Violation(models.Model):
    session = models.ForeignKey(ExamSession, on_delete=models.CASCADE, db_index=True)
    reason = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['session', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.reason} at {self.timestamp}"

class Screenshot(models.Model):
    session = models.ForeignKey(ExamSession, on_delete=models.CASCADE, db_index=True)
    image = models.TextField()
    reason = models.CharField(max_length=255)
    captured_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['session', '-captured_at']),
        ]
    
    def __str__(self):
        return f"Screenshot: {self.reason}"

class Exam(models.Model):
    name = models.CharField(max_length=200)
    duration_minutes = models.IntegerField(default=30)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Question(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='questions', null=True, blank=True)
    text = models.TextField()
    option_a = models.CharField(max_length=255)
    option_b = models.CharField(max_length=255)
    option_c = models.CharField(max_length=255)
    option_d = models.CharField(max_length=255)
    correct_answer = models.CharField(max_length=1, choices=[('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')])
    
    def __str__(self):
        return self.text[:50]

class TestResult(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, null=True, blank=True)
    session = models.OneToOneField(ExamSession, on_delete=models.SET_NULL, null=True, blank=True)
    student_name = models.CharField(max_length=100)
    score = models.IntegerField()
    total_questions = models.IntegerField()
    date_taken = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.student_name} - {self.score}/{self.total_questions}"

class Student(models.Model):
    student_id = models.CharField(max_length=50, unique=True, db_index=True)
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=200)
    password = models.CharField(max_length=128)  # Store hashed password
    created_by_admin = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['student_id']),
            models.Index(fields=['email']),
        ]
    
    def __str__(self):
        return f"{self.student_id} - {self.name}"
