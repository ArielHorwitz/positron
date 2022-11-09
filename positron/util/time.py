"""Time utilities."""

from typing import Optional, Callable
import time
import contextlib


def ping() -> float:
    """Generate a time value to be later used by `pong`."""
    return time.perf_counter() * 1000


def pong(ping_: float) -> float:
    """Return the time delta in ms from a value given by `ping`."""
    return (time.perf_counter() * 1000) - ping_


@contextlib.contextmanager
def pingpong(
    *,
    logger: Optional[Callable[[str], None]] = None,
    log: str = "Pingpong",
    return_elapsed: Optional[Callable[[float], None]] = None,
):
    """A context manager to record the elapsed time of execution of a code block.

    Args:
        logger: Callback that takes a string with the pingpong result.
        log: Description to add to the logging callback.
        return_elapsed: Callback that takes a float of the pingpong result.

    <u>__Example usage:__</u>
    ```python
    with pingpong('Counting to a million', logger=print, return_elapsed=callback):
        count = 0
        for i in range(1_000_000):
            count += 1
    ```
    Will result in a console output: `'Counting to a million elapsed in: 1.234 ms'`

    And will call `callback` with an argument `1.234`.
    """
    p = ping()
    yield p
    elapsed = pong(p)
    if callable(logger):
        logger(f"{log} elapsed in: {elapsed:.3f} ms")
    if callable(return_elapsed):
        return_elapsed(elapsed)
