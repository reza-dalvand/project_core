"""
فرم‌های اپ landing
"""
from django import forms


class ContactForm(forms.Form):
    """فرم تماس با ما"""
    full_name = forms.CharField(
        max_length=100,
        required=True,
        label='نام و نام خانوادگی',
    )
    phone = forms.CharField(
        max_length=20,
        required=True,
        label='شماره تماس',
    )
    email = forms.EmailField(
        required=False,
        label='ایمیل',
    )
    subject = forms.CharField(
        max_length=200,
        required=True,
        label='موضوع',
    )
    message = forms.CharField(
        widget=forms.Textarea,
        required=True,
        label='پیام',
    )

    def clean_phone(self):
        """پاکسازی شماره تماس"""
        phone = self.cleaned_data['phone']
        # تبدیل ارقام فارسی/عربی به انگلیسی
        phone = (
            phone
            .translate(str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789'))
            .translate(str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789'))
        )
        # حذف کاراکترهای اضافی
        phone = ''.join(c for c in phone if c.isdigit() or c == '+')
        return phone