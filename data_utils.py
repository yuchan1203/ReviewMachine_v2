import pandas as pd


def calculate_sentiment_counts(df):
    """
    감정 라벨별 개수를 딕셔너리로 반환합니다.
    """
    labels = ["매우 긍정", "긍정", "보통", "부정", "매우 부정"]
    counts = {}
    for label in labels:
        counts[label] = int((df["sentiment"] == label).sum())
    return counts


def prepare_timeline_data(df):
    """
    시간 흐름 그래프에 사용할 기간별 감정 점수 데이터를 생성합니다.
    """
    timeline_source = df.copy()
    timeline_source["at"] = pd.to_datetime(timeline_source["at"])
    timeline_source["date"] = timeline_source["at"].dt.normalize()

    # 먼저 일별 점수 총합을 만든 뒤, 주/월은 일별 총합을 다시 집계합니다.
    daily_df = timeline_source.groupby("date", as_index=False)["sentiment_score"].sum()

    return daily_df


def prepare_timeline_data_by_period(df, period="일별", week_start="월요일"):
    """
    사용자가 선택한 기간(일별/주별/월별) 기준의 감정 점수 추이 데이터를 생성합니다.
    주별/월별은 일별 점수 총합을 기준으로 다시 합산합니다.
    """
    daily_df = prepare_timeline_data(df)

    if period == "주별":
        weekly_df = daily_df.copy()
        week_period = "W-SUN" if week_start == "월요일" else "W-SAT"
        weekly_df["date"] = weekly_df["date"].dt.to_period(week_period).dt.start_time
        return weekly_df.groupby("date", as_index=False)["sentiment_score"].sum()

    if period == "월별":
        monthly_df = daily_df.copy()
        monthly_df["date"] = monthly_df["date"].dt.to_period("M").dt.start_time
        return monthly_df.groupby("date", as_index=False)["sentiment_score"].sum()

    return daily_df
