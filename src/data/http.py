from __future__ import annotations

import os
import ssl

import httpx
import truststore


def ssl_context() -> ssl.SSLContext:
    return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)


def browser_headers() -> dict[str, str]:
    """One ordinary browser identity, plus the contact address used for public filings."""
    contact = os.getenv("SEC_USER_AGENT", "Epilith/0.1 (research)").strip() or "Epilith/0.1 (research)"
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 "
            + contact
        ),
        "Accept": "text/html,application/pdf,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }


def client(headers: dict[str, str], timeout: float) -> httpx.Client:
    return httpx.Client(
        timeout=timeout,
        headers=headers,
        follow_redirects=True,
        verify=ssl_context(),
    )
