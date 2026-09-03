from fastapi.testclient import TestClient

from pgaibot.app import app


def test_health() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_twiml_endpoint_returns_xml() -> None:
    client = TestClient(app)

    response = client.post("/twiml/spike-test")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")
    assert "spike-test" in response.text


def test_twilio_status_echoes_form() -> None:
    client = TestClient(app)

    response = client.post(
        "/twilio/status/spike-test",
        data={"CallSid": "CA123", "CallStatus": "completed"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "run_id": "spike-test",
        "received": {"CallSid": "CA123", "CallStatus": "completed"},
    }
