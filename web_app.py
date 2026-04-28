import os
import traceback
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


def _render_crawl_progress():
    progress = st.progress(0, text="데이터 크롤링 준비 중...")
    progress.progress(20, text="크롤링 대상 정보를 확인하고 있습니다...")
    return progress


def _render_analysis_progress(done, total, progress_bar):
    ratio = 0 if total == 0 else done / total
    percent = int(ratio * 100)
    progress_bar.progress(percent, text=f"리뷰 분석 진행 중... ({done}/{total})")


def _resolve_actual_device(requested_device):
    if requested_device != "gpu":
        return "cpu"
    try:
        import torch

        if torch.cuda.is_available():
            return "gpu"
    except Exception:
        pass
    return "cpu"


initialize_session_state()

st.set_page_config(page_title="ReviewMachine v2", layout="wide")
st.title("📊 ReviewMachine v2: 앱 리뷰 감정 분석기")
st.markdown("구글 플레이 스토어의 앱 ID를 입력해 리뷰를 수집하고 단계별로 분석할 수 있어요.")

with st.sidebar:
    st.header("입력 방식 선택")
    analysis_device_label = st.selectbox("분석 장치", ["CPU", "GPU"], key="analysis_device")
    menu = st.radio("데이터 소스", ["실시간 크롤링", "CSV 파일 업로드"])
    uploaded_file = None
    crawl_mode = "count_latest"
    period_days = None
    review_count = None

    if menu == "실시간 크롤링":
        app_id = st.text_input("앱 ID 입력", value="com.kakao.talk")
        collect_mode_label = st.radio(
            "리뷰 수집 방식",
            ["개수 지정 (최신순)", "기간 전체 (현재부터)"],
            horizontal=True,
            key="live_collect_mode",
        )
        if collect_mode_label == "개수 지정 (최신순)":
            crawl_mode = "count_latest"
            review_count = st.number_input("수집 개수 (1~10000)", min_value=1, max_value=10000, value=300, step=1)
        else:
            crawl_mode = "period_all"
            period_label = st.selectbox(
                "기간 선택",
                ["1일 전", "1주일 전", "1개월 전", "3개월 전", "6개월 전", "1년 전", "2년 전"],
                key="live_period_mode",
            )
            period_days_map = {
                "1일 전": 1,
                "1주일 전": 7,
                "1개월 전": 30,
                "3개월 전": 90,
                "6개월 전": 180,
                "1년 전": 365,
                "2년 전": 730,
            }
            period_days = period_days_map[period_label]
        load_button = st.button("크롤링 시작")
    else:
        uploaded_file = st.file_uploader("CSV 파일을 선택하세요", type=["csv"])
        app_id = uploaded_file.name.split(".")[0] if uploaded_file is not None else "uploaded_file"
        load_button = st.button("데이터 불러오기")


if load_button:
    try:
        crawl_progress = _render_crawl_progress()
        df, is_already_analyzed = load_source_dataframe(
            menu=menu,
            app_id=app_id,
            review_count=review_count if (menu == "실시간 크롤링" and crawl_mode == "count_latest") else 1,
            start_date=None,
            end_date=None,
            uploaded_file=uploaded_file if menu == "CSV 파일 업로드" else None,
            crawl_mode=crawl_mode,
            period_days=period_days,
        )
        crawl_progress.progress(100, text="데이터 크롤링(또는 불러오기) 완료")

        if df is not None:
            if menu == "실시간 크롤링" and crawl_mode == "count_latest" and len(df) < review_count:
                st.warning(
                    f"요청한 {review_count}개보다 적은 {len(df)}개만 수집되었습니다. "
                    "가져올 수 있는 최신 리뷰가 부족해 가능한 만큼만 가져왔습니다."
                )

            st.session_state.source_df = df
            st.session_state.source_is_analyzed = is_already_analyzed
            st.session_state.source_app_id = app_id

            if is_already_analyzed:
                st.session_state.analyzed_df = df
                st.session_state.current_app_id = app_id
                st.session_state.analysis_runtime_info = None
                st.success("분석된 데이터를 불러왔습니다.")
            else:
                st.session_state.analyzed_df = None
                st.session_state.current_app_id = ""
                st.session_state.analysis_runtime_info = None
                st.success("크롤링이 완료되었습니다. 먼저 CSV를 다운로드하거나, 이어서 분석을 진행하세요.")
    except ReviewPipelineError as exc:
        st.error(str(exc))
    except Exception as exc:
        st.error("예상치 못한 오류가 발생했습니다. 아래 상세 오류를 확인해주세요.")
        st.code("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))


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
            requested_device = "gpu" if analysis_device_label == "GPU" else "cpu"
            actual_device = _resolve_actual_device(requested_device)
            st.info(f"분석 장치: 요청 {requested_device.upper()} / 실제 {actual_device.upper()}")
            analysis_progress = st.progress(0, text=f"리뷰 분석을 준비하고 있습니다... ({actual_device.upper()})")
            analyzed_df, runtime_info = run_sentiment_analysis(
                source_df.copy(),
                progress_callback=lambda done, total: _render_analysis_progress(done, total, analysis_progress),
                device=requested_device,
                return_runtime_info=True,
            )
            analysis_progress.progress(100, text="리뷰 분석 완료")
            st.session_state.analyzed_df = analyzed_df
            st.session_state.current_app_id = source_app_id
            st.session_state.analysis_runtime_info = runtime_info
            st.success("리뷰 분석이 완료되었습니다.")
        except ReviewPipelineError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error("리뷰 분석 중 오류가 발생했습니다. 아래 상세 오류를 확인해주세요.")
            st.code("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))


if st.session_state.analyzed_df is not None:
    df = st.session_state.analyzed_df
    current_app_id = st.session_state.current_app_id
    runtime_info = st.session_state.analysis_runtime_info

    if runtime_info is not None:
        requested = runtime_info.get("requested_device", "cpu").upper()
        actual = runtime_info.get("actual_device", "cpu").upper()
        model_mode = runtime_info.get("model_mode", "unknown")
        st.caption(f"분석 장치: 요청 {requested} / 실제 {actual} | 모델 경로: {model_mode}")

    render_file_info_section(df, current_app_id)
    render_sentiment_section(df)
    render_timeline_section(df)
    render_detail_section(df, current_app_id)
