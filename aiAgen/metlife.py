# 매트라이프 /db 확인 /판매중단패이지/db저장 이슈
# 코드 수정
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import os
import sys
from datetime import datetime

# 프로젝트 루트를 sys.path에 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    # Metlife 스크레이퍼는 PdfLinkExtractor를 직접 사용하지 않는 것으로 보이나,
    # 다른 스크레이퍼와의 일관성 및 추후 확장성을 위해 import 시도만 남겨둘 수 있습니다.
    # from neoali.pdf_link_scraper import PdfLinkExtractor
    from neoali.DB_save import DatabaseManager
except ImportError as e:
    # PdfLinkExtractor = None # PdfLinkExtractor 사용 안 함
    DatabaseManager = None
    print(f"경고: DatabaseManager 모듈 임포트 실패 ({e}). DB 저장 기능이 비활성화됩니다.")

METLIFE_DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads", "metlife")
if not os.path.exists(METLIFE_DOWNLOAD_DIR):
    os.makedirs(METLIFE_DOWNLOAD_DIR)


def get_metlife_product_info(scrape_target="주보험", click_all_history=False):
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    # 다운로드 폴더 설정 (PdfLinkExtractor를 사용하지 않으므로 직접적인 효과는 없을 수 있으나, 일반적인 설정)
    prefs = {
        "download.default_directory": METLIFE_DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True
    }
    options.add_experimental_option("prefs", prefs)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    wait = WebDriverWait(driver, 10)

    url = "https://brand.metlife.co.kr/pn/mcvrgProd/retrieveMcvrgProdMain.do"
    print(f"메트라이프생명 '{scrape_target}' 정보 스크래핑 시작...")
    driver.get(url)
    time.sleep(1)

    products_data = []
    product_type = scrape_target

    try:
        if scrape_target == "특약":
            try:
                special_terms_tab = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "ul.uiDropCont > li:nth-child(2) > a"))
                )
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", special_terms_tab)
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", special_terms_tab)
                print("  특약 탭으로 전환 중...")
                time.sleep(3)
            except Exception as e:
                print(f"  특약 탭 클릭 중 오류: {e}")
                driver.quit()
                return []

        wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.table_fix_wrapper > table.tblList > tbody > tr"))
        )

        if click_all_history:
            print("  '이전 판매기간 펼치기' 버튼 처리 중...")
            try:
                expand_buttons = driver.find_elements(By.XPATH, "//button[@class='button toggler']")
                if not expand_buttons:
                    expand_buttons = driver.find_elements(
                        By.XPATH, "//button[contains(normalize-space(), '이전 판매기간 펼치기') or contains(normalize-space(), '펼치기')]")
                if not expand_buttons:
                    expand_buttons = driver.find_elements(By.XPATH, "//a[contains(text(), '이전 판매기간 펼치기')]")

                for button in expand_buttons:
                    try:
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                        time.sleep(0.5)
                        driver.execute_script("arguments[0].click();", button)
                        time.sleep(1)
                    except Exception as e_btn:
                        print(f"    펼치기 버튼 클릭 오류: {e_btn}")
            except Exception as e_find_btn:
                print(f"  펼치기 버튼 검색 중 오류: {e_find_btn}")

        time.sleep(2)  # 펼치기 후 DOM 안정화 대기

        rows = driver.find_elements(By.CSS_SELECTOR, "div.table_fix_wrapper > table.tblList > tbody > tr")
        current_main_product_name = "N/A"

        for i, row in enumerate(rows):
            th_cells = row.find_elements(By.TAG_NAME, "th")
            td_cells = row.find_elements(By.TAG_NAME, "td")

            product_name, sales_period = "N/A", "N/A"
            business_manual_link, summary_link, terms_link = "N/A", "N/A", "N/A"

            if th_cells and "rowspan" in th_cells[0].get_attribute("outerHTML") and \
               len(td_cells) == 2 and td_cells[0].get_attribute("rowspan") and \
               td_cells[1].get_attribute("colspan"):
                current_main_product_name = td_cells[0].text.strip()
                continue
            elif not th_cells and \
                ((product_type == "주보험" and len(td_cells) == 7)
                 or (product_type == "특약" and len(td_cells) == 2)):
                product_name = current_main_product_name
                sales_period = td_cells[0].text.strip()
                if product_type == "주보험":
                    bm_links = td_cells[1].find_elements(By.TAG_NAME, "a")
                    business_manual_link = bm_links[0].get_attribute('href') if bm_links and bm_links[0].text.strip() != "-" else "N/A"
                    s_links = td_cells[2].find_elements(By.TAG_NAME, "a")
                    summary_link = s_links[0].get_attribute('href') if s_links and s_links[0].text.strip() != "-" else "N/A"
                    t_links = td_cells[3].find_elements(By.TAG_NAME, "a")
                    terms_link = t_links[0].get_attribute('href') if t_links and t_links[0].text.strip() != "-" else "N/A"
                elif product_type == "특약":
                    t_links = td_cells[1].find_elements(By.TAG_NAME, "a")
                    terms_link = t_links[0].get_attribute('href') if t_links and t_links[0].text.strip() != "-" else "N/A"
            elif th_cells and "display: none" in th_cells[0].get_attribute("outerHTML") and \
                ((product_type == "주보험" and len(td_cells) == 8)
                 or (product_type == "특약" and len(td_cells) == 3)):
                product_name = td_cells[0].text.strip()
                current_main_product_name = product_name
                sales_period = td_cells[1].text.strip()
                if product_type == "주보험":
                    bm_links = td_cells[2].find_elements(By.TAG_NAME, "a")
                    business_manual_link = bm_links[0].get_attribute('href') if bm_links and bm_links[0].text.strip() != "-" else "N/A"
                    s_links = td_cells[3].find_elements(By.TAG_NAME, "a")
                    summary_link = s_links[0].get_attribute('href') if s_links and td_cells[3].text.strip() != "-" else "N/A"
                    t_links = td_cells[4].find_elements(By.TAG_NAME, "a")
                    terms_link = t_links[0].get_attribute('href') if t_links and t_links[0].text.strip() != "-" else "N/A"
                elif product_type == "특약":
                    t_links = td_cells[2].find_elements(By.TAG_NAME, "a")
                    terms_link = t_links[0].get_attribute('href') if t_links and t_links[0].text.strip() != "-" else "N/A"
            else:
                continue

            products_data.append({
                "product_name": product_name, "sales_period": sales_period,
                "business_manual_link": business_manual_link, "summary_link": summary_link,
                "terms_link": terms_link, "type": product_type
            })
    except Exception as e:
        print(f"  '{scrape_target}' 데이터 추출 중 오류: {e}")
    finally:
        if driver:
            driver.quit()
    print(f"메트라이프생명 '{scrape_target}' 정보 스크래핑 완료.")
    return products_data


def is_valid_metlife_link(link_str):
    if not link_str or not isinstance(link_str, str) or not link_str.strip():
        return False

    invalid_markers = ["N/A"]  # Metlife는 주로 "N/A" 또는 실제 링크, 가끔 "-" 텍스트
    if link_str == "-" or any(marker in link_str for marker in invalid_markers):  # "-"도 유효하지 않음으로 처리
        return False

    if link_str.strip().lower().startswith("javascript:"):  # jsFileDown 등 처리
        # JavaScript 링크는 현재 직접적인 파일 경로로 변환하기 어려우므로 유효하지 않다고 판단.
        # PdfLinkExtractor를 사용한다면 네트워크 가로채기로 처리 가능하나, 여기서는 사용 안 함.
        return False

    # HTTP 링크 확인 및 로컬 PDF 파일 확인 로직은 제거됩니다.
    return True


if __name__ == '__main__':
    all_product_entries = []

    main_insurance_data = get_metlife_product_info(scrape_target="주보험", click_all_history=True)
    if main_insurance_data:
        all_product_entries.extend(main_insurance_data)

    special_terms_data = get_metlife_product_info(scrape_target="특약", click_all_history=True)
    if special_terms_data:
        all_product_entries.extend(special_terms_data)

    if all_product_entries:
        if DatabaseManager:
            print("DB 저장 진행중...")
            structured_rows_to_save = []
            scraped_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            company_name = "메트라이프생명"

            for item in all_product_entries:
                product_name_val = item.get("product_name")
                sales_period_val = item.get("sales_period")
                product_code_val = None  # 상품코드 정보 없음
                product_type_val = item.get("type")  # "주보험" 또는 "특약"

                # 문서 타입과 링크 매핑
                # 특약의 경우 business_manual_link와 summary_link가 없을 수 있음
                doc_map = {}
                if product_type_val == "주보험":
                    doc_map = {
                        "사업방법서": item.get("business_manual_link"),
                        "상품요약서": item.get("summary_link"),
                        "약관": item.get("terms_link")
                    }
                elif product_type_val == "특약":
                    doc_map = {  # 특약은 약관만 존재
                        "약관": item.get("terms_link")
                    }

                has_valid_link_for_this_product = False
                current_product_docs = []
                for doc_type, link_url in doc_map.items():
                    if is_valid_metlife_link(link_url):
                        # Metlife 링크는 대부분 절대 URL이므로 별도 변환 불필요
                        has_valid_link_for_this_product = True
                        current_product_docs.append([
                            company_name, product_name_val, product_code_val,
                            doc_type, sales_period_val, scraped_time, link_url
                        ])

                if has_valid_link_for_this_product:
                    structured_rows_to_save.extend(current_product_docs)

            if structured_rows_to_save:
                with DatabaseManager(db_name="insurance_products.db") as db_manager:
                    saved_count = db_manager.save_data(structured_rows_to_save)
                print(f"DB 저장 완료. 총 {saved_count}건 문서 정보 저장.")
            else:
                print("DB에 저장할 유효한 문서 정보가 없습니다.")
            print(f"총 스크래핑된 상품 항목(주보험/특약, 버전 포함) 수: {len(all_product_entries)}개")
        else:
            print("DatabaseManager 사용 불가. DB 저장 기능을 건너뜁니다.")
    else:
        print("스크래핑된 상품 데이터가 없습니다.")
