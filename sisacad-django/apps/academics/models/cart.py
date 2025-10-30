from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta


class EnrollmentCart(models.Model):
    """Carrito de matrícula (1 por estudiante y término)"""
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enrollment_carts')
    term = models.ForeignKey('Term', on_delete=models.CASCADE, related_name='carts')
    
    is_confirmed = models.BooleanField(default=False)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'enrollment_carts'
        unique_together = [['student', 'term']]
        indexes = [
            models.Index(fields=['student', 'term']),
        ]
    
    def __str__(self):
        return f"Carrito {self.student.username} - {self.term.code}"
    
    def is_active(self):
        """Verifica si el carrito está activo (no confirmado)"""
        return not self.is_confirmed
    
    def get_active_items(self):
        """Retorna ítems activos (con reserva válida)"""
        now = timezone.now()
        return self.items.filter(
            reservation__isnull=False,
            reservation__reserved_until__gt=now,
            reservation__is_released=False
        )
    
    def get_total_credits(self):
        """Calcula total de créditos en el carrito"""
        from django.db.models import Sum
        result = self.get_active_items().aggregate(
            total=Sum('course_group__course__credits')
        )
        return result['total'] or 0


class CartItem(models.Model):
    """Ítem en el carrito de matrícula"""
    cart = models.ForeignKey(EnrollmentCart, on_delete=models.CASCADE, related_name='items')
    course_group = models.ForeignKey('CourseGroup', on_delete=models.CASCADE)
    
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'cart_items'
        unique_together = [['cart', 'course_group']]
        indexes = [
            models.Index(fields=['cart', 'course_group']),
        ]
    
    def __str__(self):
        return f"{self.cart.student.username} - {self.course_group}"
    
    def get_reservation(self):
        """Obtiene la reserva activa de este ítem"""
        try:
            return self.reservation
        except CapReservation.DoesNotExist:
            return None


class CapReservation(models.Model):
    """Reserva temporal de cupo"""
    cart_item = models.OneToOneField(
        CartItem,
        on_delete=models.CASCADE,
        related_name='reservation'
    )
    course_group = models.ForeignKey('CourseGroup', on_delete=models.CASCADE)
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    term = models.ForeignKey('Term', on_delete=models.CASCADE)
    
    reserved_at = models.DateTimeField(auto_now_add=True)
    reserved_until = models.DateTimeField()
    is_released = models.BooleanField(default=False)
    released_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'cap_reservations'
        indexes = [
            models.Index(fields=['course_group', 'student', 'term']),
            models.Index(fields=['reserved_until', 'is_released']),
        ]
    
    def __str__(self):
        return f"Reserva {self.student.username} - {self.course_group}"
    
    def is_valid(self):
        """Verifica si la reserva sigue válida"""
        return not self.is_released and timezone.now() < self.reserved_until
    
    def release(self):
        """Libera la reserva"""
        if not self.is_released:
            self.is_released = True
            self.released_at = timezone.now()
            self.save()
    
    @staticmethod
    def create_reservation(cart_item, course_group, student, term, minutes=15):
        """Crea una nueva reserva"""
        reserved_until = timezone.now() + timedelta(minutes=minutes)
        return CapReservation.objects.create(
            cart_item=cart_item,
            course_group=course_group,
            student=student,
            term=term,
            reserved_until=reserved_until
        )