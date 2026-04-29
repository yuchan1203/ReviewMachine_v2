"""
Session utilities are not required for the FastAPI-based frontend.
Provide a no-op initializer to preserve compatibility with any code
that still imports `initialize_session_state()` from this module.
"""

def initialize_session_state():
    # No-op for FastAPI deployment; session is managed client-side.
    return None
