import time
from collections import defaultdict

# In-memory storage: key -> list of timestamps
_ATTEMPTS = defaultdict(list)

def is_rate_limited(key: str, limit: int = 5, window_seconds: int = 300) -> bool:
    """
    Checks if a key has exceeded the limit within window_seconds.
    Returns True if rate limited, False otherwise.
    """
    now = time.time()
    attempts = _ATTEMPTS[key]
    
    # Prune old timestamps
    _ATTEMPTS[key] = [t for t in attempts if now - t < window_seconds]
    
    if len(_ATTEMPTS[key]) >= limit:
        return True
    
    return False

def record_attempt(key: str):
    """Records an attempt timestamp for the key."""
    _ATTEMPTS[key].append(time.time())

def clear_attempts(key: str):
    """Clears attempts for a key on successful action."""
    if key in _ATTEMPTS:
        del _ATTEMPTS[key]
