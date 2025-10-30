from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from ..models import (
    EnrollmentCart, CartItem, CapReservation, 
    GroupPairing, Enrollment, EnrollmentAttempt
)
import json


class CartService:
    """Servicio para manejar el carrito de matrícula"""
    
    @staticmethod
    def get_or_create_cart(student, term):
        """Obtiene o crea el carrito del estudiante para el término"""
        cart, created = EnrollmentCart.objects.get_or_create(
            student=student,
            term=term,
            defaults={'is_confirmed': False}
        )
        return cart
    
    @staticmethod
    @transaction.atomic
    def add_to_cart(student, course_group, term):
        """
        Agrega un curso al carrito con reserva de cupo.
        Maneja emparejamiento teoría-lab automáticamente.
        """
        errors = []
        
        # Verificar bloqueos del estudiante
        if hasattr(student, 'student_profile'):
            profile = student.student_profile
            if profile.has_any_hold():
                return False, profile.get_hold_reasons()
        
        # Obtener o crear carrito
        cart = CartService.get_or_create_cart(student, term)
        
        if cart.is_confirmed:
            return False, ["El carrito ya fue confirmado"]
        
        # Verificar si ya está en el carrito
        if CartItem.objects.filter(cart=cart, course_group=course_group).exists():
            return False, ["El curso ya está en tu carrito"]
        
        # Verificar si ya está matriculado
        if Enrollment.objects.filter(
            student=student,
            course_group=course_group,
            term=term,
            status='ENROLLED'
        ).exists():
            return False, ["Ya estás matriculado en este curso"]
        
        # Verificar emparejamiento teoría-lab
        groups_to_add = [course_group]
        try:
            pairing = GroupPairing.objects.get(
                term=term,
                theory_group=course_group,
                is_mandatory=True
            )
            groups_to_add.append(pairing.lab_group)
        except GroupPairing.DoesNotExist:
            try:
                pairing = GroupPairing.objects.get(
                    term=term,
                    lab_group=course_group,
                    is_mandatory=True
                )
                groups_to_add.append(pairing.theory_group)
            except GroupPairing.DoesNotExist:
                pass
        
        # Intentar reservar cupo para todos los grupos
        term_rules = term.rules
        minutes = term_rules.cart_reservation_minutes if hasattr(term, 'rules') else 15
        
        for group in groups_to_add:
            # Bloquear fila de la sección (SELECT FOR UPDATE)
            from ..models import CourseGroup
            locked_group = CourseGroup.objects.select_for_update().get(pk=group.pk)
            
            # Verificar cupos disponibles
            available = locked_group.get_available_slots()
            if available <= 0:
                errors.append(f"No hay cupos en {locked_group}")
                continue
            
            # Crear ítem en el carrito
            cart_item = CartItem.objects.create(
                cart=cart,
                course_group=locked_group
            )
            
            # Crear reserva
            CapReservation.create_reservation(
                cart_item=cart_item,
                course_group=locked_group,
                student=student,
                term=term,
                minutes=minutes
            )
        
        # Log de auditoría
        EnrollmentAttempt.objects.create(
            student=student,
            term=term,
            action='ADD_TO_CART',
            success=len(errors) == 0,
            error_message='; '.join(errors) if errors else '',
            details=json.dumps({
                'course_group_id': course_group.id,
                'groups_added': [g.id for g in groups_to_add]
            })
        )
        
        if errors:
            return False, errors
        
        return True, ["Curso(s) agregado(s) al carrito exitosamente"]
    
    @staticmethod
    @transaction.atomic
    def remove_from_cart(student, course_group, term):
        """Elimina un curso del carrito y libera su reserva"""
        cart = CartService.get_or_create_cart(student, term)
        
        try:
            cart_item = CartItem.objects.get(cart=cart, course_group=course_group)
            
            # Liberar reserva si existe
            try:
                reservation = cart_item.reservation
                reservation.release()
            except CapReservation.DoesNotExist:
                pass
            
            cart_item.delete()
            return True, ["Curso eliminado del carrito"]
        except CartItem.DoesNotExist:
            return False, ["El curso no está en tu carrito"]
    
    @staticmethod
    def get_cart_summary(student, term):
        """Obtiene resumen del carrito con reservas"""
        cart = CartService.get_or_create_cart(student, term)
        
        items = []
        now = timezone.now()
        
        for cart_item in cart.items.all():
            item_data = {
                'cart_item': cart_item,
                'course_group': cart_item.course_group,
                'reservation': None,
                'is_expired': True,
                'time_left': None
            }
            
            try:
                reservation = cart_item.reservation
                item_data['reservation'] = reservation
                item_data['is_expired'] = not reservation.is_valid()
                
                if reservation.is_valid():
                    time_left = reservation.reserved_until - now
                    item_data['time_left'] = int(time_left.total_seconds() / 60)
            except CapReservation.DoesNotExist:
                pass
            
            items.append(item_data)
        
        return {
            'cart': cart,
            'items': items,
            'total_credits': cart.get_total_credits()
        }