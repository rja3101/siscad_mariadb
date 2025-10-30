from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone


class Term(models.Model):
    """Periodo académico (ej: 2025-1, 2025-2)"""
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'terms'
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.code} - {self.name}"


class EnrollmentWindow(models.Model):
    """Ventana de matrícula para un periodo"""
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name='enrollment_windows')
    name = models.CharField(max_length=100)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'enrollment_windows'
        ordering = ['start_datetime']
    
    def __str__(self):
        return f"{self.term.code} - {self.name}"
    
    def is_open(self):
        """Verifica si la ventana está abierta"""
        now = timezone.now()
        return self.is_active and self.start_datetime <= now <= self.end_datetime


class TermRule(models.Model):
    """Reglas de matrícula por término"""
    term = models.OneToOneField(Term, on_delete=models.CASCADE, related_name='rules')
    
    # Límites de créditos
    min_credits = models.IntegerField(default=12, validators=[MinValueValidator(0)])
    max_credits = models.IntegerField(default=22, validators=[MinValueValidator(0)])
    
    # Límites por GPA
    max_credits_low_gpa = models.IntegerField(
        default=16,
        validators=[MinValueValidator(0)],
        help_text="Máximo de créditos para estudiantes con GPA < 2.5"
    )
    low_gpa_threshold = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=2.5,
        help_text="Umbral de GPA bajo"
    )
    
    # Tiempo de reserva del carrito (en minutos)
    cart_reservation_minutes = models.IntegerField(
        default=15,
        validators=[MinValueValidator(1)],
        help_text="Minutos que dura la reserva de cupo en el carrito"
    )
    
    # Configuraciones adicionales
    allow_course_repeat = models.BooleanField(
        default=True,
        help_text="Permitir repetir cursos ya aprobados"
    )
    
    class Meta:
        db_table = 'term_rules'
    
    def __str__(self):
        return f"Reglas {self.term.code}"
    
    def get_max_credits_for_gpa(self, gpa):
        """Retorna el máximo de créditos según el GPA del estudiante"""
        if gpa < self.low_gpa_threshold:
            return self.max_credits_low_gpa
        return self.max_credits