# agent-ready Worker — successor asset source candidate

**Status: migration candidate only. Not deployed.**

This Worker previously fetched the 25 October 2026 e-book supplement from the retiring `unclehowell/cedwyn` repository. The successor source is `unclehowell/bucklerfamily-estate/main/web/ebooks/supplement/cedwyn-supplement-2026-10-25.pdf`.

The old and successor Git tree entries have the same blob SHA `955b1547ec5208341876402b5e432b417a41e7bf` and size 461,679 bytes. The PDF itself is unchanged.

No schedule, route, binding, redirect mapping, cache rule or production Worker is changed by this source snapshot. Before deployment, compare the candidate against the live export, test PDF response headers and range requests, and preserve rollback.

Source: exact deployed Cloudflare Worker export checked on 28 November 2026; supplement file blob `955b1547ec5208341876402b5e432b417a41e7bf`.
