from collections import defaultdict, deque
from time import monotonic


class SlidingWindowLimiter:
    def __init__(self, limit: int, window_seconds: float) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)

    def is_limited(self, key: str) -> bool:
        now = monotonic()
        events = self._events[key]
        while events and now - events[0] > self.window_seconds:
            events.popleft()
        return len(events) >= self.limit

    def hit(self, key: str) -> None:
        self._events[key].append(monotonic())

    def reset(self, key: str) -> None:
        self._events.pop(key, None)

    def reset_all(self) -> None:
        self._events.clear()


login_limiter = SlidingWindowLimiter(limit=5, window_seconds=15 * 60)
