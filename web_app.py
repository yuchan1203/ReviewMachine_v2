import calendar
import os
import warnings
from datetime import date

import streamlit as st
from transformers import logging

from review_pipeline import ReviewPipelineError, load_source_dataframe, run_sentiment_analysis
from session_utils import initialize_session_state
from ui_sections import (
    render_detail_section,
    render_file_info_section,
    render_sentiment_section,
    render_timeline_section,
)

warnings.filterwarnings("ignore")
logging.set_verbosity_error()
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"


def _to_month_range(start_year, start_month, end_year, end_month):
    start_date = date(start_year, start_month, 1)
    last_day = calendar.monthrange(end_year, end_month)[1]
    end_date = date(end_year, end_month, last_day)
    return start_date, end_date


def _year_options():
    today = date.today()
    return list(range(2015, today.year + 2))


def _render_crawl_progress():
    progress = st.progress(0, text="데이터 크롤링 준비 중...")
    progress.progress(20, text="크롤링 대상 정보를 확인하고 있습니다...")
    return progress


def _render_analysis_progress(done, total, progress_bar):
    ratio = 0 if total == 0 else done / total
    percent = int(ratio * 100)
    progress_bar.progress(percent, text=f"리뷰 분석 진행 중... ({done}/{total})")


initialize_session_state()

st.set_page_config(page_title="ReviewMachine v2", layout="wide")
st.title("📊 ReviewMachine v2: 앱 리뷰 감정 분석기")
st.markdown("구글 플레이 스토어의 앱 ID를 입력해 리뷰를 수집하고 단계별로 분석할 수 있어요.")

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
                "기간이 길수록 API 호출이 늘어 시간이 더 걸릴 수 있습니다."
            )

        today = date.today()
        years = _year_options()
        default_year_index = years.index(today.year) if today.year in years else len(years) - 1

        st.markdown("**크롤링 기간 (월 단위)**")
        s_col1, s_col2 = st.columns(2)
        with s_col1:
            start_year = st.selectbox("시작 연도", years, index=default_year_index, key="live_crawl_start_year")
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
            end_year = st.selectbox("종료 연도", years, index=default_year_index, key="live_crawl_end_year")
        with e_col2:
            end_month = st.selectbox(
                "종료 월",
                list(range(1, 13)),
                index=today.month - 1,
                format_func=lambda m: f"{m}월",
                key="live_crawl_end_month",
            )

        st.caption("각 월은 1일~말일까지로 적용됩니다.")
        load_button = st.button("크롤링 시작")
    else:
        uploaded_file = st.file_uploader("CSV 파일을 선택하세요", type=["csv"])
        app_id = uploaded_file.name.split(".")[0] if uploaded_file is not None else "uploaded_file"
        load_button = st.button("데이터 불러오기")


if load_button:
    try:
        start_date = None
        end_date = None
        if menu == "실시간 크롤링":
            start_date, end_date = _to_month_range(start_year, start_month, end_year, end_month)
            if start_date > end_date:
                st.error("기간 설정이 올바르지 않습니다. 시작 월이 종료 월보다 늦을 수 없습니다.")
                st.stop()

        crawl_progress = _render_crawl_progress()
        df, is_already_analyzed = load_source_dataframe(
            menu=menu,
            app_id=app_id,
            review_count=review_count if menu == "실시간 크롤링" else None,
            start_date=start_date,
            end_date=end_date,
            uploaded_file=uploaded_file if menu == "CSV 파일 업로드" else None,
            sample_mode=sample_mode,
        )
        crawl_progress.progress(100, text="데이터 크롤링(또는 불러오기) 완료")

        if df is not None:
            if menu == "실시간 크롤링" and len(df) < review_count:
                st.warning(
                    f"요청한 {review_count}개보다 적은 {len(df)}개만 수집되었습니다. "
                    "선택한 기간 내 리뷰가 부족해 가능한 만큼만 가져왔습니다."
                )

            st.session_state.source_df = df
            st.session_state.source_is_analyzed = is_already_analyzed
            st.session_state.source_app_id = app_id

            if is_already_analyzed:
                st.session_state.analyzed_df = df
                st.session_state.current_app_id = app_id
                st.success("분석된 데이터를 불러왔습니다.")
            else:
                st.session_state.analyzed_df = None
                st.session_state.current_app_id = ""
                st.success("크롤링이 완료되었습니다. 먼저 CSV를 다운로드하거나, 이어서 분석을 진행하세요.")
    except ReviewPipelineError as exc:
        st.error(str(exc))
    except Exception:
        st.error("예상치 못한 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")


if st.session_state.source_df is not None and not st.session_state.source_is_analyzed:
    source_df = st.session_state.source_df
    source_app_id = st.session_state.source_app_id

    st.subheader("1단계 완료: 크롤링 데이터")
    raw_csv = source_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button(
        label="크롤링 데이터 CSV 다운로드",
        data=raw_csv,
        file_name=f"crawled_{source_app_id}.csv",
        mime="text/csv",
    )

    if st.button("분석하기", type="primary"):
        try:
            analysis_progress = st.progress(0, text="리뷰 분석을 준비하고 있습니다...")
            analyzed_df = run_sentiment_analysis(
                source_df.copy(),
                progress_callback=lambda done, total: _render_analysis_progress(done, total, analysis_progress),
            )
            analysis_progress.progress(100, text="리뷰 분석 완료")
            st.session_state.analyzed_df = analyzed_df
            st.session_state.current_app_id = source_app_id
            st.success("리뷰 분석이 완료되었습니다.")
        except ReviewPipelineError as exc:
            st.error(str(exc))
        except Exception:
            st.error("리뷰 분석 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")


if st.session_state.analyzed_df is not None:
    df = st.session_state.analyzed_df
    current_app_id = st.session_state.current_app_id

    render_file_info_section(df, current_app_id)
    render_sentiment_section(df)
    render_timeline_section(df)
    render_detail_section(df, current_app_id)
