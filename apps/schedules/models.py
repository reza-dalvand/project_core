"""
زمان‌بندی و ساعات کاری — با تاریخ جلالی
هر کسب‌وکار = ۱ نفر (بدون تیم)
"""
from django.db import models
from apps.core.models import BaseModel


class ServiceSchedule(BaseModel):
    """زمان‌بندی خدمت در یک روز خاص (تاریخ جلالی ذخیره شود)"""

    business = models.ForeignKey(
        'businesses.Business',
        on_delete=models.CASCADE,
        related_name='schedules',
        verbose_name='کسب‌وکار',
    )
    service = models.ForeignKey(
        'services.Service',
        on_delete=models.CASCADE,
        related_name='schedules',
        verbose_name='خدمت',
    )
    
    # ═══════════ تاریخ جلالی ═══════════
    jy = models.IntegerField('سال جلالی')
    jm = models.IntegerField('ماه جلالی (1-12)')
    jd = models.IntegerField('روز جلالی')
    date_key = models.CharField('کلید تاریخ', max_length=10)

    # ═══════════ ساعات کاری ═══════════
    work_start = models.TimeField('ساعت شروع')
    work_end = models.TimeField('ساعت پایان')
    slot_duration = models.IntegerField('مدت هر نوبت (دقیقه)')

    # ═══════════ استراحت‌ها ═══════════
    breaks = models.JSONField(
        'استراحت‌ها',
        default=list,
        help_text='[{start: "13:00", end: "14:00"}, ...]',
    )

    # ═══════════ محاسبه شده ═══════════
    slot_count = models.IntegerField('تعداد اسلات‌ها', default=0)

    class Meta:
        db_table = 'service_schedules'
        verbose_name = '🕐 زمان‌بندی خدمت'
        verbose_name_plural = '🕐 زمان‌بندی‌های خدمات'
        # ✅ صحیح: فقط یک schedule برای هر خدمت در هر روز
        unique_together = ['service', 'date_key']
        ordering = ['jy', 'jm', 'jd']

    def __str__(self):
        return f'{self.business.name} - {self.service.name} - {self.date_key}'

    def save(self, *args, **kwargs):
        self.date_key = f'{self.jy}/{self.jm:02d}/{self.jd:02d}'

        if self.work_start and self.work_end and self.slot_duration > 0:
            start_minutes = self.work_start.hour * 60 + self.work_start.minute
            end_minutes = self.work_end.hour * 60 + self.work_end.minute
            total_minutes = end_minutes - start_minutes

            for break_time in self.breaks:
                try:
                    break_start = (
                        int(break_time['start'].split(':')[0]) * 60
                        + int(break_time['start'].split(':')[1])
                    )
                    break_end = (
                        int(break_time['end'].split(':')[0]) * 60
                        + int(break_time['end'].split(':')[1])
                    )
                    total_minutes -= (break_end - break_start)
                except (KeyError, ValueError, IndexError):
                    pass

            self.slot_count = max(0, total_minutes // self.slot_duration)

        super().save(*args, **kwargs)