"""Google Play Integrity backend verification service.

Calls Google's decodeIntegrityToken API to resolve a REQUIRES_BACKEND_VERIFICATION
token into an authoritative MEETS_* or FAILS verdict.

When no API key / package name is configured the service returns a bypass verdict
(REQUIRES_BACKEND_VERIFICATION, nonce_valid=True) so the pipeline degrades
gracefully without raising an exception.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

_DECODE_URL = (
    "https://playintegrity.googleapis.com/v1/{package_name}:decodeIntegrityToken"
)


class PlayIntegrityError(Exception):
    """Raised when the Google API call fails or returns an unexpected structure."""


@dataclass
class PlayIntegrityVerdict:
    verdict: str
    nonce_valid: bool
    app_recognition: str | None = field(default=None)
    licensing_verdict: str | None = field(default=None)


class PlayIntegrityService:
    def __init__(
        self,
        api_key: str,
        package_name: str,
        *,
        timeout: int = 10,
    ) -> None:
        self._api_key = api_key
        self._package_name = package_name
        self._timeout = timeout

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key and self._package_name)

    def verify_token(
        self,
        integrity_token: str,
        expected_nonce: str,
    ) -> PlayIntegrityVerdict:
        """Verify *integrity_token* against Google's Play Integrity API.

        Returns a bypass verdict (REQUIRES_BACKEND_VERIFICATION) when not
        configured.  Raises :exc:`PlayIntegrityError` on network or API errors
        so callers can decide whether to fail the pipeline or log + continue.
        """
        if not self.is_configured:
            return PlayIntegrityVerdict(
                verdict="REQUIRES_BACKEND_VERIFICATION",
                nonce_valid=True,
            )

        url = (
            _DECODE_URL.format(package_name=self._package_name)
            + f"?key={self._api_key}"
        )
        body = json.dumps({"integrity_token": integrity_token}).encode()
        req = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode(errors="replace")
            raise PlayIntegrityError(
                f"Google Play Integrity API HTTP {exc.code}: {error_body}"
            ) from exc
        except OSError as exc:
            raise PlayIntegrityError(f"Network error: {exc}") from exc

        return _parse_decoded_payload(data, expected_nonce)


def _parse_decoded_payload(
    data: dict,
    expected_nonce: str,
) -> PlayIntegrityVerdict:
    payload = data.get("tokenPayloadExternal", {})

    request_details = payload.get("requestDetails", {})
    returned_nonce = request_details.get("nonce", "")
    nonce_valid = returned_nonce == expected_nonce

    device_integrity = payload.get("deviceIntegrity", {})
    device_verdicts = set(device_integrity.get("deviceRecognitionVerdict", []))

    if not nonce_valid:
        verdict = "FAILS"
    elif "MEETS_STRONG_INTEGRITY" in device_verdicts:
        verdict = "MEETS_STRONG_INTEGRITY"
    elif "MEETS_DEVICE_INTEGRITY" in device_verdicts:
        verdict = "MEETS_DEVICE_INTEGRITY"
    elif "MEETS_BASIC_INTEGRITY" in device_verdicts:
        verdict = "MEETS_BASIC_INTEGRITY"
    else:
        verdict = "FAILS"

    app_integrity = payload.get("appIntegrity", {})
    account_details = payload.get("accountDetails", {})

    return PlayIntegrityVerdict(
        verdict=verdict,
        nonce_valid=nonce_valid,
        app_recognition=app_integrity.get("appRecognitionVerdict"),
        licensing_verdict=account_details.get("appLicensingVerdict"),
    )
