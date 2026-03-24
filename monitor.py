import requests
import json
import os
import hashlib
from bs4 import BeautifulSoup

# ── 슬랙 웹훅 URL (GitHub Secrets에서 자동으로 주입됨) ──────────────
SLACK_WEBHOOK_URL = os.environ["SLACK_WEBHOOK_URL"]

# ── 모니터링 페이지 목록 ──────────────────────────────────────────────
PAGES = [
    # 공정거래위원회
    {
        "name": "공정위 | 보도자료",
        "emoji": "⚖️",
        "url": "https://www.ftc.go.kr/www/selectBbsNttList.do?bordCd=3&key=12&searchCtgry=01,02",
        "base_url": "https://www.ftc.go.kr",
        "row_sel": "table tbody tr",
        "link_sel": "td.tit a, td.subject a, td.title a",
    },
    {
        "name": "공정위 | 의결서",
        "emoji": "⚖️",
        "url": "https://www.ftc.go.kr/www/selectDlbrMtrList.do?key=9",
        "base_url": "https://www.ftc.go.kr",
        "row_sel": "table tbody tr",
        "link_sel": "td.tit a, td.subject a, td.title a",
    },
    {
        "name": "공정위 | 사건처리결과",
        "emoji": "⚖️",
        "url": "https://case.ftc.go.kr/ocp/co/ltfr.do",
        "base_url": "https://case.ftc.go.kr",
        "row_sel": "table tbody tr",
        "link_sel": "td a",
    },
    {
        "name": "공정위 | 전원회의 회의록",
        "emoji": "⚖️",
        "url": "https://case.ftc.go.kr/ocp/co/decsnMtgRcord.do",
        "base_url": "https://case.ftc.go.kr",
        "row_sel": "table tbody tr",
        "link_sel": "td a",
    },
    # 한국소비자원
    {
        "name": "소비자원 | 보도자료",
        "emoji": "🛡️",
        "url": "https://www.kca.go.kr/home/sub.do?menukey=4002",
        "base_url": "https://www.kca.go.kr",
        "row_sel": "table tbody tr",
        "link_sel": "td.subject a, td.tit a, td.title a",
    },
    # 금융위원회
    {
        "name": "금융위 | 보도자료",
        "emoji": "💰",
        "url": "https://www.fsc.go.kr/no010101",
        "base_url": "https://www.fsc.go.kr",
        "row_sel": "table tbody tr, ul.boardList li",
        "link_sel": "td.subject a, td.tit a, a.title, p.subject a",
    },
    # 금융감독원
    {
        "name": "금감원 | 공시자료",
        "emoji": "🏦",
        "url": "https://www.fss.or.kr/fss/job/openInfo/list.do?menuNo=200476",
        "base_url": "https://www.fss.or.kr",
        "row_sel": "table tbody tr",
        "link_sel": "td.title a, td.subject a, td a",
    },
    {
        "name": "금감원 | 제도개선자료",
        "emoji": "🏦",
        "url": "https://www.fss.or.kr/fss/job/openInfoImpr/list.do?menuNo=200483",
        "base_url": "https://www.fss.or.kr",
        "row_sel": "table tbody tr",
        "link_sel": "td.title a, td.subject a, td a",
    },
    {
        "name": "금감원 | 보도자료",
        "emoji": "🏦",
        "url": "https://www.fss.or.kr/fss/bbs/B0000188/list.do?menuNo=200218",
        "base_url": "https://www.fss.or.kr",
        "row_sel": "table tbody tr",
        "link_sel": "td.title a, td.subject a, td a",
    },
    # 국토교통부
    {
        "name": "국토부 | 보도자료",
        "emoji": "🏗️",
        "url": "https://www.molit.go.kr/USR/NEWS/m_71/lst.jsp?cate=1",
        "base_url": "https://www.molit.go.kr",
        "row_sel": "table tbody tr",
        "link_sel": "td.subject a, td.tit a, td.title a",
    },
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/122.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

# ── 이전 실행에서 본 글 목록 불러오기 / 저장하기 ───────────────────────
# GitHub Actions는 실행마다 환경이 초기화되므로
# 이전에 본 글 ID를 seen.json 파일에 저장해두고 커밋합니다
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
    """제목+링크로 고유 ID 생성"""
    raw = f"{title}|{link}"
    return hashlib.md5(raw.encode()).hexdigest()

# ── 페이지 스크래핑 ────────────────────────────────────────────────────
def get_articles(page):
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
        print(f"[오류] {page['name']} 파싱 실패: {e}")
    return articles

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

# ── 메인 실행 ──────────────────────────────────────────────────────────
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
