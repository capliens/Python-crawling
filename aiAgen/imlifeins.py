# im라이프/판매중단페이지/db확인/pdf저장 이슈,db저장위치 이슈 db 저장안됨
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from seleniumwire import webdriver
from webdriver_manager.chrome import ChromeDriverManager

import os
import sys
from datetime import datetime  # datetime 임포트 추가

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from neoali.pdf_link_scraper import PdfLinkExtractor
    from neoali.DB_save import DatabaseManager  # DatabaseManager 임포트 활성화
except ImportError as e:
    PdfLinkExtractor = None
    DatabaseManager = None  # DatabaseManager 초기화
    print(f"경고: 모듈 임포트 실패 ({e}). 일부 기능이 비활성화될 수 있습니다.")

MG_DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads", "imlifeins")
if not os.path.exists(MG_DOWNLOAD_DIR):
    os.makedirs(MG_DOWNLOAD_DIR)


def get_product_info(url):
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev_shm_usage")

    driver = None
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(url)

        # 페이지 로드를 기다립니다.
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        pdf_extractor = None
        if PdfLinkExtractor:  # PdfLinkExtractor가 성공적으로 임포트된 경우에만 인스턴스 생성
            pdf_extractor = PdfLinkExtractor(driver, download_directory=MG_DOWNLOAD_DIR, verify_url_liveness=False)

        product_list = []
        tables = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "table.colTbl tbody"))
        )

        for table_idx, table in enumerate(tables):  # 테이블 인덱스 추가
            last_product_name = ""  # rowspan이 적용된 상품명을 추적
            rows = table.find_elements(By.TAG_NAME, "tr")
            for row_idx, row in enumerate(rows):  # 행 인덱스 추가
                # 각 행에서 td 요소를 찾습니다.
                cols = row.find_elements(By.TAG_NAME, "td")

                # td 요소가 없는 행 (예: th만 있는 행)은 건너뜁니다.
                if not cols:
                    continue

                current_product_name = ""
                sales_start_date = ""
                sales_end_date = ""
                summary_link = ""
                business_method_link = ""
                terms_link = ""

                # 상품명 추출: class="al"을 가진 td를 찾습니다.
                product_name_element_found = False
                for col in cols:
                    if "al" in col.get_attribute("class"):
                        current_product_name = col.text.strip()
                        last_product_name = current_product_name
                        product_name_element_found = True
                        break

                if not product_name_element_found:
                    current_product_name = last_product_name  # 이전 상품명 사용

                # 상품명 td의 인덱스를 찾아서 그 다음 td부터 판매기간 및 링크를 추출합니다.
                start_index_for_data = 0
                if product_name_element_found:
                    for i, col in enumerate(cols):
                        if "al" in col.get_attribute("class"):
                            start_index_for_data = i + 1
                            break

                # 판매개시일
                if start_index_for_data < len(cols):
                    sales_start_date = cols[start_index_for_data].text.strip()

                # 판매중지일
                if start_index_for_data + 1 < len(cols):
                    sales_end_date = cols[start_index_for_data + 1].text.strip()

                sales_period = f"{sales_start_date} ~ {sales_end_date}"

                # 각 링크에 대한 XPath를 동적으로 생성하여 PdfLinkExtractor 사용
                # click_and_get_download_link 함수 사용

                # 상품요약서 링크
                if start_index_for_data + 2 < len(cols):
                    try:
                        summary_a_tag = cols[start_index_for_data + 2].find_element(By.TAG_NAME, "a")
                        summary_title = summary_a_tag.get_attribute("title")
                        if summary_title and pdf_extractor:
                            summary_xpath = f"//a[@title='{summary_title}']"
                            extracted_link = pdf_extractor.click_and_get_download_link(summary_xpath)
                            if extracted_link:
                                summary_link = extracted_link
                    except NoSuchElementException:
                        pass

                # 사업방법서 링크
                if start_index_for_data + 3 < len(cols):
                    try:
                        business_method_a_tag = cols[start_index_for_data + 3].find_element(By.TAG_NAME, "a")
                        business_method_title = business_method_a_tag.get_attribute("title")
                        if business_method_title and pdf_extractor:
                            business_method_xpath = f"//a[@title='{business_method_title}']"
                            extracted_link = pdf_extractor.click_and_get_download_link(business_method_xpath)
                            if extracted_link:
                                business_method_link = extracted_link
                    except NoSuchElementException:
                        pass

                # 보험약관 링크
                if start_index_for_data + 4 < len(cols):
                    try:
                        terms_a_tag = cols[start_index_for_data + 4].find_element(By.TAG_NAME, "a")
                        terms_title = terms_a_tag.get_attribute("title")
                        if terms_title and pdf_extractor:
                            terms_xpath = f"//a[@title='{terms_title}']"
                            extracted_link = pdf_extractor.click_and_get_download_link(terms_xpath)
                            if extracted_link:
                                terms_link = extracted_link
                    except NoSuchElementException:
                        pass

                product_list.append({
                    "상품명": current_product_name,
                    "판매기간": sales_period,
                    "상품요약서": summary_link,
                    "사업방법서": business_method_link,
                    "약관": terms_link
                })

        # DB에 저장
        if DatabaseManager:
            db_name = os.path.join(MG_DOWNLOAD_DIR, "_imlifeins_data.db")
            with DatabaseManager(db_name=db_name) as db_manager:
                structured_rows = []
                scraped_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                company_name = "IM라이프"  # 회사명 고정

                for product in product_list:
                    product_name = product["상품명"]
                    sales_period = product["판매기간"]

                    # 상품요약서
                    if product["상품요약서"]:
                        structured_rows.append((
                            company_name, product_name, None,  # product_code는 현재 없음
                            "상품요약서", sales_period, scraped_at, product["상품요약서"]
                        ))

                    # 사업방법서
                    if product["사업방법서"]:
                        structured_rows.append((
                            company_name, product_name, None,
                            "사업방법서", sales_period, scraped_at, product["사업방법서"]
                        ))

                    # 약관
                    if product["약관"]:
                        structured_rows.append((
                            company_name, product_name, None,
                            "약관", sales_period, scraped_at, product["약관"]
                        ))

                if structured_rows:
                    db_manager.save_data(structured_rows)
                else:
                    print("DB에 저장할 데이터가 없습니다.")

        return product_list

    except TimeoutException:
        print("페이지 로드 시간 초과")
        return None
    except Exception as e:
        print(f"오류 발생: {e}")
        return None
    finally:
        if driver:
            driver.quit()


if __name__ == "__main__":
    url = "https://www.imlifeins.co.kr/BA/BA_A020.do"
    product_data = get_product_info(url)
    if product_data:
        for product in product_data:
            print("--- 상품 정보 ---")
            for key, value in product.items():
                print(f"{key}: {value}")
            print("-----------------")
    else:
        print("상품 정보를 가져오지 못했습니다.")
