from unittest.mock import patch, MagicMock
from messaging import send_email, send_sms, build_spot_message


def test_build_spot_message():
    spot = {"name": "T-Street", "parking_cost": "Free", "parking_notes": ""}
    conditions = {
        "wave_min": 2, "wave_max": 3,
        "condition_rating": "Fair",
        "tide_trend": "Rising",
        "wind_direction_type": "Offshore",
    }
    directions_url = "https://www.google.com/maps/dir/?api=1&destination=33.4,-117.6"
    subject, body = build_spot_message(spot, conditions, directions_url)
    assert "T-Street" in subject
    assert "2-3" in subject
    assert "Rising" in body
    assert "Offshore" in body
    assert "Free" in body
    assert directions_url in body


def test_send_email_calls_smtp():
    with patch("messaging.smtplib.SMTP_SSL") as mock_smtp_class:
        mock_smtp = MagicMock()
        mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_smtp)
        mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

        result = send_email(
            gmail_address="test@gmail.com",
            gmail_password="password",
            to_address="friend@gmail.com",
            subject="Surf Alert",
            body="Test body",
        )
        assert result is True


def test_send_sms_calls_smtp():
    with patch("messaging.smtplib.SMTP_SSL") as mock_smtp_class:
        mock_smtp = MagicMock()
        mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_smtp)
        mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

        result = send_sms(
            gmail_address="test@gmail.com",
            gmail_password="password",
            sms_gateway_address="9495551234@tmomail.net",
            body="Test SMS",
        )
        assert result is True
