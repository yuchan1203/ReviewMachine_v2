# A. 모델 임포트

# A-1. 라이브러리 임포트
import pandas as pd
import os
import traceback
import warnings
from datetime import date

# A-2. 내부 모듈 임포트
import streamlit as st
from transformers import logging

# A-3. 앱 모듈 임포트
from review_pipeline import ReviewPipelineError, load_source_dataframe, run_sentiment_analysis
from session_utils import initialize_session_state
from ui_sections import (
    render_detail_section,
    render_file_info_section,
    render_sentiment_section,
    render_timeline_section,
)


# B. 경고 무시 및 로깅 레벨 설정
warnings.filterwarnings("ignore")
logging.set_verbosity_error()
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"


# C. 예외 정의
def _render_crawl_progress():
    progress = st.progress(0, text="데이터 크롤링 준비 중...")
    progress.progress(20, text="크롤링 대상 정보를 확인하고 있습니다...")
    return progress

# D-1. 입력 데이터 검증 함수
REQUIRED_COLUMNS = ["at", "content"]
def validate_input_dataframe(df):
    if df is None:
        raise ReviewPipelineError("데이터를 불러오지 못했습니다.")


# D-2. 분석 진행 상황 표시 함수
def _render_analysis_progress(done, total, progress_bar):
    ratio = 0 if total == 0 else done / total
    percent = int(ratio * 100)
    progress_bar.progress(percent, text=f"리뷰 분석 진행 중... ({done}/{total})")


# E. 실제 분석 장치 결정 함수
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


# F. 입력 데이터 검증 함수
REQUIRED_COLUMNS = ["at", "content"]
def validate_input_dataframe(df):
    if df is None:
        raise ReviewPipelineError("데이터를 불러오지 못했습니다.")


# G. 데이터프레임이 비어있는지 확인
def validate_non_empty_dataframe(df):
    if df is None or df.empty:
        raise ReviewPipelineError("데이터가 비어 있습니다.")


# H. 네비게이션 상태 초기화
def init_navigation_state():
    if "nav_state" not in st.session_state:
        st.session_state.nav_state = "main"


# I. 입력 데이터 검증 함수 (통합)
def validate_input_dataframe(df):
    if df is None:
        raise ReviewPipelineError("데이터를 불러오지 못했습니다.")
    if df.empty:
        raise ReviewPipelineError("리뷰 데이터가 비어 있습니다.")
    missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_columns:
        raise ReviewPipelineError(
            f"필수 컬럼이 없습니다: {', '.join(missing_columns)}. "
            "CSV에 at, content 컬럼이 포함되어 있는지 확인해주세요."
        )
    non_empty_content = df["content"].astype(str).str.strip() != ""
    if not non_empty_content.any():
        raise ReviewPipelineError("리뷰 본문(content)에 분석 가능한 텍스트가 없습니다.")


# J. 입력 데이터 검증 함수 (분리된 단계)
def validate_input_dataframe(df):
    # J-1. 데이터프레임이 None인지 확인
    if df is None:
        raise ReviewPipelineError("데이터를 불러오지 못했습니다.")
    
    # J-2. 데이터프레임이 비어있는지 확인
    if df.empty:
        raise ReviewPipelineError("리뷰 데이터가 비어 있습니다.")

    # J-3. 필수 컬럼 존재 여부 확인
    missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_columns:
        raise ReviewPipelineError(
            f"필수 컬럼이 없습니다: {', '.join(missing_columns)}. "
            "CSV에 at, content 컬럼이 포함되어 있는지 확인해주세요."
        )
    
    # J-4. 리뷰 본문(content)에 분석 가능한 텍스트가 있는지 확인
    non_empty_content = df["content"].astype(str).str.strip() != ""

    # J-5. 분석 가능한 텍스트가 하나도 없는 경우 예외 발생
    if not non_empty_content.any():
        raise ReviewPipelineError("리뷰 본문(content)에 분석 가능한 텍스트가 없습니다.")
    

# K. 네비게이션 함수 및 상태 초기화
def navigate_to(state):
    st.session_state.nav_state = state


# L. 모든 상태 초기화 함수
def reset_all_state():
    st.session_state.source_df = None
    st.session_state.source_is_analyzed = False
    st.session_state.analyzed_df = None
    st.session_state.current_app_id = ""
    st.session_state.analysis_runtime_info = None
    st.session_state.uploaded_file_data = None
    st.session_state.nav_state = "main"


# ============================================================
# 메인 메뉴 화면
# ============================================================
def render_main_menu():
    """메인 메뉴 화면"""
    st.markdown("## 🎯 시작 화면을 선택하세요")
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📁 파일 업로드")
        st.markdown("이미 수집된 CSV 파일을 업로드하여 분석합니다.")
        if st.button("📂 파일 업로드로 이동", key="btn_file_upload", width='stretch'):
            navigate_to("file_upload")
    
    with col2:
        st.markdown("### 🔄 새로 시작하기")
        st.markdown("새로운 앱 리뷰를 크롤링하여 분석을 시작합니다.")
        if st.button("🚀 새로 시작하기", key="btn_new_start", width='stretch'):
            navigate_to("new_start")


# ============================================================
# 새로 시작하기 화면
# ============================================================
def render_new_start():
    """새로 시작하기 화면"""
    st.markdown("## 🔄 새로 시작하기")
    st.markdown("---")
    
    # 1. 리뷰 앱 선택
    st.markdown("### 1️⃣ 앱 선택")
    app_id = st.text_input("구글 플레이 스토어 앱 ID", value="com.kakao.talk", key="new_app_id")
    st.caption("예: com.kakao.talk, com.instagram.android, com.samsung.android.mobileservice")
    
    # 2. 크롤링 방식 선택
    st.markdown("### 2️⃣ 크롤링 방식 선택")
    crawl_mode = st.radio(
        "수집 방식",
        ["개수 지정 (최신순)", "기간 전체 (현재부터)"],
        horizontal=True,
        key="new_crawl_mode"
    )
    
    review_count = None
    period_days = None
    
    if crawl_mode == "개수 지정 (최신순)":
        review_count = st.number_input("수집 개수 (1~10000)", min_value=1, max_value=10000, value=300, step=1, key="new_review_count")
    else:
        period_label = st.selectbox(
            "기간 선택",
            ["1일 전", "1주일 전", "1개월 전", "3개월 전", "6개월 전", "1년 전", "2년 전"],
            key="new_period"
        )
        period_days_map = {
            "1일 전": 1, "1주일 전": 7, "1개월 전": 30, "3개월 전": 90,
            "6개월 전": 180, "1년 전": 365, "2년 전": 730
        }
        period_days = period_days_map[period_label]
    
    # 3. 버튼을 눌러 크롤링 시작
    st.markdown("### 3️⃣ 크롤링 시작")
    if st.button("🔥 크롤링 시작", type="primary", key="btn_start_crawl", width='stretch'):
        try:
            crawl_progress = _render_crawl_progress()
            df, is_already_analyzed = load_source_dataframe(
                menu="실시간 크롤링",
                app_id=app_id,
                review_count=review_count if review_count else 1,
                start_date=None,
                end_date=None,
                uploaded_file=None,
                crawl_mode="count_latest" if crawl_mode == "개수 지정 (최신순)" else "period_all",
                period_days=period_days,
            )
            crawl_progress.progress(100, text="데이터 크롤링 완료")
            
            if df is not None:
                if crawl_mode == "개수 지정 (최신순)" and len(df) < review_count:
                    st.warning(f"요청한 {review_count}개보다 적은 {len(df)}개만 수집되었습니다.")
                
                st.session_state.source_df = df
                st.session_state.source_is_analyzed = is_already_analyzed
                st.session_state.source_app_id = app_id
                st.success("크롤링이 완료되었습니다!")
                navigate_to("continue_analysis")
        except ReviewPipelineError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error("예상치 못한 오류가 발생했습니다.")
            st.code("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
    
    st.markdown("---")
    if st.button("↩ 메인으로", key="btn_back_main", width='stretch'):
        navigate_to("main")


# ============================================================
# 파일 업로드 화면
# ============================================================
def render_file_upload():
    """파일 업로드 화면"""
    st.markdown("## 📁 파일 업로드")
    st.markdown("---")
    
    # session state에서 파일 데이터 확인
    uploaded_file = st.session_state.get("uploaded_file_data")
    
    # 파일이 session에 없으면 새로 업로드
    if uploaded_file is None:
        new_uploaded_file = st.file_uploader("CSV 파일을 선택하세요", type=["csv"], key="upload_file")
        
        if new_uploaded_file is not None:
            # 파일 데이터를 session에 저장
            st.session_state.uploaded_file_data = new_uploaded_file
            uploaded_file = new_uploaded_file
    
    if uploaded_file is not None:
        try:
            app_id = uploaded_file.name.split(".")[0] if uploaded_file.name else "uploaded_file"
            
            # 이미 처리된 데이터가 있는지 확인
            if st.session_state.get("source_df") is not None and st.session_state.get("source_app_id") == app_id:
                # 이미 처리된 데이터가 있음
                df = st.session_state.source_df
                is_already_analyzed = st.session_state.source_is_analyzed
                st.success("파일이 로드되었습니다!")
            else:
                crawl_progress = _render_crawl_progress()
                df, is_already_analyzed = load_source_dataframe(
                    menu="CSV 파일 업로드",
                    app_id=app_id,
                    review_count=1,
                    start_date=None,
                    end_date=None,
                    uploaded_file=uploaded_file,
                    crawl_mode="count_latest",
                    period_days=None,
                )
                crawl_progress.progress(100, text="데이터 불러오기 완료")
                
                st.session_state.source_df = df
                st.session_state.source_is_analyzed = is_already_analyzed
                st.session_state.source_app_id = app_id
            
            # 1. 분석 완료된 파일인지 크롤링만 된 파일인지 파악
            if st.session_state.source_is_analyzed:
                st.success("분석 완료된 파일입니다!")
                navigate_to("result")
            else:
                st.success("크롤링만 된 파일입니다. 분석을 진행하세요.")
                navigate_to("continue_analysis")
        except ReviewPipelineError as exc:
            st.error(str(exc))
            # 오류 시 session 초기화
            st.session_state.uploaded_file_data = None
        except Exception as exc:
            st.error("파일 처리 중 오류가 발생했습니다.")
            st.code("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
            st.session_state.uploaded_file_data = None
    
    st.markdown("---")
    if st.button("↩ 메인으로", key="btn_back_main2", width='stretch'):
        st.session_state.uploaded_file_data = None
        navigate_to("main")


# ============================================================
# 이어서 분석 화면
# ============================================================
def render_continue_analysis():
    """이어서 분석 화면"""
    source_df = st.session_state.source_df
    source_app_id = st.session_state.source_app_id
    
    # 데이터가 없으면 메인으로 이동
    if source_df is None:
        st.error("크롤링 데이터가 없습니다. 다시 시작해주세요.")
        st.markdown("---")
        if st.button("↩ 메인으로", key="btn_back_main3", width='stretch'):
            navigate_to("main")
        return
    
    st.markdown("## ▶ 이어서 분석")
    st.markdown("---")
    
    # 크롤링 데이터 표시
    st.subheader("1단계 완료: 크롤링 데이터")
    st.dataframe(source_df.head(10), width='stretch')
    st.caption(f"총 {len(source_df)}개의 리뷰")
    
    raw_csv = source_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button(
        label="💾 크롤링 데이터 CSV 다운로드",
        data=raw_csv,
        file_name=f"crawled_{source_app_id}.csv",
        mime="text/csv",
    )
    
    st.markdown("---")
    
    # 1. 분석 장치 선택하기
    st.markdown("### 분석 장치 선택")
    analysis_device_label = st.selectbox("분석 장치", ["CPU", "GPU"], key="analysis_device")
    
    # 2. 분석 시작
    if st.button("🔍 분석 시작", type="primary", key="btn_start_analysis", width='stretch'):
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
            st.success("리뷰 분석이 완료되었습니다!")
            navigate_to("result")
        except ReviewPipelineError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error("리뷰 분석 중 오류가 발생했습니다.")
            st.code("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
    
    st.markdown("---")
    if st.button("↩ 메인으로", key="btn_back_main3", width='stretch'):
        navigate_to("main")


# ============================================================
# 결과 표시 화면
# ============================================================
def render_result():
    """결과 표시 화면"""
    df = st.session_state.analyzed_df
    current_app_id = st.session_state.current_app_id
    runtime_info = st.session_state.analysis_runtime_info
    
    # 데이터가 없으면 메인으로 이동
    if df is None:
        st.error("분석 결과가 없습니다. 다시 시작해주세요.")
        st.markdown("---")
        if st.button("🔄 처음부터 다시 시작", key="btn_back_main4", width='stretch'):
            reset_all_state()
        return
    
    st.markdown("## 📊 분석 결과")
    st.markdown("---")
    
    if runtime_info is not None:
        requested = runtime_info.get("requested_device", "cpu").upper()
        actual = runtime_info.get("actual_device", "cpu").upper()
        model_mode = runtime_info.get("model_mode", "unknown")
        st.caption(f"분석 장치: 요청 {requested} / 실제 {actual} | 모델 경로: {model_mode}")
    
    # 결과 표시
    render_file_info_section(df, current_app_id)
    render_sentiment_section(df)
    render_timeline_section(df)
    render_detail_section(df, current_app_id)
    
    st.markdown("---")
    if st.button("🔄 처음부터 다시 시작", key="btn_back_main4", width='stretch'):
        reset_all_state()


# ============================================================
# 메인 앱 실행
# ============================================================
def main():
    initialize_session_state()
    init_navigation_state()
    
    st.set_page_config(page_title="ReviewMachine v2", layout="wide")
    st.title("📊 ReviewMachine v2: 앱 리뷰 감정 분석기")
    st.markdown("구글 플레이 스토어의 앱 ID를 입력해 리뷰를 수집하고 단계별로 분석할 수 있어요.")
    
    # 현재 상태에 따른 화면 렌더링
    nav_state = st.session_state.nav_state
    
    if nav_state == "main":
        render_main_menu()
    elif nav_state == "new_start":
        render_new_start()
    elif nav_state == "file_upload":
        render_file_upload()
    elif nav_state == "continue_analysis":
        render_continue_analysis()
    elif nav_state == "result":
        render_result()


if __name__ == "__main__":
    main()