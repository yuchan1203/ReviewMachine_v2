'''
이 파일은 리뷰 데이터의 로딩, 검증, 감정 분석 실행을 담당하는 파이프라인을 정의합니다.
A. 모듈 임포트: 필요한 라이브러리 로딩
B. 상수 및 예외 정의: 분석된 데이터프레임 여부 판단을 위한 컬럼 목록과 사용자에게 안내 가능한 예외 정의
C. 데이터 검증 및 분석 함수 정의: 분석된 데이터프레임 여부 판단 함수와 입력 데이터 검증 함수 정의
D. 입력 데이터 검증 함수 정의: 데이터프레임이 None이거나 비어 있는 경우, 필수 컬럼이 없는 경우, 리뷰 본문이 모두 비어 있는 경우에 대한 예외 처리
E. 리뷰 데이터 로딩 함수 정의: 실시간 크롤링과 CSV 파일 업로드에 따른 데이터 로딩 및 검증 로직 구현
F. 감정 분석 실행 함수 정의: 입력 데이터 검증, 리뷰 분석기 인스턴스 생성, 배치 단위로 감정 분석 실행 및 진행 상황 업데이트, 분석 결과를 데이터프레임에 추가하는 로직 구현
'''


# A. 모듈 임포트

# A-1. 표준 라이브러리
from datetime import datetime
import pandas as pd

# A-2. 프로젝트 내부 모듈
from app_scraper import get_reviews
from analyzer import get_review_analyzer


# B. 상수 및 예외 정의

# B-1. 분석된 데이터프레임 여부 판단을 위한 컬럼 목록
ANALYZED_COLUMNS = ["sentiment", "sentiment_score", "confidence"]
REQUIRED_COLUMNS = ["at", "content"]

# B-2. 사용자에게 안내 가능한 데이터/분석 단계 예외 정의
class ReviewPipelineError(Exception):
    pass


# C. 데이터 검증 및 분석 함수 정의
def is_analyzed_dataframe(df):
    return all(col in df.columns for col in ANALYZED_COLUMNS)


# D. 입력 데이터 검증 함수 정의
def validate_input_dataframe(df):

    # D-1. 데이터프레임이 None인 경우 예외 발생
    if df is None:
        raise ReviewPipelineError("데이터를 불러오지 못했습니다.")
    
    # D-2. 데이터프레임이 비어 있는 경우 예외 발생
    if df.empty:
        raise ReviewPipelineError("리뷰 데이터가 비어 있습니다.")
    
    # D-3. 필수 컬럼이 없는 경우 예외 발생
    missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_columns:
        raise ReviewPipelineError(
            f"필수 컬럼이 없습니다: {', '.join(missing_columns)}. "
            "CSV에 at, content 컬럼이 포함되어 있는지 확인해주세요."
        )
    
    # D-4. 리뷰 본문이 모두 비어 있는 경우 예외 발생
    non_empty_content = df["content"].astype(str).str.strip() != ""
    if not non_empty_content.any():
        raise ReviewPipelineError("리뷰 본문(content)에 분석 가능한 텍스트가 없습니다.")




# E. 리뷰 데이터 로딩 함수 정의
def load_source_dataframe(menu, app_id, review_count, start_date, end_date, uploaded_file, crawl_mode="count_latest", period_days=None):

    # E-1. 실시간 크롤링 선택
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
    
    # E-2. CSV 파일 업로드 선택
    if menu == "CSV 파일 업로드" and uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
        except Exception as exc:
            raise ReviewPipelineError("CSV 파일을 읽는 중 오류가 발생했습니다.") from exc
        validate_input_dataframe(df)
        return df, is_analyzed_dataframe(df)
    
    # E-3. 그 외의 경우는 예외 처리
    raise ReviewPipelineError("데이터를 불러오는 방법을 선택하고, 필요한 정보를 입력해주세요.")


# F. 감정 분석 실행 함수 정의
def run_sentiment_analysis(df, progress_callback=None, batch_size=32, device="cpu", return_runtime_info=False):

    # F-1. 입력 데이터 검증
    validate_input_dataframe(df)
    
    # F-2. 리뷰 분석기 인스턴스 생성 및 감정 분석 실행
    analyzer = get_review_analyzer(device=device)
    texts = df["content"].fillna("").astype(str).tolist()
    total = len(texts)
    analysis_results = []

    # F-3. 리뷰가 없는 경우 바로 반환
    if total == 0:
        if return_runtime_info:
            return df, analyzer.runtime_info()
        return df

    # F-4. 배치 단위로 감정 분석 실행 및 진행 상황 업데이트
    safe_batch_size = max(1, int(batch_size))
    for start_idx in range(0, total, safe_batch_size):
        end_idx = min(start_idx + safe_batch_size, total)
        batch_texts = texts[start_idx:end_idx]
        analysis_results.extend(analyzer.analyze_list(batch_texts))
        if progress_callback is not None:
            progress_callback(end_idx, total)
    
    # F-5. 분석 결과를 데이터프레임에 추가
    df["sentiment"] = [r["sentiment"] for r in analysis_results]
    df["sentiment_score"] = [r["sentiment_score"] for r in analysis_results]
    df["confidence"] = [r["confidence"] for r in analysis_results]
    
    # F-6. 런타임 정보 반환 여부에 따라 결과 반환
    if return_runtime_info:
        return df, analyzer.runtime_info()
    
    # F-7. 분석된 데이터프레임 반환
    return df
