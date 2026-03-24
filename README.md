# 📢 정부기관 보도자료 알림봇

PC를 꺼도, Colab을 닫아도 GitHub 서버가 자동으로 실행해줍니다.

## 모니터링 대상

| 기관 | 페이지 |
|---|---|
| ⚖️ 공정거래위원회 | 보도자료, 의결서, 사건처리결과, 전원회의 회의록 |
| 🛡️ 한국소비자원 | 보도자료 |
| 💰 금융위원회 | 보도자료 |
| 🏦 금융감독원 | 공시자료, 제도개선자료, 보도자료 |
| 🏗️ 국토교통부 | 보도자료 |

## 설치 방법

### 1단계: 이 저장소를 GitHub에 올리기
1. GitHub에서 새 저장소(Repository) 생성
2. 이 파일들을 업로드

### 2단계: 슬랙 웹훅 URL을 GitHub Secrets에 등록
1. GitHub 저장소 → **Settings** 탭
2. 왼쪽 메뉴 **Secrets and variables → Actions**
3. **New repository secret** 클릭
4. Name: `SLACK_WEBHOOK_URL`
5. Secret: 슬랙 웹훅 URL 붙여넣기 → **Add secret**

### 3단계: Actions 활성화 확인
1. 저장소 상단 **Actions** 탭 클릭
2. 워크플로우가 보이면 완료
3. **Run workflow** 버튼으로 즉시 테스트 가능

## 실행 주기
평일 오전 8시 ~ 오후 8시, 30분마다 자동 실행됩니다.
주말/공휴일은 보도자료가 거의 없어서 제외했습니다.
변경하려면 `.github/workflows/monitor.yml`의 cron 값을 수정하세요.

## 페이지 추가 방법
`monitor.py`의 `PAGES` 리스트에 아래 형태로 추가:

```python
{
    "name": "기관명 | 페이지명",
    "emoji": "📋",
    "url": "모니터링할 URL",
    "base_url": "https://도메인",
    "row_sel": "table tbody tr",
    "link_sel": "td.subject a",
},
```
