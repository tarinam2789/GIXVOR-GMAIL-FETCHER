"""
Seeds the database with a fake search + fake emails, so you can demo
or record the UI without ever connecting to a real Gmail account.

Usage:
    python manage.py seed_demo
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from fetcher.models import CachedEmail, SearchQuery

DEMO_SENDER = "priya@northwind-designs.example"
DEMO_GMAIL = "demo.inbox@gmail.com"

DEMO_EMAILS = [
    {
        "subject": "Revised homepage mockups attached",
        "from_address": "Priya Anand <priya@northwind-designs.example>",
        "to_address": "demo.inbox@gmail.com",
        "days_ago": 1,
        "body": (
            "Hi there,\n\nAttached are the revised homepage mockups based on "
            "yesterday's feedback call. I tightened up the hero section and "
            "swapped in the new logo treatment we discussed.\n\nLet me know "
            "if the spacing on mobile feels right, and I'll move on to the "
            "pricing page next.\n\nBest,\nPriya"
        ),
        "attachments": ["homepage_v3.fig", "mobile_preview.png"],
    },
    {
        "subject": "Re: Timeline for the Q3 launch",
        "from_address": "Priya Anand <priya@northwind-designs.example>",
        "to_address": "demo.inbox@gmail.com",
        "days_ago": 4,
        "body": (
            "Following up on the timeline — if we lock the design by the "
            "15th, dev should have enough runway to hit the Q3 launch date.\n\n"
            "Can we grab 20 minutes this week to walk through the component "
            "library together?"
        ),
        "attachments": [],
    },
    {
        "subject": "Invoice #1042 for July",
        "from_address": "Priya Anand <priya@northwind-designs.example>",
        "to_address": "demo.inbox@gmail.com",
        "days_ago": 9,
        "body": (
            "Hi,\n\nAttached is invoice #1042 covering design work for July. "
            "Payment terms are net 15 as usual.\n\nThanks for another great "
            "month working together!\n\nPriya"
        ),
        "attachments": ["invoice_1042.pdf"],
    },
    {
        "subject": "Quick question about the color palette",
        "from_address": "Priya Anand <priya@northwind-designs.example>",
        "to_address": "demo.inbox@gmail.com",
        "days_ago": 16,
        "body": (
            "Should the secondary accent color carry over into the email "
            "templates too, or keep those closer to the old brand guide for "
            "now? Want to make sure marketing isn't caught off guard."
        ),
        "attachments": [],
    },
    {
        "subject": "Kickoff notes + next steps",
        "from_address": "Priya Anand <priya@northwind-designs.example>",
        "to_address": "demo.inbox@gmail.com",
        "days_ago": 24,
        "body": (
            "Great kicking things off today. Recapping what we agreed on:\n\n"
            "1. Wireframes by end of week\n2. Brand audit shared by Monday\n"
            "3. Weekly check-ins on Thursdays at 2pm\n\nExcited to get "
            "started!"
        ),
        "attachments": ["kickoff_notes.docx"],
    },
]


class Command(BaseCommand):
    help = "Seeds a fake search + fake emails so the UI can be demoed without a real Gmail account."

    def handle(self, *args, **options):
        query = SearchQuery.objects.create(
            session_key="demo",
            gmail_address=DEMO_GMAIL,
            sender_email=DEMO_SENDER,
            mailbox="INBOX",
            result_count=len(DEMO_EMAILS),
            succeeded=True,
        )

        now = timezone.now()
        for item in DEMO_EMAILS:
            received_at = now - timedelta(days=item["days_ago"])
            CachedEmail.objects.create(
                query=query,
                subject=item["subject"],
                from_address=item["from_address"],
                to_address=item["to_address"],
                date_header=received_at.strftime("%a, %d %b %Y %H:%M:%S +0000"),
                received_at=received_at,
                snippet=item["body"][:220],
                body_text=item["body"],
                has_attachments=bool(item["attachments"]),
                attachment_names="|".join(item["attachments"]),
            )

        self.stdout.write(self.style.SUCCESS(f"Seeded demo search (id={query.pk})."))
        self.stdout.write(f"Visit: http://127.0.0.1:8000/results/{query.pk}/")