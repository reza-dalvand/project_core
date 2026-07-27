"""
سیگنال‌های اپ businesses
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import Business, Service


@receiver(post_save, sender=Business)
def business_status_changed(sender, instance, created, **kwargs):
    """
    وقتی وضعیت کسب‌وکار تغییر کرد:
    - اگر تایید شد: ایمیل/پیامک به صاحب کسب‌وکار
    - اگر رد شد: ایمیل/پیامک با دلیل رد
    """
    if created:
        return  # کسب‌وکار جدید ایجاد شده، هنوز تایید نشده

    # بررسی تغییر وضعیت
    # نکته: برای تشخیص تغییر وضعیت، باید از cache یا database استفاده کنیم
    # در اینجا ساده‌سازی می‌کنیم

    if instance.status == Business.Status.APPROVED:
        # ارسال نوتیفیکیشن تایید
        try:
            # ارسال ایمیل (اگر تنظیم شده باشد)
            if instance.owner.email:
                send_mail(
                    subject=f'تایید کسب‌وکار {instance.name}',
                    message=f'تبریک! کسب‌وکار "{instance.name}" شما در زیبانو تایید شد.\n\n'
                            f'اکنون می‌توانید خدمات خود را ثبت و نوبت‌دهی را شروع کنید.',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[instance.owner.email],
                    fail_silently=True,
                )

            # ارسال پیامک (بعداً پیاده‌سازی می‌شود)
            # SMSService.send(
            #     phone=instance.owner.phone,
            #     template_type='business_approved',
            #     variables={'business_name': instance.name}
            # )

            print(f"✅ Business approved: {instance.name}")

        except Exception as e:
            print(f"Error sending approval notification: {e}")

    elif instance.status == Business.Status.REJECTED:
        # ارسال نوتیفیکیشن رد
        try:
            if instance.owner.email:
                send_mail(
                    subject=f'رد کسب‌وکار {instance.name}',
                    message=f'متاسفانه کسب‌وکار "{instance.name}" شما در زیبانو تایید نشد.\n\n'
                            f'دلیل رد: {instance.rejection_reason}\n\n'
                            f'لطفاً اطلاعات را اصلاح و مجدداً ارسال کنید.',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[instance.owner.email],
                    fail_silently=True,
                )

            # ارسال پیامک
            # SMSService.send(
            #     phone=instance.owner.phone,
            #     template_type='business_rejected',
            #     variables={
            #         'business_name': instance.name,
            #         'reason': instance.rejection_reason
            #     }
            # )

            print(f"❌ Business rejected: {instance.name}")

        except Exception as e:
            print(f"Error sending rejection notification: {e}")


@receiver(post_save, sender=Service)
@receiver(post_delete, sender=Service)
def update_business_services_count(sender, instance, **kwargs):
    """بروزرسانی تعداد خدمات کسب‌وکار"""
    business = instance.business
    if business:
        business.services_count = business.services.filter(is_active=True).count()
        business.save(update_fields=['services_count'])