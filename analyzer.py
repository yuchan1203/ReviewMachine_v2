from transformers import pipeline


class ReviewAnalyzer:
    def __init__(self, device="cpu"):
        # GPU/CPU 디바이스 설정
        device_map = 0 if device != "cpu" else -1
        
        self.model = pipeline(
            "sentiment-analysis", 
            model="jaehyeong/koelectra-base-v3-generalized-sentiment-analysis",
            device=device_map
        )

    def _refine_sentiment(self, result):
        """제안해주신 대칭적 5단계 분류 로직"""
        label = result['label']
        score = result['score']
        
        # 1. 긍정 확신 구간 (label '1')
        if label == '1':
            if score >= 0.85:
                return '매우 긍정', 2
            elif score >= 0.55:
                return '긍정', 1
            else:
                return '보통', 0
                
        # 2. 부정 확신 구간 (label '0')
        else:
            if score >= 0.85:
                return '매우 부정', -2
            elif score >= 0.55:
                return '부정', -1
            else:
                return '보통', 0

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
            refined_data.append({
                'sentiment': sentiment_text,
                'sentiment_score': sentiment_score,
                'confidence': round(res['score'], 2)
            })
        return refined_data