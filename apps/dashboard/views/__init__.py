# apps/dashboard/views/__init__.py
"""
✅ فاز ۱: تکمیل ایمپورت‌ها
ماژول‌های جدید (فاز ۸ و ۹) هم اکسپورت می‌شوند
"""
from .auth import (
    login_view,
    verify_otp_view,
    resend_otp_view,
    logout_view,
)
from .home import home_view
from .users import (
    users_list_view,
    user_detail_view,
    user_toggle_active_view,
)
from .businesses import (
    businesses_list_view,
    business_detail_view,
    business_approve_view,
    business_reject_view,
    business_toggle_vip_view,
)
from .financial import (
    financial_index_view,
    transactions_list_view,
    transaction_detail_view,
    settlements_list_view,
    settlement_approve_view,
    settlement_reject_view,
)
from .content import (
    content_index_view,
    explore_list_view,
    explore_toggle_pin_view,
    explore_delete_view,
    portfolios_list_view,
    portfolio_delete_view,
    model_requests_list_view,
    model_request_delete_view,
    line_rentals_list_view,
    line_rental_delete_view,
    price_lists_view,
)
from .support import (
    support_index_view,
    tickets_list_view,
    ticket_detail_view,
    messages_list_view,
    message_detail_view,
    notifications_list_view,
    sms_logs_view,
)
from .settings import (
    settings_index_view,
    roles_list_view,
    role_create_view,
    role_edit_view,
    role_delete_view,
    admins_list_view,
    admin_create_view,
    admin_toggle_active_view,
    admin_delete_view,
    system_settings_view,
    sms_templates_view,
    sms_template_edit_view,
    landing_settings_view,
)

# ✅ فاز ۱: ماژول‌های جدید (فاز ۸ و ۹)
from .bookings import (
    bookings_index_view,
    appointments_list_view,
    appointment_detail_view,
    appointment_cancel_view,
    appointment_status_change_view,
    services_list_view,
    service_detail_view,
    service_toggle_active_view,
    schedules_list_view,
)
from .bulk import bulk_view
from .export import export_view
from .audit_log import audit_log_view
from .dashboard_search import dashboard_search_view
from .alerts import alerts_view