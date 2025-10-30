from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import json


class Enrollment(models.Model):
    """Matrícula confirmada"""
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enrollments')
    course_group = models.ForeignKey('CourseGroup', on_delete=models.CASCADE, related_name='enrollments')
    term = models.ForeignKey('Term', on_delete=models.CASCADE, related_name='enrollments')
    
    STATUS_CHOICES = [
        ('ENROLLED', 'Matriculado'),
        ('DROPPED', 'Retirado'),
        ('AUDITING', 'Oyente'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ENROLLED')
    
    enrolled_at = models.DateTimeField(auto_now_add=True)
    dropped_at = models.DateTimeField(null=True, blank=True)
    
    # Auditoría
    enrolled_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='enrollments_created'
    )
    
    class Meta:
        db_table = 'enrollments'
        unique_together = [['student', 'course_group', 'term']]
        indexes = [
            models.Index(fields=['student', 'term']),
            models.Index(fields=['course_group', 'status']),
        ]
    
    def __str__(self):
        return f"{self.student.username} - {self.course_group}"
    
    def is_active(self):
        """Verifica si la matrícula está activa"""
        return self.status == 'ENROLLED'
    
    def drop(self, dropped_by=None):
        """Da de baja la matrícula"""
        self.status = 'DROPPED'
        self.dropped_at = timezone.now()
        self.save()
        
        # Log de auditoría
        EnrollmentAttempt.objects.create(
            student=self.student,
            term=self.term,
            action='DROP',
            success=True,
            details=json.dumps({
                'course_group_id': self.course_group.id,
                'dropped_by': dropped_by.username if dropped_by else 'system'
            })
        )


class Waitlist(models.Model):
    """Lista de espera para una sección"""
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='waitlists')
    course_group = models.ForeignKey('CourseGroup', on_delete=models.CASCADE, related_name='waitlist')
    term = models.ForeignKey('Term', on_delete=models.CASCADE, related_name='waitlists')
    
    position = models.IntegerField()
    added_at = models.DateTimeField(auto_now_add=True)
    
    STATUS_CHOICES = [
        ('WAITING', 'En espera'),
        ('PROMOTED', 'Promovido'),
        ('CANCELLED', 'Cancelado'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='WAITING')
    
    class Meta:
        db_table = 'waitlists'
        unique_together = [['student', 'course_group', 'term']]
        ordering = ['position', 'added_at']
        indexes = [
            models.Index(fields=['course_group', 'status', 'position']),
        ]
    
    def __str__(self):
        return f"Waitlist {self.student.username} - {self.course_group} (pos: {self.position})"


class PaymentOrder(models.Model):
    """Orden de pago generada tras confirmar matrícula"""
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_orders')
    term = models.ForeignKey('Term', on_delete=models.CASCADE, related_name='payment_orders')
    
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    STATUS_CHOICES = [
        ('PENDING', 'Pendiente'),
        ('PAID', 'Pagado'),
        ('CANCELLED', 'Cancelado'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'payment_orders'
        indexes = [
            models.Index(fields=['student', 'term', 'status']),
        ]
    
    def __str__(self):
        return f"Orden {self.id} - {self.student.username} - {self.status}"


class EnrollmentAttempt(models.Model):
    """Auditoría de intentos de matrícula"""
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enrollment_attempts')
    term = models.ForeignKey('Term', on_delete=models.CASCADE, related_name='enrollment_attempts')
    
    ACTION_CHOICES = [
        ('CONFIRM', 'Confirmar matrícula'),
        ('DROP', 'Dar de baja'),
        ('SWAP', 'Cambiar sección'),
        ('ADD_TO_CART', 'Agregar al carrito'),
        ('WAITLIST', 'Agregar a waitlist'),
    ]
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    
    success = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)
    details = models.TextField(blank=True, help_text="JSON con detalles adicionales")
    
    attempted_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        db_table = 'enrollment_attempts'
        indexes = [
            models.Index(fields=['student', 'term', 'attempted_at']),
            models.Index(fields=['action', 'success']),
        ]
    
    def __str__(self):
        return f"{self.action} - {self.student.username} - {'✓' if self.success else '✗'}"