from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from bookings.models import FAQQuestion
from django.utils import timezone
import os

User = get_user_model()

class Command(BaseCommand):
    help = 'Populate sample FAQ questions for TRANSOVA'

    def handle(self, *args, **options):
        if FAQQuestion.objects.exists():
            self.stdout.write(
                self.style.WARNING('FAQQuestions already exist. Skipping population.')
            )
            return

        # Sample FAQs
        samples = [
            {
                'subject': 'What truck types are available?',
                'question': 'I need to know what kinds of trucks I can book for my load.',
                'answer': 'TRANSOVA offers: 10ft/14ft/20ft containers, flatbeds, reefers. Filter by load type/weight in booking form. Use Price Calculator for best fit.',
                'is_public': True,
            },
            {
                'subject': 'How do drivers accept jobs?',
                'question': 'How does the matching process work between customers and drivers?',
                'answer': 'Bids from companies reviewed in dashboard. Accept best offer or auto-assign. Driver confirms pickup time. Track via My Bookings.',
                'is_public': True,
            },
            {
                'subject': 'What documents do I need?',
                'question': 'What paperwork is required for booking?',
                'answer': 'No docs needed upfront. Provide GSTIN if applicable for invoice. Driver handles POD (Proof of Delivery) with signature/photo.',
                'is_public': True,
            },
            {
                'subject': 'Can companies manage multiple trucks?',
                'question': 'How do fleet owners operate on TRANSOVA?',
                'answer': 'Yes! Companies add trucks/drivers in Fleet dashboard. Bid on jobs, manage assignments, track payments/wallet.',
                'is_public': True,
            },
            {
                'subject': 'How to become a driver?',
                'question': 'I want to join as a truck driver.',
                'answer': 'Join a registered company fleet. They add your truck/driver profile. Complete verification. Accept jobs from dashboard.',
                'is_public': True,
            },
            {
                'subject': 'What is Proof of Delivery?',
                'question': 'Explain the delivery confirmation process.',
                'answer': 'Driver uploads delivery photo + recipient signature. Marks booking COMPLETE. Triggers balance payment release.',
                'is_public': True,
            },
            {
                'subject': 'How are disputes handled?',
                'question': 'What if goods are damaged?',
                'answer': 'Contact support within 24hrs with POD photos. Mediation via admin dashboard. Insurance optional for high-value loads.',
                'is_public': True,
            },
            {
                'subject': 'Do you offer subscriptions?',
                'question': 'Is there a subscription plan?',
                'answer': 'Yes! Admin Subscriptions page has plans for high-volume shippers. Reduced commission + priority matching.',
                'is_public': True,
            },
        ]

        created = 0
        for sample in samples:
            faq = FAQQuestion.objects.create(
                subject=sample['subject'],
                question=sample['question'],
                answer=sample['answer'],
                status='ANSWERED',
                is_public=sample['is_public'],
                answered_at=timezone.now(),
            )
            created += 1

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created} sample FAQ questions.')
        )
        self.stdout.write('Run `python manage.py admin_faq` to make some public or edit.')

