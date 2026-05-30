import os

from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand


PROVIDERS = (
    ("google", "Google", "GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET"),
    ("facebook", "Facebook", "FACEBOOK_OAUTH_CLIENT_ID", "FACEBOOK_OAUTH_CLIENT_SECRET"),
)


class Command(BaseCommand):
    help = "Configure django-allauth SocialApp records from environment variables."

    def handle(self, *args, **options):
        domain = os.environ.get("DJANGO_SITE_DOMAIN", "127.0.0.1:8000")
        site, _ = Site.objects.update_or_create(
            id=1,
            defaults={"domain": domain, "name": os.environ.get("DJANGO_SITE_NAME", "Tro Tot Sinh Vien")},
        )

        configured = []
        skipped = []
        for provider, name, client_id_env, secret_env in PROVIDERS:
            client_id = os.environ.get(client_id_env)
            secret = os.environ.get(secret_env)
            if not client_id or not secret:
                skipped.append(provider)
                continue

            app, _ = SocialApp.objects.update_or_create(
                provider=provider,
                name=name,
                defaults={"client_id": client_id, "secret": secret},
            )
            app.sites.set([site])
            configured.append(provider)

        if configured:
            self.stdout.write(self.style.SUCCESS(f"Configured OAuth providers: {', '.join(configured)}."))
        if skipped:
            self.stdout.write(self.style.WARNING(f"Skipped providers without credentials: {', '.join(skipped)}."))

