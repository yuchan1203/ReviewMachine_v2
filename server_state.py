"""
Simple in-memory server state for storing uploaded, crawled and analyzed dataframes.
This is intentionally minimal and non-persistent; suitable for local development.
"""
import threading
import pandas as pd

_state_lock = threading.Lock()
_state = {
    # uploads: app_id -> DataFrame
    "uploads": {},
    # crawled: (app_id,count,mode,period) -> DataFrame
    "crawled": {},
    # analyzed: app_id -> DataFrame
    "analyzed": {},
    # runtime_info: app_id -> dict
    "runtime_info": {},
}


def save_upload(app_id, df: pd.DataFrame):
    with _state_lock:
        _state["uploads"][app_id] = df.copy()


def get_upload(app_id):
    with _state_lock:
        return _state["uploads"].get(app_id)


def save_crawled(key, df: pd.DataFrame):
    with _state_lock:
        _state["crawled"][key] = df.copy()


def get_crawled(key):
    with _state_lock:
        return _state["crawled"].get(key)


def save_analyzed(app_id, df: pd.DataFrame):
    with _state_lock:
        _state["analyzed"][app_id] = df.copy()


def get_analyzed(app_id):
    with _state_lock:
        return _state["analyzed"].get(app_id)


def save_runtime_info(app_id, info: dict):
    with _state_lock:
        _state["runtime_info"][app_id] = dict(info)


def get_runtime_info(app_id):
    with _state_lock:
        return _state["runtime_info"].get(app_id)
 