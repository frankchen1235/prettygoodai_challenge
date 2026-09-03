from pgaibot.twiml import connectivity_twiml, media_stream_twiml


def test_connectivity_twiml_contains_expected_voice_response() -> None:
    body = connectivity_twiml("spike-test")

    assert body.startswith("<?xml")
    assert "<Response>" in body
    assert "<Say" in body
    assert "spike-test" in body
    assert "<Hangup" in body


def test_media_stream_twiml_contains_connect_stream() -> None:
    body = media_stream_twiml("stream-test", "wss://example.com/ws/twilio/stream-test")

    assert "<Connect>" in body
    assert '<Stream name="stream-test" url="wss://example.com/ws/twilio/stream-test" />' in body
    assert "<Hangup" in body
