import random
from datetime import date

from google_play_scraper import Sort, reviews
import pandas as pd


def _month_keys_inclusive(start_date: date, end_date: date):
    keys = []
    y, m = start_date.year, start_date.month
    while (y, m) <= (end_date.year, end_date.month):
        keys.append((y, m))
        if m == 12:
            y, m = y + 1, 1
        else:
            m += 1
    return keys


def _allocate_per_month(total: int, month_keys: list):
    n = len(month_keys)
    if n == 0:
        return {}
    base = total // n
    rem = total % n
    return {month_keys[i]: base + (1 if i < rem else 0) for i in range(n)}


def _reservoir_offer(reservoir: list, k: int, item: dict, seen: int) -> int:
    """Vitter: 무한 스트림에서 균등하게 k개 표본을 고르는 1-pass 리저버."""
    seen += 1
    if k <= 0:
        return seen
    if len(reservoir) < k:
        reservoir.append(item)
    else:
        j = random.randint(1, seen)
        if j <= k:
            reservoir[j - 1] = item
    return seen


def _review_in_window(review, start_date, end_date):
    review_date = pd.to_datetime(review.get("at"), errors="coerce")
    if pd.isna(review_date):
        return None
    d = review_date.date()
    if end_date is not None and d > end_date:
        return None
    if start_date is not None and d < start_date:
        return None
    return d


def _get_reviews_latest(app_id, safe_count, start_date, end_date):
    collected = []
    continuation_token = None
    reached_before_start = False

    while len(collected) < safe_count and not reached_before_start:
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
            d = review_date.date()
            if end_date is not None and d > end_date:
                continue
            if start_date is not None and d < start_date:
                reached_before_start = True
                continue

            collected.append(review)
            if len(collected) >= safe_count:
                break

        if continuation_token is None:
            break

    return collected


def _get_reviews_even_monthly(app_id, safe_count, start_date, end_date):
    month_keys = _month_keys_inclusive(start_date, end_date)
    quotas = _allocate_per_month(safe_count, month_keys)
    reservoirs = {k: [] for k in month_keys}
    seen_by_month = {k: 0 for k in month_keys}

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

            d = _review_in_window(review, start_date, end_date)
            if d is None:
                continue

            month_key = (d.year, d.month)
            q = quotas.get(month_key, 0)
            if q <= 0:
                continue

            seen_by_month[month_key] = _reservoir_offer(
                reservoirs[month_key], q, review, seen_by_month[month_key]
            )

        if continuation_token is None:
            break
        if start_date is not None and batch_oldest is not None and batch_oldest < start_date:
            break

    collected = []
    for mk in month_keys:
        collected.extend(reservoirs[mk])

    return collected


def get_reviews(
    app_id,
    count=100,
    start_date=None,
    end_date=None,
    sample_mode="latest",
):
    """
    특정 앱의 ID를 입력받아 리뷰를 수집하고 데이터프레임으로 변환합니다.

    sample_mode:
      - "latest": 기간 내에서 최신순으로 count개까지
      - "even_monthly": 기간을 월 단위로 나누고, 각 월에 count를 균등 배분한 뒤
        해당 월 리뷰 스트림에서 무작위(리저버 샘플링)로 추출
    """
    safe_count = int(count)
    if safe_count < 1:
        safe_count = 1
    if safe_count > 10000:
        safe_count = 10000

    if sample_mode == "even_monthly":
        if start_date is None or end_date is None:
            sample_mode = "latest"
        elif not _month_keys_inclusive(start_date, end_date):
            return pd.DataFrame(columns=["at", "userName", "score", "content"])

    if sample_mode == "even_monthly":
        collected = _get_reviews_even_monthly(app_id, safe_count, start_date, end_date)
    else:
        collected = _get_reviews_latest(app_id, safe_count, start_date, end_date)

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