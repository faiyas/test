from django.contrib import admin
from django.utils.html import format_html
from .models import ExamSession, Screenshot, Violation, Student, Exam, Question, TestResult

@admin.register(Screenshot)
class ScreenshotAdmin(admin.ModelAdmin):
    list_display = ['id', 'session_candidate', 'reason', 'captured_at', 'image_preview']
    list_filter = ['reason', 'captured_at']
    search_fields = ['session__candidate_id', 'reason']
    readonly_fields = ['image_display']
    
    def session_candidate(self, obj):
        return obj.session.candidate_id
    session_candidate.short_description = 'Candidate ID'
    
    def image_preview(self, obj):
        return format_html(
            '<img src="{}" style="max-width: 100px; max-height: 75px;" />',
            obj.image
        )
    image_preview.short_description = 'Preview'
    
    def image_display(self, obj):
        return format_html(
            '<img src="{}" style="max-width: 600px; max-height: 450px;" />',
            obj.image
        )
    image_display.short_description = 'Full Image'


@admin.register(ExamSession)
class ExamSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'candidate_id', 'started_at', 'violations', 'completed', 'can_retake', 'retake_requested']
    list_filter = ['completed', 'can_retake', 'retake_requested', 'terminated', 'started_at']
    search_fields = ['candidate_id']
    readonly_fields = ['started_at', 'violations']
    actions = ['approve_retake', 'deny_retake', 'reset_for_retake']
    
    fieldsets = (
        ('Session Info', {
            'fields': ('candidate_id', 'started_at', 'violations', 'terminated', 'completed')
        }),
        ('Retake Management', {
            'fields': ('can_retake', 'retake_requested', 'retake_reason')
        }),
    )
    
    def approve_retake(self, request, queryset):
        count = queryset.update(can_retake=True, retake_requested=False)
        self.message_user(request, f'{count} retake request(s) approved.')
    approve_retake.short_description = "✅ Approve retake requests"
    
    def deny_retake(self, request, queryset):
        count = queryset.update(retake_requested=False, can_retake=False)
        self.message_user(request, f'{count} retake request(s) denied.')
    deny_retake.short_description = "❌ Deny retake requests"
    
    def reset_for_retake(self, request, queryset):
        count = queryset.update(can_retake=True, retake_requested=False, completed=False, terminated=False)
        self.message_user(request, f'{count} session(s) reset for retake.')
    reset_for_retake.short_description = "🔄 Reset session for retake"


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ['student_id', 'email', 'name', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['student_id', 'email', 'name']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Student Login Credentials', {
            'fields': ('student_id', 'email', 'password'),
            'description': 'Create login credentials for the student. Student will use EMAIL and PASSWORD to log in.'
        }),
        ('Personal Information', {
            'fields': ('name',)
        }),
        ('Account Status', {
            'fields': ('is_active', 'created_by_admin', 'created_at')
        }),
    )
    
    def save_model(self, request, obj, form, change):
        # Hash password if it's being set/changed and not already hashed
        if 'password' in form.changed_data:
            from django.contrib.auth.hashers import make_password
            if not obj.password.startswith('pbkdf2_'):  # Check if already hashed
                obj.password = make_password(obj.password)
        super().save_model(request, obj, form, change)


@admin.register(Violation)
class ViolationAdmin(admin.ModelAdmin):
    list_display = ['id', 'session_candidate', 'reason', 'timestamp']
    list_filter = ['reason', 'timestamp']
    search_fields = ['session__candidate_id', 'reason']
    readonly_fields = ['timestamp']
    
    def session_candidate(self, obj):
        return obj.session.candidate_id
    session_candidate.short_description = 'Candidate ID'


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'duration_minutes', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name']


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['id', 'exam', 'text_preview', 'correct_answer']
    list_filter = ['exam', 'correct_answer']
    search_fields = ['text']
    
    def text_preview(self, obj):
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    text_preview.short_description = 'Question'


@admin.register(TestResult)
class TestResultAdmin(admin.ModelAdmin):
    list_display = ['id', 'student_name', 'exam', 'score', 'total_questions', 'percentage', 'date_taken']
    list_filter = ['exam', 'date_taken']
    search_fields = ['student_name']
    readonly_fields = ['date_taken']
    
    def percentage(self, obj):
        if obj.total_questions > 0:
            return f"{(obj.score / obj.total_questions * 100):.1f}%"
        return "0%"
    percentage.short_description = 'Score %'
