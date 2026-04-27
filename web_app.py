import streamlit as st
import warnings
import os
import calendar
from datetime import date

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


def _to_month_range(start_year, start_month, end_year, end_month):
    start_date = date(start_year, start_month, 1)
    last_day = calendar.monthrange(end_year, end_month)[1]
    end_date = date(end_year, end_month, last_day)
    return start_date, end_date


def _year_options():
    today = date.today()
    return list(range(2015, today.year + 2))


# 세션 상태 초기화
initialize_session_state()

# 화면 설정
st.set_page_config(page_title="ReviewMachine v2", layout="wide")
st.title("📊 ReviewMachine v2: 앱 리뷰 감정 분석기")
st.markdown("구글 플레이 스토어의 앱 ID를 입력하여 실시간 리뷰 분석 결과를 확인하세요.")

# 사이드바 설정
with st.sidebar:
    st.header("입력 방식 선택")
    menu = st.radio("데이터 소스", ["실시간 크롤링", "CSV 파일 업로드"])
    uploaded_file = None
    sample_mode = "latest"

    if menu == "실시간 크롤링":
        app_id = st.text_input("앱 ID 입력", value="com.kakao.talk")
        review_count = st.number_input("수집 개수 (1~10000)", min_value=1, max_value=10000, value=300, step=1)
        sample_mode_label = st.radio(
            "데이터 선택 방식",
            ["최신순", "월별 균등"],
            horizontal=True,
            key="live_sample_mode",
        )
        sample_mode = "even_monthly" if sample_mode_label == "월별 균등" else "latest"
        if sample_mode == "even_monthly":
            st.caption(
                "월별 균등: 선택 기간의 월 수로 수집 개수를 나눈 뒤, 각 달에서 무작위로 뽑습니다. "
                "기간이 길수록 API를 더 많이 호출하므로 시간이 걸릴 수 있습니다."
            )

        today = date.today()
        years = _year_options()
        default_year_index = years.index(today.year) if today.year in years else len(years) - 1

        st.markdown("**크롤링 기간 (월 단위)**")
        s_col1, s_col2 = st.columns(2)
        with s_col1:
            start_year = st.selectbox(
                "시작 연도",
                years,
                index=default_year_index,
                key="live_crawl_start_year",
            )
        with s_col2:
            start_month = st.selectbox(
                "시작 월",
                list(range(1, 13)),
                index=today.month - 1,
                format_func=lambda m: f"{m}월",
                key="live_crawl_start_month",
            )

        e_col1, e_col2 = st.columns(2)
        with e_col1:
            end_year = st.selectbox(
                "종료 연도",
                years,
                index=default_year_index,
                key="live_crawl_end_year",
            )
        with e_col2:
            end_month = st.selectbox(
                "종료 월",
                list(range(1, 13)),
                index=today.month - 1,
                format_func=lambda m: f"{m}월",
                key="live_crawl_end_month",
            )

        st.caption("각 월은 1일~말일까지로 적용됩니다.")
    else:
        uploaded_file = st.file_uploader("CSV 파일을 선택하세요", type=['csv'])
        if uploaded_file is not None:
            app_id = uploaded_file.name.split('.')[0]
        else:
            app_id = "uploaded_file"

    analyze_button = st.button("분석 시작")


if analyze_button:
    try:
        start_date = None
        end_date = None
        if menu == "실시간 크롤링":
            start_date, end_date = _to_month_range(
                start_year, start_month, end_year, end_month
            )
            if start_date > end_date:
                st.error("기간 설정이 올바르지 않습니다. 시작 월이 종료 월보다 늦을 수 없습니다.")
                st.stop()

        with st.spinner('데이터를 준비 중입니다...'):
            df, is_already_analyzed = load_source_dataframe(
                menu=menu,
                app_id=app_id,
                review_count=review_count if menu == "실시간 크롤링" else None,
                start_date=start_date,
                end_date=end_date,
                uploaded_file=uploaded_file if menu == "CSV 파일 업로드" else None,
                sample_mode=sample_mode,
            )

            if df is not None:
                if menu == "실시간 크롤링" and len(df) < review_count:
                    st.warning(
                        f"요청한 {review_count}개보다 적은 {len(df)}개만 수집되었습니다. "
                        "선택한 기간 내 리뷰가 부족해 가능한 만큼만 가져왔습니다."
                    )
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