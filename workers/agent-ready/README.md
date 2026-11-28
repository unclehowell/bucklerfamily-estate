# agent-ready Worker — production asset source

**Status: live Worker patched on 28 November 2026.**

The deployed Worker `agent-ready` now fetches the e-book supplement from:

`https://raw.githubusercontent.com/unclehowell/bucklerfamily-estate/main/web/ebooks/supplement/cedwyn-supplement-2026-10-25.pdf`

The successor file is byte-identical to the former source (blob SHA `955b1547ec5208341876402b5e432b417a41e7bf`; 461,679 bytes).

All four deployed Worker parts were retained (`footer.js`, `index.js`, `registry.txt`, `webmcp.txt`) and the existing `GARDEN_STORE` service binding was preserved. The change did not alter routes, cron, secrets or KV/D1 state.

This entry documents the live URL change. It does not represent a full rebuild of the surrounding asset registry or a broader Worker refactor.

Source: Cloudflare Worker multipart export/settings read-back and GitHub blob comparison checked 28 November 2026.
