'''
이 파일은 리뷰 데이터의 감정 분석 결과를 계산하고 시각화에 필요한 데이터를 준비하는 기능을 담당합니다.
A. 모듈 임포트: 필요한 라이브러리 로딩
B. 감정 분석 결과 계산 및 시각화 데이터 준비 함수 정의: 감정별 리뷰 수 계산 함수와 시간 흐름 그래프에 사용할 기간별 감정 점수 데이터 생성 함수 정의
C. 시간 흐름에 따른 감정 점수 추이 데이터 생성 함수 정의: 사용자가 선택한 기간(일별/주별/월별) 기준의 감정 점수 추이 데이터를 생성하는 함수 정의
'''



# A. 모듈 임포트
import pandas as pd


# B. 감정 분석 결과 계산 및 시각화 데이터 준비 함수 정의
def calculate_sentiment_counts(df):
    labels = ["매우 긍정", "긍정", "보통", "부정", "매우 부정"]
    counts = {}
    for label in labels:
        counts[label] = int((df["sentiment"] == label).sum())
    return counts


# C. 시간 흐름 그래프에 사용할 기간별 감정 점수 데이터 생성 함수 정의
def prepare_timeline_data(df):

    # C-1. 리뷰 데이터프레임을 날짜별로 그룹화하여 감정 점수의 총합을 계산
    timeline_source = df.copy()
    timeline_source["at"] = pd.to_datetime(timeline_source["at"])
    timeline_source["date"] = timeline_source["at"].dt.normalize()

    # C-2. 날짜별 감정 점수 총합 계산
    daily_df = timeline_source.groupby("date", as_index=False)["sentiment_score"].sum()

    # C-3. 날짜별 감정 점수 데이터프레임 반환
    return daily_df


# D. 사용자가 선택한 기간(일별/주별/월별) 기준의 감정 점수 추이 데이터를 생성하는 함수 정의
def prepare_timeline_data_by_period(df, period="일별", week_start="월요일"):

    # D-1. 일별 감정 점수 데이터프레임 생성
    daily_df = prepare_timeline_data(df)

    # D-2. 사용자가 선택한 기간 기준으로 감정 점수 추이 데이터프레임 생성
    if period == "주별":
        weekly_df = daily_df.copy()
        week_period = "W-SUN" if week_start == "월요일" else "W-SAT"
        weekly_df["date"] = weekly_df["date"].dt.to_period(week_period).dt.start_time
        return weekly_df.groupby("date", as_index=False)["sentiment_score"].sum()
    if period == "월별":
        monthly_df = daily_df.copy()
        monthly_df["date"] = monthly_df["date"].dt.to_period("M").dt.start_time
        return monthly_df.groupby("date", as_index=False)["sentiment_score"].sum()

    # D-3. 일별 감정 점수 데이터프레임 반환
    return daily_df
