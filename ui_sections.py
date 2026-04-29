'''
이 파일은 리뷰 데이터의 UI 섹션별 렌더링을 담당합니다.
A. 모듈 임포트: 필요한 라이브러리 로딩
B. 파일 정보 섹션: CSV 파일 및 데이터 정보 표시
C. 감정 분석 결과 시각화 섹션: 감정 분포 차트 및 통계 표시
D. 시간 흐름에 따른 감정 점수 추이 섹션: 라인 차트로 감정 점수 추이 시각화
E. 상세 리뷰 데이터 섹션: 분석된 리뷰 데이터 테이블 및 CSV 다운로드 기능
'''


"""
Utility functions that prepare section data for the FastAPI frontend.
These functions return serializable dicts instead of rendering UI.
"""
from datetime import datetime
import pandas as pd
from data_utils import calculate_sentiment_counts, prepare_timeline_data_by_period


def get_file_info(df: pd.DataFrame, current_app_id: str):
    info_df = df.copy()
    info_df["at"] = pd.to_datetime(info_df["at"]) if not info_df.empty else pd.Series([], dtype="datetime64[ns]")
    start_date = info_df["at"].min().strftime("%Y-%m-%d") if not info_df.empty else None
    end_date = info_df["at"].max().strftime("%Y-%m-%d") if not info_df.empty else None
    total_reviews = int(len(info_df))
    is_analyzed = all(col in info_df.columns for col in ["sentiment", "sentiment_score"]) if not info_df.empty else False
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return {
        "data_type": "analyzed" if is_analyzed else "raw",
        "app_id": current_app_id,
        "total_reviews": total_reviews,
        "start_date": start_date,
        "end_date": end_date,
        "queried_at": current_time,
    }


def get_sentiment_counts(df: pd.DataFrame):
    return calculate_sentiment_counts(df)


def get_timeline(df: pd.DataFrame, period: str = "일별", week_start: str = "월요일"):
    timeline = prepare_timeline_data_by_period(df, period=period, week_start=week_start)
    timeline = timeline.assign(date=timeline['date'].dt.strftime('%Y-%m-%d'))
    return timeline.to_dict(orient='records')
