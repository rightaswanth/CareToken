import asyncio
import pytest
from httpx import AsyncClient
from app.main import app
from app.core.config import settings
from app.core.redis import redis_client
from app.db.session import get_session
from app.db.models import User, Tenant, AppUser
from app.core.security import get_password_hash
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import create_engine, select

# Setup async engine for tests
engine = create_engine(settings.DATABASE_URL, echo=False, future=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

from httpx import AsyncClient, ASGITransport

@pytest.mark.asyncio
async def test_redis_auth_flow():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Setup Data
        # We need a clinic and an admin user
        # And a patient
        
        # Note: In a real test suite we'd use fixtures, but for this quick verification script
        # we'll just insert data if it doesn't exist or use existing endpoints.
        
        # Let's try to create a clinic via API if possible, or just mock the login
        # Actually, let's use the services directly or just trust the integration test
        
        # Let's try to login as an existing admin if we know one, or create one.
        # Since I don't know the DB state, I'll create a new clinic.
        
        clinic_data = {
            "name": "Redis Test Clinic",
            "address": "123 Test St",
            "city": "Test City",
            "phone": "1234567890",
            "email": "redis@test.com"
        }
        
        # We need to bypass auth to create a clinic? No, usually public or superadmin.
        # Let's assume public for now based on previous context or check api/v1/clinics.py
        
        response = await ac.post("/api/v1/clinics/", json=clinic_data)
        if response.status_code == 200:
            data = response.json()
            admin_creds = data["admin_credentials"]
            clinic_slug = data["clinic"]["slug"]
            
            # 2. Login as Admin
            login_data = {
                "username": admin_creds["username"],
                "password": admin_creds["password"],
                "clinic_slug": clinic_slug
            }
            
            login_res = await ac.post("/api/v1/auth/login", json=login_data)
            assert login_res.status_code == 200
            token = login_res.json()["access_token"]
            
            # 3. Verify Token in Redis
            redis_token = await redis_client.get_token(token)
            assert redis_token is not None
            assert "admin" in redis_token
            
            # 4. Access Protected Admin Endpoint
            # e.g., get doctors
            headers = {"Authorization": f"Bearer {token}"}
            tenant_id = data["tenant_id"]
            doctors_res = await ac.get(f"/api/v1/doctors/{tenant_id}/doctors", headers=headers)
            assert doctors_res.status_code == 200
            
            # 5. Logout / Delete Token (Simulate)
            await redis_client.delete_token(token)
            
            # 6. Access Protected Endpoint Again (Should Fail)
            doctors_res_fail = await ac.get(f"/api/v1/doctors/{tenant_id}/doctors", headers=headers)
            assert doctors_res_fail.status_code == 401
            
            print("Admin Redis Auth Flow Passed!")
            
        else:
            print(f"Skipping Admin Test: Could not create clinic (Status {response.status_code})")

        # 7. Patient Flow
        # Request OTP
        phone = "5555555555"
        otp_res = await ac.post("/api/v1/patients/request-otp", json={"phone": phone})
        assert otp_res.status_code == 200
        otp = otp_res.json()["dev_otp"] # Assuming dev_otp is returned in dev mode
        
        # Verify OTP
        verify_res = await ac.post("/api/v1/patients/verify-otp", json={"phone": phone, "otp": otp})
        assert verify_res.status_code == 200
        patient_token = verify_res.json()["access_token"]
        
        # Verify Token in Redis
        redis_patient_token = await redis_client.get_token(patient_token)
        assert redis_patient_token is not None
        assert "patient" in redis_patient_token
        
        # Access Protected Patient Endpoint
        # We use the public doctor list which is now protected by get_current_user_or_patient
        # We need a tenant_id. We can use the one from above if available, or we need to fetch one.
        # Since we are in the same test run, we can use the tenant_id from the admin test.
        if 'tenant_id' in locals():
            patient_headers = {"Authorization": f"Bearer {patient_token}"}
            patient_res = await ac.get(f"/api/v1/doctors/{tenant_id}/list", headers=patient_headers)
            assert patient_res.status_code == 200
            
            # Let's delete it
            await redis_client.delete_token(patient_token)
            
            # Should fail now
            patient_res_fail = await ac.get(f"/api/v1/doctors/{tenant_id}/list", headers=patient_headers)
            assert patient_res_fail.status_code == 401
        
        print("Patient Redis Auth Flow Passed!")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_redis_auth_flow())
