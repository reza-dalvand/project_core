from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Appointment


@receiver(post_save, sender=Appointment)
def update_time_slot_status(sender, instance, **kwargs):
    """بروزرسانی وضعیت اسلات زمانی بعد از تغییر نوبت"""
    if instance.time_slot:
        if instance.status in [Appointment.Status.RESERVED, Appointment.Status.CONFIRMED]:
            instance.time_slot.status = 'booked'
        elif instance.status in [
            Appointment.Status.CANCELLED_BY_CUSTOMER,
            Appointment.Status.CANCELLED_BY_SALON,
        ]:
            instance.time_slot.status = 'available'
        instance.time_slot.save(update_fields=['status'])