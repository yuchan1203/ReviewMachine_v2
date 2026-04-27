import pandas as pd
from app_scraper import get_reviews
from analyzer import ReviewAnalyzer

def run_project(app_id, count=50):
    print(f"[{app_id}] 리뷰 수집을 시작합니다...")
    
    # 1. 데이터 수집 (3단계 결과물 활용)
    df = get_reviews(app_id, count)
    
    # 2. 감성 분석 엔진 초기화 (4단계 결과물 활용)
    print("AI 모델을 로드하여 분석 중입니다. 잠시만 기다려 주세요...")
    analyzer = ReviewAnalyzer()
    
    # 3. 분석 실행
    # 분석 모델의 입력으로 리뷰 내용(content) 리스트를 전달합니다.
    texts = df['content'].tolist()
    predictions = analyzer.analyze(texts)
    
    # 4. 결과 데이터 가공
    # 1은 긍정, 0은 부정으로 변환하여 새 컬럼에 저장
    df['sentiment'] = [('긍정' if p['label'] == '1' else '부정') for p in predictions]
    df['confidence'] = [round(p['score'], 2) for p in predictions]
    
    # 5. CSV 파일로 저장
    filename = f"reviews_{app_id}.csv"
    df.to_csv(filename, index=False, encoding='utf-8-sig')
    print(f"✅ 분석 완료! 결과가 '{filename}'에 저장되었습니다.")

if __name__ == "__main__":
    # 분석하고 싶은 앱 ID와 개수를 입력하세요.
    target_app = 'com.kakao.talk' 
    run_project(target_app, count=30)