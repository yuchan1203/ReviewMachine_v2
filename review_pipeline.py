import pandas as pd

from app_scraper import get_reviews
from analyzer import ReviewAnalyzer


ANALYZED_COLUMNS = ["sentiment", "sentiment_score", "confidence"]


def is_analyzed_dataframe(df):
    return all(col in df.columns for col in ANALYZED_COLUMNS)


def load_source_dataframe(menu, app_id, review_count, uploaded_file):
    if menu == "실시간 크롤링":
        df = get_reviews(app_id, count=review_count)
        return df, False

    if menu == "CSV 파일 업로드" and uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        return df, is_analyzed_dataframe(df)

    return None, False


def run_sentiment_analysis(df):
    analyzer = ReviewAnalyzer()
    texts = df["content"].tolist()
    analysis_results = analyzer.analyze_list(texts)
    df["sentiment"] = [r["sentiment"] for r in analysis_results]
    df["sentiment_score"] = [r["sentiment_score"] for r in analysis_results]
    df["confidence"] = [r["confidence"] for r in analysis_results]
    return df
