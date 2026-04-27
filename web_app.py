# A. 모듈 임포트 및 설정

# A-1.UI 관련 모듈
import streamlit as st

# A-2. 경고 무시 및 로거 조절
import warnings
import os
warnings.filterwarnings("ignore")
from transformers import logging
logging.set_verbosity_error() # 에러 수준이 아니면 출력하지 않음
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

# A-3. 데이터 처리 관련 모듈 
import pandas as pd
from app_scraper import get_reviews
from analyzer import ReviewAnalyzer
from visualizer import draw_sentiment_charts
from data_utils import calculate_sentiment_counts, prepare_timeline_data


# B. 사전 설정 및 화면 설정

# B-1. 분석 결과 저장
if 'analyzed_df' not in st.session_state:
    st.session_state.analyzed_df = None
if 'current_app_id' not in st.session_state:
    st.session_state.current_app_id = ""

# B-2. 화면 설정
st.set_page_config(page_title="ReviewMachine v2", layout="wide")
st.title("📊 ReviewMachine v2: 앱 리뷰 감성 분석기")
st.markdown("구글 플레이 스토어의 앱 ID를 입력하여 실시간 리뷰 분석 결과를 확인하세요.")

# B-3. 사이드바 설정
with st.sidebar:
    st.header("입력 방식 선택")
    menu = st.radio("데이터 소스", ["실시간 크롤링", "CSV 파일 업로드"])
    
    if menu == "실시간 크롤링":
        app_id = st.text_input("앱 ID 입력", value="com.kakao.talk")
        review_count = st.slider("수집 개수", 10, 200, 50)
    else:
        uploaded_file = st.file_uploader("CSV 파일을 선택하세요", type=['csv'])
        if uploaded_file is not None:
            app_id = uploaded_file.name.split('.')[0]
        else:
            app_id = "uploaded_file"

    analyze_button = st.button("분석 시작")


# C. 메인 분석 로직
if analyze_button:
    # C-1. 데이터 초기화
    df = None

    with st.spinner('데이터를 준비 중입니다...'):
        # C-2. 데이터 소스 확보
        if menu == "실시간 크롤링":
            df = get_reviews(app_id, count=review_count)
            is_already_analyzed = False
        elif menu == "CSV 파일 업로드" and uploaded_file is not None:
            df = pd.read_csv(uploaded_file)
            is_already_analyzed = all(col in df.columns for col in ['sentiment', 'sentiment_score', 'confidence'])

        if df is not None:
            # C-3. 분석 단계: 이미 분석된 파일이 아니라면 AI 엔진 가동
            if not is_already_analyzed:
                with st.spinner('AI 감정 분석 중...'):
                    analyzer = ReviewAnalyzer()
                    texts = df['content'].tolist()
                    analysis_results = analyzer.analyze_list(texts)
                    
                    df['sentiment'] = [r['sentiment'] for r in analysis_results]
                    df['sentiment_score'] = [r['sentiment_score'] for r in analysis_results]
                    df['confidence'] = [r['confidence'] for r in analysis_results]
            # C-4. 분석 완료 후 세션 상태에 저장
            st.session_state.analyzed_df = df
            st.session_state.current_app_id = app_id
            st.success("데이터 분석이 완료되었습니다!")


# D. 결과 출력 로직
if st.session_state.analyzed_df is not None:

    # D-1. 세션에서 데이터 복구
    df = st.session_state.analyzed_df
    current_app_id = st.session_state.current_app_id

    # D-2. 감정 분포 차트
    with st.expander("📊 감성 분포 시각화 및 통계", expanded=False):
        sentiment_counts = calculate_sentiment_counts(df)
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("매우 긍정", f"{sentiment_counts['매우 긍정']}개")
        col2.metric("긍정", f"{sentiment_counts['긍정']}개")
        col3.metric("보통", f"{sentiment_counts['보통']}개")
        col4.metric("부정", f"{sentiment_counts['부정']}개")
        col5.metric("매우 부정", f"{sentiment_counts['매우 부정']}개")
        st.divider()
        chart_type = st.radio(
            "차트 종류 선택",
            ["막대 그래프", "도넛형 차트"],
            horizontal=True,
            key="chart_type_expander",
        )
        fig = draw_sentiment_charts(df, chart_type)
        st.plotly_chart(fig, width='stretch')

    # D-3. 시간 흐름 그래프
    with st.expander("📈 시간 흐름에 따른 감정 점수 추이", expanded=True):
        timeline_df = prepare_timeline_data(df)
        st.line_chart(data=timeline_df, x="date", y="sentiment_score")
        st.info("💡 0보다 위면 긍정, 아래면 부정적인 여론을 의미합니다.")

    # D-4. 상세 데이터 및 다운로드
    with st.expander("📄 상세 리뷰 데이터 및 내보내기", expanded=False):
        st.dataframe(df, width='stretch')
        
        csv = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button(
            label="분석 결과 CSV 다운로드",
            data=csv,
            file_name=f"analyzed_{current_app_id}.csv",
            mime="text/csv",
        )