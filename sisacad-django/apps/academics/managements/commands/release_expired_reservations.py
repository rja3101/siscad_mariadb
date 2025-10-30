from django.core.management.base import BaseCommand
from django.utils import timezone
from academics.models import CapReservation, CartItem


class Command(BaseCommand):
    help = 'Libera reservas de cupo vencidas en el carrito'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Muestra las reservas a liberar sin ejecutar cambios',
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        now = timezone.now()
        
        # Buscar reservas vencidas
        expired_reservations = CapReservation.objects.filter(
            is_released=False,
            reserved_until__lt=now
        ).select_related('cart_item', 'student', 'course_group')
        
        count = expired_reservations.count()
        
        if count == 0:
            self.stdout.write(
                self.style.SUCCESS('No hay reservas vencidas')
            )
            return
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'[DRY RUN] Se liberarían {count} reservas vencidas:'
                )
            )
            
            for reservation in expired_reservations:
                self.stdout.write(
                    f'  - {reservation.student.username}: '
                    f'{reservation.course_group} '
                    f'(vencida: {reservation.reserved_until})'
                )
        else:
            # Liberar reservas
            released_count = 0
            
            for reservation in expired_reservations:
                try:
                    reservation.release()
                    released_count += 1
                    
                    self.stdout.write(
                        f'✓ Liberada: {reservation.student.username} - '
                        f'{reservation.course_group}'
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f'✗ Error liberando reserva {reservation.id}: {str(e)}'
                        )
                    )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n✓ {released_count}/{count} reservas liberadas exitosamente'
                )
            )
            
            # Opcional: Eliminar ítems del carrito sin reserva válida
            orphan_items = CartItem.objects.filter(
                reservation__is_released=True
            )
            orphan_count = orphan_items.count()
            
            if orphan_count > 0:
                orphan_items.delete()
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ {orphan_count} ítems huérfanos eliminados del carrito'
                    )
                )