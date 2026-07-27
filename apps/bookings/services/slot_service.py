"""
Slot Service - محاسبه اسلات‌های آزاد بر اساس برنامه کاری
"""
from datetime import datetime, timedelta, date, time
from typing import List, Dict, Optional
from django.db.models import Q

from apps.businesses.models import Schedule, ScheduleBreak, Service, Employee
from apps.bookings.models import TimeSlot, Appointment


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
        from apps.businesses.models import Business

        # بررسی وجود کسب‌وکار
        try:
            business = Business.objects.get(id=business_id, status='approved')
        except Business.DoesNotExist:
            return []

        # بررسی وجود خدمت
        try:
            service = Service.objects.get(
                id=service_id,
                business=business,
                is_active=True
            )
        except Service.DoesNotExist:
            return []

        # دریافت روز هفته (0=شنبه تا 6=جمعه)
        # Python: 0=Monday ... 6=Sunday
        # Persian: 0=Saturday ... 6=Friday
        py_weekday = target_date.weekday()  # 0=Mon, 6=Sun
        # تبدیل: Sat=0, Sun=1, Mon=2, Tue=3, Wed=4, Thu=5, Fri=6
        persian_weekday = (py_weekday + 2) % 7

        # پیدا کردن برنامه کاری
        try:
            schedule = Schedule.objects.get(
                business=business,
                service=service,
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

        # دریافت بازه‌های استراحت
        breaks = list(ScheduleBreak.objects.filter(schedule=schedule))

        # حذف اسلات‌هایی که با استراحت تداخل دارند
        slots = SlotService._filter_break_conflicts(slots, breaks, service.duration_minutes)

        # دریافت نوبت‌های رزرو شده
        booked_appointments = Appointment.objects.filter(
            business=business,
            service=service,
            date=target_date,
            status__in=[
                Appointment.Status.RESERVED,
                Appointment.Status.CONFIRMED,
                Appointment.Status.IN_PROGRESS,
            ]
        )

        # اگر کارمند خاصی انتخاب شده، فقط نوبت‌های آن کارمند را فیلتر کن
        if employee_id:
            booked_appointments = booked_appointments.filter(
                Q(employee_id=employee_id) | Q(employee__isnull=True)
            )

        # حذف اسلات‌های رزرو شده
        slots = SlotService._filter_booked_slots(slots, booked_appointments, service.duration_minutes)

        # حذف اسلات‌های گذشته (اگر تاریخ امروز است)
        today = date.today()
        if target_date == today:
            now = datetime.now().time()
            # حداقل ۳۰ دقیقه قبل از زمان فعلی
            min_time = (datetime.combine(today, now) + timedelta(minutes=30)).time()
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

        # اسلات‌ها بر اساس duration_minutes تولید می‌شوند
        # اما هر اسلات باید حداقل service_duration دقیقه فضا داشته باشد
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
            breaks: List[ScheduleBreak],
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
            for brk in breaks:
                brk_start = datetime.combine(date.today(), brk.start_time)
                brk_end = datetime.combine(date.today(), brk.end_time)

                # تداخل: اسلات با استراحت همپوشانی دارد
                if slot_start < brk_end and slot_end > brk_start:
                    has_conflict = True
                    break

            if not has_conflict:
                filtered.append(slot)

        return filtered

    @staticmethod
    def _filter_booked_slots(
            slots: List[Dict],
            booked_appointments,
            service_duration: int,
    ) -> List[Dict]:
        """حذف اسلات‌هایی که قبلاً رزرو شده‌اند"""
        if not booked_appointments.exists():
            return slots

        # لیست زمان‌های رزرو شده
        booked_times = []
        for apt in booked_appointments:
            booked_start = datetime.combine(date.today(), apt.time)
            booked_end = booked_start + timedelta(minutes=service_duration)
            booked_times.append((booked_start, booked_end))

        filtered = []
        for slot in slots:
            slot_start = datetime.combine(date.today(), slot['start_time'])
            slot_end = datetime.combine(date.today(), slot['end_time'])

            has_conflict = False
            for booked_start, booked_end in booked_times:
                if slot_start < booked_end and slot_end > booked_start:
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
        from apps.businesses.models import Business

        try:
            business = Business.objects.get(id=business_id, status='approved')
            service = Service.objects.get(id=service_id, business=business, is_active=True)
        except (Business.DoesNotExist, Service.DoesNotExist):
            return []

        available_dates = []
        today = date.today()

        for i in range(days_ahead):
            target_date = today + timedelta(days=i)
            slots = SlotService.get_available_slots(business_id, service_id, target_date)

            if slots:
                # تبدیل به jalaali
                import jdatetime
                j_date = jdatetime.date.fromgregorian(date=target_date)

                # روز هفته فارسی
                py_weekday = target_date.weekday()
                persian_weekday = (py_weekday + 2) % 7
                weekday_names = ['شنبه', 'یکشنبه', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنجشنبه', 'جمعه']

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