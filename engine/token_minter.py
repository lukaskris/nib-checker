"""Mint Cloudflare Turnstile tokens on oss.go.id via injected implicit widget.

Chrome+CDP gets detected (api.js refuses to init), so backend is camoufox
(patched Firefox). Token rules (verified): hostname-bound, single-use, short-lived.
"""
import asyncio
import os

from camoufox.async_api import AsyncCamoufox

OSS_PAGE = "https://oss.go.id/id"
SITEKEY = "0x4AAAAAAB6dVZCgIaP5qKs3"

INJECT = """
(() => {
    window.__tok = null;
    const d = document.createElement('div');
    d.className = 'cf-turnstile';
    d.dataset.sitekey = %KEY%;
    d.dataset.callback = '__onTok';
    window.__onTok = t => { window.__tok = t; };
    d.style.cssText = 'position:fixed;bottom:10px;right:10px;z-index:2147483647';
    document.body.appendChild(d);
    const s = document.createElement('script');
    s.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js';
    document.head.appendChild(s);
})();
""".replace("%KEY%", repr(SITEKEY))


async def mint_token(headless: bool = True, timeout_s: int = 120) -> str:
    proxy = None
    if os.environ.get("https_proxy") or os.environ.get("HTTPS_PROXY"):
        proxy = {"server": os.environ.get("https_proxy") or os.environ["HTTPS_PROXY"]}
    async with AsyncCamoufox(headless=headless, humanize=True, proxy=proxy) as browser:
        page = await browser.new_page()
        await page.goto(OSS_PAGE, wait_until="domcontentloaded", timeout=60000)
        await page.evaluate(INJECT)
        for i in range(timeout_s):
            state = await page.evaluate(
                """() => ({
                    tok: window.__tok,
                    val: (() => { const x = document.querySelector('input[name=cf-turnstile-response]'); return x ? x.value : null; })(),
                    iframe: document.querySelectorAll('iframe[src*=challenges]').length,
                })"""
            )
            tok = state.get("tok") or (state.get("val") or None)
            if tok:
                return tok
            if i % 15 == 0:
                print(f"  mint: t={i}s iframe={state['iframe']}")
            await page.wait_for_timeout(1000)
        raise TimeoutError(f"token not minted in {timeout_s}s")


if __name__ == "__main__":
    tok = asyncio.run(mint_token())
    print("TOKEN_LEN", len(tok))
