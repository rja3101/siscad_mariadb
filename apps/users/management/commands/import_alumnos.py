from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.apps import apps
import csv
from pathlib import Path

class Command(BaseCommand):
    help = "Importa alumnos desde un CSV y les asigna password '123' y rol Alumno."

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str, help="Ruta al CSV de alumnos")

    def handle(self, *args, **opts):
        csv_path = Path(opts["csv_path"])
        if not csv_path.exists():
            self.stderr.write(self.style.ERROR(f"No existe: {csv_path}"))
            return

        User = get_user_model()
        Role = apps.get_model("users", "Role")
        alumno_role, _ = Role.objects.get_or_create(name="Alumno")

        creados = 0
        actualizados = 0
        with csv_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                username = row["cui"].strip()
                email = row["email"].strip().lower()
                first_name = row["nombres"].strip()
                last_name = f'{row["ap_paterno"].strip()} {row["ap_materno"].strip()}'

                user, created = User.objects.get_or_create(
                    username=username,
                    defaults=dict(email=email, first_name=first_name, last_name=last_name),
                )
                if created:
                    user.set_password("123")
                    user.is_active = True
                    user.is_staff = False
                    user.role = alumno_role  # si tu User tiene este campo
                    user.save()
                    creados += 1
                else:
                    # actualiza datos si cambiaron
                    changed = False
                    for k, v in [("email", email), ("first_name", first_name), ("last_name", last_name)]:
                        if getattr(user, k) != v:
                            setattr(user, k, v); changed = True
                    if getattr(user, "role", None) != alumno_role:
                        user.role = alumno_role; changed = True
                    if changed:
                        user.save(); actualizados += 1

        self.stdout.write(self.style.SUCCESS(
            f"OK - creados: {creados}, actualizados: {actualizados}"
        ))
