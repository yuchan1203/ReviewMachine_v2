from transformers import pipeline


class ReviewAnalyzer:
    def __init__(self, device="cpu"):
        self.mode = "primary"
        self.model = None
        self.model_error = None
        self.device = device
        self.pipeline_device = self._resolve_pipeline_device(device)

        try:
            self.model = pipeline(
                "sentiment-analysis",
                model="jaehyeong/koelectra-base-v3-generalized-sentiment-analysis",
                device=self.pipeline_device,
            )
            self.mode = "primary"
            return
        except Exception as exc:
            self.model_error = exc

        try:
            self.model = pipeline(
                "sentiment-analysis",
                model="nlptown/bert-base-multilingual-uncased-sentiment",
                device=self.pipeline_device,
            )
            self.mode = "fallback_multilingual"
            return
        except Exception:
            self.model = None
            self.mode = "rule_based"

    def _resolve_pipeline_device(self, device):
        if device != "gpu":
            return -1
        try:
            import torch

            if torch.cuda.is_available():
                return 0
        except Exception:
            pass
        self.device = "cpu"
        return -1

    def _refine_sentiment_primary(self, result):
        label = result["label"]
        score = result["score"]
        if label == "1":
            if score >= 0.85:
                return "매우 긍정", 2
            if score >= 0.55:
                return "긍정", 1
            return "보통", 0
        if score >= 0.85:
            return "매우 부정", -2
        if score >= 0.55:
            return "부정", -1
        return "보통", 0

    def _refine_sentiment_multilingual(self, result):
        label = str(result.get("label", "")).strip()
        score = float(result.get("score", 0.5))
        stars = 3
        if label and label[0].isdigit():
            stars = int(label[0])

        if stars >= 5:
            return "매우 긍정", 2, score
        if stars == 4:
            return "긍정", 1, score
        if stars == 3:
            return "보통", 0, score
        if stars == 2:
            return "부정", -1, score
        return "매우 부정", -2, score

    def _rule_based_score(self, text):
        t = (text or "").strip()
        if not t:
            return "보통", 0, 0.5

        pos_words = ["좋", "최고", "만족", "추천", "편리", "훌륭", "감사"]
        neg_words = ["별로", "최악", "불편", "오류", "버그", "느림", "짜증", "삭제"]
        pos = sum(1 for w in pos_words if w in t)
        neg = sum(1 for w in neg_words if w in t)
        diff = pos - neg

        if diff >= 2:
            return "매우 긍정", 2, 0.6
        if diff == 1:
            return "긍정", 1, 0.58
        if diff == 0:
            return "보통", 0, 0.5
        if diff == -1:
            return "부정", -1, 0.58
        return "매우 부정", -2, 0.6

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
            if self.mode == "primary":
                sentiment, sentiment_score = self._refine_sentiment_primary(res)
                confidence = round(float(res.get("score", 0.5)), 2)
            else:
                sentiment, sentiment_score, confidence = self._refine_sentiment_multilingual(res)
                confidence = round(confidence, 2)
            refined.append(
                {
                    "sentiment": sentiment,
                    "sentiment_score": sentiment_score,
                    "confidence": confidence,
                }
            )
        return refined

    def runtime_info(self):
        return {
            "requested_device": self.device,
            "actual_device": "gpu" if self.pipeline_device == 0 else "cpu",
            "model_mode": self.mode,
        }
