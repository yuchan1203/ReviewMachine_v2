"""
Session utilities are not required for the FastAPI-based frontend.
Provide a no-op initializer to preserve compatibility with any code
that still imports `initialize_session_state()` from this module.
"""

def initialize_session_state():
<<<<<<< HEAD
    # No-op for FastAPI deployment; session is managed client-side.
    return None
=======
    if "analyzed_df" not in st.session_state:
        st.session_state.analyzed_df = None
    if "source_df" not in st.session_state:
        st.session_state.source_df = None
    if "source_is_analyzed" not in st.session_state:
        st.session_state.source_is_analyzed = False
    if "source_app_id" not in st.session_state:
        st.session_state.source_app_id = ""
    if "current_app_id" not in st.session_state:
        st.session_state.current_app_id = ""
    if "analysis_runtime_info" not in st.session_state:
        st.session_state.analysis_runtime_info = None
    if "hf_token" not in st.session_state:
        st.session_state.hf_token = ""
>>>>>>> b9b8b76aa51729b16ac6e463598c50f47734bdce
