from datetime import date, timedelta

from google_play_scraper import Sort, reviews
import pandas as pd


def _get_reviews_latest(app_id, safe_count):
    collected = []
    continuation_token = None

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


def _get_reviews_since(app_id, start_date):
    collected = []
    continuation_token = None

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


def get_reviews(
    app_id,
    count=100,
    crawl_mode="count_latest",
    period_days=None,
):
    """
    특정 앱의 ID를 입력받아 리뷰를 수집하고 데이터프레임으로 변환합니다.

    crawl_mode:
      - "count_latest": 최신순에서 count개 수집
      - "period_all": 오늘 기준 period_days 이내 리뷰 전체 수집
    """
    if crawl_mode == "period_all":
        safe_days = max(1, int(period_days or 1))
        start_date = date.today() - timedelta(days=safe_days)
        collected = _get_reviews_since(app_id, start_date)
    else:
        safe_count = max(1, min(10000, int(count)))
        collected = _get_reviews_latest(app_id, safe_count)

    df = pd.DataFrame(collected)
    if df.empty:
        return pd.DataFrame(columns=["at", "userName", "score", "content"])

    df = df[["at", "userName", "score", "content"]]
    df["at"] = pd.to_datetime(df["at"], errors="coerce")
    df = df.sort_values("at", ascending=True, na_position="last").reset_index(drop=True)

    return df

if __name__ == "__main__":
    # 코드가 잘 작동하는지 테스트하기 위한 구간입니다.
    # 테스트용 앱 ID: 'com.kakao.talk' (카카오톡)
    print("데이터 수집 중...")
    test_df = get_reviews('com.kakao.talk', count=10)
    print(test_df)
