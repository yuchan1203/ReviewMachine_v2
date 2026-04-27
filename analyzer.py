from transformers import pipeline

class ReviewAnalyzer:
    def __init__(self):
        # 모델 로드 (이전과 동일)
        self.model = pipeline(
            "sentiment-analysis", 
            model="jaehyeong/koelectra-base-v3-generalized-sentiment-analysis"
        )

    def _refine_sentiment(self, result):
        """내부용: 개별 분석 결과를 5단계로 세분화"""
        label = result['label']
        score = result['score']
        
        if label == '1': # 긍정 모델 기준
            if score >= 0.85: return '매우 긍정', 2
            else: return '긍정', 1
        else: # 부정 모델 기준
            if score >= 0.85: return '매우 부정', -2
            elif score >= 0.55: return '부정', -1
            else: return '보통', 0

    def analyze_list(self, texts):
        """리뷰 리스트를 받아 정제된 결과 리스트를 반환"""
        raw_results = self.model(texts)
        refined_data = []
        
        for res in raw_results:
            sentiment_text, sentiment_score = self._refine_sentiment(res)
            refined_data.append({
                'sentiment': sentiment_text,
                'sentiment_score': sentiment_score,
                'confidence': round(res['score'], 2)
            })
        return refined_data