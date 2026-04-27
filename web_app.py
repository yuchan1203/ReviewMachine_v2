# 화면 설정 관련 모듈
import streamlit as st

# 경고 무시 및 로거 조절
import warnings
import os
warnings.filterwarnings("ignore")
from transformers import logging
logging.set_verbosity_error() # 에러 수준이 아니면 출력하지 않음
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

# 데이터 처리 관련 모듈 
import pandas as pd
from app_scraper import get_reviews
from analyzer import ReviewAnalyzer
import plotly.express as px

# 분석 결과 저장
if 'analyzed_df' not in st.session_state:
    st.session_state.analyzed_df = None
if 'current_app_id' not in st.session_state:
    st.session_state.current_app_id = ""

# 화면 설정
st.set_page_config(page_title="ReviewMachine v2", layout="wide")
st.title("📊 ReviewMachine v2: 앱 리뷰 감성 분석기")
st.markdown("구글 플레이 스토어의 앱 ID를 입력하여 실시간 리뷰 분석 결과를 확인하세요.")

# 사이드바 설정
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

# 메인 분석 로직
if analyze_button:
    df = None

    with st.spinner('데이터를 준비 중입니다...'):
        # 데이터 소스 확보
        if menu == "실시간 크롤링":
            df = get_reviews(app_id, count=review_count)
            is_already_analyzed = False
        elif menu == "CSV 파일 업로드" and uploaded_file is not None:
            df = pd.read_csv(uploaded_file)
            is_already_analyzed = all(col in df.columns for col in ['sentiment', 'sentiment_score', 'confidence'])

        if df is not None:
            # 분석 단계: 이미 분석된 파일이 아니라면 AI 엔진 가동
            if not is_already_analyzed:
                with st.spinner('AI 감정 분석 중...'):
                    analyzer = ReviewAnalyzer()
                    texts = df['content'].tolist()
                    analysis_results = analyzer.analyze_list(texts)
                    
                    df['sentiment'] = [r['sentiment'] for r in analysis_results]
                    df['sentiment_score'] = [r['sentiment_score'] for r in analysis_results]
                    df['confidence'] = [r['confidence'] for r in analysis_results]
            # 분석 완료 후 세션 상태에 저장
            st.session_state.analyzed_df = df
            st.session_state.current_app_id = app_id
            st.success("데이터 분석이 완료되었습니다!")

# --- [2] 결과 출력 로직 (세션에 데이터가 있으면 무조건 표시) ---
if st.session_state.analyzed_df is not None:
    # 세션에서 데이터 복구
    df = st.session_state.analyzed_df
    current_app_id = st.session_state.current_app_id

    # 감정 순서 고정을 위한 설정
    sentiment_order = ['매우 부정', '부정', '보통', '긍정', '매우 긍정']

    # 1. 시계열 그래프
    st.subheader("📈 시간 흐름에 따른 감정 점수 추이")
    df['at'] = pd.to_datetime(df['at'])
    df['date'] = df['at'].dt.date
    timeline_df = df.groupby('date')['sentiment_score'].mean().reset_index()
    st.line_chart(data=timeline_df, x='date', y='sentiment_score')
    st.info("💡 위 그래프가 0보다 위에 있으면 긍정적, 아래에 있으면 부정적인 여론이 강했음을 의미합니다.")

    # 2. 요약 지표 (Metric)
    col1, col2, col3, col4, col5 = st.columns(5)
    v_pos = len(df[df['sentiment'] == '매우 긍정'])
    pos = len(df[df['sentiment'] == '긍정'])
    neu = len(df[df['sentiment'] == '보통'])
    neg = len(df[df['sentiment'] == '부정'])
    v_neg = len(df[df['sentiment'] == '매우 부정'])

    col1.metric("매우 긍정", f"{v_pos}개")
    col2.metric("긍정", f"{pos}개")
    col3.metric("보통", f"{neu}개")
    col4.metric("부정", f"{neg}개")
    col5.metric("매우 부정", f"{v_neg}개")

    # 3. 차트 시각화 섹션
    st.subheader("📊 감성 분포 시각화")
    chart_type = st.radio("차트 종류 선택", ["막대 그래프", "도넛형 차트"], horizontal=True)

    color_map = {
        '매우 부정': '#FF4B4B', '부정': '#FFA500', '보통': '#FFFF00',
        '긍정': '#00FF00', '매우 긍정': '#0000FF'
    }

    chart_data = df['sentiment'].value_counts().reindex(sentiment_order, fill_value=0).reset_index()
    chart_data.columns = ['감성', '개수']

    if chart_type == "막대 그래프":
        fig = px.bar(chart_data, x='감성', y='개수', color='감성',
                     color_discrete_map=color_map, category_orders={'감성': sentiment_order})
    else:
        fig = px.pie(chart_data, names='감성', values='개수', color='감성',
                     color_discrete_map=color_map, hole=0.5, category_orders={'감성': sentiment_order})

    st.plotly_chart(fig, width='stretch')

    # 4. 상세 데이터 및 다운로드
    st.subheader("상세 리뷰 분석 결과")
    st.dataframe(df, width='stretch')

    csv = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
    st.download_button(
        label="분석 결과가 포함된 CSV 다운로드",
        data=csv,
        file_name=f"analyzed_{current_app_id}.csv",
        mime="text/csv",
    )