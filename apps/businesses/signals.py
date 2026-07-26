"""
سیگنال‌های اپ businesses
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Service


@receiver(post_save, sender=Service)
@receiver(post_delete, sender=Service)
def update_business_services_count(sender, instance, **kwargs):
    """بروزرسانی تعداد خدمات کسب‌وکار"""
    business = instance.business
    if business:
        business.services_count = business.services.filter(is_active=True).count()
        business.save(update_fields=['services_count'])