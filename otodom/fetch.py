import requests as r

from otodom.constants import USER_AGENT


def fetch_listing_html(url: str) -> str:
    headers = {"User-Agent": USER_AGENT}
    resp = r.get(url, headers=headers)
    resp.raise_for_status()
    return resp.text
