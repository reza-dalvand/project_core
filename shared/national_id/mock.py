"""
Mock National ID Verifier برای محیط توسعه
"""
import logging
import random
from typing import Optional

from .base import AbstractNationalIdVerifier, VerificationResult

logger = logging.getLogger(__name__)


class MockNationalIdVerifier(AbstractNationalIdVerifier):
    """
    Verifier تقلبی برای توسعه
    کد ملی 0012345679 → همیشه موفق
    سایر: ۷۰٪ احتمال موفقیت
    """

    TEST_NATIONAL_ID = '0012345679'

    def verify(
        self,
        national_id: str,
        phone: str,
        full_name: Optional[str] = None,
    ) -> VerificationResult:
        national_id = self.validate_national_id(national_id)

        logger.info(
            f"🔍 [MOCK Shahkar] national_id={national_id}, phone={phone}"
        )

        # کد تست — همیشه موفق
        if national_id == self.TEST_NATIONAL_ID:
            return VerificationResult(
                success=True,
                verified_name='کاربر آزمایشی زیبانو',
                national_id=national_id,
            )

        # حالت عادی: ۷۰٪ موفقیت
        if random.random() < 0.7:
            return VerificationResult(
                success=True,
                verified_name=full_name or 'نام تایید شده از سامانه',
                national_id=national_id,
            )

        return VerificationResult(
            success=False,
            error_message='کد ملی با شماره موبایل تطابق ندارد',
            error_code='MISMATCH',
        )