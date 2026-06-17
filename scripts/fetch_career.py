#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
단국대학교 교수 강의경력(findLctCrerInq) 파싱 스크립트.

보안 원칙
---------
- 교번/비밀번호는 **터미널에서 직접 입력**(getpass)받는다. 인자/대화/로그에 남기지 않는다.
- 비밀번호는 메모리 변수로만 사용하고, 출력 JSON·파일·표준출력 어디에도 기록하지 않는다.
- 교번은 기본적으로 출력 JSON에 포함하지 않는다(--keep-id로만 포함).

전제
----
- 단국대 webinfo 포털의 '강의경력조회' 메뉴는 **교수(전임) 계정**에서만 보인다.
  (강사 계정에는 해당 메뉴/데이터가 없다.)

사용
----
    python3 fetch_career.py                 # 교번·비번을 터미널에서 입력, 창이 보이는 모드
    python3 fetch_career.py --headless      # 브라우저 창 숨김
    python3 fetch_career.py --out ./out.json --name 홍길동

환경변수(선택, CI 등 비대화 환경용 — 평문 노출 주의):
    DKU_ID, DKU_PW 가 있으면 입력 프롬프트를 건너뛴다.
"""
import argparse
import datetime
import getpass
import html as htmllib
import json
import os
import re
import sys
import time

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
except ImportError:
    sys.exit("playwright가 필요합니다.  pip install playwright  &&  playwright install chromium")

BASE = "https://webinfo.dankook.ac.kr"
LOGIN_URL = f"{BASE}/member/logon.do"
CAREER_URL = f"{BASE}/tiac/univ/lssn/lfpl/views/findLctCrerInq.do?_view=ok"

COLUMNS = ["no", "year", "semester", "institution", "department",
           "position", "course", "start_date", "end_date", "lecture_hours"]


def read_credentials():
    """교번·비밀번호를 환경변수 또는 터미널에서 안전하게 읽는다."""
    uid = os.environ.get("DKU_ID") or input("단국대 교번(ID): ").strip()
    pw = os.environ.get("DKU_PW")
    if not pw:
        pw = getpass.getpass("비밀번호(입력 중 화면에 표시되지 않음): ")
    if not uid or not pw:
        sys.exit("교번/비밀번호가 비어 있습니다.")
    return uid, pw


def login(page, uid, pw):
    page.goto(LOGIN_URL, wait_until="networkidle")
    page.fill("#user_id", uid)
    page.fill("#user_password", pw)
    page.click("button[onclick*='doLogin']")
    try:
        page.wait_for_url(
            lambda u: "logon" not in u.lower() and "login" not in u.lower(),
            timeout=15000,
        )
    except PWTimeout:
        if "logon" in page.url.lower():
            sys.exit("로그인 실패: 교번 또는 비밀번호를 확인하세요.")


def grab_career_html(page):
    page.goto(CAREER_URL, wait_until="domcontentloaded")
    time.sleep(2)
    # 조회 버튼이 있으면 눌러 데이터 로드(없으면 무시)
    for sel in ["a:has-text('조회')", "button:has-text('조회')",
                "input[value='조회']", "button.btn_search"]:
        try:
            loc = page.locator(sel)
            if loc.count() > 0:
                loc.first.click()
                page.wait_for_load_state("networkidle")
                time.sleep(2)
                break
        except Exception:
            pass
    return page.content()


def parse_career_table(html):
    tables = re.findall(r"<table[^>]*>.*?</table>", html, re.S)
    target = None
    for t in tables:
        if "담당과목" in t and "년도" in t:
            target = t
            break
    if target is None and tables:
        target = max(tables, key=lambda t: t.count("<tr"))
    records = []
    if not target:
        return records
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", target, re.S):
        cells = [
            htmllib.unescape(re.sub(r"<[^>]+>", "", c)).replace("\xa0", " ").strip()
            for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S)
        ]
        if len(cells) < 10 or not cells[0].isdigit():
            continue
        rec = dict(zip(COLUMNS, cells[:10]))
        rec["no"] = int(rec["no"])
        records.append(rec)
    return records


def main():
    ap = argparse.ArgumentParser(
        description="단국대 교수 강의경력(findLctCrerInq)을 JSON으로 저장한다.")
    ap.add_argument("--out", default="dku_lecture_career.json", help="출력 JSON 경로")
    ap.add_argument("--name", default="", help="교수명(출력 라벨용, 선택)")
    ap.add_argument("--headless", action="store_true", help="브라우저 창 숨김")
    ap.add_argument("--keep-id", action="store_true",
                    help="출력 JSON에 교번 포함(기본은 미포함)")
    args = ap.parse_args()

    uid, pw = read_credentials()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=args.headless)
            page = browser.new_page()
            login(page, uid, pw)
            html = grab_career_html(page)
            browser.close()
    finally:
        pw = None  # 비밀번호 즉시 폐기

    records = parse_career_table(html)
    data = {
        "professor": args.name or None,
        "source": "단국대학교 webinfo 강의경력조회 (findLctCrerInq.do)",
        "source_url": CAREER_URL,
        "extracted_at": datetime.date.today().isoformat(),
        "total": len(records),
        "records": records,
    }
    if args.keep_id:
        data["account"] = uid

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    if not records:
        # 디버그용 HTML 덤프(개인정보 없음: 본인 강의 목록 페이지)
        dbg = os.path.splitext(args.out)[0] + "_debug.html"
        with open(dbg, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"⚠ 강의경력 데이터를 찾지 못했습니다. (교수 계정이 아니거나 페이지 구조 변경)")
        print(f"  디버그 HTML: {dbg}")
        sys.exit(3)

    years = sorted({r["year"] for r in records})
    print(f"✓ 저장 완료: {len(records)}건 → {args.out}")
    print(f"  기간: {years[0]} ~ {years[-1]}")


if __name__ == "__main__":
    main()
