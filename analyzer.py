from transformers import pipeline

class ReviewAnalyzer:
    def __init__(self):
        # 한국어 감성 분석에 특화된 모델 로드
        # 'sentiment-analysis' 파이프라인을 사용하여 긍정/부정을 분류합니다.
        self.model = pipeline(
            "sentiment-analysis", 
            model="jaehyeong/koelectra-base-v3-generalized-sentiment-analysis"
        )

    def analyze(self, texts):
        """
        리뷰 텍스트 리스트를 받아 감성 분석 결과를 반환합니다.
        """
        results = self.model(texts)
        # 결과 예시: [{'label': '1', 'score': 0.99}] (1: 긍정, 0: 부정)
        return results

if __name__ == "__main__":
    # 테스트 코드
    analyzer = ReviewAnalyzer()
    samples = ["이 앱 정말 편리하고 좋아요!", "업데이트 이후로 자꾸 튕겨서 짜증나요."]
    predictions = analyzer.analyze(samples)
    
    for text, pred in zip(samples, predictions):
        sentiment = "긍정" if pred['label'] == '1' else "부정"
        print(f"리뷰: {text} -> 결과: {sentiment} ({pred['score']:.2f})")