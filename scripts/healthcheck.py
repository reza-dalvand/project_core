#!/usr/bin/env python
"""
اسکریپت بررسی سلامت بک‌اند — فاز ۶
توسط Docker و CI/CD استفاده می‌شود
"""
import sys
import os
import urllib.request
import json


def check_health(url=None, timeout=5):
    """
    بررسی سلامت سرویس با فراخوانی اندپوینت نسخه اپ
    این اندپوینت بدون احراز هویت در دسترس است
    """
    # ✅ اگر URL داده نشد، از متغیر محیطی BACKEND_PORT استفاده کن (پیش‌فرض 8000)
    if url is None:
        port = os.environ.get('BACKEND_PORT', '8000')
        url = f'http://localhost:{port}/api/v1/config/app-version/'

    try:
        response = urllib.request.urlopen(url, timeout=timeout)
        if response.status == 200:
            data = json.loads(response.read().decode())
            if data.get('success'):
                print(f'✅ Backend is healthy on port {port}')
                return True
        print(f'❌ Unexpected status: {response.status}')
        return False
    except Exception as e:
        print(f'❌ Health check failed: {e}')
        return False


if __name__ == '__main__':
    url = sys.argv[1] if len(sys.argv) > 1 else None
    if url:
        healthy = check_health(url)
    else:
        healthy = check_health()
    sys.exit(0 if healthy else 1)