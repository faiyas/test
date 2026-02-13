from django.db import models

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
