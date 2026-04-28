# A. 모델 임포트
import streamlit as st
from transformers import pipeline

# B. 리뷰 분석기 정의
@st.cache_resource(show_spinner=False)
def get_review_analyzer(device="cpu"):
    """ReviewAnalyzer 인스턴스를 캐시하여 재시작 시 모델을 다시 로드하지 않음"""
    return ReviewAnalyzer(device=device)

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
    def __init__(self, device="cpu", mode="transformers"):
        device_map = 0 if device != "cpu" else -1
        self.mode = mode
        self.device = device
        self.model = pipeline(
            "sentiment-analysis", 
            model="jaehyeong/koelectra-base-v3-generalized-sentiment-analysis",
            device=device_map
        )

    # E-2. 런타임 정보 반환
    def runtime_info(self):
        return {
            "requested_device": self.device,
            "actual_device": "GPU" if self.device != "cpu" else "CPU",
            "model_mode": self.mode
        }
    
    # E-3. 감정 분석 결과를 5단계로 세분화하는 로직
    def _refine_sentiment(self, result):
        label = result['label']
        score = result['score']
        if label == '1':
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
        if self.mode == "rule_based":
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