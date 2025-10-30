from django.db import transaction
from django.utils import timezone
from ..models import (
    Enrollment, EnrollmentAttempt, PaymentOrder, Waitlist,
    CoursePrerequisite, CourseCorequisite, EnrollmentCart
)
import json


class EnrollmentService:
    """Servicio para confirmar matrículas y gestionar bajas"""
    
    @staticmethod
    def validate_prerequisites(student, course, term):
        """Valida que el estudiante cumpla con los prerrequisitos"""
        prerequisites = CoursePrerequisite.objects.filter(course=course)
        
        for prereq in prerequisites:
            # Verificar si el estudiante aprobó el prerrequisito
            approved = Enrollment.objects.filter(
                student=student,
                course_group__course=prereq.prerequisite_course,
                status='ENROLLED'
            ).exists()
            
            if not approved and prereq.is_strict:
                return False, f"Falta prerrequisito: {prereq.prerequisite_course.code}"
        
        return True, ""
    
    @staticmethod
    def validate_corequisites(student, course, cart_items, term):
        """Valida que los corequisitos estén en el carrito o matriculados"""
        corequisites = CourseCorequisite.objects.filter(course=course)
        
        for coreq in corequisites:
            # Verificar si está en el carrito
            in_cart = any(
                item.course_group.course == coreq.corequisite_course 
                for item in cart_items
            )
            
            # Verificar si ya está matriculado
            enrolled = Enrollment.objects.filter(
                student=student,
                course_group__course=coreq.corequisite_course,
                term=term,
                status='ENROLLED'
            ).exists()
            
            if not in_cart and not enrolled:
                return False, f"Falta corequisito: {coreq.corequisite_course.code}"
        
        return True, ""
    
    @staticmethod
    def check_schedule_conflicts(student, term, new_schedules, exclude_groups=None):
        """Verifica choques de horario"""
        if exclude_groups is None:
            exclude_groups = []
        
        # Obtener horarios de cursos matriculados
        enrolled = Enrollment.objects.filter(
            student=student,
            term=term,
            status='ENROLLED'
        ).exclude(course_group__in=exclude_groups)
        
        from ..models import Schedule
        existing_schedules = Schedule.objects.filter(
            course_group__in=[e.course_group for e in enrolled]
        )
        
        # Comparar horarios
        for new_sched in new_schedules:
            for exist_sched in existing_schedules:
                if EnrollmentService._schedules_overlap(new_sched, exist_sched):
                    return True, f"Choque de horario con {exist_sched.course_group}"
        
        return False, ""
    
    @staticmethod
    def _schedules_overlap(sched1, sched2):
        """Verifica si dos horarios se solapan"""
        # Verificar mismo día
        if sched1.day_of_week != sched2.day_of_week:
            return False
        
        # Verificar solapamiento de horas
        return not (sched1.end_time <= sched2.start_time or 
                   sched1.start_time >= sched2.end_time)
    
    @staticmethod
    @transaction.atomic
    def confirm_enrollment(student, term, enrolled_by=None):
        """
        Confirma la matrícula desde el carrito.
        Validaciones: ventana, cupos, choques, créditos, prerrequisitos.
        """
        errors = []
        enrollments_created = []
        
        # Verificar bloqueos
        if hasattr(student, 'student_profile'):
            profile = student.student_profile
            if profile.has_any_hold():
                return False, profile.get_hold_reasons(), []
        
        # Obtener carrito
        try:
            cart = EnrollmentCart.objects.get(student=student, term=term)
        except EnrollmentCart.DoesNotExist:
            return False, ["No tienes un carrito activo"], []
        
        if cart.is_confirmed:
            return False, ["El carrito ya fue confirmado"], []
        
        # Verificar ventana de matrícula
        windows = term.enrollment_windows.filter(is_active=True)
        if not any(w.is_open() for w in windows):
            return False, ["Ventana de matrícula cerrada"], []
        
        # Obtener ítems activos del carrito
        cart_items = cart.get_active_items()
        
        if not cart_items.exists():
            return False, ["El carrito está vacío o las reservas expiraron"], []
        
        # Verificar límite de créditos
        total_credits = cart.get_total_credits()
        
        if hasattr(term, 'rules') and hasattr(student, 'student_profile'):
            rules = term.rules
            profile = student.student_profile
            max_credits = rules.get_max_credits_for_gpa(profile.gpa)
            
            if total_credits > max_credits:
                return False, [f"Excedes el límite de créditos ({max_credits})"], []
            
            if total_credits < rules.min_credits:
                return False, [f"No cumples el mínimo de créditos ({rules.min_credits})"], []
        
        # Validar cada curso
        from ..models import CourseGroup, Schedule
        
        for cart_item in cart_items:
            group = cart_item.course_group
            course = group.course
            
            # Rebloquear sección
            locked_group = CourseGroup.objects.select_for_update().get(pk=group.pk)
            
            # Verificar cupo disponible
            if locked_group.get_available_slots() <= 0:
                errors.append(f"Sin cupos: {locked_group}")
                continue
            
            # Validar prerrequisitos
            valid, msg = EnrollmentService.validate_prerequisites(student, course, term)
            if not valid:
                errors.append(msg)
                continue
            
            # Validar corequisitos
            valid, msg = EnrollmentService.validate_corequisites(
                student, course, cart_items, term
            )
            if not valid:
                errors.append(msg)
                continue
            
            # Verificar choques de horario
            schedules = Schedule.objects.filter(course_group=locked_group)
            has_conflict, msg = EnrollmentService.check_schedule_conflicts(
                student, term, schedules
            )
            if has_conflict:
                errors.append(msg)
                continue
            
            # Crear matrícula
            enrollment = Enrollment.objects.create(
                student=student,
                course_group=locked_group,
                term=term,
                status='ENROLLED',
                enrolled_by=enrolled_by or student
            )
            enrollments_created.append(enrollment)
        
        # Si hubo errores, rollback
        if errors:
            transaction.set_rollback(True)
            return False, errors, []
        
        # Marcar carrito como confirmado
        cart.is_confirmed = True
        cart.confirmed_at = timezone.now()
        cart.save()
        
        # Generar orden de pago (stub)
        PaymentOrder.objects.create(
            student=student,
            term=term,
            amount=0.00,  # Calcular según política
            status='PENDING'
        )
        
        # Log de auditoría
        EnrollmentAttempt.objects.create(
            student=student,
            term=term,
            action='CONFIRM',
            success=True,
            details=json.dumps({
                'enrollments': [e.id for e in enrollments_created],
                'total_credits': total_credits
            })
        )
        
        return True, ["Matrícula confirmada exitosamente"], enrollments_created
    
    @staticmethod
    @transaction.atomic
    def drop_enrollment(enrollment, dropped_by=None):
        """Da de baja una matrícula y promueve waitlist si existe"""
        enrollment.drop(dropped_by)
        
        # Verificar waitlist
        waitlist_entries = Waitlist.objects.filter(
            course_group=enrollment.course_group,
            term=enrollment.term,
            status='WAITING'
        ).order_by('position', 'added_at')
        
        for waitlist_entry in waitlist_entries:
            # Verificar choques de horario
            from ..models import Schedule
            schedules = Schedule.objects.filter(course_group=enrollment.course_group)
            has_conflict, _ = EnrollmentService.check_schedule_conflicts(
                waitlist_entry.student,
                enrollment.term,
                schedules
            )
            
            if not has_conflict:
                # Promover
                Enrollment.objects.create(
                    student=waitlist_entry.student,
                    course_group=enrollment.course_group,
                    term=enrollment.term,
                    status='ENROLLED',
                    enrolled_by=dropped_by
                )
                
                waitlist_entry.status = 'PROMOTED'
                waitlist_entry.save()
                break
        
        return True, ["Matrícula dada de baja"]
    
    @staticmethod
    @transaction.atomic
    def swap_section(student, old_group, new_group, term):
        """Cambia de sección dentro del mismo curso"""
        # Verificar mismo curso
        if old_group.course != new_group.course:
            return False, ["Las secciones no son del mismo curso"]
        
        # Verificar matrícula actual
        try:
            old_enrollment = Enrollment.objects.get(
                student=student,
                course_group=old_group,
                term=term,
                status='ENROLLED'
            )
        except Enrollment.DoesNotExist:
            return False, ["No estás matriculado en la sección actual"]
        
        # Bloquear nueva sección
        from ..models import CourseGroup
        locked_new_group = CourseGroup.objects.select_for_update().get(pk=new_group.pk)
        
        # Verificar cupo
        if locked_new_group.get_available_slots() <= 0:
            return False, ["Sin cupos en la nueva sección"]
        
        # Verificar choques
        from ..models import Schedule
        schedules = Schedule.objects.filter(course_group=locked_new_group)
        has_conflict, msg = EnrollmentService.check_schedule_conflicts(
            student, term, schedules, exclude_groups=[old_group]
        )
        
        if has_conflict:
            return False, [msg]
        
        # Realizar swap
        old_enrollment.drop()
        
        Enrollment.objects.create(
            student=student,
            course_group=locked_new_group,
            term=term,
            status='ENROLLED',
            enrolled_by=student
        )
        
        # Log
        EnrollmentAttempt.objects.create(
            student=student,
            term=term,
            action='SWAP',
            success=True,
            details=json.dumps({
                'old_group_id': old_group.id,
                'new_group_id': new_group.id
            })
        )
        
        return True, ["Cambio de sección exitoso"]