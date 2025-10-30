from django.db.models import Count, Q
import csv
from io import StringIO


class ReportService:
    """Servicio para generar reportes"""
    
    @staticmethod
    def get_occupancy_report(term):
        """
        Genera reporte de ocupación por sección
        """
        from ..models import CourseGroup, Enrollment
        
        groups = CourseGroup.objects.filter(term=term).select_related('course')
        
        report_data = []
        
        for group in groups:
            enrolled_count = Enrollment.objects.filter(
                course_group=group,
                term=term,
                status='ENROLLED'
            ).count()
            
            capacity = group.capacity
            usage_pct = (enrolled_count / capacity * 100) if capacity > 0 else 0
            
            report_data.append({
                'course_code': group.course.code,
                'course_name': group.course.name,
                'section': group.section_code,
                'capacity': capacity,
                'enrolled': enrolled_count,
                'available': max(0, capacity - enrolled_count),
                'usage_pct': round(usage_pct, 2)
            })
        
        # Ordenar por código de curso y sección
        report_data.sort(key=lambda x: (x['course_code'], x['section']))
        
        return report_data
    
    @staticmethod
    def export_occupancy_csv(term):
        """Exporta reporte de ocupación a CSV"""
        report_data = ReportService.get_occupancy_report(term)
        
        output = StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=[
                'course_code', 'course_name', 'section', 
                'capacity', 'enrolled', 'available', 'usage_pct'
            ]
        )
        
        writer.writeheader()
        for row in report_data:
            writer.writerow(row)
        
        return output.getvalue()
    
    @staticmethod
    def get_enrollment_list(course_group):
        """Lista de matriculados en una sección"""
        from ..models import Enrollment
        
        enrollments = Enrollment.objects.filter(
            course_group=course_group,
            status='ENROLLED'
        ).select_related('student', 'student__student_profile').order_by(
            'student__last_name',
            'student__first_name'
        )
        
        students = []
        for enrollment in enrollments:
            student = enrollment.student
            profile = getattr(student, 'student_profile', None)
            
            students.append({
                'username': student.username,
                'full_name': student.get_full_name(),
                'email': student.email,
                'student_code': profile.student_code if profile else 'N/A',
                'enrolled_at': enrollment.enrolled_at
            })
        
        return students
    
    @staticmethod
    def get_waitlist_report(course_group):
        """Lista de espera de una sección"""
        from ..models import Waitlist
        
        waitlist_entries = Waitlist.objects.filter(
            course_group=course_group,
            status='WAITING'
        ).select_related('student', 'student__student_profile').order_by(
            'position',
            'added_at'
        )
        
        students = []
        for entry in waitlist_entries:
            student = entry.student
            profile = getattr(student, 'student_profile', None)
            
            students.append({
                'position': entry.position,
                'username': student.username,
                'full_name': student.get_full_name(),
                'email': student.email,
                'student_code': profile.student_code if profile else 'N/A',
                'added_at': entry.added_at
            })
        
        return students
    
    @staticmethod
    def get_student_schedule(student, term):
        """Horario de un estudiante"""
        from ..models import Enrollment, Schedule
        
        enrollments = Enrollment.objects.filter(
            student=student,
            term=term,
            status='ENROLLED'
        ).select_related('course_group', 'course_group__course')
        
        schedules = []
        for enrollment in enrollments:
            group_schedules = Schedule.objects.filter(
                course_group=enrollment.course_group
            ).order_by('day_of_week', 'start_time')
            
            for sched in group_schedules:
                schedules.append({
                    'course': enrollment.course_group.course,
                    'section': enrollment.course_group.section_code,
                    'day': sched.get_day_of_week_display(),
                    'start_time': sched.start_time,
                    'end_time': sched.end_time,
                    'room': sched.room or 'Por asignar'
                })
        
        # Ordenar por día y hora
        day_order = {
            'Lunes': 0, 'Martes': 1, 'Miércoles': 2,
            'Jueves': 3, 'Viernes': 4, 'Sábado': 5, 'Domingo': 6
        }
        schedules.sort(key=lambda x: (
            day_order.get(x['day'], 7),
            x['start_time']
        ))
        
        return schedules