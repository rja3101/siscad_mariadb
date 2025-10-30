from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator


class StudentProfile(models.Model):
    """Perfil académico del estudiante"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    
    # Información académica
    student_code = models.CharField(max_length=20, unique=True)
    cohort = models.CharField(max_length=10, help_text="Cohorte de ingreso (ej: 2023-A)")
    curriculum = models.CharField(max_length=50, help_text="Plan curricular")
    
    # GPA y créditos
    gpa = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0), MaxValueValidator(4.00)],
        help_text="CRAest - Promedio ponderado acumulado"
    )
    approved_credits = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Total de créditos aprobados"
    )
    
    # Bloqueos (holds)
    has_financial_hold = models.BooleanField(
        default=False,
        help_text="Bloqueado por deudas"
    )
    has_document_hold = models.BooleanField(
        default=False,
        help_text="Bloqueado por documentos pendientes"
    )
    has_academic_hold = models.BooleanField(
        default=False,
        help_text="Bloqueado por motivos académicos"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'student_profiles'
        indexes = [
            models.Index(fields=['student_code']),
            models.Index(fields=['cohort']),
        ]
    
    def __str__(self):
        return f"{self.student_code} - {self.user.get_full_name()}"
    
    def has_any_hold(self):
        """Verifica si el estudiante tiene algún bloqueo"""
        return (self.has_financial_hold or 
                self.has_document_hold or 
                self.has_academic_hold)
    
    def get_hold_reasons(self):
        """Retorna lista de razones de bloqueo"""
        reasons = []
        if self.has_financial_hold:
            reasons.append("Deuda pendiente")
        if self.has_document_hold:
            reasons.append("Documentos pendientes")
        if self.has_academic_hold:
            reasons.append("Bloqueo académico")
        return reasons