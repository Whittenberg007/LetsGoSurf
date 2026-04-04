import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def build_spot_message(spot: dict, conditions: dict, directions_url: str) -> tuple:
    """Build subject and body for a spot notification. Returns (subject, body)."""
    name = spot["name"]
    wave_min = conditions["wave_min"]
    wave_max = conditions["wave_max"]
    rating = conditions["condition_rating"]
    tide = conditions["tide_trend"]
    wind = conditions["wind_direction_type"]
    parking = spot.get("parking_cost", "Unknown")
    parking_notes = spot.get("parking_notes", "")

    subject = f"Surf Alert: {name} — {wave_min}-{wave_max}ft"

    body_lines = [
        f"{name} — {wave_min}-{wave_max}ft, {rating}",
        f"Tide: {tide} | Wind: {wind}",
        f"Parking: {parking}",
    ]
    if parking_notes:
        body_lines.append(f"  ({parking_notes})")
    body_lines.append(directions_url)

    return subject, "\n".join(body_lines)


def send_email(gmail_address: str, gmail_password: str, to_address: str, subject: str, body: str) -> bool:
    """Send an email via Gmail SMTP. Returns True on success, False on failure."""
    try:
        msg = MIMEMultipart()
        msg["From"] = gmail_address
        msg["To"] = to_address
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_address, gmail_password)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"    Email send failed: {e}")
        return False


def send_sms(gmail_address: str, gmail_password: str, sms_gateway_address: str, body: str) -> bool:
    """Send SMS via carrier email gateway. Returns True on success, False on failure."""
    try:
        msg = MIMEText(body)
        msg["From"] = gmail_address
        msg["To"] = sms_gateway_address

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_address, gmail_password)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"    SMS send failed: {e}")
        return False
