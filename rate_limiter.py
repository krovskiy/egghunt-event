from functools import wraps
from collections import defaultdict
import time
from flask import jsonify, request


class RateLimiter:
    """
    In-memory rate limiter using sliding window approach.
    Tracks requests per key (user_id or IP) and enforces limits.
    """

    def __init__(self):
        self.requests = defaultdict(list)  

    def is_allowed(self, key: str, limit: int, window: int = 60) -> bool:
        """
        Check if a request is allowed within the rate limit.

        Args:
            key: Unique identifier (user_id or IP address)
            limit: Max requests allowed in window
            window: Time window in seconds (default 60)

        Returns:
            True if request is allowed, False if rate limit exceeded
        """
        now = time.time()
        cutoff = now - window

        self.requests[key] = [ts for ts in self.requests[key] if ts > cutoff]

        if len(self.requests[key]) >= limit:
            return False

        self.requests[key].append(now)
        return True

    def get_remaining(self, key: str, limit: int, window: int = 60) -> int:
        """Get remaining requests in current window."""
        now = time.time()
        cutoff = now - window
        self.requests[key] = [ts for ts in self.requests[key] if ts > cutoff]
        return max(0, limit - len(self.requests[key]))

    def cleanup(self, max_age: int = 3600) -> None:
        """
        Remove old entries to prevent unbounded memory growth.
        Call periodically (e.g., once per hour).

        Args:
            max_age: Seconds; entries older than this are removed
        """
        now = time.time()
        cutoff = now - max_age

        for key in list(self.requests.keys()):
            self.requests[key] = [ts for ts in self.requests[key] if ts > cutoff]
            if not self.requests[key]:
                del self.requests[key]

    def clear(self) -> None:
        """Emergency reset of all limits."""
        self.requests.clear()


# Global instance
_rate_limiter = RateLimiter()


def rate_limit(limit: int, window: int = 60, per_user: bool = True):
    """
    Decorator to rate limit an endpoint.

    Args:
        limit: Max requests allowed in time window
        window: Time window in seconds (default 60 = 1 minute)
        per_user: If True, limit per authenticated user ID; if False, limit per IP

    Example:
        @app.route("/api/create_egg", methods=["POST"])
        @rate_limit(limit=5)  # 5 requests per minute per user
        def create_egg():
            ...
    """

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if per_user:
                # Try to get authenticated user
                from backend import get_current_user
                allowed, user_data = get_current_user(request)
                key = user_data["id"] if allowed and user_data else request.remote_addr
            else:
                key = request.remote_addr

            if not _rate_limiter.is_allowed(key, limit, window):
                remaining = _rate_limiter.get_remaining(key, limit, window)
                return (
                    jsonify(
                        {
                            "error": "Rate limit exceeded",
                            "limit": limit,
                            "window": window,
                            "remaining": remaining,
                        }
                    ),
                    429,
                )

            return f(*args, **kwargs)

        return wrapper

    return decorator


def get_rate_limiter():
    """Get the global rate limiter instance for manual control."""
    return _rate_limiter