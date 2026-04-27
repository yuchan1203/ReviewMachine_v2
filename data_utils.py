import pandas as pd


def calculate_sentiment_counts(df):
    """
    감성 라벨별 개수를 딕셔너리로 반환합니다.
    """
    labels = ["매우 긍정", "긍정", "보통", "부정", "매우 부정"]
    counts = {}
    for label in labels:
        counts[label] = int((df["sentiment"] == label).sum())
    return counts


def prepare_timeline_data(df):
    """
    시간 흐름 그래프에 사용할 일자별 평균 감정 점수 데이터를 생성합니다.
    """
    timeline_source = df.copy()
    timeline_source["at"] = pd.to_datetime(timeline_source["at"])
    timeline_source["date"] = timeline_source["at"].dt.date
    timeline_df = timeline_source.groupby("date")["sentiment_score"].mean().reset_index()
    return timeline_df
