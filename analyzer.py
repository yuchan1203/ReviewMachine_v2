'''
이 파일은 리뷰 분석기의 핵심 로직을 포함하고 있습니다.
모델 로드, 감정 분석 수행, 그리고 입력 데이터 검증과 관련된 기능이 구현되어 있습니다.
또한, 예외 처리를 통해 사용자에게 명확한 피드백을 제공할 수 있도록 설계되었습니다.
'''

<<<<<<< HEAD
"""
A lightweight analyzer factory with simple in-memory caching to replace
Streamlit's `cache_resource` decorator. Keeps one cached analyzer per
`device` key.
"""
from functools import lru_cache


@lru_cache(maxsize=16)
def get_review_analyzer(device="cpu", hf_token: str | None = None):
    """Return a cached ReviewAnalyzer for the given device and optional HF token.

    The HF token is included in the cache key so callers that pass a different
    token will get a separate analyzer instance which can load private models.
    """
    return ReviewAnalyzer(device=device, hf_token=hf_token)
=======
# A. 모델 임포트
import streamlit as st
# Defer importing `transformers` until model construction to avoid
# pulling heavy dependencies (like `torch`) at module import time.
_HAS_TRANSFORMERS = None

# B. 리뷰 분석기 정의
@st.cache_resource(show_spinner=False)
def get_review_analyzer(device="cpu"):
    """ReviewAnalyzer 인스턴스를 캐시하여 재시작 시 모델을 다시 로드하지 않음

    If the `transformers` package is not available, this will return a
    rule-based analyzer so the app can run without heavy dependencies.
    """
    return ReviewAnalyzer(device=device)
>>>>>>> b9b8b76aa51729b16ac6e463598c50f47734bdce

# C. 예외 정의
class ReviewPipelineError(Exception):
    """사용자에게 안내 가능한 데이터/분석 단계 예외"""
    pass

# D. 입력 데이터 검증 및 로딩 함수
REQUIRED_COLUMNS = ["at", "content"]
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

# E. 리뷰 분석기 클래스
class ReviewAnalyzer:
    # E-1. 초기화: 모델 로드 및 디바이스 설정
<<<<<<< HEAD
    def __init__(self, device="cpu", mode="transformers", hf_token: str | None = None):
        self.mode = mode
        self.device = device
        self.model = None
        self.hf_token = hf_token
=======
    def __init__(self, device="cpu", mode="transformers"):
        self.mode = mode
        self.device = device
        self.model = None
>>>>>>> b9b8b76aa51729b16ac6e463598c50f47734bdce

        # Try to import transformers.pipeline lazily and construct the model
        if mode == "transformers":
            try:
                from transformers import pipeline
                _HAS = True
            except Exception:
                pipeline = None
                _HAS = False

            if _HAS:
                device_map = 0 if device != "cpu" else -1
                try:
<<<<<<< HEAD
                    # Pass the Hugging Face auth token when provided so private
                    # models or gated checkpoints can be loaded.
                    kwargs = {"device": device_map}
                    if self.hf_token:
                        kwargs["use_auth_token"] = self.hf_token
                    self.model = pipeline(
                        "sentiment-analysis",
                        model="jaehyeong/koelectra-base-v3-generalized-sentiment-analysis",
                        **kwargs,
=======
                    self.model = pipeline(
                        "sentiment-analysis",
                        model="jaehyeong/koelectra-base-v3-generalized-sentiment-analysis",
                        device=device_map,
>>>>>>> b9b8b76aa51729b16ac6e463598c50f47734bdce
                    )
                except Exception:
                    # Fall back to rule-based if model fails to load
                    self.model = None
                    self.mode = "rule_based"
            else:
                self.model = None
                self.mode = "rule_based"
        else:
            self.mode = "rule_based"

    # E-2. 런타임 정보 반환
    def runtime_info(self):
        return {
            "requested_device": self.device,
            "actual_device": "GPU" if self.device != "cpu" else "CPU",
            "model_mode": self.mode
        }
    
    # E-3. 감정 분석 결과를 5단계로 세분화하는 로직
    def _refine_sentiment(self, result):
        # Normalize label handling from various models
        label = str(result.get('label', '')).lower()
        score = float(result.get('score', 0.0))

        # Interpret label heuristically: positive vs negative
        is_positive = any(k in label for k in ['1', 'pos', 'positive', '긍정'])

        if is_positive:
            if score >= 0.85:
                return '매우 긍정', 2
            elif score >= 0.55:
                return '긍정', 1
            else:
                return '보통', 0
        else:
            if score >= 0.85:
                return '매우 부정', -2
            elif score >= 0.55:
                return '부정', -1
            else:
                return '보통', 0
    
    # E-4. 룰 기반 감정 분석 (예시)
    def _rule_based_score(self, text):
        positive_keywords = ['좋아요', '최고', '추천', '만족']
        negative_keywords = ['별로', '최악', '비추천', '불만족']
        positive_score = sum(text.count(word) for word in positive_keywords)
        negative_score = sum(text.count(word) for word in negative_keywords)
        if positive_score > negative_score:
            sentiment = '긍정'
            sentiment_score = 1
            confidence = positive_score / (positive_score + negative_score + 1e-5)
        elif negative_score > positive_score:
            sentiment = '부정'
            sentiment_score = -1
            confidence = negative_score / (positive_score + negative_score + 1e-5)
        else:
            sentiment = '보통'
            sentiment_score = 0
            confidence = 0.5
        return sentiment, sentiment_score, confidence
    
    # E-5. 텍스트 리스트에 대한 감정 분석 수행
    def analyze_list(self, texts):
        if self.mode == "rule_based" or (self.mode == "transformers" and self.model is None):
            refined = []
            for text in texts:
                sentiment, sentiment_score, confidence = self._rule_based_score(text)
                refined.append(
                    {
                        "sentiment": sentiment,
                        "sentiment_score": sentiment_score,
                        "confidence": round(confidence, 2),
                    }
                )
            return refined
        raw_results = self.model(texts)
        refined = []
        for res in raw_results:
            sentiment_text, sentiment_score = self._refine_sentiment(res)
            refined.append({
                'sentiment': sentiment_text,
                'sentiment_score': sentiment_score,
                'confidence': round(res['score'], 2)
            })
        return refined