# apps/accounts/services/shahkar_service.py
# جایگزین با یک فایل ساده که فقط re-export می‌کند

"""
این فایل برای سازگاری با کدهای قدیمی حفظ شده است.
منبع اصلی: shared/national_id/
"""
from shared.national_id import get_national_id_verifier

# برای سازگاری با کدهای قدیمی
ShahkarService = get_national_id_verifier