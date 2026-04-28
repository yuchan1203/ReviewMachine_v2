# A. 모듈 임포트
import streamlit as st

# B. 세션 상태 초기화 함수 정의
def initialize_session_state():
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
