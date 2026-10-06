"""OSS RBA public NIB API client."""
import httpx

API_URL = "https://api-prd.oss.go.id/v1/reg/public/nib"
# ponytail: static public key hardcoded in oss.go.id frontend bundle; fetch dynamically if they rotate it
USER_KEY = "846ee507525c6b00d18733e066bd5686"

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36"
)


class OssError(Exception):
    def __init__(self, status: int, body: str):
        super().__init__(f"HTTP {status}: {body[:200]}")
        self.status = status
        self.body = body


def check_nib(nib: str, turnstile_token: str, timeout: float = 30.0) -> dict:
    """POST public NIB lookup. Returns parsed JSON dict. Raises OssError on non-200."""
    headers = {
        "Accept": "*/*",
        "Content-Type": "application/json",
        "Origin": "https://oss.go.id",
        "Referer": "https://oss.go.id/",
        "User-Agent": UA,
        "user_key": USER_KEY,
        "cf-turnstile-response": turnstile_token,
    }
    r = httpx.post(API_URL, json={"dataNib": {"nib": nib}}, headers=headers, timeout=timeout)
    if r.status_code != 200:
        raise OssError(r.status_code, r.text)
    return r.json()
