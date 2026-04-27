from google_play_scraper import Sort, reviews
import pandas as pd

def get_reviews(app_id, count=100):
    """
    특정 앱의 ID를 입력받아 리뷰를 수집하고 데이터프레임으로 변환합니다.
    """
    # reviews 함수는 결과(list)와 계속 스크롤하기 위한 토큰을 반환합니다.
    result, _ = reviews(
        app_id,
        lang='ko',     # 한국어 리뷰만
        country='kr',  # 한국 지역 설정
        sort=Sort.MOST_RELEVANT, # 관련성 높은 순 (또는 NEWEST로 변경 가능)
        count=count    # 수집할 개수
    )
    
    # 수집된 데이터를 표(DataFrame) 형태로 변환
    df = pd.DataFrame(result)
    
    # 포트폴리오 활용에 불필요한 정보는 제외하고 핵심 컬럼만 필터링
    # at: 작성시간, userName: 작성자, score: 별점, content: 리뷰 내용
    df = df[['at', 'userName', 'score', 'content']]
    
    return df

if __name__ == "__main__":
    # 코드가 잘 작동하는지 테스트하기 위한 구간입니다.
    # 테스트용 앱 ID: 'com.kakao.talk' (카카오톡)
    print("데이터 수집 중...")
    test_df = get_reviews('com.kakao.talk', count=10)
    print(test_df)