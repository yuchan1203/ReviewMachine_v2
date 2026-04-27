import pandas as pd

from app_scraper import get_reviews
from analyzer import ReviewAnalyzer


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


def load_source_dataframe(
    menu, app_id, review_count, start_date, end_date, uploaded_file, sample_mode="latest"
):
    if menu == "실시간 크롤링":
        try:
            df = get_reviews(
                app_id,
                count=review_count,
                start_date=start_date,
                end_date=end_date,
                sample_mode=sample_mode,
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


def run_sentiment_analysis(df):
    validate_input_dataframe(df)
    analyzer = ReviewAnalyzer()
    texts = df["content"].fillna("").astype(str).tolist()
    analysis_results = analyzer.analyze_list(texts)
    df["sentiment"] = [r["sentiment"] for r in analysis_results]
    df["sentiment_score"] = [r["sentiment_score"] for r in analysis_results]
    df["confidence"] = [r["confidence"] for r in analysis_results]
    return df
