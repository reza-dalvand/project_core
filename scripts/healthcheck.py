#!/usr/bin/env python
"""
اسکریپت بررسی سلامت بک‌اند — فاز ۶
توسط Docker و CI/CD استفاده می‌شود
"""
import sys
import urllib.request
import json


def check_health(url='http://localhost:8000/api/v1/config/app-version/', timeout=5):
    """
    بررسی سلامت سرویس با فراخوانی اندپوینت نسخه اپ
    این اندپوینت بدون احراز هویت در دسترس است
    """
    try:
        response = urllib.request.urlopen(url, timeout=timeout)
        if response.status == 200:
            data = json.loads(response.read().decode())
            if data.get('success'):
                print('✅ Backend is healthy')
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