import streamlit as st
import yfinance as yf
import feedparser
import urllib.parse

# 페이지 기본 설정
st.set_page_config(page_title="사령관 대시보드", layout="wide")
st.title("📈 사령관 전용 터미널 (매크로 & 타겟 종목)")

# --- 1. 매크로 지표 & 환율 ---
st.header("1. 매크로 방어선 (한·미·일)")
macro_tickers = {
    "원/달러 환율": "KRW=X",
    "원/엔 환율(100엔)": "JPYKRW=X",
    "나스닥": "^IXIC",
    "S&P 500": "^GSPC",
    "WTI 원유 (뇌관)": "CL=F",
    "브렌트유 (뇌관)": "BZ=F"
}

cols = st.columns(6) # 4개에서 6개로 늘림
for i, (name, ticker) in enumerate(macro_tickers.items()):
    try:
        data = yf.Ticker(ticker).history(period="5d")
        today = data['Close'].iloc[-1]
        yest = data['Close'].iloc[-2]
        
        # 엔화는 100엔 기준으로 변환
        if ticker == "JPYKRW=X": 
            today *= 100
            yest *= 100
            
        diff = (today - yest) / yest * 100
        cols[i].metric(label=name, value=f"{today:,.2f}", delta=f"{diff:.2f}%")
    except:
        cols[i].metric(label=name, value="Error", delta="-")

st.divider()

# --- 2. 타겟 4종목 시세 ---
st.header("2. 타겟 5개 기업 시세")
stocks = {
    "Nvidia (AI 대장)": "NVDA",
    "SPCX (AI/인프라)": "SPCX",
    "Alphabet (자체칩/AI)": "GOOGL",
    "Intuitive (의료로봇)": "ISRG",
    "Vertex (바이오)": "VRTX"
}

cols_s = st.columns(5) # 4개에서 5개로 늘림
for i, (name, ticker) in enumerate(stocks.items()):
    try:
        data = yf.Ticker(ticker).history(period="5d")
        today = data['Close'].iloc[-1]
        yest = data['Close'].iloc[-2]
        diff = (today - yest) / yest * 100
        cols_s[i].metric(label=name, value=f"${today:,.2f}", delta=f"{diff:.2f}%")
    except:
        cols_s[i].metric(label=name, value="Error", delta="-")

st.divider()

# --- 3. 실시간 뉴스 크롤링 ---
st.header("3. 핵심 산업 뉴스 클리핑")

def get_news(query):
    encoded_query = urllib.parse.quote(query)
    # 구글 뉴스 RSS URL (한국 기준)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko"
    feed = feedparser.parse(url)
    for entry in feed.entries[:5]: # 최신 5개만 출력
        st.write(f"- [{entry.title}]({entry.link})")

col1, col2 = st.columns(2)

with col1:
    st.subheader("📍 반도체 & AI (SPCX, GOOGL)")
    # 반도체, AI 관련 뉴스 필터링
    get_news("스페이스X OR 구글 OR SPCX OR GOOGL (반도체 OR AI OR 데이터센터)")

with col2:
    st.subheader("📍 의료 & 바이오 (ISRG, VRTX)")
    # 의료 로봇, 바이오 관련 뉴스 필터링
    get_news("인튜이티브 서지컬 OR 버텍스 OR ISRG OR VRTX (의료 OR 로봇 OR 바이오)")
    st.divider()

# --- 4. 거시 경제 핵심 뉴스 ---
st.header("4. 매크로 팩트 체크 (한·미·일)")

mac_col1, mac_col2 = st.columns(2)

with mac_col1:
    st.subheader("🇺🇸 미국 (연준·금리·인플레)")
    # 미국 거시경제 필터링
    get_news("연준 OR 파월 OR 금리 인하 OR CPI OR 미국 인플레이션")

with mac_col2:
    st.subheader("🇯🇵·🇰🇷 아시아 (엔캐리·한국은행)")
    # 일본/한국 거시경제 필터링
    get_news("일본은행 OR BOJ OR 엔캐리 OR 한국은행 금리")
