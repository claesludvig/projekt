#!/usr/bin/env python3
"""research.sebgroup.com/macro-ficc rendered "SEB Research / Loading..." for
a plain httpx GET - the real content loads client-side via JS. Tries a
headless browser instead and also logs any JSON network responses, since a
SPA usually calls a JSON API under the hood that would be a much more
robust integration point than scraping rendered HTML."""

import json

from playwright.sync_api import sync_playwright

URL = "https://research.sebgroup.com/macro-ficc"


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        json_responses = []

        def on_response(response):
            ct = response.headers.get("content-type", "")
            if "json" in ct and response.request.resource_type in ("xhr", "fetch"):
                try:
                    body = response.json()
                except Exception as e:
                    body = f"<could not parse JSON: {e}>"
                json_responses.append((response.request.method, response.url, response.status, body))

        page.on("response", on_response)

        print(f"Navigating to {URL} ...")
        page.goto(URL, wait_until="networkidle", timeout=45000)
        page.wait_for_timeout(3000)

        print(f"\nPage title: {page.title()}")
        print(f"\n=== JSON XHR/fetch responses seen ({len(json_responses)}) ===")
        for method, url, status, body in json_responses:
            print(f"\n--- {method} {status} {url} ---")
            text = json.dumps(body, ensure_ascii=False, indent=2) if not isinstance(body, str) else body
            print(text[:4000])

        # Also try each mapi endpoint directly with the browser's own request
        # context (carries whatever cookies/headers the page picked up), to
        # confirm they're independently fetchable without a full page load.
        print("\n=== Direct re-fetch of mapi endpoints via page.request ===")
        for ep in [
            "https://research.sebgroup.com/mapi/reports/fixed/latest",
            "https://research.sebgroup.com/mapi/v2/reports?nbrows=5&reporttype=Macro",
            "https://research.sebgroup.com/mapi/macroanalysts",
        ]:
            try:
                resp = page.request.get(ep, timeout=15000)
                print(f"\n--- GET {resp.status} {ep} ---")
                try:
                    print(json.dumps(resp.json(), ensure_ascii=False, indent=2)[:3000])
                except Exception:
                    print(resp.text()[:1000])
            except Exception as e:
                print(f"  FEL: {e}")

        print("\n=== Rendered body text (first 3000 chars) ===")
        body_text = page.inner_text("body")
        print(body_text[:3000])

        print("\n=== Links on rendered page (first 60) ===")
        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        seen = set()
        for h in hrefs:
            if h not in seen:
                seen.add(h)
                print(f"  {h}")
            if len(seen) >= 60:
                break

        browser.close()


if __name__ == "__main__":
    main()
