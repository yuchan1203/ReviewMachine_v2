import streamlit as st
import warnings
import os

warnings.filterwarnings("ignore")
from transformers import logging
logging.set_verbosity_error()
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

from review_pipeline import ReviewPipelineError, load_source_dataframe, run_sentiment_analysis
from session_utils import initialize_session_state
from ui_sections import (
    render_detail_section,
    render_file_info_section,
    render_sentiment_section,
    render_timeline_section,
)

# 세션 상태 초기화
initialize_session_state()

# 화면 설정
st.set_page_config(page_title="ReviewMachine v2", layout="wide")
st.title("📊 ReviewMachine v2: 앱 리뷰 감성 분석기")
st.markdown("구글 플레이 스토어의 앱 ID를 입력하여 실시간 리뷰 분석 결과를 확인하세요.")

# 사이드바 설정
with st.sidebar:
    st.header("입력 방식 선택")
    menu = st.radio("데이터 소스", ["실시간 크롤링", "CSV 파일 업로드"])

    if menu == "실시간 크롤링":
        app_id = st.text_input("앱 ID 입력", value="com.kakao.talk")
        review_count = st.slider("수집 개수", 10, 200, 50)
    else:
        uploaded_file = st.file_uploader("CSV 파일을 선택하세요", type=['csv'])
        if uploaded_file is not None:
            app_id = uploaded_file.name.split('.')[0]
        else:
            app_id = "uploaded_file"

    analyze_button = st.button("분석 시작")


if analyze_button:
    try:
        with st.spinner('데이터를 준비 중입니다...'):
            df, is_already_analyzed = load_source_dataframe(
                menu=menu,
                app_id=app_id,
                review_count=review_count if menu == "실시간 크롤링" else None,
                uploaded_file=uploaded_file if menu == "CSV 파일 업로드" else None,
            )

            if df is not None:
                if not is_already_analyzed:
                    with st.spinner('AI 감정 분석 중...'):
                        df = run_sentiment_analysis(df)
                st.session_state.analyzed_df = df
                st.session_state.current_app_id = app_id
                st.success("데이터 분석이 완료되었습니다!")
    except ReviewPipelineError as exc:
        st.error(str(exc))
    except Exception:
        st.error("예상치 못한 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")


if st.session_state.analyzed_df is not None:
    df = st.session_state.analyzed_df
    current_app_id = st.session_state.current_app_id

    render_file_info_section(df, current_app_id)
    render_sentiment_section(df)
    render_timeline_section(df)
    render_detail_section(df, current_app_id)