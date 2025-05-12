from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
import sqlite3
from datetime import datetime

# ───── 1. 셀레니움 드라이버 설정 ─────
options = Options()
options.add_argument("--headless")  # 창 없이 실행하려면 주석 해제
driver = webdriver.Chrome(options=options)
driver.get("https://epostlife.go.kr/ASISDM00AT.do")
time.sleep(2)  # 로딩 대기

# ───── 2. 데이터 수집 (list1 ~ listN 자동 반복) ─────
data_list = []
list_index = 1

while True:
    rows = driver.find_elements(
        By.XPATH, f"//tbody[@name='list{list_index}']/tr")
    if not rows:
        break

    for row in rows:
        cells = row.find_elements(By.TAG_NAME, "td")
        row_data = []

        for cell in cells:
            text = cell.text.strip()
            try:
                link = cell.find_element(
                    By.TAG_NAME, "a"
                ).get_attribute("href")
            except:
                link = None

            if link:
                row_data.append((text, link))
            else:
                row_data.append(text)

        data_list.append(row_data)

    list_index += 1

# ───── 3. 구조화 ─────
structured_rows = []
for row in data_list:
    if len(row) < 3:
        continue
    title, code, date = row[:3]
    for item in row[3:]:
        if isinstance(item, tuple):
            doc_type, link = item
            structured_rows.append([
                "우정산업본부",  # company_name
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # scraped_at
                title,
                code,
                doc_type,
                date,
                link
            ])

# ───── 4. DB 저장 ─────
with sqlite3.connect("web_data.db") as conn:
    cursor = conn.cursor()
    # # 테이블 생성
    cursor.execute("""
        CREATE TABLE insurance_docs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT,
            product_name TEXT,
            product_code TEXT,
            document_type TEXT,
            sales_period TEXT,
            scraped_at TIMESTAMP,
            link TEXT,
            UNIQUE(company_name,product_name,
                   product_code,document_type,
                   sales_period,link
                   )
        );
    """)

    # 데이터 삽입
    cursor.executemany("""
        INSERT INTO insurance_docs (
            company_name, scraped_at, product_name,
            product_code, document_type, sales_period, link
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, structured_rows)

print(f"{len(structured_rows)}건 저장 완료")
driver.quit()
