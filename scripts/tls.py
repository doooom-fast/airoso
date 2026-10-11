"""HTTPS trust for the engine's live fetches. Certificate verification is never turned off here.

Why this exists (2026-10-11, Windows): Python's default ``urllib`` context hands OpenSSL every
certificate in BOTH Windows stores, Trusted Root and Intermediate ("CA"), as one flat list of
trust anchors. This machine's Intermediate store still holds Let's Encrypt's 2020 cross-certificate
"ISRG Root X2, issued by ISRG Root X1", which expired 2025-09-15. overpass-api.de's chain runs
leaf -> YE2 -> Root YE -> ISRG Root X2 -> ISRG Root X1, and the server sends a valid 2026
cross-certificate for that last link. OpenSSL looks in its trusted list first, finds only the
expired copy, and fails with "certificate has expired". curl asks Windows itself to verify
(Schannel/CryptoAPI), gets the valid path, and succeeds.

``truststore`` (PyPA, the same library pip uses for its own downloads) does what curl does: it
hands verification to the operating system's verifier. When it isn't installed,
:func:`https_context` returns ``None`` and ``urlopen(..., context=None)`` behaves exactly as it
always has, so a machine without it (the Mac) is unchanged.
"""
from __future__ import annotations

import ssl


def https_context() -> ssl.SSLContext | None:
    """An OS-verified TLS context for ``urllib.request.urlopen(context=...)``, or ``None``
    (urllib's own default) when ``truststore`` isn't installed. Always verifies hostname + chain."""
    try:
        import truststore
    except ImportError:
        return None
    return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
