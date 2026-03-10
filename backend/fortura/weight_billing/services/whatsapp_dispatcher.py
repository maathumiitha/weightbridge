import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from django.conf import settings


@dataclass
class WhatsAppDispatchResult:
    status: str
    message: str
    delivery_id: str = ""
    provider_response: str = ""


class WhatsAppDispatchService:
    """
    Offline-safe WhatsApp dispatcher.

    - If provider settings are missing, it returns QUEUED_VIRTUAL.
    - If provider settings exist, it attempts a real HTTP POST.
    """

    def __init__(self):
        self.api_url = getattr(settings, "WHATSAPP_API_URL", "").strip()
        self.api_token = getattr(settings, "WHATSAPP_API_TOKEN", "").strip()
        self.sender_id = getattr(settings, "WHATSAPP_SENDER_ID", "").strip()
        self.timeout_seconds = int(getattr(settings, "WHATSAPP_TIMEOUT_SECONDS", 8))

    @property
    def is_configured(self):
        return bool(self.api_url and self.api_token and self.sender_id)

    def send_slip(self, *, to_phone, pdf_url, slip_number, customer_name):
        message = f"Dear {customer_name}, your weighment slip {slip_number} is ready."
        payload = {
            "to": to_phone,
            "sender_id": self.sender_id,
            "message": message,
            "attachment_url": pdf_url,
            "attachment_name": f"{slip_number}.pdf",
        }

        if not self.is_configured:
            return WhatsAppDispatchResult(
                status="QUEUED_VIRTUAL",
                message="WhatsApp provider is not configured. Recorded as virtual queue.",
            )

        try:
            req = urllib.request.Request(
                self.api_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_token}",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                raw = resp.read().decode("utf-8", errors="ignore")
                return WhatsAppDispatchResult(
                    status="SENT",
                    message="WhatsApp message sent to provider.",
                    provider_response=raw,
                )
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            return WhatsAppDispatchResult(
                status="FAILED",
                message=f"Provider HTTP error: {exc.code}",
                provider_response=body,
            )
        except Exception as exc:
            return WhatsAppDispatchResult(
                status="FAILED",
                message=f"Provider connection error: {exc}",
            )
