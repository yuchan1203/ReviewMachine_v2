# A. 모듈 임포트
import plotly.express as px
import pandas as pd

# B. 감정 분석 결과를 바탕으로 막대 그래프 또는 도넛 차트를 생성하는 함수 정의
def draw_sentiment_charts(df, chart_type):
    # B-1. 순서 및 색상 정의
    sentiment_order = ['매우 부정', '부정', '보통', '긍정', '매우 긍정']
    color_map = {
        '매우 부정': '#FF4B4B', '부정': '#FFA500', '보통': '#FFFF00',
        '긍정': '#00FF00', '매우 긍정': '#0000FF'
    }

    # B-2. 데이터 집계
    chart_data = df['sentiment'].value_counts().reindex(sentiment_order, fill_value=0).reset_index()
    chart_data.columns = ['감정', '개수']

    # B-3. 차트 생성
    if chart_type == "막대 그래프":
        fig = px.bar(
            chart_data, x='감정', y='개수', color='감정',
            color_discrete_map=color_map, 
            category_orders={'감정': sentiment_order}
        )
    else:
        fig = px.pie(
            chart_data, names='감정', values='개수', color='감정',
            color_discrete_map=color_map, hole=0.5,
            category_orders={'감정': sentiment_order}
        )

    # B-4. 레이아웃 조정
    fig.update_layout(
        title="감정 분포",
        showlegend=False,
        xaxis_title="감정",
        yaxis_title="개수",
        xaxis={'categoryorder':'array', 'categoryarray':sentiment_order}
    )

    # B-5. 차트 반환
    return fig