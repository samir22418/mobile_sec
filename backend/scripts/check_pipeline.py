import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import load_settings
from app.main import create_app
from app.models import RiskAssessment, TelemetryPayload


def run_pipeline():
    print("Testing AEGIS Pipeline...")
    import os
    os.environ["AEGIS_ACCEPTED_ENROLLMENT_TOKENS"] = "test-token"
    os.environ["AEGIS_ANALYST_TOKENS"] = "test-analyst"
    
    settings = load_settings()
    app = create_app(settings)
    client = TestClient(app)

    print("1. Injecting test telemetry payload...")
    from tests.conftest import sample_payload, suspicious_app
    payload = sample_payload(
        payload_id="pipeline-test-payload-001",
        device_id="test-device-pipeline",
        scan_id=12345,
        apps=[suspicious_app()],
    )
    
    headers = {"Authorization": "Bearer test-token"}
    response = client.post("/api/v1/telemetry", json=payload, headers=headers)
    if response.status_code != 202:
        print(f"FAILED: Ingestion returned {response.status_code}")
        print(f"Reason: {response.json()}")
        return

    print("2. Ingestion successful. Checking database for Risk Assessment...")
    session = app.state.session_factory()
    try:
        # Since we are using process_inline=True for tests, processing is synchronous
        record = session.scalar(select(TelemetryPayload).where(TelemetryPayload.payload_id == "pipeline-test-payload-001"))
        if not record:
            print("FAILED: Payload record not found in DB.")
            return
            
        print(f"   Status: {record.processing_status}")
        
        risk = session.scalar(select(RiskAssessment).where(RiskAssessment.payload_id == "pipeline-test-payload-001"))
        if risk:
            print(f"3. Risk Assessment completed! Score: {risk.risk_score}/100")
            print("   Risk factors were evaluated.")
        else:
            print("FAILED: Risk Assessment not generated.")
            return

        print("4. Testing API Retrieval...")
        analyst_headers = {"Authorization": "Bearer test-analyst"}
        latest_risk = client.get("/api/v1/devices/test-device-pipeline/latest-risk", headers=analyst_headers)
        if latest_risk.status_code == 200:
            print(f"   API confirmed latest risk: {latest_risk.json()['risk_score']}")
            print("PIPELINE VALIDATION SUCCESSFUL!")
        else:
            print("FAILED: Could not retrieve latest risk from API.")

    finally:
        session.close()

if __name__ == "__main__":
    run_pipeline()
