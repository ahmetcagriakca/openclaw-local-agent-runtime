"""Plugin handler executor — D-118.

Dispatches events to plugin handlers with timeout and error isolation.
"""
import logging
import threading
from typing import Callable

logger = logging.getLogger("mcc.plugins.executor")

HANDLER_TIMEOUT_S = 30


def execute_handler(handler: Callable, event_data: dict, plugin_name: str) -> dict | None:
    """Execute a plugin handler with timeout and error isolation.

    Returns handler result dict or None on error/timeout.
    Never raises — all exceptions are caught and logged.
    """
    result = [None]
    error = [None]

    def _run():
        try:
            result[0] = handler(event_data)
        except Exception as e:
            error[0] = str(e)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    thread.join(timeout=HANDLER_TIMEOUT_S)

    if thread.is_alive():
        logger.error("Plugin %s handler timed out after %ds", plugin_name, HANDLER_TIMEOUT_S)
        return None

    if error[0]:
        logger.error("Plugin %s handler error: %s", plugin_name, error[0])
        return None

    return result[0]
