# A. 모듈 임포트

# A-1. 표준 라이브러리
from datetime import datetime

# A-2. 서드파티 라이브러리
import pandas as pd
import plotly.express as px
import streamlit as st

# A-3. 프로젝트 내부 모듈
from data_utils import calculate_sentiment_counts, prepare_timeline_data_by_period
from visualizer import draw_sentiment_charts


# B. UI 섹션별 렌더링 함수 정의
def render_file_info_section(df, current_app_id):
    with st.expander("📄 CSV 파일 및 데이터 정보", expanded=True):
        info_df = df.copy()
        info_df["at"] = pd.to_datetime(info_df["at"])
        start_date = info_df["at"].min().strftime("%Y-%m-%d")
        end_date = info_df["at"].max().strftime("%Y-%m-%d")
        total_reviews = len(info_df)
        is_analyzed = all(col in info_df.columns for col in ["sentiment", "sentiment_score"])
        status_text = "✅ 분석 완료 데이터" if is_analyzed else "🔍 원본 데이터 (분석 필요)"
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        info_col1, info_col2 = st.columns(2)
        with info_col1:
            st.write(f"**📂 데이터 유형:** {status_text}")
            st.write(f"**📱 대상 앱 ID:** `{current_app_id}`")
            st.write(f"**🔢 리뷰 총 개수:** {total_reviews}개")
        with info_col2:
            st.write(f"**📅 데이터 기간:** {start_date} ~ {end_date}")
            st.write(f"**⏰ 조회/생성 일시:** {current_time}")


# C. 감정 분석 결과 시각화 섹션 렌더링 함수 정의
def render_sentiment_section(df):
    with st.expander("📊 감정 분포 시각화 및 통계", expanded=False):
        with st.expander("감정별 리뷰 수", expanded=True):
            sentiment_counts = calculate_sentiment_counts(df)
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("매우 긍정", f"{sentiment_counts['매우 긍정']}개")
            col2.metric("긍정", f"{sentiment_counts['긍정']}개")
            col3.metric("보통", f"{sentiment_counts['보통']}개")
            col4.metric("부정", f"{sentiment_counts['부정']}개")
            col5.metric("매우 부정", f"{sentiment_counts['매우 부정']}개")

        with st.expander("감정 분포 차트", expanded=True):
            chart_type = st.radio(
                "차트 종류 선택",
                ["막대 그래프", "도넛형 차트"],
                horizontal=True,
                key="chart_type_expander",
            )
            fig = draw_sentiment_charts(df, chart_type)
            st.plotly_chart(fig, width="stretch")


# D. 시간 흐름에 따른 감정 점수 추이 섹션 렌더링 함수 정의
def render_timeline_section(df):
    with st.expander("📈 시간 흐름에 따른 감정 점수 추이", expanded=True):
        period = st.radio(
            "집계 단위 선택",
            ["일별", "주별", "월별"],
            horizontal=True,
            key="timeline_period",
        )

        week_start = "월요일"
        if period == "주별":
            week_start = st.radio(
                "주 시작 요일",
                ["월요일", "일요일"],
                horizontal=True,
                key="timeline_week_start",
            )

        timeline_df = prepare_timeline_data_by_period(df, period, week_start=week_start)

        min_date = timeline_df["date"].min()
        max_date = timeline_df["date"].max()

        fig = px.line(
            timeline_df,
            x="date",
            y="sentiment_score",
            markers=True,
            labels={"date": "날짜", "sentiment_score": f"{period} 감정 점수 합계"},
        )
        fig.update_xaxes(range=[min_date, max_date], rangeslider_visible=False)
        st.plotly_chart(fig, width="stretch")
        st.info("💡 0보다 위면 긍정, 아래면 부정적인 여론을 의미합니다.")


# E. 상세 리뷰 데이터 섹션 렌더링 함수 정의
def render_detail_section(df, current_app_id):
    with st.expander("📄 상세 리뷰 데이터 및 내보내기", expanded=False):
        st.dataframe(df, width="stretch")
        csv = df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button(
            label="분석 결과 CSV 다운로드",
            data=csv,
            file_name=f"analyzed_{current_app_id}.csv",
            mime="text/csv",
        )
