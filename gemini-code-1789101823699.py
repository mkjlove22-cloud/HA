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

import urllib.parse
import feedparser
import difflib
import streamlit as st

# --- 3. 실시간 뉴스 크롤링 (중복 차단 로직 적용) ---
# --- 3. 보유 종목 핵심 변화 ---
import re
import urllib.parse
from datetime import datetime, timezone
from difflib import SequenceMatcher

import feedparser
import streamlit as st


WATCHLIST = [
    {
        "label": "엔비디아 (NVDA)",
        "query": '"NVIDIA" OR NVDA OR 엔비디아',
        "official_url": "https://investor.nvidia.com/",
        "official_feeds": [],
    },
    {
        "label": "알파벳 (GOOGL)",
        "query": '"Alphabet Inc." OR GOOGL OR GOOG OR 알파벳',
        "official_url": "https://abc.xyz/investor/",
        "official_feeds": [],
    },
    {
        "label": "인튜이티브 서지컬 (ISRG)",
        "query": '"Intuitive Surgical" OR ISRG OR "인튜이티브 서지컬"',
        "official_url": "https://isrg.gcs-web.com/press-releases",
        "official_feeds": [],
    },
    {
        "label": "버텍스 (VRTX)",
        "query": '"Vertex Pharmaceuticals" OR VRTX OR "버텍스 파마슈티컬스"',
        "official_url": "https://investors.vrtx.com/news-events/press-releases",
        # 공식 보도자료 RSS. 접근이 막혀도 아래 Google 뉴스 결과로 자동 대체됩니다.
        "official_feeds": [
            "https://investors.vrtx.com/rss/news-releases.xml?items=15"
        ],
    },
]

# 한국 보도와 미국 원문 보도를 함께 확인한다.
EDITIONS = [
    {"hl": "ko", "gl": "KR", "ceid": "KR:ko", "origin": "Google 뉴스 한국"},
    {"hl": "en-US", "gl": "US", "ceid": "US:en", "origin": "Google 뉴스 미국"},
]

EVENT_TERMS = {
    "실적·전망": (
        "earnings", "financial results", "quarterly results",
        "revenue", "guidance", "forecast", "실적", "매출", "전망",
    ),
    "규제·임상": (
        "fda", "approval", "clearance", "phase", "trial",
        "clinical", "nda", "bla", "pdufa", "임상", "승인",
    ),
    "인수·제휴": (
        "acquisition", "acquire", "merger", "partnership",
        "collaboration", "인수", "합병", "제휴",
    ),
    "보안·법규": (
        "security", "cybersecurity", "vulnerability", "cve",
        "breach", "export control", "antitrust", "lawsuit",
        "regulation", "보안", "취약점", "규제", "소송",
    ),
    "제품·운영": (
        "launch", "release", "product", "data center",
        "recall", "outage", "출시", "제품", "장애", "리콜",
    ),
    "경영진": (
        "ceo", "cfo", "leadership", "executive", "appoint",
        "resigns", "경영진", "대표", "임원",
    ),
}

STOPWORDS = {
    "nvidia", "nvda", "alphabet", "googl", "goog",
    "intuitive", "surgical", "isrg", "vertex",
    "pharmaceuticals", "vrtx", "엔비디아", "알파벳",
    "인튜이티브", "서지컬", "버텍스", "파마슈티컬스",
}


@st.cache_data(ttl=900, show_spinner=False)
def fetch_feed(url, limit=30):
    try:
        feed = feedparser.parse(url)
        return [dict(entry) for entry in feed.entries[:limit]]
    except Exception:
        return []


def google_news_url(query, edition):
    params = {
        "q": query,
        "hl": edition["hl"],
        "gl": edition["gl"],
        "ceid": edition["ceid"],
    }
    return "https://news.google.com/rss/search?" + urllib.parse.urlencode(params)


def published_at(entry):
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not parsed:
        return None
    return datetime(*parsed[:6], tzinfo=timezone.utc)


def event_category(title):
    lowered = title.casefold()

    category, hit_count = max(
        (
            (name, sum(term in lowered for term in terms))
            for name, terms in EVENT_TERMS.items()
        ),
        key=lambda item: item[1],
    )

    return category if hit_count else "일반 회사 뉴스", hit_count


def freshness_score(entry):
    published = published_at(entry)
    if not published:
        return 0

    days_old = max(0, (datetime.now(timezone.utc) - published).days)

    if days_old <= 2:
        return 8
    if days_old <= 7:
        return 5
    if days_old <= 30:
        return 2
    return 0


def news_score(entry):
    _, event_hits = event_category(entry.get("title", ""))
    score = event_hits * 10 + freshness_score(entry)

    # 공식 발표이면서 핵심 사건 키워드가 있으면 우선한다.
    if entry.get("_official") and event_hits:
        score += 100

    return score


def title_key(title):
    # 제목 끝의 "- Reuters" 같은 매체 표기는 중복 비교에서 제외한다.
    plain = re.sub(r"\s[-|]\s[^-|]+$", "", title.casefold())
    words = re.findall(r"[a-z0-9]+|[가-힣]+", plain)
    return " ".join(word for word in words if word not in STOPWORDS)


def same_event(title_a, title_b):
    a = title_key(title_a)
    b = title_key(title_b)

    if not a or not b:
        return False

    if a == b or SequenceMatcher(None, a, b).ratio() >= 0.78:
        return True

    words_a = set(a.split())
    words_b = set(b.split())
    overlap = len(words_a & words_b)
    union = len(words_a | words_b)

    return overlap >= 3 and union and overlap / union >= 0.55


def unique_articles(entries):
    selected = []
    seen_links = set()

    for entry in sorted(entries, key=news_score, reverse=True):
        link = entry.get("link", "")
        title = entry.get("title", "")

        if not title or (link and link in seen_links):
            continue

        if any(same_event(title, old.get("title", "")) for old in selected):
            continue

        selected.append(entry)
        if link:
            seen_links.add(link)

    return selected


def get_company_articles(company):
    entries = []

    # 공식 발표는 가능한 경우 우선 수집한다.
    for feed_url in company["official_feeds"]:
        for entry in fetch_feed(feed_url):
            entry["_origin"] = "공식 발표"
            entry["_official"] = True
            entries.append(entry)

    # Google 뉴스는 독립 보도와 공식 발표의 보조 수집망으로 사용한다.
    for edition in EDITIONS:
        url = google_news_url(company["query"], edition)
        for entry in fetch_feed(url):
            entry["_origin"] = edition["origin"]
            entry["_official"] = False
            entries.append(entry)

    return entries


def show_company_news(company):
    st.markdown(f"#### {company['label']}")

    entries = get_company_articles(company)

    # 오래된 기사만 있을 경우보다 최신 변화가 우선되게 한다.
    recent_entries = [
        entry for entry in entries
        if published_at(entry) is None
        or (datetime.now(timezone.utc) - published_at(entry)).days <= 45
    ]

    articles = unique_articles(recent_entries or entries)

    if not articles:
        st.caption("수집된 최근 기사가 없습니다. 공식 발표를 직접 확인하세요.")
        st.link_button("공식 발표 보기", company["official_url"])
        return

    article = articles[0]  # 회사당 한 개의 핵심 기사
    category, _ = event_category(article.get("title", ""))
    published = published_at(article)
    date_text = published.strftime("%Y-%m-%d") if published else "발행일 미상"

    st.link_button(
        f"핵심 기사 · {article['title']}",
        article["link"],
        use_container_width=True,
    )
    st.caption(f"{category} · {article.get('_origin', '뉴스')} · {date_text}")
    st.link_button("공식 발표", company["official_url"], use_container_width=True)


st.header("3. 보유 종목 핵심 변화")

columns = st.columns(2)
for index, company in enumerate(WATCHLIST):
    with columns[index % 2]:
        show_company_news(company)

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

# --- 5. 비상장 딥테크 감시망 (IPO & 빅테크 투자) ---
st.header("5. 비상장 딥테크 감시망 (IPO & 빅테크 투자)")

# 10개 타겟을 두 섹션으로 나누어 배치
ipo_col1, ipo_col2 = st.columns(2)

with ipo_col1:
    st.subheader("🚀 우주 인프라 & 양자 컴퓨팅")
    # 바르다 스페이스, K2 스페이스, 퀀텀 머신스, 싸이퀀텀
    get_news('("Varda Space" OR "K2 Space" OR "Quantum Machines" OR PsiQuantum) AND (IPO OR "S-1" OR 상장 OR 인수 OR funding)')

with ipo_col2:
    st.subheader("🧬 바이오 파운드리 & 🤖 피지컬 AI")
    # 컬처 바이오, 아시모프, 셀레스티얼, 헬리온, Pi, 피규어 AI
    get_news('("Culture Biosciences" OR Asimov OR "Celestial AI" OR "Helion Energy" OR "Physical Intelligence" OR "Figure AI") AND (IPO OR "S-1" OR 상장 OR 인수 OR funding)')
    
st.divider()
