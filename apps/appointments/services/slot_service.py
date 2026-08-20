"""
Slot Service — محاسبه اسلات‌های آزاد بر اساس ServiceSchedule
با تاریخ جلالی
"""
import logging
from datetime import datetime, timedelta, date, time
from typing import List, Dict, Optional

import jdatetime
from django.core.cache import cache
from django.db.models import Q

from apps.appointments.models import Appointment
from apps.schedules.models import ServiceSchedule
from apps.businesses.models import Business
from apps.services.models import Service

logger = logging.getLogger(__name__)


class SlotService:
    """سرویس محاسبه اسلات‌های زمانی آزاد — با تاریخ جلالی"""

    CACHE_TIMEOUT = 300  # ۵ دقیقه

    # ═══════════════════════════════════════════════
    #   دریافت اسلات‌های آزاد
    # ═══════════════════════════════════════════════

    @staticmethod
    def get_available_slots(
        business_id: int,
        service_id: int,
        jy: int,
        jm: int,
        jd: int,
    ) -> List[Dict]:
        """
        دریافت تمام اسلات‌های آزاد برای یک تاریخ جلالی خاص

        الگوریتم:
        1. ServiceSchedule روز مورد نظر را پیدا کن
        2. اسلات‌ها را بر اساس work_start، work_end و slot_duration تولید کن
        3. استراحت‌ها (breaks) را حذف کن
        4. نوبت‌های رزرو شده را حذف کن
        5. اسلات‌های گذشته را حذف کن (اگر امروز است)
        """
        cache_key = (
            f'slots_{business_id}_{service_id}'
            f'_{jy}_{jm}_{jd}'
        )
        cached = cache.get(cache_key)
        if cached:
            return cached

        # بررسی وجود کسب‌وکار و خدمت
        try:
            business = Business.objects.only('id', 'status').get(
                id=business_id,
                status=Business.Status.APPROVED,
            )
            service = Service.objects.only(
                'id', 'is_active', 'duration', 'business_id',
            ).get(
                id=service_id,
                business_id=business_id,
                is_active=True,
            )
        except (Business.DoesNotExist, Service.DoesNotExist):
            return []

        # پیدا کردن ServiceSchedule برای تاریخ جلالی
        date_key = f'{jy}/{jm:02d}/{jd:02d}'
        try:
            schedule = ServiceSchedule.objects.only(
                'id', 'work_start', 'work_end', 'slot_duration', 'breaks',
            ).get(
                business_id=business_id,
                service_id=service_id,
                date_key=date_key,
            )
        except ServiceSchedule.DoesNotExist:
            return []

        if not schedule.work_start or not schedule.work_end:
            return []

        # ۱. تولید اسلات‌های اولیه
        slots = SlotService._generate_time_slots(
            work_start=schedule.work_start,
            work_end=schedule.work_end,
            slot_duration=schedule.slot_duration or 30,
            service_duration=service.duration,
        )

        # ۲. حذف اسلات‌هایی که با استراحت تداخل دارند
        if schedule.breaks:
            slots = SlotService._filter_break_conflicts(
                slots,
                schedule.breaks,
                service.duration,
            )

        # ۳. دریافت نوبت‌های رزرو شده
        booked_qs = Appointment.objects.filter(
            business_id=business_id,
            service_id=service_id,
            jy=jy,
            jm=jm,
            jd=jd,
            status__in=[
                Appointment.Status.RESERVED,
            ],
        )

        booked_times = set(
            booked_qs.values_list('time_slot', flat=True)
        )

        # ۴. حذف اسلات‌های رزرو شده
        slots = SlotService._filter_booked_slots(
            slots,
            booked_times,
            service.duration,
        )

        # ۵. حذف اسلات‌های گذشته (اگر امروز است)
        today = jdatetime.date.today()
        if jy == today.year and jm == today.jmonth and jd == today.jday:
            # ✅ استفاده از timezone-aware
            from django.utils import timezone as dj_timezone
            now_tehran = dj_timezone.now().astimezone()
            current_time = now_tehran.time()

            # حداقل ۳۰ دقیقه از الان
            min_datetime = (
                datetime.combine(date.today(), current_time)
                + timedelta(minutes=30)
            )
            min_time = min_datetime.time()

            slots = [s for s in slots if s['start_time'] >= min_time]
            
        # فرمت‌دهی خروجی
        result = []
        for slot in slots:
            result.append({
                'id': f'{jy}{jm:02d}{jd:02d}_{slot["start_time"].strftime("%H%M")}',
                'jy': jy,
                'jm': jm,
                'jd': jd,
                'date_key': date_key,
                'start_time': slot['start_time'].strftime('%H:%M'),
                'end_time': slot['end_time'].strftime('%H:%M'),
                'is_available': True,
                'display_time': slot['start_time'].strftime('%H:%M'),
            })

        # Cache کردن نتیجه
        cache.set(cache_key, result, timeout=SlotService.CACHE_TIMEOUT)
        return result

    # ═══════════════════════════════════════════════
    #   دریافت روزهای دارای اسلات آزاد
    # ═══════════════════════════════════════════════

    @staticmethod
    def get_available_dates(
        business_id: int,
        service_id: int,
        days_ahead: int = 30,
    ) -> List[Dict]:
        """
        دریافت روزهای دارای اسلات آزاد برای N روز آینده
        با تاریخ جلالی
        """
        try:
            Business.objects.only('id', 'status').get(
                id=business_id,
                status=Business.Status.APPROVED,
            )
            Service.objects.only('id', 'is_active', 'business_id').get(
                id=service_id,
                business_id=business_id,
                is_active=True,
            )
        except (Business.DoesNotExist, Service.DoesNotExist):
            return []

        available_dates = []
        today = jdatetime.date.today()

        for i in range(days_ahead):
            target = today + jdatetime.timedelta(days=i)

            slots = SlotService.get_available_slots(
                business_id=business_id,
                service_id=service_id,
                jy=target.year,
                jm=target.month,
                jd=target.day,
            )

            if slots:
                # محاسبه روز هفته
                gregorian_date = target.togregorian()
                py_weekday = gregorian_date.weekday()
                persian_weekday = (py_weekday + 2) % 7
                weekday_names = [
                    'شنبه', 'یکشنبه', 'دوشنبه',
                    'سه‌شنبه', 'چهارشنبه', 'پنجشنبه', 'جمعه',
                ]

                available_dates.append({
                    'jy': target.year,
                    'jm': target.month,
                    'jd': target.day,
                    'date_key': f'{target.year}/{target.month:02d}/{target.day:02d}',
                    'day_of_week': persian_weekday,
                    'weekday_name': weekday_names[persian_weekday],
                    'available_slots_count': len(slots),
                    'is_today': i == 0,
                    'is_friday': persian_weekday == 6,
                })

        return available_dates

    # ═══════════════════════════════════════════════
    #   متدهای کمکی
    # ═══════════════════════════════════════════════

    @staticmethod
    def _generate_time_slots(
        work_start: time,
        work_end: time,
        slot_duration: int,
        service_duration: int,
    ) -> List[Dict]:
        """تولید اسلات‌های زمانی بر اساس مدت هر نوبت"""
        slots = []
        start_dt = datetime.combine(date.today(), work_start)
        end_dt = datetime.combine(date.today(), work_end)

        current = start_dt
        while current + timedelta(minutes=service_duration) <= end_dt:
            slot_end = current + timedelta(minutes=service_duration)
            slots.append({
                'start_time': current.time(),
                'end_time': slot_end.time(),
            })
            current += timedelta(minutes=slot_duration)

        return slots

    @staticmethod
    def _filter_break_conflicts(
        slots: List[Dict],
        breaks: list,
        service_duration: int,
    ) -> List[Dict]:
        """حذف اسلات‌هایی که با استراحت‌ها تداخل دارند"""
        if not breaks:
            return slots

        filtered = []
        for slot in slots:
            slot_start = datetime.combine(date.today(), slot['start_time'])
            slot_end = datetime.combine(date.today(), slot['end_time'])

            has_conflict = False
            for brk in breaks:
                try:
                    brk_start_str = brk.get('start', '')
                    brk_end_str = brk.get('end', '')
                    if not brk_start_str or not brk_end_str:
                        continue

                    brk_start_dt = datetime.combine(
                        date.today(),
                        datetime.strptime(brk_start_str, '%H:%M').time(),
                    )
                    brk_end_dt = datetime.combine(
                        date.today(),
                        datetime.strptime(brk_end_str, '%H:%M').time(),
                    )

                    if slot_start < brk_end_dt and slot_end > brk_start_dt:
                        has_conflict = True
                        break
                except (ValueError, KeyError):
                    continue

            if not has_conflict:
                filtered.append(slot)

        return filtered

    @staticmethod
    def _filter_booked_slots(
        slots: List[Dict],
        booked_times: set,
        service_duration: int,
    ) -> List[Dict]:
        """حذف اسلات‌هایی که قبلاً رزرو شده‌اند"""
        if not booked_times:
            return slots

        filtered = []
        for slot in slots:
            slot_start = datetime.combine(date.today(), slot['start_time'])
            slot_end = datetime.combine(date.today(), slot['end_time'])

            has_conflict = False
            for booked_time in booked_times:
                try:
                    booked_dt = datetime.combine(date.today(), booked_time)
                    booked_end = booked_dt + timedelta(minutes=service_duration)

                    if slot_start < booked_end and slot_end > booked_dt:
                        has_conflict = True
                        break
                except (TypeError, ValueError):
                    continue

            if not has_conflict:
                filtered.append(slot)

        return filtered