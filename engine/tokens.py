"""Turnstile tokens for the OSS RBA public NIB API, via cf-bypass."""
from cf_bypass import TokenPool

OSS_PAGE = "https://oss.go.id/id"
SITEKEY = "0x4AAAAAAB6dVZCgIaP5qKs3"

_pool = TokenPool(SITEKEY, OSS_PAGE)

get_token = _pool.get
warm_next = _pool.warm_next
