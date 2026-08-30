import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create the initial Django superuser from environment variables."

    def handle(self, *args, **options):
        username = os.getenv("DJANGO_SUPERUSER_USERNAME")
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD")
        email = os.getenv("DJANGO_SUPERUSER_EMAIL", "")
        if not username or not password:
            self.stdout.write("Admin environment variables are not set; skipped.")
            return
        user_model = get_user_model()
        user, created = user_model.objects.get_or_create(
            username=username,
            defaults={"email": email, "is_staff": True, "is_superuser": True},
        )
        if created:
            user.set_password(password)
            user.save(update_fields=("password",))
            self.stdout.write(self.style.SUCCESS(f"Created administrator {username}."))
        else:
            self.stdout.write(f"Administrator {username} already exists; skipped.")
