# apps/dashboard/services/audit_service.py
"""
سرویس لاگ حسابرسی (Audit Log) داشبورد ادمین
✅ فاز ۵: ثبت ساختاریافته عملیات‌های حساس

عملیات‌هایی که لاگ می‌شوند:
- تایید/رد کسب‌وکار
- ایجاد/حذف/غیرفعال‌سازی ادمین
- تغییر تنظیمات سیستم
- تایید/رد تسویه مالی
- تغییر وضعیت VIP
- تغییر نقش‌ها
"""
import json
import logging

logger = logging.getLogger('dashboard.audit')


class DashboardAuditService:
    """سرویس لاگ حسابرسی داشبورد"""

    # ─── دسته‌بندی عملیات‌ها ───
    class Action:
        # کسب‌وکارها
        BUSINESS_APPROVED = 'business.approved'
        BUSINESS_REJECTED = 'business.rejected'
        BUSINESS_VIP_TOGGLED = 'business.vip_toggled'

        # ادمین‌ها
        ADMIN_CREATED = 'admin.created'
        ADMIN_DELETED = 'admin.deleted'
        ADMIN_TOGGLED = 'admin.toggled'

        # نقش‌ها
        ROLE_CREATED = 'role.created'
        ROLE_EDITED = 'role.edited'
        ROLE_DELETED = 'role.deleted'

        # تنظیمات
        SYSTEM_SETTINGS_UPDATED = 'settings.system_updated'
        SMS_TEMPLATE_EDITED = 'settings.sms_template_edited'
        LANDING_SETTINGS_UPDATED = 'settings.landing_updated'

        # مالی
        SETTLEMENT_APPROVED = 'financial.settlement_approved'
        SETTLEMENT_REJECTED = 'financial.settlement_rejected'

        # احراز هویت
        ADMIN_LOGIN = 'auth.login'
        ADMIN_LOGOUT = 'auth.logout'

    @classmethod
    def log(
        cls,
        request,
        action: str,
        target_type: str = '',
        target_id=None,
        target_name: str = '',
        details: dict = None,
        severity: str = 'info',
    ):
        """
        ثبت یک رویداد حسابرسی

        Args:
            request: HttpRequest برای استخراج اطلاعات کاربر و IP
            action: شناسه عملیات (مثلاً 'business.approved')
            target_type: نوع آبجکت هدف (مثلاً 'business')
            target_id: شناسه آبجکت هدف
            target_name: نام نمایشی آبجکت هدف
            details: جزئیات اضافی
            severity: سطح اهمیت (info, warning, critical)
        """
        # استخراج اطلاعات ادمین
        admin_phone = request.session.get('dashboard_admin_phone', 'unknown')
        admin_role = request.session.get('dashboard_role', 'unknown')

        # استخراج IP
        client_ip = cls._get_client_ip(request)

        # ساخت لاگ ساختاریافته
        audit_entry = {
            'action': action,
            'admin_phone': admin_phone,
            'admin_role': admin_role,
            'client_ip': client_ip,
            'target_type': target_type,
            'target_id': str(target_id) if target_id else None,
            'target_name': target_name,
            'details': details or {},
            'severity': severity,
        }

        # انتخاب متد لاگ بر اساس شدت
        log_message = (
            f"[AUDIT] {action} | "
            f"admin={admin_phone}({admin_role}) | "
            f"ip={client_ip} | "
            f"target={target_type}:{target_id}({target_name}) | "
            f"details={json.dumps(details or {}, ensure_ascii=False)}"
        )

        if severity == 'critical':
            logger.critical(log_message)
        elif severity == 'warning':
            logger.warning(log_message)
        else:
            logger.info(log_message)

    @classmethod
    def _get_client_ip(cls, request):
        """استخراج IP کاربر"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')

    # ═══════════════════════════════════════════
    #   متدهای میان‌بر برای عملیات‌های رایج
    # ═══════════════════════════════════════════

    @classmethod
    def log_business_approved(cls, request, business):
        """لاگ تایید کسب‌وکار"""
        cls.log(
            request=request,
            action=cls.Action.BUSINESS_APPROVED,
            target_type='business',
            target_id=business.id,
            target_name=business.name,
            details={
                'owner_phone': business.owner.phone,
                'category': business.category.name,
                'city': business.city.name,
            },
        )

    @classmethod
    def log_business_rejected(cls, request, business, reason):
        """لاگ رد کسب‌وکار"""
        cls.log(
            request=request,
            action=cls.Action.BUSINESS_REJECTED,
            target_type='business',
            target_id=business.id,
            target_name=business.name,
            details={
                'owner_phone': business.owner.phone,
                'rejection_reason': reason,
            },
            severity='warning',
        )

    @classmethod
    def log_business_vip_toggled(cls, request, business, is_vip):
        """لاگ تغییر وضعیت VIP"""
        cls.log(
            request=request,
            action=cls.Action.BUSINESS_VIP_TOGGLED,
            target_type='business',
            target_id=business.id,
            target_name=business.name,
            details={'is_vip': is_vip},
        )

    @classmethod
    def log_admin_created(cls, request, admin_user, role_name=''):
        """لاگ ایجاد ادمین"""
        cls.log(
            request=request,
            action=cls.Action.ADMIN_CREATED,
            target_type='admin',
            target_id=admin_user.id,
            target_name=admin_user.user.phone,
            details={
                'role': role_name,
                'user_full_name': admin_user.user.full_name,
            },
            severity='warning',
        )

    @classmethod
    def log_admin_deleted(cls, request, admin_user):
        """لاگ حذف ادمین"""
        cls.log(
            request=request,
            action=cls.Action.ADMIN_DELETED,
            target_type='admin',
            target_id=admin_user.id,
            target_name=admin_user.user.phone,
            severity='critical',
        )

    @classmethod
    def log_admin_toggled(cls, request, admin_user, is_active):
        """لاغ تغییر وضعیت ادمین"""
        cls.log(
            request=request,
            action=cls.Action.ADMIN_TOGGLED,
            target_type='admin',
            target_id=admin_user.id,
            target_name=admin_user.user.phone,
            details={'is_active': is_active},
            severity='warning',
        )

    @classmethod
    def log_role_created(cls, request, role):
        """لاگ ایجاد نقش"""
        cls.log(
            request=request,
            action=cls.Action.ROLE_CREATED,
            target_type='role',
            target_id=role.id,
            target_name=role.get_name_display(),
            details={'permissions': role.permissions},
            severity='warning',
        )

    @classmethod
    def log_role_deleted(cls, request, role):
        """لاغ حذف نقش"""
        cls.log(
            request=request,
            action=cls.Action.ROLE_DELETED,
            target_type='role',
            target_id=role.id,
            target_name=role.get_name_display(),
            severity='critical',
        )

    @classmethod
    def log_system_settings_updated(cls, request, config):
        """لاغ بروزرسانی تنظیمات سیستم"""
        cls.log(
            request=request,
            action=cls.Action.SYSTEM_SETTINGS_UPDATED,
            target_type='settings',
            target_id=config.id if config else None,
            target_name='AppConfig',
            details={
                'latest_version': config.latest_version if config else '',
                'is_maintenance': config.is_maintenance if config else False,
            },
            severity='critical',
        )

    @classmethod
    def log_settlement_approved(cls, request, settlement):
        """لاغ تایید تسویه"""
        cls.log(
            request=request,
            action=cls.Action.SETTLEMENT_APPROVED,
            target_type='settlement',
            target_id=settlement.id,
            target_name=settlement.business.name,
            details={
                'amount': settlement.amount,
                'bank_sheba': settlement.bank_sheba,
            },
        )

    @classmethod
    def log_settlement_rejected(cls, request, settlement, reason):
        """لاغ رد تسویه"""
        cls.log(
            request=request,
            action=cls.Action.SETTLEMENT_REJECTED,
            target_type='settlement',
            target_id=settlement.id,
            target_name=settlement.business.name,
            details={
                'amount': settlement.amount,
                'rejection_reason': reason,
            },
            severity='warning',
        )

    @classmethod
    def log_landing_settings_updated(cls, request):
        """لاغ بروزرسانی تنظیمات لندینگ"""
        cls.log(
            request=request,
            action=cls.Action.LANDING_SETTINGS_UPDATED,
            target_type='settings',
            target_name='SiteSettings',
            severity='warning',
        )

    @classmethod
    def log_sms_template_edited(cls, request, template):
        """لاغ ویرایش قالب پیامک"""
        cls.log(
            request=request,
            action=cls.Action.SMS_TEMPLATE_EDITED,
            target_type='sms_template',
            target_id=template.id,
            target_name=template.name,
            details={'type': template.type},
            severity='warning',
        )