import ipaddress

from fastapi import Request

from app.core.config import config


def _is_trusted_proxy(address: str) -> bool:
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return False
    return any(ip in network for network in config.TRUSTED_PROXY_NETWORKS)


def get_real_ip_address(request: Request) -> str:
    """
    Resolves the real client IP address for logging and rate limiting.

    Proxy headers are client-controlled, so they are only honoured when the direct peer is a
    configured trusted proxy (`TRUSTED_PROXIES`). `X-Forwarded-For` is then walked right-to-left,
    skipping trusted hops, so a client cannot spoof its address by sending its own header.
    """
    peer = request.client.host if request.client else None
    if not peer:
        return "unknown"
    if not _is_trusted_proxy(peer):
        return peer
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        hops = [hop.strip() for hop in x_forwarded_for.split(",") if hop.strip()]
        for hop in reversed(hops):
            if not _is_trusted_proxy(hop):
                return hop
    x_real_ip = request.headers.get("X-Real-IP")
    if x_real_ip:
        return x_real_ip.strip()
    return peer
