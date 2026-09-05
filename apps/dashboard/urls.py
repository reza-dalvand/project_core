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
    bulk,       
    export,        
    audit_log,  
    dashboard_search,  
    alerts, 
    bookings,     
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
    path('users/create/', users.user_create_view, name='user_create'),
    path('users/<int:user_id>/', users.user_detail_view, name='user_detail'),
    path('users/<int:user_id>/edit/', users.user_edit_view, name='user_edit'),
    path('users/<int:user_id>/toggle/', users.user_toggle_active_view, name='user_toggle_active'),
    path('users/<int:user_id>/delete/', users.user_delete_view, name='user_delete'),
    path('users/<int:user_id>/notify/', users.user_notify_view, name='user_notify'),

    # ─── کسب‌وکارها ───
    path('businesses/', businesses.businesses_list_view, name='businesses_list'),
    path('businesses/create/', businesses.business_create_view, name='business_create'),
    path('businesses/<int:business_id>/', businesses.business_detail_view, name='business_detail'),
    path('businesses/<int:business_id>/edit/', businesses.business_edit_view, name='business_edit'),
    path('businesses/<int:business_id>/delete/', businesses.business_delete_view, name='business_delete'),
    path('businesses/<int:business_id>/approve/', businesses.business_approve_view, name='business_approve'),
    path('businesses/<int:business_id>/reject/', businesses.business_reject_view, name='business_reject'),
    path('businesses/<int:business_id>/toggle-vip/', businesses.business_toggle_vip_view, name='business_toggle_vip'),
    path('businesses/<int:business_id>/reset-slug/', businesses.business_reset_slug_view, name='business_reset_slug'),
    path('businesses/<int:business_id>/gallery/<int:gallery_id>/delete/', businesses.business_gallery_delete_view, name='business_gallery_delete'),
    path('businesses/<int:business_id>/services/<int:service_id>/toggle/', businesses.business_service_toggle_view, name='business_service_toggle'),
    path('businesses/<int:business_id>/appointments/<int:appointment_id>/cancel/', businesses.business_appointment_cancel_view, name='business_appointment_cancel'),

    # ─── مالی ───
    path('financial/', financial.financial_index_view, name='financial'),
    path('financial/transactions/', financial.transactions_list_view, name='transactions_list'),
    path('financial/transactions/create/', financial.transaction_create_view, name='transaction_create'),
    path('financial/transactions/<int:transaction_id>/', financial.transaction_detail_view, name='transaction_detail'),
    path('financial/transactions/<int:transaction_id>/edit/', financial.transaction_edit_view, name='transaction_edit'),
    path('financial/settlements/', financial.settlements_list_view, name='settlements_list'),
    path('financial/settlements/create/', financial.settlement_create_view, name='settlement_create'),
    path('financial/settlements/<int:settlement_id>/edit/', financial.settlement_edit_view, name='settlement_edit'),
    path('financial/settlements/<int:settlement_id>/delete/', financial.settlement_delete_view, name='settlement_delete'),
    path('financial/settlements/<int:settlement_id>/approve/', financial.settlement_approve_view, name='settlement_approve'),
    path('financial/settlements/<int:settlement_id>/reject/', financial.settlement_reject_view, name='settlement_reject'),

    # ─── محتوا ───
    path('content/', content.content_index_view, name='content'),
    path('content/explore/', content.explore_list_view, name='explore_list'),
    path('content/explore/create/', content.explore_create_view, name='explore_create'),
    path('content/explore/<int:post_id>/edit/', content.explore_edit_view, name='explore_edit'),
    path('content/explore/<int:post_id>/toggle-pin/', content.explore_toggle_pin_view, name='explore_toggle_pin'),
    path('content/explore/<int:post_id>/delete/', content.explore_delete_view, name='explore_delete'),
    path('content/portfolios/', content.portfolios_list_view, name='portfolios_list'),
    path('content/portfolios/<int:portfolio_id>/edit/', content.portfolio_edit_view, name='portfolio_edit'),
    path('content/portfolios/<int:portfolio_id>/delete/', content.portfolio_delete_view, name='portfolio_delete'),
    path('content/ads/model-requests/', content.model_requests_list_view, name='model_requests_list'),
    path('content/ads/model-requests/<int:request_id>/edit/', content.model_request_edit_view, name='model_request_edit'),
    path('content/ads/model-requests/<int:request_id>/delete/', content.model_request_delete_view, name='model_request_delete'),
    path('content/ads/line-rentals/', content.line_rentals_list_view, name='line_rentals_list'),
    path('content/ads/line-rentals/<int:rental_id>/edit/', content.line_rental_edit_view, name='line_rental_edit'),
    path('content/ads/line-rentals/<int:rental_id>/delete/', content.line_rental_delete_view, name='line_rental_delete'),
    path('content/price-lists/', content.price_lists_view, name='price_lists'),
    path('content/price-lists/<int:price_list_id>/edit/', content.price_list_edit_view, name='price_list_edit'),

    # ─── پشتیبانی ───
    path('support/', support.support_index_view, name='support'),
    path('support/tickets/', support.tickets_list_view, name='tickets_list'),
    path('support/tickets/create/', support.ticket_create_view, name='ticket_create'),
    path('support/tickets/bulk-status/', support.ticket_bulk_status_view, name='ticket_bulk_status'),
    path('support/tickets/<int:ticket_id>/', support.ticket_detail_view, name='ticket_detail'),
    path('support/tickets/<int:ticket_id>/delete/', support.ticket_delete_view, name='ticket_delete'),
    path('support/messages/', support.messages_list_view, name='messages_list'),
    path('support/messages/<int:message_id>/', support.message_detail_view, name='message_detail'),
    path('support/messages/<int:message_id>/delete/', support.message_delete_view, name='message_delete'),
    path('support/notifications/', support.notifications_list_view, name='notifications_list'),
    path('support/notifications/create/', support.notification_create_view, name='notification_create'),
    path('support/notifications/<int:notification_id>/delete/', support.notification_delete_view, name='notification_delete'),
    path('support/sms-logs/', support.sms_logs_view, name='sms_logs'),
    path('support/sms/send/', support.sms_send_view, name='sms_send'),

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
    path('settings/sms/create/', settings.sms_template_create_view, name='sms_template_create'),
    path('settings/sms/<int:template_id>/edit/', settings.sms_template_edit_view, name='sms_template_edit'),
    path('settings/sms/<int:template_id>/delete/', settings.sms_template_delete_view, name='sms_template_delete'),
    path('settings/landing/', settings.landing_settings_view, name='landing_settings'),
    path('settings/landing-items/', settings.landing_items_view, name='landing_items'),

        # ─── نوبت‌ها و خدمات ───
    path('bookings/', bookings.bookings_index_view, name='bookings'),
    path('bookings/appointments/', bookings.appointments_list_view, name='appointments_list'),
    path('bookings/appointments/<int:appointment_id>/', bookings.appointment_detail_view, name='appointment_detail'),
    path('bookings/appointments/<int:appointment_id>/cancel/', bookings.appointment_cancel_view, name='appointment_cancel'),
    path('bookings/appointments/<int:appointment_id>/status/', bookings.appointment_status_change_view, name='appointment_status_change'),
    path('bookings/services/', bookings.services_list_view, name='services_list'),
    path('bookings/services/<int:service_id>/', bookings.service_detail_view, name='service_detail'),
    path('bookings/services/<int:service_id>/toggle/', bookings.service_toggle_active_view, name='service_toggle_active'),
    path('bookings/schedules/', bookings.schedules_list_view, name='schedules_list'),


    # ─── بهبودهای نهایی ───
    path('bulk/', bulk.bulk_view, name='bulk'),
    path('export/', export.export_view, name='export'),
    path('audit-log/', audit_log.audit_log_view, name='audit_log'),
    path('search/', dashboard_search.dashboard_search_view, name='dashboard_search'),
    path('alerts/', alerts.alerts_view, name='alerts'),
]