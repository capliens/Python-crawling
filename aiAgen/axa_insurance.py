# axa 손해보험 /db 확인
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import time
from datetime import datetime
import os  # sys.path 수정을 위해 추가
import sys  # sys.path 수정을 위해 추가

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from neoali.DB_save import DatabaseManager
except ImportError as e:
    DatabaseManager = None
    print(f"경고: DatabaseManager 모듈 임포트 실패 ({e}). DB 저장 기능이 비활성화됩니다.")


def scrape_axa_insurance_products():
    print("AXA손해보험 스크래핑 시작...")
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    url = ("https://www.axa.co.kr/AsianPlatformInternet/html/axacms/common/intro/disclosure/insurance/index.html")
    driver.get(url)
    wait = WebDriverWait(driver, 10)
    extracted_data = []
    print("현재 판매 상품 정보 수집 중...")
    try:
        current_products_tab = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "div.tab.tap_price > ul > li > a.m2.bg"))
        )
        current_products_tab.click()
        time.sleep(2)

        table_container = wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//div[contains(@class, 'tb_board') and contains(@class, 'drop_tb') and contains(@class, 'cmsTabWrap2')]")
            )
        )
        rows = table_container.find_elements(By.TAG_NAME, "tr")

        if not rows:
            print("오류: 테이블 행을 찾을 수 없습니다.")
            driver.quit()
            return extracted_data

        current_product_name = None
        for row in rows:
            row_id = row.get_attribute("id")
            if row_id and row_id.startswith("CatIDsb"):
                product_name_td = row.find_elements(By.TAG_NAME, "td")
                if product_name_td:
                    current_product_name = product_name_td[0].get_attribute('textContent').strip()
                continue

            cells = row.find_elements(By.TAG_NAME, "td")
            sales_period = cells[0].get_attribute('textContent').strip() if len(cells) > 0 else ""

            doc_links = []
            link_types = ["상품요약서", "약관", "사업방법서"]
            for i, link_type in enumerate(link_types):
                link_data = None
                if len(cells) > (i + 1):
                    try:
                        link_element = cells[i + 1].find_element(By.TAG_NAME, "a")
                        href = link_element.get_attribute("href")
                        if href and href.strip() != "#" and href.strip() != "":  # 유효한 링크인지 추가 확인
                            link_data = (link_type, href)
                    except NoSuchElementException:
                        pass
                doc_links.append(link_data)

            if current_product_name:  # 상품명이 있는 경우에만 데이터 추가
                extracted_data.append({
                    "product_name": current_product_name,
                    "sales_period": sales_period,
                    "summary_link": doc_links[0],
                    "terms_link": doc_links[1],
                    "business_method_link": doc_links[2]
                })
        print("현재 판매 상품 정보 수집 완료.")
    except (TimeoutException, NoSuchElementException) as e:
        print(f"스크래핑 중 오류: {e}")
    except Exception as e:
        print(f"스크래핑 중 예상치 못한 오류: {e}")
    finally:
        driver.quit()
        print("AXA손해보험 스크래핑 완료.")
    return extracted_data


def is_valid_axa_link(link_tuple):
    return link_tuple and isinstance(link_tuple, tuple) and len(link_tuple) == 2 and \
        link_tuple[1] and isinstance(link_tuple[1], str) and link_tuple[1].startswith("http")


if __name__ == "__main__":
    scraped_product_info = scrape_axa_insurance_products()

    if scraped_product_info:
        if DatabaseManager:
            print("DB 저장 진행중...")
            structured_rows_to_save = []
            scraped_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            company_name = "AXA손해보험"

            for item in scraped_product_info:
                product_name = item.get("product_name")
                sales_period = item.get("sales_period")
                product_code = None

                # 각 문서 타입에 대해 링크 유효성 검사 및 저장 데이터 생성
                doc_details = [
                    item.get("summary_link"),
                    item.get("terms_link"),
                    item.get("business_method_link")
                ]

                has_valid_link_for_product = False
                current_product_docs = []

                for detail_tuple in doc_details:
                    if is_valid_axa_link(detail_tuple):
                        doc_type, link_url = detail_tuple
                        has_valid_link_for_product = True
                        current_product_docs.append([
                            company_name,
                            product_name,
                            product_code,
                            doc_type,
                            sales_period,
                            scraped_time,
                            link_url
                        ])

                if has_valid_link_for_product:
                    structured_rows_to_save.extend(current_product_docs)

            if structured_rows_to_save:
                with DatabaseManager(db_name="insurance_products.db") as db_manager:
                    saved_count = db_manager.save_data(structured_rows_to_save)
                print(f"DB 저장 완료. 총 {saved_count}건 문서 정보 저장.")
            else:
                print("DB 저장할 유효한 문서 정보 없음.")
            print(f"총 스크래핑된 상품 그룹 수: {len(scraped_product_info)}개")  # 상품 그룹 수로 변경
        else:
            print("DatabaseManager 사용 불가. DB 저장 건너뜀.")
    else:
        print("스크래핑된 상품 데이터 없음.")
