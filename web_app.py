import streamlit as st
import pandas as pd
from app_scraper import get_reviews
from analyzer import ReviewAnalyzer

# 페이지 설정
st.set_page_config(page_title="ReviewMachine v2", layout="wide")

st.title("📊 ReviewMachine v2: 앱 리뷰 감성 분석기")
st.markdown("구글 플레이 스토어의 앱 ID를 입력하여 실시간 리뷰 분석 결과를 확인하세요.")

# --- 사이드바 설정 영역 ---
with st.sidebar:
    st.header("입력 방식 선택")
    menu = st.radio("데이터 소스", ["실시간 크롤링", "CSV 파일 업로드"])
    
    if menu == "실시간 크롤링":
        app_id = st.text_input("앱 ID 입력", value="com.kakao.talk")
        review_count = st.slider("수집 개수", 10, 200, 50)
    else:
        uploaded_file = st.file_uploader("CSV 파일을 선택하세요", type=['csv'])
        if uploaded_file is not None:
            # 업로드된 파일명에서 확장자를 제거하여 app_id로 사용 (예: data.csv -> data)
            app_id = uploaded_file.name.split('.')[0]
        else:
            app_id = "uploaded_file" # 파일이 아직 없을 때의 기본값

    analyze_button = st.button("분석 시작")

# --- 메인 분석 로직 영역 ---
if analyze_button:
    df = None # 분석할 데이터 저장 변수

    with st.spinner('데이터 준비 및 AI 분석 중...'):
        # 1. 데이터 로드 (분기 처리)
        if menu == "실시간 크롤링":
            df = get_reviews(app_id, count=review_count)
        elif menu == "CSV 파일 업로드" and uploaded_file is not None:
            df = pd.read_csv(uploaded_file)
            # 필수 컬럼(content)이 있는지 확인
            if 'content' not in df.columns:
                st.error("CSV 파일에 'content' 컬럼이 필요합니다.")
                st.stop()
        
        if df is not None:
            analyzer = ReviewAnalyzer()
            texts = df['content'].tolist()
            
            # analyzer.py에서 업그레이드한 함수 호출
            analysis_results = analyzer.analyze_list(texts)
            
            # 결과 대입 (코드가 훨씬 간결해집니다!)
            df['sentiment'] = [r['sentiment'] for r in analysis_results]
            df['sentiment_score'] = [r['sentiment_score'] for r in analysis_results]
            df['confidence'] = [r['confidence'] for r in analysis_results]

        # --- 추가되는 시계열 분석 로직 ---
        st.subheader("📈 시간 흐름에 따른 감성 추이")

        # 순서 고정을 위한 설정
        sentiment_order = ['매우 부정', '부정', '보통', '긍정', '매우 긍정']
        sentiment_counts = df['sentiment'].value_counts().reindex(sentiment_order, fill_value=0)

        # 막대 그래프 출력
        st.bar_chart(sentiment_counts)

        # 시계열 그래프 (기존 점수 체계 유지)
        st.subheader("📈 시간 흐름에 따른 감성 점수 추이")
        df['at'] = pd.to_datetime(df['at'])
        df['date'] = df['at'].dt.date
        timeline_df = df.groupby('date')['sentiment_score'].mean().reset_index()
        st.line_chart(data=timeline_df, x='date', y='sentiment_score')
        
        st.info("💡 위 그래프가 0보다 위에 있으면 긍정적, 아래에 있으면 부정적인 여론이 강했음을 의미합니다.")

        # 4. 결과 시각화 - 요약 통계 (5개 컬럼으로 확장)
        col1, col2, col3, col4, col5 = st.columns(5)
        
        # 각 상태별 개수 계산
        v_pos = len(df[df['sentiment'] == '매우 긍정'])
        pos = len(df[df['sentiment'] == '긍정'])
        neu = len(df[df['sentiment'] == '보통'])
        neg = len(df[df['sentiment'] == '부정'])
        v_neg = len(df[df['sentiment'] == '매우 부정'])

        # 메트릭 표시
        col1.metric("매우 긍정", f"{v_pos}개")
        col2.metric("긍정", f"{pos}개")
        col3.metric("보통", f"{neu}개")
        col4.metric("부정", f"{neg}개")
        col5.metric("매우 부정", f"{v_neg}개")

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
        st.success("데이터 분석이 완료되었습니다!")