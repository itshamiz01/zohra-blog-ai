"""
Zohra — SSRF Protection & Safe HTTP Client.

Validates that target URLs and all redirects never resolve to:
- localhost / loopback addresses
- private network ranges (RFC 1918)
- link-local addresses (RFC 3927, RFC 4291)
- cloud metadata services (169.254.169.254, metadata.google.internal, etc.)
- non-HTTP/HTTPS schemes (file://, ftp://, gopher://, etc.)
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from app.core.exceptions import ZohraError
from app.core.logging import get_logger

logger = get_logger("discovery.security.ssrf")


class SSRFProtectionError(ZohraError):
    """Raised when a URL attempts to access a forbidden or internal address."""

    def __init__(self, message: str, url: str = ""):
        super().__init__(f"SSRF blocked: {message} (url={url})", code="SSRF_FORBIDDEN")
        self.url = url


# Forbidden cloud metadata hostnames
FORBIDDEN_HOSTNAMES: set[str] = {
    "metadata.google.internal",
    "metadata.internal",
    "instance-data",
}

# Forbidden private/special IP networks
FORBIDDEN_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),  # Current network (only valid as source)
    ipaddress.ip_network("10.0.0.0/8"),  # RFC 1918 private
    ipaddress.ip_network("100.64.0.0/10"),  # Shared address space / CGNAT
    ipaddress.ip_network("127.0.0.0/8"),  # Loopback
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local / AWS & GCP metadata
    ipaddress.ip_network("172.16.0.0/12"),  # RFC 1918 private
    ipaddress.ip_network("192.0.0.0/24"),  # IETF protocol assignments
    ipaddress.ip_network("192.0.2.0/24"),  # TEST-NET-1
    ipaddress.ip_network("192.168.0.0/16"),  # RFC 1918 private
    ipaddress.ip_network("198.18.0.0/15"),  # Benchmark testing
    ipaddress.ip_network("198.51.100.0/24"),  # TEST-NET-2
    ipaddress.ip_network("203.0.113.0/24"),  # TEST-NET-3
    ipaddress.ip_network("224.0.0.0/4"),  # Multicast
    ipaddress.ip_network("240.0.0.0/4"),  # Reserved for future use
    ipaddress.ip_network("255.255.255.255/32"),  # Broadcast
    # IPv6
    ipaddress.ip_network("::1/128"),  # Loopback
    ipaddress.ip_network("::/128"),  # Unspecified
    ipaddress.ip_network("fc00::/7"),  # Unique local address (ULA)
    ipaddress.ip_network("fe80::/10"),  # Link-local
    ipaddress.ip_network("ff00::/8"),  # Multicast
]


def is_ip_allowed(ip_str: str) -> bool:
    """Check if an IP address string is public and not in forbidden private/link-local ranges."""
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False

    if (
        ip.is_loopback
        or ip.is_private
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    ):
        return False

    return all(ip not in network for network in FORBIDDEN_NETWORKS)


def validate_url_for_ssrf(url: str) -> str:
    """
    Validate a URL to ensure it does not target forbidden or internal endpoints.
    Resolves the domain and checks all resolved IP addresses.
    Returns the validated URL on success, raises SSRFProtectionError on failure.
    """
    if not url or not isinstance(url, str):
        raise SSRFProtectionError("Empty or invalid URL")

    url = url.strip()
    parsed = urlparse(url)

    # 1. Enforce scheme: only http and https
    if parsed.scheme.lower() not in {"http", "https"}:
        raise SSRFProtectionError(
            f"Disallowed URL scheme: '{parsed.scheme}'. Only http and https permitted", url
        )

    # 2. Hostname validation
    hostname = parsed.hostname
    if not hostname:
        raise SSRFProtectionError("Missing hostname in URL", url)

    hostname_lower = hostname.lower()

    if hostname_lower in FORBIDDEN_HOSTNAMES:
        raise SSRFProtectionError(f"Forbidden cloud metadata hostname: {hostname}", url)

    if hostname_lower in {"localhost", "localhost.localdomain"}:
        raise SSRFProtectionError("Direct localhost reference is forbidden", url)

    # 3. If hostname is directly an IP literal, validate immediately
    try:
        ip_direct = ipaddress.ip_address(hostname_lower)
        if not is_ip_allowed(str(ip_direct)):
            raise SSRFProtectionError(f"Forbidden IP address: {ip_direct}", url)
        return url
    except ValueError:
        # Not a direct IP, continue to DNS resolution check
        pass

    # 4. Resolve hostname via DNS to verify all destination IPs
    try:
        addr_info = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise SSRFProtectionError(f"DNS resolution failure for host '{hostname}': {e}", url) from e

    if not addr_info:
        raise SSRFProtectionError(f"No IP addresses resolved for '{hostname}'", url)

    for item in addr_info:
        sockaddr = item[4]
        ip_resolved = sockaddr[0]
        if not is_ip_allowed(ip_resolved):
            raise SSRFProtectionError(
                f"Resolved IP {ip_resolved} for host '{hostname}' falls within forbidden address space",
                url,
            )

    return url


class SSRFValidator:
    is_safe_ip = staticmethod(is_ip_allowed)

    @staticmethod
    def is_safe_url(url: str) -> bool:
        try:
            validate_url_for_ssrf(url)
            return True
        except SSRFProtectionError:
            return False
        except Exception:
            return False
