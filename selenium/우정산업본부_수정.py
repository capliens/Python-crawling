from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.edge.options import Options  # EdgeOptions 임포트
from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC

import sqlite3
from datetime import datetime

# ───── 1. 스크래퍼 클래스 정의 ─────


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

            while cell_idx < len(cells) or (len(rowspan_cache) > 0 and (
                    col_idx, row_index) in rowspan_cache):
                # 먼저 캐시된 rowspan 값 삽입
                if (col_idx, row_index) in rowspan_cache:
                    row_data.append(rowspan_cache[(col_idx, row_index)])
                    del rowspan_cache[(col_idx, row_index)]
                    col_idx += 1
                    continue

                if cell_idx >= len(cells):
                    break  # 셀은 다 썼는데 캐시도 끝났으면 종료

                cell = cells[cell_idx]
                cell_idx += 1

                text = cell.text.strip().replace("\n", "")
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
                    link_text = link_element.text.strip()

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

                # rowspan 처리
                rowspan = cell.get_attribute("rowspan")
                if rowspan and int(rowspan) > 1:
                    for i in range(1, int(rowspan)):
                        rowspan_cache[(col_idx, row_index + i)] = value

                col_idx += 1

            if row_data:
                data_list.append(row_data)


# ───── 2. 셀레니움 드라이버 설정 ─────
options = Options()
driver = webdriver.Chrome(options=options)
# driver = webdriver.Edge(options=options)
# driver.get("https://epostlife.go.kr/ASISDM00AT.do")
driver.get("https://epostlife.go.kr/ASISDM00BT.do")
wait = WebDriverWait(driver, 10)

all_data = []
scraper2 = EpostScraper(driver, tf=False)
all_data.extend(scraper2.get_all_data())

# --------임시----------

# btn1 = wait.until(EC.presence_of_element_located((By.ID, "_tapBtnArea01")))
# btn2 = wait.until(EC.presence_of_element_located((By.ID, "_tapBtnArea02")))

# title1 = btn1.get_attribute("title")
# title2 = btn2.get_attribute("title")

# # 클릭 전에 팝업이 사라졌는지 확인


# def wait_popup_to_disappear():
#     try:
#         wait.until(EC.invisibility_of_element_located(
#             (By.CLASS_NAME, "popup_header")))
#     except:
#         pass  # 팝업이 없으면 넘어감


# all_data = []

# if title1 == "선택됨":
#     print("버튼 1 클릭됨")
#     scraper1 = EpostScraper(driver, tf=True)
#     all_data.extend(scraper1.get_all_data())
#     wait_popup_to_disappear()
#     driver.execute_script("arguments[0].click();", btn2)
#     print("버튼 2 클릭됨")
#     scraper2 = EpostScraper(driver, tf=False)
#     all_data.extend(scraper2.get_all_data())

# elif title2 == "선택됨":
#     print("버튼 2 클릭됨")
#     scraper2 = EpostScraper(driver, tf=False)
#     all_data.extend(scraper2.get_all_data())
#     wait_popup_to_disappear()
#     driver.execute_script("arguments[0].click();", btn1)
#     print("버튼 1 클릭됨")
#     scraper1 = EpostScraper(driver, tf=True)
#     all_data.extend(scraper1.get_all_data())

# else:
#     print("선택된 탭이 없습니다.")

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
                "우정산업본부",         # company_name
                scraped_time,
                title,             # product_name
                code,              # product_code
                doc_type,          # document_type
                date,              # sales_period
                link
            ])

# ───── 5. DB 저장 ─────
with sqlite3.connect("web_data.db") as conn:
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS insurance_docs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT,
            scraped_at TIMESTAMP,
            product_name TEXT,
            product_code TEXT,
            document_type TEXT,
            sales_period TEXT,
            link TEXT,
            UNIQUE(company_name, product_name, product_code,
                   document_type, sales_period, link)
        );
    """)

    cursor.executemany("""
        INSERT OR IGNORE INTO insurance_docs (
            company_name, scraped_at, product_name,
            product_code, document_type, sales_period, link
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, structured_rows)

    conn.commit()

print(f"{len(structured_rows)}건 저장 완료")
driver.quit()
