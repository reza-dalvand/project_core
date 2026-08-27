"""
Kavenegar SMS Provider
مستندات: https://kavenegar.com/rest.html

متدهای کاوه‌نگار:
- verify_lookup: فقط برای پترن‌های احراز هویت (مثل کد تایید)
- sms_send: ارسال پیام ساده (برای اطلاع‌رسانی مثل رزرو)
- sms_sendarray: ارسال گروهی (برای تبلیغات)
"""
import json
import logging
from typing import List, Optional
from .base import AbstractSmsProvider, SmsResult, BulkSmsResult

logger = logging.getLogger(__name__)


class KavenegarSmsProvider(AbstractSmsProvider):
    """
    ارسال پیامک از طریق کاوه‌نگار
    """
    DEFAULT_TIMEOUT = 20

    def __init__(self, api_key: str, timeout: int = None):
        if not api_key:
            raise ValueError('KAVENEGAR_API_KEY تنظیم نشده است')
        self._api_key = api_key
        self._timeout = timeout or self.DEFAULT_TIMEOUT
        self._api = None

    @property
    def api(self):
        """Lazy init برای KavenegarAPI"""
        if self._api is None:
            try:
                from kavenegar import KavenegarAPI
                self._api = KavenegarAPI(self._api_key, timeout=self._timeout)
            except ImportError:
                raise ImportError(
                    'پکیج kavenegar نصب نیست. '
                    'نصب کنید: pip install kavenegar'
                )
        return self._api

    # ═══════════════════════════════════════════════
    #   ارسال کد تایید یکبار مصرف (احراز هویت)
    # ═══════════════════════════════════════════════
    def send_otp(self, phone: str, template_name: str, token: str) -> SmsResult:
        """
        ارسال کد تایید یکبار مصرف از طریق پترن احراز هویت
        فقط برای لاگین/ثبت‌نام
        """
        phone = self.validate_phone(phone)

        try:
            params = {
                'receptor': phone,
                'template': template_name,
                'token': token,
                'type': 'sms',
            }
            response = self.api.verify_lookup(params)
            entry = response['entries']

            return SmsResult(
                success=True,
                message_id=str(entry.get('messageid', '')),
                cost=entry.get('cost', 0),
            )
        except Exception as e:
            logger.error(f"Kavenegar OTP error → {phone}: {e}")
            return SmsResult(
                success=False,
                error_message=str(e),
            )

    # ═══════════════════════════════════════════════
    #   ارسال پیامک قالبی (پترن احراز هویت)
    # ═══════════════════════════════════════════════
    def send_pattern(self, phone: str, template_name: str, **kwargs) -> SmsResult:
        """
        ارسال پیامک قالبی از طریق پترن احراز هویت
        فقط برای پترن‌های احراز هویت
        """
        phone = self.validate_phone(phone)

        try:
            params = {
                'receptor': phone,
                'template': template_name,
                **kwargs,
            }
            response = self.api.verify_lookup(params)
            entry = response['entries']

            return SmsResult(
                success=True,
                message_id=str(entry.get('messageid', '')),
                cost=entry.get('cost', 0),
            )
        except Exception as e:
            logger.error(
                f"Kavenegar pattern error → {phone}, "
                f"template={template_name}: {e}"
            )
            return SmsResult(
                success=False,
                error_message=str(e),
            )

    # ═══════════════════════════════════════════════
    #   ارسال پیامک ساده (اطلاع‌رسانی مثل رزرو)
    # ═══════════════════════════════════════════════
    def send(self, phone: str, message: str, sender: str = '') -> SmsResult:
        """
        ارسال پیامک ساده (برای اطلاع‌رسانی مثل رزرو)
        """
        phone = self.validate_phone(phone)

        try:
            params = {
                'receptor': phone,
                'message': message,
            }
            if sender:
                params['sender'] = sender

            response = self.api.sms_send(params)
            entry = response['entries'][0]

            return SmsResult(
                success=True,
                message_id=str(entry.get('messageid', '')),
                cost=entry.get('cost', 0),
            )
        except Exception as e:
            logger.error(f"Kavenegar send error → {phone}: {e}")
            return SmsResult(
                success=False,
                error_message=str(e),
            )

    # ═══════════════════════════════════════════════
    #   ارسال گروهی (تبلیغات)
    # ═══════════════════════════════════════════════
    def send_bulk(
        self,
        recipients: List[str],
        messages: List[str],
        senders: List[str] = None,
    ) -> BulkSmsResult:
        """
        ارسال گروهی پیامک (برای تبلیغات)
        """
        if not recipients:
            return BulkSmsResult(
                success=False,
                error_message='لیست دریافت‌کنندگان خالی است',
            )

        # اعتبارسنجی شماره‌ها
        valid_recipients = []
        for phone in recipients:
            try:
                valid_recipients.append(self.validate_phone(phone))
            except ValueError as e:
                logger.warning(f"Invalid phone in bulk send: {e}")

        if not valid_recipients:
            return BulkSmsResult(
                success=False,
                error_message='هیچ شماره معتبری یافت نشد',
            )

        try:
            params = {
                'receptor': json.dumps(valid_recipients),
                'message': json.dumps(messages),
            }
            if senders:
                params['sender'] = json.dumps(senders)

            response = self.api.sms_sendarray(params)

            total_sent = 0
            total_cost = 0
            message_ids = []

            for entry in response.get('entries', []):
                if entry.get('messageid'):
                    total_sent += 1
                    message_ids.append(str(entry.get('messageid')))
                    total_cost += entry.get('cost', 0)

            return BulkSmsResult(
                success=True,
                total_sent=total_sent,
                total_failed=len(valid_recipients) - total_sent,
                total_cost=total_cost,
                message_ids=message_ids,
            )
        except Exception as e:
            logger.error(f"Kavenegar bulk send error: {e}")
            return BulkSmsResult(
                success=False,
                error_message=str(e),
            )

    # ═══════════════════════════════════════════════
    #   دریافت اعتبار
    # ═══════════════════════════════════════════════
    def get_credit(self) -> int:
        """دریافت اعتبار باقیمانده"""
        try:
            response = self.api.account_info()
            return response.get('remaincredit', 0)
        except Exception as e:
            logger.error(f"Kavenegar credit error: {e}")
            return 0