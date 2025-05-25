from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException
import time

import sqlite3
from datetime import datetime

options = Options()
driver = webdriver.Chrome(options=options)
# driver.get("https://www.idbins.com/FWMAIV1534.do")
driver.get("https://www.idbins.com/FWMAIV1535.do")
wait = WebDriverWait(driver, 10)
all_data = []


wait = WebDriverWait(driver, 10)
all_data = []


def safe_click(element, retries=3, wait_sec=1):
    for _ in range(retries):
        try:
            driver.execute_script("arguments[0].click();", element)
            time.sleep(wait_sec)
            return True
        except StaleElementReferenceException:
            time.sleep(wait_sec)
    return False


def get_step1_items():
    try:
        wait.until(EC.presence_of_element_located((By.ID, "mCSB_1_container")))
        container = driver.find_element(By.ID, "mCSB_1_container")
        return container.find_elements(
            By.CSS_SELECTOR, 'ul > li.dp1 a[onclick^="getStep2"]')
    except TimeoutException:
        print("step1 항목 없음")
        return []


def get_step2_items():
    try:
        wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "ul#step2_list > li")))
        container = driver.find_element(By.ID, "mCSB_2_container")
        return container.find_elements(
            By.CSS_SELECTOR, "ul#step2_list > li > a")
    except TimeoutException:
        print("step2 항목 없음")
        return []


def get_step3_items():
    try:
        wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "ul#step3_list > li > a")))
        container = driver.find_element(By.ID, "mCSB_3_container")
        return container.find_elements(
            By.CSS_SELECTOR, "ul#step3_list > li > a")
    except TimeoutException:
        print("step3 항목 없음")
        return []


def extract_detail_data():
    wait.until(EC.presence_of_element_located(
        (By.CSS_SELECTOR, "ul.result > li")))
    container = driver.find_element(By.ID, "mCSB_4_container")
    name = container.find_element(By.ID, "step4_name").text.strip()
    date = container.find_element(By.ID, "step4_date").text.strip()

    data_list = [name, date]

    link_elements = container.find_elements(
        By.CSS_SELECTOR, "ul.btn_list > li")
    for li in link_elements[:3]:
        try:
            cell = li.find_element(By.TAG_NAME, "a")
            onclick_value = cell.get_attribute("onclick")
            if onclick_value:
                file_code = onclick_value.split(",")[1].strip().strip(")")
                text = cell.find_element(By.TAG_NAME, "span").text.strip()
                full_link = f"https://www.idbins.com/cYakgwanDown.do?FilePath=InsProduct/{file_code}"
                data_list.append((text, full_link))
        except Exception:
            continue
    return data_list


# 상태 기반 계층 탐색
step1_items = get_step1_items()
for i in range(len(step1_items)):
    step1_items = get_step1_items()  # 매번 재조회
    if i >= len(step1_items):
        continue
    if not safe_click(step1_items[i]):
        print(f"[1단계 실패] index={i}")
        continue

    step2_items = get_step2_items()
    if not step2_items:
        continue
    for j in range(len(step2_items)):
        step2_items = get_step2_items()
        if j >= len(step2_items):
            continue
        if not safe_click(step2_items[j]):
            print(f"[2단계 실패] index={j}")
            continue

        step3_items = get_step3_items()
        if not step3_items:
            continue
        for k in range(len(step3_items)):
            step3_items = get_step3_items()
            if k >= len(step3_items):
                continue
            if not safe_click(step3_items[k]):
                print(f"[3단계 실패] index={k}")
                continue

            try:
                data = extract_detail_data()
                all_data.append(data)
                print(f"[OK] {data[0]}")
            except Exception as e:
                print(f"[데이터 추출 실패] 3단계 index={k}, 오류: {e}")

# ───── 4. 구조화 ─────
structured_rows = []
scraped_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

for row in all_data:
    if len(row) < 2:
        continue
    title, date = row[:2]
    for item in row[2:]:
        if isinstance(item, tuple):
            doc_type, link = item
            structured_rows.append([
                "DB손해보험",         # company_name
                title,             # product_name
                "null",              # product_code
                doc_type,          # document_type
                date,              # sales_period
                scraped_time,
                link
            ])

# ───── 5. DB 저장 ─────
with sqlite3.connect("DB손해보험_web_data.db") as conn:
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS insurance_docs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT,
            product_name TEXT,
            product_code TEXT,
            document_type TEXT,
            sales_period TEXT,
            scraped_at TIMESTAMP,
            link TEXT,
            UNIQUE(company_name, product_name, product_code,
                   document_type, sales_period, link)
        );
    """)

    cursor.executemany("""
        INSERT OR IGNORE INTO insurance_docs (
            company_name, product_name,product_code,
            document_type, sales_period,scraped_at, link
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, structured_rows)

    conn.commit()

print(f"{len(structured_rows)}건 저장 완료")
driver.quit()
