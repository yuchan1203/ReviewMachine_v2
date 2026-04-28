import pandas as pd
import streamlit as st

from app_scraper import get_reviews
from analyzer import get_review_analyzer


ANALYZED_COLUMNS = ["sentiment", "sentiment_score", "confidence"]
REQUIRED_COLUMNS = ["at", "content"]


class ReviewPipelineError(Exception):
    """사용자에게 안내 가능한 데이터/분석 단계 예외"""


def is_analyzed_dataframe(df):
    return all(col in df.columns for col in ANALYZED_COLUMNS)


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


@st.cache_data(show_spinner=False)
def load_source_dataframe(
    menu, app_id, review_count, start_date, end_date, uploaded_file, crawl_mode="count_latest", period_days=None
):
    if menu == "실시간 크롤링":
        try:
            df = get_reviews(
                app_id,
                count=review_count,
                crawl_mode=crawl_mode,
                period_days=period_days,
            )
        except Exception as exc:
            raise ReviewPipelineError(
                "리뷰 크롤링에 실패했습니다. 앱 ID를 확인하거나 잠시 후 다시 시도해주세요."
            ) from exc
        validate_input_dataframe(df)
        return df, False

    if menu == "CSV 파일 업로드" and uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
        except Exception as exc:
            raise ReviewPipelineError("CSV 파일을 읽는 중 오류가 발생했습니다.") from exc
        validate_input_dataframe(df)
        return df, is_analyzed_dataframe(df)

    return None, False


def run_sentiment_analysis(df, progress_callback=None, batch_size=32, device="cpu", return_runtime_info=False):
    validate_input_dataframe(df)
    
    # 캐시된 analyzer 사용 - 재시작 시 모델 다시 로드 안 함
    analyzer = get_review_analyzer(device=device)
    texts = df["content"].fillna("").astype(str).tolist()
    total = len(texts)
    analysis_results = []

    if total == 0:
        if return_runtime_info:
            return df, analyzer.runtime_info()
        return df

    safe_batch_size = max(1, int(batch_size))
    for start_idx in range(0, total, safe_batch_size):
        end_idx = min(start_idx + safe_batch_size, total)
        batch_texts = texts[start_idx:end_idx]
        analysis_results.extend(analyzer.analyze_list(batch_texts))
        if progress_callback is not None:
            progress_callback(end_idx, total)

    df["sentiment"] = [r["sentiment"] for r in analysis_results]
    df["sentiment_score"] = [r["sentiment_score"] for r in analysis_results]
    df["confidence"] = [r["confidence"] for r in analysis_results]
    if return_runtime_info:
        return df, analyzer.runtime_info()
    return df
