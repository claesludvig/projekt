#!/usr/bin/env python3
"""Testar om mapi/v2/reports faktiskt gar att anropa direkt med httpx (utan
webblasare/cookies) - skulle gora hela scrapern enklare och snabbare an att
kora Playwright i produktion."""

import httpx

BASE = "https://research.sebgroup.com"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


def call(path: str) -> None:
    url = f"{BASE}{path}"
    print(f"\n--- GET {url} ---")
    try:
        r = httpx.get(url, headers=HEADERS, timeout=20.0)
        print(f"status={r.status_code}")
        print(r.text[:2500])
    except Exception as e:
        print(f"FEL: {e}")


def main() -> None:
    call("/mapi/v2/reports?nbrows=10")
    call("/mapi/v2/reports?nbrows=5&reporttype=Fed%20policy")
    call("/mapi/v2/reports?nbrows=5&reporttype=FX%20Daily")
    call("/mapi/reports/types/freetext")


if __name__ == "__main__":
    main()
