import requests
import json
import os
import hashlib
import feedparser
from bs4 import BeautifulSoup

SLACK_WEBHOOK_URL = os.environ["SLACK_WEBHOOK_URL"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/122.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

# ── 모니터링 설정 ─────────────────────────────────────────────────────
# type: "scrape" = 직접 스크래핑 / "rss" = RSS 피드
PAGES = [
    # ─── 직접 접속 가능한 사이트 (스크래핑) ──────────────────────────
    {
        "type": "scrape",
        "name": "공정위 | 사건처리결과",
        "emoji": "⚖️",
        "url": "https://case.ftc.go.kr/ocp/co/ltfr.do",
        "base_url": "https://case.ftc.go.kr",
        "row_sel": "table tbody tr",
        "link_sel": "td a",
    },
    {
        "type": "scrape",
        "name": "공정위 | 전원회의 회의록",
        "emoji": "⚖️",
        "url": "https://case.ftc.go.kr/ocp/co/decsnMtgRcord.do",
        "base_url": "https://case.ftc.go.kr",
        "row_sel": "table tbody tr",
        "link_sel": "td a",
    },
    {
        "type": "scrape",
        "name": "금감원 | 공시자료",
        "emoji": "🏦",
        "url": "https://www.fss.or.kr/fss/job/openInfo/list.do?menuNo=200476",
        "base_url": "https://www.fss.or.kr",
        "row_sel": "table tbody tr",
        "link_sel": "td.title a, td.subject a, td a",
    },
    {
        "type": "scrape",
        "name": "금감원 | 제도개선자료",
        "emoji": "🏦",
        "url": "https://www.fss.or.kr/fss/job/openInfoImpr/list.do?menuNo=200483",
        "base_url": "https://www.fss.or.kr",
        "row_sel": "table tbody tr",
        "link_sel": "td.title a, td.subject a, td a",
    },
    {
        "type": "scrape",
        "name": "금감원 | 보도자료",
        "emoji": "🏦",
        "url": "https://www.fss.or.kr/fss/bbs/B0000188/list.do?menuNo=200218",
        "base_url": "https://www.fss.or.kr",
        "row_sel": "table tbody tr",
        "link_sel": "td.title a, td.subject a, td a",
    },

    # ─── 정책브리핑 RSS로 대체 (해외 IP 차단 기관) ────────────────────
    # 공정위 보도자료 → 정책브리핑 RSS (공정거래위원회 필터)
    {
        "type": "rss",
        "name": "공정위 | 보도자료",
        "emoji": "⚖️",
        "url": "https://www.korea.kr/rss/pressRelease.do",
        "filter_keyword": "공정거래위원회",  # 제목이나 출처에 이 단어가 있는 것만 알림
    },
    # 금융위 보도자료 → 정책브리핑 RSS
    {
        "type": "rss",
        "name": "금융위 | 보도자료",
        "emoji": "💰",
        "url": "https://www.korea.kr/rss/pressRelease.do",
        "filter_keyword": "금융위원회",
    },
    # 소비자원 보도자료 → 정책브리핑 RSS
    {
        "type": "rss",
        "name": "소비자원 | 보도자료",
        "emoji": "🛡️",
        "url": "https://www.korea.kr/rss/pressRelease.do",
        "filter_keyword": "소비자원",
    },
    # 국토부 보도자료 → 정책브리핑 RSS
    {
        "type": "rss",
        "name": "국토부 | 보도자료",
        "emoji": "🏗️",
        "url": "https://www.korea.kr/rss/pressRelease.do",
        "filter_keyword": "국토교통부",
    },
]

SEEN_FILE = "seen.json"

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_seen(seen):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(seen, f, ensure_ascii=False, indent=2)

def make_uid(title, link):
    return hashlib.md5(f"{title}|{link}".encode()).hexdigest()

# ── RSS 방식으로 글 가져오기 ──────────────────────────────────────────
def get_articles_rss(page):
    articles = []
    try:
        feed = feedparser.parse(page["url"])
        keyword = page.get("filter_keyword", "")
        for entry in feed.entries:
            title = entry.get("title", "")
            link = entry.get("link", "")
            # 출처(author/source) 또는 제목에 키워드 포함된 것만
            source = entry.get("author", "") + entry.get("source", {}).get("title", "")
            if keyword and keyword not in title and keyword not in source:
                continue
            if not title or len(title) < 5:
                continue
            articles.append({"title": title, "link": link})
    except Exception as e:
        print(f"  [오류] {page['name']} RSS 실패: {e}")
    return articles

# ── 스크래핑 방식으로 글 가져오기 ─────────────────────────────────────
def get_articles_scrape(page):
    articles = []
    try:
        res = requests.get(page["url"], headers=HEADERS, timeout=15)
        res.encoding = res.apparent_encoding
        soup = BeautifulSoup(res.text, "lxml")
        rows = soup.select(page["row_sel"])
        for row in rows:
            tag = row.select_one(page["link_sel"])
            if not tag:
                continue
            title = tag.get_text(separator=" ", strip=True)
            if not title or len(title) < 6:
                continue
            href = tag.get("href", "")
            if href and href.startswith("/"):
                href = page["base_url"] + href
            elif href and not href.startswith("http"):
                href = page["url"].rsplit("/", 1)[0] + "/" + href
            articles.append({"title": title, "link": href or page["url"]})
    except Exception as e:
        print(f"  [오류] {page['name']} 스크래핑 실패: {e}")
    return articles

def get_articles(page):
    if page["type"] == "rss":
        return get_articles_rss(page)
    else:
        return get_articles_scrape(page)

# ── 슬랙 전송 ──────────────────────────────────────────────────────────
def send_slack(page, article):
    text = (
        f"{page['emoji']} *{page['name']}*\n"
        f"> {article['title']}\n"
        f"> 🔗 {article['link']}"
    )
    try:
        res = requests.post(
            SLACK_WEBHOOK_URL,
            data=json.dumps({"text": text}),
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        if res.status_code != 200:
            print(f"[슬랙 오류] {res.status_code}: {res.text}")
        else:
            print(f"[전송] {page['name']} | {article['title'][:50]}")
    except Exception as e:
        print(f"[슬랙 전송 실패] {e}")

# ── 메인 ───────────────────────────────────────────────────────────────
def main():
    seen = load_seen()
    updated = False

    for page in PAGES:
        name = page["name"]
        if name not in seen:
            seen[name] = []

        articles = get_articles(page)
        print(f"[체크] {name}: {len(articles)}건 수집")

        for a in articles:
            uid = make_uid(a["title"], a["link"])
            if uid not in seen[name]:
                seen[name].append(uid)
                send_slack(page, a)
                updated = True

    if updated:
        save_seen(seen)
        print("[완료] seen.json 업데이트됨")
    else:
        print("[완료] 새 글 없음")

if __name__ == "__main__":
    main()
