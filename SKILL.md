---
name: dku-lecture-career
description: 단국대학교 교수의 강의경력(webinfo 강의경력조회)을 파싱해 JSON으로 저장하는 스킬. 교번·비밀번호는 LLM(대화)에 입력하지 않고 사용자가 터미널에서 직접 입력(getpass)한다. "단국대 강의경력 수집/파싱/받아줘" 요청 시 EJIS가 실행 방법을 안내한다.
---

# dku-lecture-career (단국대 교수 강의경력 파싱)

단국대 webinfo 포털의 **강의경력조회(findLctCrerInq)** 표를 파싱해 JSON으로 저장한다.

## 보안 원칙 (가장 중요)

> **EJIS(LLM)는 이 스크립트를 직접 실행하지 않는다.**
> 비밀번호가 대화·로그에 노출되지 않도록, **사용자가 본인 터미널에서 직접 실행**한다.
> EJIS는 ①실행 명령을 안내하고 ②실행이 끝난 뒤 생성된 JSON을 읽어 후속 작업(요약·노트 연동)만 한다.

- 교번·비밀번호: 스크립트가 `getpass`로 터미널에서 직접 입력받는다. 인자/환경변수로 강요하지 않는다.
- 비밀번호는 메모리 변수로만 쓰고 사용 직후 폐기. 출력 JSON·표준출력·파일 어디에도 남기지 않는다.
- 교번은 기본 출력에서 제외(`--keep-id` 옵션으로만 포함).

## 전제

- '강의경력조회' 메뉴는 **교수(전임) 계정**에서만 보인다. **강사 계정에는 없다.**

## 실행 방법 (사용자가 터미널에서)

최초 1회 설치:
```bash
cd <레포 경로>           # 예: ~/dev/dku-lecture-career
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

실행:
```bash
python3 scripts/fetch_career.py --name 홍길동 --out ./홍길동_강의경력.json
# 교번(ID), 비밀번호를 터미널에서 입력한다. 비번은 화면에 표시되지 않는다.
```

옵션:
- `--out`       출력 JSON 경로(기본 `dku_lecture_career.json`)
- `--name`      교수명(출력 라벨)
- `--headless`  브라우저 창 숨김(기본은 창 표시)
- `--keep-id`   출력 JSON에 교번 포함(기본 미포함)

## EJIS의 역할 (실행 후)

1. 사용자에게 위 실행 명령을 안내한다(직접 실행하지 않는다).
2. 사용자가 "다 됐다 / 경로는 ○○" 라고 하면, 그 JSON을 Read로 읽는다.
3. 요청 시 요약 통계 산출, 옵시디언 인물 노트(예: `80. Entities/81. People/<이름>.md`) 연동.

## 출력 JSON 스키마

```json
{
  "professor": "홍길동",
  "source": "단국대학교 webinfo 강의경력조회 (findLctCrerInq.do)",
  "source_url": "https://webinfo.dankook.ac.kr/.../findLctCrerInq.do?_view=ok",
  "extracted_at": "2026-06-17",
  "total": 231,
  "records": [
    {"no":1,"year":"2025","semester":"2학기","institution":"단국대학교",
     "department":"교육대학원","position":"교수","course":"...",
     "start_date":"2025-09-01","end_date":"2026-02-28","lecture_hours":"3"}
  ]
}
```

## 셀렉터 참고(페이지 구조 변경 시 갱신)

- 로그인: `#user_id`, `#user_password`, `button[onclick*='doLogin']`
- 강의경력: `findLctCrerInq.do?_view=ok` → 조회 버튼(`a:has-text('조회')`) → 헤더에 `년도`·`담당과목` 가진 `<table>`
