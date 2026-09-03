"""
مسیرهای داشبورد مدیریت — فاز ۷ (نهایی)
"""
from django.urls import path
from .views import (
    auth,
    home,
    users,
    businesses,
    financial,
    content,
    support,
    settings,
)

app_name = 'dashboard'

urlpatterns = [
    # ─── احراز هویت ───
    path('login/', auth.login_view, name='login'),
    path('verify/', auth.verify_otp_view, name='verify_otp'),
    path('resend/', auth.resend_otp_view, name='resend_otp'),
    path('logout/', auth.logout_view, name='logout'),

    # ─── صفحه اصلی ───
    path('', home.home_view, name='home'),

    # ─── کاربران ───
    path('users/', users.users_list_view, name='users_list'),
    path('users/<int:user_id>/', users.user_detail_view, name='user_detail'),
    path('users/<int:user_id>/toggle/', users.user_toggle_active_view, name='user_toggle_active'),

    # ─── کسب‌وکارها ───
    path('businesses/', businesses.businesses_list_view, name='businesses_list'),
    path('businesses/<int:business_id>/', businesses.business_detail_view, name='business_detail'),
    path('businesses/<int:business_id>/approve/', businesses.business_approve_view, name='business_approve'),
    path('businesses/<int:business_id>/reject/', businesses.business_reject_view, name='business_reject'),
    path('businesses/<int:business_id>/toggle-vip/', businesses.business_toggle_vip_view, name='business_toggle_vip'),

    # ─── مالی ───
    path('financial/', financial.financial_index_view, name='financial'),
    path('financial/transactions/', financial.transactions_list_view, name='transactions_list'),
    path('financial/transactions/<int:transaction_id>/', financial.transaction_detail_view, name='transaction_detail'),
    path('financial/settlements/', financial.settlements_list_view, name='settlements_list'),
    path('financial/settlements/<int:settlement_id>/approve/', financial.settlement_approve_view, name='settlement_approve'),
    path('financial/settlements/<int:settlement_id>/reject/', financial.settlement_reject_view, name='settlement_reject'),

    # ─── محتوا ───
    path('content/', content.content_index_view, name='content'),
    path('content/explore/', content.explore_list_view, name='explore_list'),
    path('content/explore/<int:post_id>/toggle-pin/', content.explore_toggle_pin_view, name='explore_toggle_pin'),
    path('content/explore/<int:post_id>/delete/', content.explore_delete_view, name='explore_delete'),
    path('content/portfolios/', content.portfolios_list_view, name='portfolios_list'),
    path('content/portfolios/<int:portfolio_id>/delete/', content.portfolio_delete_view, name='portfolio_delete'),
    path('content/ads/model-requests/', content.model_requests_list_view, name='model_requests_list'),
    path('content/ads/model-requests/<int:request_id>/delete/', content.model_request_delete_view, name='model_request_delete'),
    path('content/ads/line-rentals/', content.line_rentals_list_view, name='line_rentals_list'),
    path('content/ads/line-rentals/<int:rental_id>/delete/', content.line_rental_delete_view, name='line_rental_delete'),
    path('content/price-lists/', content.price_lists_view, name='price_lists'),

    # ─── پشتیبانی ───
    path('support/', support.support_index_view, name='support'),
    path('support/tickets/', support.tickets_list_view, name='tickets_list'),
    path('support/tickets/<int:ticket_id>/', support.ticket_detail_view, name='ticket_detail'),
    path('support/messages/', support.messages_list_view, name='messages_list'),
    path('support/messages/<int:message_id>/', support.message_detail_view, name='message_detail'),
    path('support/notifications/', support.notifications_list_view, name='notifications_list'),
    path('support/sms-logs/', support.sms_logs_view, name='sms_logs'),

    # ─── تنظیمات ───
    path('settings/', settings.settings_index_view, name='settings'),
    path('settings/roles/', settings.roles_list_view, name='roles_list'),
    path('settings/roles/create/', settings.role_create_view, name='role_create'),
    path('settings/roles/<int:role_id>/edit/', settings.role_edit_view, name='role_edit'),
    path('settings/roles/<int:role_id>/delete/', settings.role_delete_view, name='role_delete'),
    path('settings/admins/', settings.admins_list_view, name='admins_list'),
    path('settings/admins/create/', settings.admin_create_view, name='admin_create'),
    path('settings/admins/<int:admin_id>/toggle/', settings.admin_toggle_active_view, name='admin_toggle_active'),
    path('settings/admins/<int:admin_id>/delete/', settings.admin_delete_view, name='admin_delete'),
    path('settings/system/', settings.system_settings_view, name='system_settings'),
    path('settings/sms/', settings.sms_templates_view, name='sms_templates'),
    path('settings/sms/<int:template_id>/edit/', settings.sms_template_edit_view, name='sms_template_edit'),
    path('settings/landing/', settings.landing_settings_view, name='landing_settings'),
]