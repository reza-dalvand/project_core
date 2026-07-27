"""
Slot Service - محاسبه اسلات‌های آزاد بر اساس برنامه کاری
✅ بهینه‌شده: استفاده از values_list و set operations
"""
from datetime import datetime, timedelta, date, time
from typing import List, Dict, Optional
from django.db.models import Q
from django.core.cache import cache

from apps.bookings.models import Schedule, ScheduleBreak, TimeSlot, Appointment
from apps.businesses.models import Service, Employee, Business


class SlotService:
    """سرویس محاسبه اسلات‌های زمانی آزاد"""

    @staticmethod
    def get_available_slots(
        business_id: int,
        service_id: int,
        target_date: date,
        employee_id: Optional[int] = None,
    ) -> List[Dict]:
        """
        دریافت تمام اسلات‌های آزاد برای یک تاریخ خاص

        الگوریتم:
        1. برنامه کاری روز مورد نظر را پیدا کن
        2. اسلات‌ها را بر اساس start_time، end_time و slot_duration تولید کن
        3. بازه‌های استراحت را حذف کن
        4. نوبت‌های رزرو شده را حذف کن
        5. اسلات‌های گذشته را حذف کن
        """
        # ✅ استفاده از cache برای کاهش کوئری‌های تکراری
        cache_key = f'slots_{business_id}_{service_id}_{target_date}_{employee_id}'
        cached_slots = cache.get(cache_key)
        if cached_slots:
            return cached_slots

        # بررسی وجود کسب‌وکار و خدمت با only() برای کاهش overhead
        try:
            business = Business.objects.only('id', 'status').get(
                id=business_id,
                status='approved'
            )
            service = Service.objects.only(
                'id', 'is_active', 'duration_minutes', 'business_id'
            ).get(
                id=service_id,
                business_id=business_id,
                is_active=True
            )
        except (Business.DoesNotExist, Service.DoesNotExist):
            return []

        # دریافت روز هفته (0=شنبه تا 6=جمعه)
        py_weekday = target_date.weekday()  # 0=Mon, 6=Sun
        persian_weekday = (py_weekday + 2) % 7

        # پیدا کردن برنامه کاری
        try:
            schedule = Schedule.objects.only(
                'id', 'start_time', 'end_time', 'slot_duration'
            ).get(
                business_id=business_id,
                service_id=service_id,
                weekday=persian_weekday,
                is_working=True
            )
        except Schedule.DoesNotExist:
            return []

        if not schedule.start_time or not schedule.end_time:
            return []

        # تولید اسلات‌های اولیه
        slot_duration = schedule.slot_duration or 30
        slots = SlotService._generate_time_slots(
            start_time=schedule.start_time,
            end_time=schedule.end_time,
            duration_minutes=slot_duration,
            service_duration=service.duration_minutes,
        )

        # دریافت بازه‌های استراحت با values() برای کاهش overhead
        breaks = list(
            ScheduleBreak.objects.filter(schedule_id=schedule.id)
            .values_list('start_time', 'end_time')
        )

        # حذف اسلات‌هایی که با استراحت تداخل دارند
        slots = SlotService._filter_break_conflicts(
            slots, breaks, service.duration_minutes
        )

        # ✅ دریافت نوبت‌های رزرو شده با values_list
        booked_appointments_qs = Appointment.objects.filter(
            business_id=business_id,
            service_id=service_id,
            date=target_date,
            status__in=[
                Appointment.Status.RESERVED,
                Appointment.Status.CONFIRMED,
                Appointment.Status.IN_PROGRESS,
            ]
        )

        if employee_id:
            booked_appointments_qs = booked_appointments_qs.filter(
                Q(employee_id=employee_id) | Q(employee__isnull=True)
            )

        # ✅ استفاده از values_list برای کاهش overhead
        booked_times_list = list(
            booked_appointments_qs.values_list('time', flat=True)
        )

        # ✅ استفاده از set operations برای سرعت بیشتر
        booked_times_set = set()
        for booked_time in booked_times_list:
            booked_start = datetime.combine(date.today(), booked_time)
            booked_end = booked_start + timedelta(minutes=service.duration_minutes)
            booked_times_set.add((booked_start.time(), booked_end.time()))

        # حذف اسلات‌های رزرو شده
        slots = SlotService._filter_booked_slots(
            slots, booked_times_set, service.duration_minutes
        )

        # حذف اسلات‌های گذشته (اگر تاریخ امروز است)
        today = date.today()
        if target_date == today:
            now = datetime.now().time()
            min_time = (
                datetime.combine(today, now) + timedelta(minutes=30)
            ).time()
            slots = [s for s in slots if s['start_time'] >= min_time]

        # فرمت‌دهی خروجی
        result = []
        for slot in slots:
            result.append({
                'id': f"{target_date.strftime('%Y%m%d')}_{slot['start_time'].strftime('%H%M')}",
                'date': target_date.isoformat(),
                'start_time': slot['start_time'].strftime('%H:%M'),
                'end_time': slot['end_time'].strftime('%H:%M'),
                'is_available': True,
                'display_time': slot['start_time'].strftime('%H:%M'),
            })

        # ✅ Cache کردن نتیجه برای 5 دقیقه
        cache.set(cache_key, result, timeout=300)

        return result

    @staticmethod
    def _generate_time_slots(
        start_time: time,
        end_time: time,
        duration_minutes: int,
        service_duration: int,
    ) -> List[Dict]:
        """تولید اسلات‌های زمانی بر اساس مدت هر نوبت"""
        slots = []
        start_dt = datetime.combine(date.today(), start_time)
        end_dt = datetime.combine(date.today(), end_time)

        current = start_dt
        while current + timedelta(minutes=service_duration) <= end_dt:
            slot_end = current + timedelta(minutes=service_duration)
            slots.append({
                'start_time': current.time(),
                'end_time': slot_end.time(),
            })
            current += timedelta(minutes=duration_minutes)

        return slots

    @staticmethod
    def _filter_break_conflicts(
        slots: List[Dict],
        breaks: List[tuple],  # ✅ تغییر به tuple به جای object
        service_duration: int,
    ) -> List[Dict]:
        """حذف اسلات‌هایی که با بازه‌های استراحت تداخل دارند"""
        if not breaks:
            return slots

        filtered = []
        for slot in slots:
            slot_start = datetime.combine(date.today(), slot['start_time'])
            slot_end = datetime.combine(date.today(), slot['end_time'])
            has_conflict = False

            for brk_start, brk_end in breaks:  # ✅ استفاده از tuple
                brk_start_dt = datetime.combine(date.today(), brk_start)
                brk_end_dt = datetime.combine(date.today(), brk_end)

                if slot_start < brk_end_dt and slot_end > brk_start_dt:
                    has_conflict = True
                    break

            if not has_conflict:
                filtered.append(slot)

        return filtered

    @staticmethod
    def _filter_booked_slots(
        slots: List[Dict],
        booked_times: set,  # ✅ تغییر به set به جای queryset
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

            for booked_start, booked_end in booked_times:
                booked_start_dt = datetime.combine(date.today(), booked_start)
                booked_end_dt = datetime.combine(date.today(), booked_end)

                if slot_start < booked_end_dt and slot_end > booked_start_dt:
                    has_conflict = True
                    break

            if not has_conflict:
                filtered.append(slot)

        return filtered

    @staticmethod
    def get_available_dates(
        business_id: int,
        service_id: int,
        days_ahead: int = 30,
    ) -> List[Dict]:
        """
        دریافت روزهای دارای اسلات آزاد برای ۳۰ روز آینده
        """
        try:
            business = Business.objects.only('id', 'status').get(
                id=business_id,
                status='approved'
            )
            service = Service.objects.only('id', 'is_active', 'business_id').get(
                id=service_id,
                business_id=business_id,
                is_active=True
            )
        except (Business.DoesNotExist, Service.DoesNotExist):
            return []

        available_dates = []
        today = date.today()

        for i in range(days_ahead):
            target_date = today + timedelta(days=i)
            slots = SlotService.get_available_slots(
                business_id, service_id, target_date
            )

            if slots:
                import jdatetime
                j_date = jdatetime.date.fromgregorian(date=target_date)

                py_weekday = target_date.weekday()
                persian_weekday = (py_weekday + 2) % 7
                weekday_names = [
                    'شنبه', 'یکشنبه', 'دوشنبه',
                    'سه‌شنبه', 'چهارشنبه', 'پنجشنبه', 'جمعه'
                ]

                available_dates.append({
                    'jy': j_date.year,
                    'jm': j_date.month,
                    'jd': j_date.day,
                    'day_of_week': persian_weekday,
                    'weekday_name': weekday_names[persian_weekday],
                    'date': target_date.isoformat(),
                    'available_slots_count': len(slots),
                    'is_today': i == 0,
                    'is_friday': persian_weekday == 6,
                })

        return available_dates