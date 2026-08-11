"""
تست‌های نوبت‌ها — با تاریخ جلالی
"""
import pytest
from datetime import time
from django.urls import reverse
from rest_framework import status

from apps.appointments.models import Appointment


@pytest.mark.django_db
class TestCreateAppointment:
    def test_create_appointment_api(
        self, authenticated_customer_client, test_service
    ):
        url = reverse('appointments:create-appointment')
        response = authenticated_customer_client.post(url, {
            'service_id': test_service.id,
            'jy': 1405,
            'jm': 4,
            'jd': 22,
            'time_slot': '10:00',
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()['success'] is True

    def test_create_appointment_with_jalali_date(
        self, authenticated_customer_client, test_service
    ):
        url = reverse('appointments:create-appointment')
        response = authenticated_customer_client.post(url, {
            'service_id': test_service.id,
            'jy': 1405,
            'jm': 1,
            'jd': 1,
            'time_slot': '14:00',
        })
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()['data']
        assert data['jy'] == 1405
        assert data['jm'] == 1
        assert data['jd'] == 1


@pytest.mark.django_db
class TestCustomerAppointments:
    def test_my_appointments(
        self, authenticated_customer_client, customer_user,
        approved_business, test_service,
    ):
        Appointment.objects.create(
            business=approved_business,
            service=test_service,
            customer=customer_user,
            jy=1405, jm=4, jd=22,
            time_slot=time(10, 0),
            total_price=450000,
        )
        url = reverse('appointments:my-appointments')
        response = authenticated_customer_client.get(url)
        assert response.status_code == 200
        assert response.json()['success'] is True


@pytest.mark.django_db
class TestBusinessAppointments:
    def test_business_appointments(
        self, authenticated_business_client, customer_user,
        approved_business, test_service,
    ):
        Appointment.objects.create(
            business=approved_business,
            service=test_service,
            customer=customer_user,
            jy=1405, jm=4, jd=22,
            time_slot=time(10, 0),
            total_price=450000,
        )
        url = reverse('appointments:business-appointments')
        response = authenticated_business_client.get(url)
        assert response.status_code == 200


@pytest.mark.django_db
class TestCancelAppointment:
    def test_cancel_by_customer(
        self, authenticated_customer_client, test_appointment
    ):
        url = reverse('appointments:cancel-appointment', kwargs={'pk': test_appointment.id})
        response = authenticated_customer_client.post(url, {
            'reason_text': 'تغییر برنامه',
        })
        assert response.status_code == 200
        test_appointment.refresh_from_db()
        assert test_appointment.status == 'cancelled_by_customer'

    def test_cancel_by_business(
        self, authenticated_business_client, test_appointment
    ):
        url = reverse('appointments:cancel-by-business', kwargs={'pk': test_appointment.id})
        response = authenticated_business_client.post(url, {
            'reason_text': 'تعطیلی سالن',
        })
        assert response.status_code == 200
        test_appointment.refresh_from_db()
        assert test_appointment.status == 'cancelled_by_salon'


@pytest.mark.django_db
class TestVerifyCode:
    def test_verify_service_code(
        self, authenticated_business_client, test_appointment
    ):
        test_appointment.status = Appointment.Status.RESERVED
        test_appointment.save()
        code = test_appointment.verification_code

        url = reverse('appointments:verify-code', kwargs={'pk': test_appointment.id})
        response = authenticated_business_client.post(url, {'code': code})
        assert response.status_code == 200
        test_appointment.refresh_from_db()
        assert test_appointment.status == 'done'

    def test_verify_invalid_code(
        self, authenticated_business_client, test_appointment
    ):
        url = reverse('appointments:verify-code', kwargs={'pk': test_appointment.id})
        response = authenticated_business_client.post(url, {'code': '0000'})
        assert response.status_code == 400


@pytest.mark.django_db
class TestAppointmentStats:
    def test_stats(self, authenticated_business_client, test_appointment):
        url = reverse('appointments:business-stats')
        response = authenticated_business_client.get(url)
        assert response.status_code == 200
        data = response.json()['data']
        assert 'total' in data
        assert 'reserved' in data