import streamlit as st
import pandas as pd
from app_scraper import get_reviews
from analyzer import ReviewAnalyzer

# 페이지 설정
st.set_page_config(page_title="ReviewMachine v2", layout="wide")

st.title("📊 ReviewMachine v2: 앱 리뷰 감성 분석기")
st.markdown("구글 플레이 스토어의 앱 ID를 입력하여 실시간 리뷰 분석 결과를 확인하세요.")

# 사이드바 설정
with st.sidebar:
    st.header("설정")
    app_id = st.text_input("앱 ID 입력", value="com.kakao.talk")
    review_count = st.slider("수집 개수", min_value=10, max_value=200, value=50)
    analyze_button = st.button("데이터 수집 및 분석 시작")

# 분석 로직 실행
if analyze_button:
    with st.spinner('리뷰 수집 및 AI 분석 중...'):
        # 1. 수집
        df = get_reviews(app_id, count=review_count)
        
        # 2. 분석
        analyzer = ReviewAnalyzer()
        texts = df['content'].tolist()
        predictions = analyzer.analyze(texts)
        
        # 3. 데이터 가공
        df['sentiment'] = [('긍정' if p['label'] == '1' else '부정') for p in predictions]
        df['confidence'] = [p['score'] for p in predictions]

        # 4. 결과 시각화 - 요약 통계
        col1, col2 = st.columns(2)
        pos_count = len(df[df['sentiment'] == '긍정'])
        neg_count = len(df[df['sentiment'] == '부정'])

        col1.metric("긍정 리뷰", f"{pos_count}개")
        col2.metric("부정 리뷰", f"{neg_count}개")

        # 5. 차트 표시
        st.subheader("감성 분포")
        st.bar_chart(df['sentiment'].value_counts())

        # 6. 데이터 표 표시
        st.subheader("상세 리뷰 분석 결과")
        st.dataframe(df, use_container_width=True)

        # 7. 다운로드 버튼
        csv = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button(
            label="분석 결과 CSV 다운로드",
            data=csv,
            file_name=f"analysis_{app_id}.csv",
            mime="text/csv",
        )