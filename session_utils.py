import streamlit as st


def initialize_session_state():
    if "analyzed_df" not in st.session_state:
        st.session_state.analyzed_df = None
    if "current_app_id" not in st.session_state:
        st.session_state.current_app_id = ""
