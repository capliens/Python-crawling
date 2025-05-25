from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.edge.options import Options  # EdgeOptions 임포트
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import sqlite3
from datetime import datetime

# ───── 1. 스크래퍼 클래스 정의 ───── 오류 발생


class EpostScraper:
    def __init__(self, driver, tf: bool):
        self.driver = driver
        self.tf = tf  # True: tbody name=list / False: tbody id=stopPrdTbody0

    def get_all_data(self):
        data_list = []
        list_index = 1
        while True:
            if self.tf:
                tbody_xpath = f"//tbody[@name='list{list_index}']"
            else:
                tbody_xpath = f"//tbody[@id='stopPrdTbody0{list_index}']"
            try:
                rows = self.driver.find_elements(By.XPATH, f"{tbody_xpath}/tr")
                if not rows:
                    break
                self._extract_rows(rows, data_list)
                list_index += 1
            except NoSuchElementException:
                break  # 해당 tbody가 더 이상 없으면 종료
        return data_list

    def _extract_rows(self, rows, data_list):
        rowspan_cache = {}

        for row_index, row in enumerate(rows):
            cells = row.find_elements(By.CLASS_NAME, "txt_c")
            row_data = []
            col_idx = 0
            cell_idx = 0

            while cell_idx < len(cells) or (
                    col_idx, row_index) in rowspan_cache:
                if (col_idx, row_index) in rowspan_cache:
                    # 캐시된 rowspan 값 사용 후 삭제
                    row_data.append(rowspan_cache[(col_idx, row_index)])
                    del rowspan_cache[(col_idx, row_index)]
                    col_idx += 1
                    continue

                if cell_idx >= len(cells):
                    break

                cell = cells[cell_idx]
                cell_idx += 1

                text = cell.get_attribute("textContent").replace("\n", "")
                link = None
                link_text = None
                link_element = None
                data_href_value = None

                try:
                    link_element = cell.find_element(By.TAG_NAME, "a")
                    link = link_element.get_attribute("href")
                    if link is None:
                        data_href_value = link_element.get_attribute(
                            "data-href")
                except NoSuchElementException:
                    pass

                if link_element is not None:
                    link_text = link_element.get_attribute(
                        "textContent").strip()

                if link or data_href_value:
                    if self.tf is True:
                        if text == "약관보기":
                            value = ("약관", link)
                        else:
                            value = (text, link)
                    else:
                        base_url = "https://epostlife.go.kr"
                        full_url = base_url + data_href_value
                        if link_text == '':
                            value = ("약관", full_url)
                        else:
                            value = (text, full_url)
                else:
                    value = text

                # 현재 위치에 값 추가
                row_data.append(value)

                # rowspan 처리: 기존에 이미 같은 위치에 값이 있다면 덮어쓰지 않도록 확인
                rowspan = cell.get_attribute("rowspan")
                if rowspan and int(rowspan) > 1:
                    for i in range(1, int(rowspan)):
                        key = (col_idx, row_index + i)
                        if key not in rowspan_cache:
                            rowspan_cache[key] = value

                col_idx += 1

            if row_data:
                data_list.append(row_data)


# ───── 2. 셀레니움 드라이버 설정 ─────
options = Options()
driver = webdriver.Chrome(options=options)
# driver = webdriver.Edge(options=options)
driver.get("https://epostlife.go.kr/ASISDM00AT.do")

wait = WebDriverWait(driver, 10)

all_data = []
scraper1 = EpostScraper(driver, tf=True)
all_data.extend(scraper1.get_all_data())

driver.get("https://epostlife.go.kr/ASISDM00BT.do")
wait = WebDriverWait(driver, 10)

scraper2 = EpostScraper(driver, tf=False)
all_data.extend(scraper2.get_all_data())

# ───── 4. 구조화 ─────
structured_rows = []
scraped_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

for row in all_data:
    if len(row) < 3:
        continue
    title, code, date = row[:3]
    for item in row[3:]:
        if isinstance(item, tuple):
            doc_type, link = item
            structured_rows.append([
                "우정사업본부",         # company_name
                title,             # product_name
                code,              # product_code
                doc_type,          # document_type
                date,              # sales_period
                scraped_time,
                link
            ])

# ───── 5. DB 저장 ─────
with sqlite3.connect("우정사업본부_web_data.db") as conn:
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
