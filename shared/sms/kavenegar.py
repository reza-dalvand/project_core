"""
Kavenegar SMS Provider
مستندات: https://kavenegar.com/rest.html

متدهای کاوه‌نگار:
- sms_send: ارسال پیام ساده
- verify_lookup: ارسال پترن احراز هویت
- sms_sendarray: ارسال گروهی
"""
import json
import logging
from typing import List

from .base import AbstractSmsProvider, SmsResult, BulkSmsResult

logger = logging.getLogger(__name__)


class KavenegarSmsProvider(AbstractSmsProvider):
    """ارسال پیامک از طریق کاوه‌نگار"""

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
                self._api = KavenegarAPI(self._api_key)
            except ImportError:
                raise ImportError(
                    'پکیج kavenegar نصب نیست. '
                    'نصب کنید: pip install kavenegar'
                )
        return self._api

    # ═══════════════════════════════════════════════
    #   ارسال کد تایید
    # ═══════════════════════════════════════════════
    # ═══════════════════════════════════════════════
    #   ارسال کد تایید
    # ═══════════════════════════════════════════════
    def send_otp(self, phone: str, token: str, template_name: str = None) -> SmsResult:
        """
        ارسال پیامک کد تایید با استفاده از verify_lookup کاوه‌نگار
        ✅ FIX: parsing بهتر + fallback به sms_send + logging دقیق
        """
        from django.conf import settings

        phone = self.validate_phone(phone)

        if not template_name:
            template_name = getattr(settings, 'KAVENEGAR_OTP_TEMPLATE', 'otp_template')

        # ─── تلاش اول: verify_lookup (پترن) ───
        try:
            params = {
                'receptor': phone,
                'template': template_name,
                'token': token,
                'type': 'sms',
            }

            logger.info(
                f'Kavenegar verify_lookup request → phone={phone}, '
                f'template={template_name}'
            )

            response = self.api.verify_lookup(params)

            # ✅ FIX: لاگ response خام برای دیباگ
            logger.info(f'Kavenegar verify_lookup raw response: {response}')

            # ✅ FIX: parsing انعطاف‌پذیر — هم dict و هم list
            entry = None

            if isinstance(response, dict):
                entries = response.get('entries', [])
                if entries:
                    entry = entries[0]
                else:
                    # شاید response مستقیماً messageid دارد
                    if response.get('messageid'):
                        entry = response
            elif isinstance(response, list) and response:
                entry = response[0]

            if entry:
                message_id = str(entry.get('messageid', ''))
                cost = entry.get('cost', 0)
                logger.info(
                    f'Kavenegar verify_lookup SUCCESS → {phone}, '
                    f'messageid={message_id}, cost={cost}'
                )
                return SmsResult(
                    success=True,
                    message_id=message_id,
                    cost=cost,
                )

            # entries خالی بود — شاید return status موفقیت‌آمیز است
            if isinstance(response, dict):
                return_status = response.get('return', {})
                if isinstance(return_status, dict) and return_status.get('status') == 200:
                    logger.warning(
                        f'Kavenegar verify_lookup: entries خالی ولی status=200 → {phone}'
                    )
                    return SmsResult(success=True, message_id='', cost=0)

            logger.error(f'Kavenegar verify_lookup: response غیرمنتظره → {phone}: {response}')

        except Exception as e:
            error_str = str(e)
            logger.warning(
                f'Kavenegar verify_lookup exception → {phone}: {error_str}'
            )

            # ✅ FIX: اگر خطای 404 (template not found) بود، fallback به sms_send
            if '404' in error_str or 'نامشخص' in error_str:
                logger.info(
                    f'Kavenegar: template "{template_name}" یافت نشد. '
                    f'Fallback به sms_send ساده → {phone}'
                )
                return self._send_otp_fallback(phone, token)

            # سایر خطاها هم fallback
            logger.warning(f'Kavenegar: fallback به sms_send → {phone}')
            return self._send_otp_fallback(phone, token)

        # اگر هیچ entry پیدا نشد، fallback
        logger.warning(f'Kavenegar: بدون entry — fallback → {phone}')
        return self._send_otp_fallback(phone, token)
    

    def _send_otp_fallback(self, phone: str, token: str) -> SmsResult:
        """
        ✅ NEW: Fallback — ارسال کد تایید به صورت پیام ساده
        وقتی verify_lookup کار نکند (template نیست، خطا دارد، ...)
        """
        try:
            message = (
                f'کد تایید بیو کلاب: {token}\n'
                f'این کد را با کسی به اشتراک نگذارید.'
            )
            return self.send(phone=phone, message=message)
        except Exception as e:
            logger.error(f'Kavenegar fallback sms_send error → {phone}: {e}')
            return SmsResult(
                success=False,
                error_message=str(e),
            )

    # ═══════════════════════════════════════════════
    #   ارسال پیام ساده
    # ═══════════════════════════════════════════════
    def send(self, phone: str, message: str, sender: str = '') -> SmsResult:
        """ارسال پیامک ساده"""
        phone = self.validate_phone(phone)

        try:
            params = {
                'receptor': phone,
                'message': message,
            }

            if sender:
                params['sender'] = sender

            response = self.api.sms_send(params)
            entries = response.get('entries', [])

            if not entries:
                return SmsResult(
                    success=False,
                    error_message='پاسخ خالی از کاوه‌نگار دریافت شد',
                )

            entry = entries[0]

            return SmsResult(
                success=True,
                message_id=str(entry.get('messageid', '')),
                cost=entry.get('cost', 0),
            )
        except Exception as e:
            logger.error(f'Kavenegar send error → {phone}: {e}')
            return SmsResult(
                success=False,
                error_message=str(e),
            )

    # ═══════════════════════════════════════════════
    #   ارسال با قالب / پترن
    # ═══════════════════════════════════════════════
    def send_pattern(self, phone: str, template_name: str, **variables) -> SmsResult:
        """
        ارسال از طریق پترن کاوه‌نگار
        معمولاً برای پترن‌های احراز هویت استفاده می‌شود.
        """
        phone = self.validate_phone(phone)

        try:
            params = {
                'receptor': phone,
                'template': template_name,
            }

            for key, value in (variables or {}).items():
                if key in {'token', 'token2', 'token3'}:
                    params[key] = value

            response = self.api.verify_lookup(params)
            entries = response.get('entries', [])

            if not entries:
                return SmsResult(
                    success=False,
                    error_message='پاسخ خالی از کاوه‌نگار دریافت شد',
                )

            entry = entries[0]

            return SmsResult(
                success=True,
                message_id=str(entry.get('messageid', '')),
                cost=entry.get('cost', 0),
            )
        except Exception as e:
            logger.error(f'Kavenegar send_pattern error → {phone}: {e}')
            return SmsResult(
                success=False,
                error_message=str(e),
            )

    # ═══════════════════════════════════════════════
    #   ارسال گروهی
    # ═══════════════════════════════════════════════
    def send_bulk(
        self,
        recipients: List[str],
        messages: List[str],
        senders: List[str] = None,
    ) -> BulkSmsResult:
        """ارسال گروهی پیامک"""
        if not recipients:
            return BulkSmsResult(
                success=False,
                error_message='لیست دریافت‌کنندگان خالی است',
            )

        valid_recipients = []
        for phone in recipients:
            try:
                valid_recipients.append(self.validate_phone(phone))
            except ValueError as e:
                logger.warning(f'Invalid phone in bulk send: {e}')

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
            logger.error(f'Kavenegar bulk send error: {e}')
            return BulkSmsResult(
                success=False,
                error_message=str(e),
            )

    # ═══════════════════════════════════════════════
    #   اعتبار
    # ═══════════════════════════════════════════════
    def get_credit(self) -> int:
        """دریافت اعتبار باقیمانده"""
        try:
            response = self.api.account_info()
            return response.get('remaincredit', 0)
        except Exception as e:
            logger.error(f'Kavenegar credit error: {e}')
            return 0