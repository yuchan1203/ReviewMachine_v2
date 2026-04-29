'''
이 파일은 Google Play Store에서 앱 리뷰를 수집하는 기능을 담당합니다.
A. 모듈 임포트: 필요한 라이브러리 로딩
B. Streamlit 캐시 데코레이터 및 예외 정의
C. 리뷰 수집 함수 정의: 최신 리뷰를 안전하게 최대 개수까지 수집하는 함수와 특정 기간 이후의 리뷰만 수집하는 함수 정의
D. 리뷰 분석기 캐싱 함수 정의: 리뷰 분석기 인스턴스를 Streamlit 캐시로 관리하여 모델 로딩을 최적화하는 함수 정의
'''

# A. 모듈 임포트
from datetime import date, timedelta
import pandas as pd
import streamlit as st

# google_play_scraper is optional for demo / development. If it's not
# installed, the app will fall back to synthetic sample data so the UI
# can still be exercised without network access or heavy dependencies.
try:
    from google_play_scraper import Sort, reviews
    _HAS_GOOGLE_PLAY_SCRAPER = True
except Exception:
    Sort = None
    reviews = None
    _HAS_GOOGLE_PLAY_SCRAPER = False


# B. Streamlit 캐시 데코레이터 및 예외 정의
@st.cache_data(show_spinner=False)


# C. 리뷰 수집 함수 정의
def _get_reviews_latest(app_id, safe_count):

    # C-1. 리뷰를 배치로 수집하여 안전하게 최대 개수까지 수집
    collected = []
    continuation_token = None

    # C-2. 리뷰 수집 루프: 배치 단위로 리뷰를 수집하고, 수집된 리뷰가 안전한 최대 개수에 도달할 때까지 반복
    while len(collected) < safe_count:
        batch_size = min(200, safe_count - len(collected))
        result, continuation_token = reviews(
            app_id,
            lang="ko",
            country="kr",
            sort=Sort.NEWEST,
            count=batch_size,
            continuation_token=continuation_token,
        )
        if not result:
            break
        for review in result:
            review_date = pd.to_datetime(review.get("at"), errors="coerce")
            if pd.isna(review_date):
                continue
            collected.append(review)
            if len(collected) >= safe_count:
                break
        if continuation_token is None:
            break
    return collected


# D. 특정 기간 내 리뷰 수집 함수 정의
def _get_reviews_since(app_id, start_date):

    # D-1. 리뷰를 배치로 수집하여 시작 날짜 이후의 리뷰만 수집
    collected = []
    continuation_token = None

    # D-2. 리뷰 수집 루프: 배치 단위로 리뷰를 수집하고, 수집된 리뷰의 날짜가 시작 날짜 이후인 경우에만 수집
    while True:
        result, continuation_token = reviews(
            app_id,
            lang="ko",
            country="kr",
            sort=Sort.NEWEST,
            count=200,
            continuation_token=continuation_token,
        )
        if not result:
            break
        batch_oldest = None
        for review in result:
            review_date = pd.to_datetime(review.get("at"), errors="coerce")
            if pd.isna(review_date):
                continue
            d = review_date.date()
            if batch_oldest is None or d < batch_oldest:
                batch_oldest = d
            if d >= start_date:
                collected.append(review)
        if continuation_token is None:
            break
        if batch_oldest is not None and batch_oldest < start_date:
            break
    return collected


# E. 리뷰 분석기 캐싱 함수 정의
def get_reviews(
        
    # E-1. 앱 ID와 수집 옵션을 받아 리뷰를 수집하는 함수 정의
    app_id,
    count=100,
    crawl_mode="count_latest",
    period_days=None,
):
    
    # E-2. 수집 모드에 따라 리뷰를 수집하는 함수 호출
    # If google_play_scraper isn't available, provide a small synthetic
    # dataset so the app can run for demo purposes.
    if not _HAS_GOOGLE_PLAY_SCRAPER:
        sample_count = min(100, max(1, int(count)))
        collected = []
        for i in range(sample_count):
            collected.append(
                {
                    "at": pd.Timestamp.now() - pd.Timedelta(days=i),
                    "userName": f"sample_user_{i}",
                    "score": 5 - (i % 5),
                    "content": f"샘플 리뷰 내용 {i} - 만족" if i % 2 == 0 else f"샘플 리뷰 내용 {i} - 불만족",
                }
            )
    else:
        if crawl_mode == "period_all":
            safe_days = max(1, int(period_days or 1))
            start_date = date.today() - timedelta(days=safe_days)
            collected = _get_reviews_since(app_id, start_date)
        else:
            safe_count = max(1, min(10000, int(count)))
            collected = _get_reviews_latest(app_id, safe_count)
    
    # E-3. 수집된 리뷰를 데이터프레임으로 변환하고, 날짜 형식으로 변환하여 정렬
    df = pd.DataFrame(collected)

    # E-4. 리뷰 데이터가 없는 경우 빈 데이터프레임 반환, 날짜 형식으로 변환하여 정렬
    if df.empty:
        return pd.DataFrame(columns=["at", "userName", "score", "content"])
    df = df[["at", "userName", "score", "content"]]
    df["at"] = pd.to_datetime(df["at"], errors="coerce")
    df = df.sort_values("at", ascending=True, na_position="last").reset_index(drop=True)
    return df