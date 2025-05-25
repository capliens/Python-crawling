from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains
from datetime import datetime
import time
import sqlite3

options = Options()
driver = webdriver.Chrome(options=options)
driver.get("https://www.idbins.com/FWMAIV1534.do")
# driver.get("https://www.idbins.com/FWMAIV1535.do")
wait = WebDriverWait(driver, 10)
action = ActionChains(driver)
all_data = []

# 1단계 메뉴 수 확인
container = wait.until(
    EC.presence_of_element_located((By.ID, "mCSB_1_container")))
a_tags = container.find_elements(
    By.CSS_SELECTOR, 'ul > li.dp1 a[onclick^="getStep2"]')
a_count = len(a_tags)

for i in a_tags or []:
    try:
        driver.execute_script("arguments[0].click();", i)
        time.sleep(1)

        wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "ul#step2_list > li")))
        container2 = driver.find_element(By.ID, "mCSB_2_container")
        a_tag2s = container2.find_elements(
            By.CSS_SELECTOR, "ul#step2_list > li > a")

        for b in a_tag2s or []:
            try:
                driver.execute_script("arguments[0].click();", b)
                time.sleep(1)
                wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "ul#step3_list > li > a")))
                container3 = driver.find_element(By.ID, "mCSB_3_container")
                a_tag3s = container3.find_elements(
                    By.CSS_SELECTOR, "ul#step3_list > li > a")
                for c in a_tag3s or []:
                    data_list = []
                    try:
                        driver.execute_script("arguments[0].click();", c)
                        time.sleep(1)

                        wait.until(EC.presence_of_element_located(
                            (By.CSS_SELECTOR, "ul.result > li")))
                        container4 = driver.find_element(
                            By.ID, "mCSB_4_container")
                        name = container4.find_element(
                            By.ID, "step4_name").get_attribute("textContent")
                        date = container4.find_element(
                            By.ID, "step4_date").get_attribute("textContent")

                        # 원래 방식: 순차 append
                        data_list.append(name)
                        data_list.append(date)

                        link_elements = container4.find_elements(
                            By.CSS_SELECTOR, "ul.btn_list > li")
                        for x in link_elements[:3]:
                            cell = x.find_element(By.TAG_NAME, "a")
                            onclick_value = cell.get_attribute("onclick")

                            # onclick_value가 None이면 해당 항목 건너뜀
                            if onclick_value:
                                onclick_value = onclick_value.split(
                                    ",")[1].strip().strip(")")
                                text = cell.find_element(
                                    By.TAG_NAME, "span").get_attribute(
                                        "textContent")
                                full_link = f"https://www.idbins.com/cYakgwanDown.do?FilePath=InsProduct/{onclick_value}"
                                value = (text, full_link)
                                data_list.append(value)
                            else:
                                print("onclick 속성이 없어서 건너뜁니다.")
                        all_data.append(data_list)
                    except Exception as e:
                        print(f"  3단계 클릭 오류: {c.get_attribute(
                            "textContent"), e}")
            except Exception as e:
                print(f"  2단계 클릭 오류: {b.get_attribute("textContent"), e}")
    except Exception as e:
        print(f"1단계 클릭 오류: {i.get_attribute("textContent"), e}")

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
