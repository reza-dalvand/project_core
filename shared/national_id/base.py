"""
Abstract National ID Verifier
الگوی Strategy Pattern برای استعلام کد ملی
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class VerificationResult:
    """نتیجه استعلام کد ملی"""
    success: bool
    verified_name: str = ''
    national_id: str = ''
    error_message: str = ''
    error_code: str = ''


class AbstractNationalIdVerifier(ABC):
    """
    کلاس پایه انتزاعی برای استعلام کد ملی
    """

    @abstractmethod
    def verify(
        self,
        national_id: str,
        phone: str,
        full_name: Optional[str] = None,
    ) -> VerificationResult:
        """
        استعلام تطبیق کد ملی با شماره موبایل
        """
        ...

    def validate_national_id(self, national_id: str) -> str:
        """اعتبارسنجی کد ملی ایران"""
        national_id = national_id.strip()
        national_id = national_id.translate(
            str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
        )

        if len(national_id) != 10:
            raise ValueError('کد ملی باید دقیقاً ۱۰ رقم باشد')

        if len(set(national_id)) == 1:
            raise ValueError('کد ملی معتبر نیست')

        check = int(national_id[9])
        total = sum(
            int(national_id[i]) * (10 - i) for i in range(9)
        )
        remainder = total % 11

        if remainder < 2:
            if check != remainder:
                raise ValueError('کد ملی معتبر نیست')
        else:
            if check != (11 - remainder):
                raise ValueError('کد ملی معتبر نیست')

        return national_id

    def normalize_phone_for_shahkar(self, phone: str) -> str:
        """تبدیل 09... به 989... برای شاهکار"""
        phone = phone.strip()
        if phone.startswith('0'):
            return '98' + phone[1:]
        return phone