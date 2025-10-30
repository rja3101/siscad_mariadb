from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from .models import Course, CourseGroup, Enrollment, Assessment, Grade

from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    Term, EnrollmentWindow, TermRule,
    StudentProfile, Enrollment, EnrollmentAttempt,
    Waitlist, PaymentOrder,
    EnrollmentCart, CartItem, CapReservation,
    CoursePrerequisite, CourseCorequisite, GroupPairing
)


@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'start_date', 'end_date', 'is_active']
    list_filter = ['is_active', 'start_date']
    search_fields = ['code', 'name']
    ordering = ['-start_date']


class EnrollmentWindowInline(admin.TabularInline):
    model = EnrollmentWindow
    extra = 1
    fields = ['name', 'start_datetime', 'end_datetime', 'is_active']


class TermRuleInline(admin.StackedInline):
    model = TermRule
    can_delete = False


@admin.register(EnrollmentWindow)
class EnrollmentWindowAdmin(admin.ModelAdmin):
    list_display = ['term', 'name', 'start_datetime', 'end_datetime', 'is_active', 'window_status']
    list_filter = ['is_active', 'term']
    search_fields = ['name', 'term__code']
    
    def window_status(self, obj):
        if obj.is_open():
            return format_html('<span style="color: green;">●  Abierta</span>')
        return format_html('<span style="color: red;">●  Cerrada</span>')
    window_status.short_description = 'Estado'


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ['student_code', 'user', 'cohort', 'gpa', 'approved_credits', 'holds_status']
    list_filter = ['cohort', 'has_financial_hold', 'has_document_hold', 'has_academic_hold']
    search_fields = ['student_code', 'user__username', 'user__first_name', 'user__last_name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Información del Usuario', {
            'fields': ('user', 'student_code', 'cohort', 'curriculum')
        }),
        ('Datos Académicos', {
            'fields': ('gpa', 'approved_credits')
        }),
        ('Bloqueos', {
            'fields': ('has_financial_hold', 'has_document_hold', 'has_academic_hold')
        }),
        ('Auditoría', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def holds_status(self, obj):
        if obj.has_any_hold():
            return format_html(
                '<span style="color: red;">⚠ Bloqueado</span>'
            )
        return format_html('<span style="color: green;">✓ Sin bloqueos</span>')
    holds_status.short_description = 'Estado'


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ['student', 'course_group', 'term', 'status', 'enrolled_at']
    list_filter = ['status', 'term', 'enrolled_at']
    search_fields = ['student__username', 'course_group__course__code', 'course_group__course__name']
    readonly_fields = ['enrolled_at', 'dropped_at']
    date_hierarchy = 'enrolled_at'
    
    actions = ['drop_selected_enrollments']
    
    def drop_selected_enrollments(self, request, queryset):
        from .services.enrollment_service import EnrollmentService
        
        count = 0
        for enrollment in queryset.filter(status='ENROLLED'):
            EnrollmentService.drop_enrollment(enrollment, dropped_by=request.user)
            count += 1
        
        self.message_user(request, f'{count} matrículas dadas de baja')
    drop_selected_enrollments.short_description = 'Dar de baja matrículas seleccionadas'


@admin.register(Waitlist)
class WaitlistAdmin(admin.ModelAdmin):
    list_display = ['position', 'student', 'course_group', 'term', 'status', 'added_at']
    list_filter = ['status', 'term', 'added_at']
    search_fields = ['student__username', 'course_group__course__code']
    ordering = ['course_group', 'position', 'added_at']
    
    actions = ['promote_to_enrollment']
    
    def promote_to_enrollment(self, request, queryset):
        count = 0
        for waitlist_entry in queryset.filter(status='WAITING'):
            # Verificar cupo
            if waitlist_entry.course_group.get_available_slots() > 0:
                Enrollment.objects.create(
                    student=waitlist_entry.student,
                    course_group=waitlist_entry.course_group,
                    term=waitlist_entry.term,
                    status='ENROLLED',
                    enrolled_by=request.user
                )
                waitlist_entry.status = 'PROMOTED'
                waitlist_entry.save()
                count += 1
        
        self.message_user(request, f'{count} estudiantes promovidos a matrícula')
    promote_to_enrollment.short_description = 'Promover a matrícula (si hay cupo)'


@admin.register(EnrollmentCart)
class EnrollmentCartAdmin(admin.ModelAdmin):
    list_display = ['student', 'term', 'is_confirmed', 'confirmed_at', 'items_count']
    list_filter = ['is_confirmed', 'term']
    search_fields = ['student__username']
    readonly_fields = ['created_at', 'updated_at', 'confirmed_at']
    
    def items_count(self, obj):
        return obj.items.count()
    items_count.short_description = 'Ítems'


@admin.register(CapReservation)
class CapReservationAdmin(admin.ModelAdmin):
    list_display = ['student', 'course_group', 'reserved_at', 'reserved_until', 'is_released', 'status_display']
    list_filter = ['is_released', 'term', 'reserved_at']
    search_fields = ['student__username', 'course_group__course__code']
    readonly_fields = ['reserved_at', 'released_at']
    date_hierarchy = 'reserved_at'
    
    def status_display(self, obj):
        if obj.is_valid():
            return format_html('<span style="color: green;">✓ Activa</span>')
        return format_html('<span style="color: gray;">○ Expirada/Liberada</span>')
    status_display.short_description = 'Estado'


@admin.register(CoursePrerequisite)
class CoursePrerequisiteAdmin(admin.ModelAdmin):
    list_display = ['course', 'prerequisite_course', 'is_strict', 'min_grade']
    list_filter = ['is_strict']
    search_fields = ['course__code', 'course__name', 'prerequisite_course__code']


@admin.register(CourseCorequisite)
class CourseCorequisiteAdmin(admin.ModelAdmin):
    list_display = ['course', 'corequisite_course']
    search_fields = ['course__code', 'course__name', 'corequisite_course__code']


@admin.register(GroupPairing)
class GroupPairingAdmin(admin.ModelAdmin):
    list_display = ['theory_group', 'lab_group', 'term', 'is_mandatory']
    list_filter = ['is_mandatory', 'term']
    search_fields = ['theory_group__course__code', 'lab_group__course__code']


@admin.register(EnrollmentAttempt)
class EnrollmentAttemptAdmin(admin.ModelAdmin):
    list_display = ['student', 'action', 'success', 'attempted_at', 'term']
    list_filter = ['action', 'success', 'term', 'attempted_at']
    search_fields = ['student__username']
    readonly_fields = ['attempted_at', 'ip_address']
    date_hierarchy = 'attempted_at'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(PaymentOrder)
class PaymentOrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'student', 'term', 'amount', 'status', 'created_at']
    list_filter = ['status', 'term', 'created_at']
    search_fields = ['student__username']
    readonly_fields = ['created_at', 'paid_at']

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "credits", "teacher")
    search_fields = ("code", "name", "teacher__username")
    list_filter = ("credits",)

@admin.register(CourseGroup)
class CourseGroupAdmin(admin.ModelAdmin):
    list_display = ("course", "section", "is_lab", "capacity", "enrolled_count")
    list_filter = ("is_lab", "course")
    search_fields = ("course__code", "course__name", "section")

class EnrollmentResource(resources.ModelResource):
    class Meta:
        model = Enrollment
        fields = ("student__username", "course_group__course__code", "course_group__section", "created_at",)
        export_order = fields

@admin.register(Enrollment)
class EnrollmentAdmin(ImportExportModelAdmin):
    resource_class = EnrollmentResource
    list_display = ("student", "course_group", "created_at")
    search_fields = ("student__username", "course_group__course__code", "course_group__section")
    list_filter = ("course_group__course__code", "created_at")

@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ("course_group", "title", "kind", "weight", "total_points")
    list_filter = ("kind", "course_group__course__code")
    search_fields = ("title", "course_group__course__name")

class GradeResource(resources.ModelResource):
    class Meta:
        model = Grade
        fields = ("student__username", "assessment__course_group__course__code",
                  "assessment__title", "score")
        export_order = fields

@admin.register(Grade)
class GradeAdmin(ImportExportModelAdmin):
    resource_class = GradeResource
    list_display = ("student", "assessment", "score")
    search_fields = ("student__username", "assessment__title")
    list_filter = ("assessment__course_group__course__code", "assessment__kind")
