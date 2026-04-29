from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import io
import pandas as pd

from server_state import save_upload, get_upload, save_analyzed, get_analyzed, save_runtime_info
from data_utils import calculate_sentiment_counts, prepare_timeline_data_by_period
# 기존에 만드신 파일에서 함수를 불러옵니다
from app_scraper import get_reviews 
from analyzer import get_review_analyzer

app = FastAPI(title="ReviewMachine V2 API")

# Serve a simple static frontend under /app
app.mount("/app", StaticFiles(directory="static", html=True), name="static")

# 데이터 규격 정의 (사용자가 보낼 데이터 형식)
class AnalyzeRequest(BaseModel):
    app_id: str
    count: int = 100
    hf_token: str | None = None

@app.get("/")
def read_root():
    return RedirectResponse(url="/app/")

@app.post("/analyze")
async def run_analysis(request: AnalyzeRequest):
    try:
        # 1. 리뷰 크롤링
        reviews = get_reviews(request.app_id, request.count)

        # 2. 분석기 생성 — 사용자가 토큰을 전달하면 인증된 모델을 로드합니다
        analyzer = get_review_analyzer(hf_token=request.hf_token)

        # 3. DataFrame -> 텍스트 리스트 변환
        if hasattr(reviews, "get") or hasattr(reviews, "columns"):
            texts = reviews["content"].astype(str).tolist()
        else:
            # 안전하게 리스트로 처리
            texts = list(reviews)

        # 4. 감성 분석 수행
        analysis_list = analyzer.analyze_list(texts)

        # 5. 간단 집계: 긍정/부정/보통 비율 계산
        counts = {"매우 긍정":0, "긍정":0, "보통":0, "부정":0, "매우 부정":0}
        for a in analysis_list:
            key = a.get("sentiment", "보통")
            counts[key] = counts.get(key, 0) + 1
        total = max(1, len(analysis_list))
        summary = {k: round(v/total*100, 1) for k,v in counts.items()}

        # Save analyzed dataframe server-side for downloads / visualization
        try:
            analyzed_df = reviews.copy()
            analyzed_df["sentiment"] = [a.get("sentiment") for a in analysis_list]
            analyzed_df["sentiment_score"] = [a.get("sentiment_score") for a in analysis_list]
            save_analyzed(request.app_id, analyzed_df)
            save_runtime_info(request.app_id, {"total": total})
        except Exception:
            # non-fatal: continue
            pass

        return {
            "status": "success",
            "app_id": request.app_id,
            "total_reviews_analyzed": total,
            "analysis_distribution_percent": summary,
            "raw_analysis": analysis_list[:100]  # 최대 100개 미리보기
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        content = await file.read()
        df = pd.read_csv(io.BytesIO(content))
        app_id = (file.filename or "uploaded").rsplit('.', 1)[0]
        save_upload(app_id, df)
        return {"status": "ok", "app_id": app_id, "rows": len(df)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/download/analyzed/{app_id}")
def download_analyzed(app_id: str):
    df = get_analyzed(app_id)
    if df is None:
        raise HTTPException(status_code=404, detail="analyzed data not found")
    buf = io.BytesIO()
    df.to_csv(buf, index=False, encoding='utf-8-sig')
    buf.seek(0)
    return StreamingResponse(buf, media_type='text/csv', headers={"Content-Disposition": f"attachment; filename=analyzed_{app_id}.csv"})


@app.get("/stats/{app_id}")
def get_stats(app_id: str, period: str = "일별", week_start: str = "월요일"):
    df = get_analyzed(app_id)
    if df is None:
        raise HTTPException(status_code=404, detail="analyzed data not found")
    counts = calculate_sentiment_counts(df)
    timeline = prepare_timeline_data_by_period(df, period=period, week_start=week_start)
    # convert timeline dates to iso
    timeline_json = timeline.assign(date=timeline['date'].dt.strftime('%Y-%m-%d')).to_dict(orient='records')
    return {"counts": counts, "timeline": timeline_json}