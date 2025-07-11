# 흥국화재/페이로드?
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from seleniumwire import webdriver
import time
import os
import sys
from datetime import datetime
import urllib.parse  # <-- urllib.parse 모듈 임포트

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from neoali.pdf_link_scraper import PdfLinkExtractor
    from neoali.DB_save import DatabaseManager
except ImportError as e:
    PdfLinkExtractor = None
    DatabaseManager = None
    print(f"경고: 모듈 임포트 실패 ({e}). 일부 기능이 비활성화될 수 있습니다.")

HEUNGKUK_DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads", "heungkukfire")
if not os.path.exists(HEUNGKUK_DOWNLOAD_DIR):
    os.makedirs(HEUNGKUK_DOWNLOAD_DIR)

# --- PdfLinkExtractor 초기화 시 사용할 URL 필터링 패턴 ---
# 개발자 도구 Network 탭에서 확인한 실제 PDF 다운로드 요청 URL의 공통 부분
# 로그에서 확인된 패턴은 'download.do'로 충분합니다.
HEUNGKUK_PDF_DOWNLOAD_URL_BASE_PATTERN = 'download.do'

# --- PDF 다운로드 요청의 기본 URL (페이로드와 합쳐질 부분) ---
# 이 URL은 'download.do' 요청이 실제로 가는 기본 URL이어야 합니다.
# 로그에서 'https://www.heungkukfire.co.kr/common/download.do' 부분이 기본 URL입니다.
HEUNGKUK_BASE_DOWNLOAD_URL = 'https://www.heungkukfire.co.kr/common/download.do'


def get_product_info_from_page_selenium(driver, pdf_extractor):
    """현재 페이지의 상품 정보를 Selenium과 PdfLinkExtractor를 사용하여 추출"""
    products = []
    product_table_container_selector = "div.tbl_chk_tb"
    try:
        # 테이블 컨테이너가 로드될 때까지 대기
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, f"{product_table_container_selector} table tbody"))
        )
        # tbody 내의 모든 tr (데이터 행)
        rows = driver.find_elements(By.CSS_SELECTOR, f"{product_table_container_selector} table tbody tr")
        if not rows:  # tbody가 없거나 tr이 없는 경우, table 바로 아래 tr 시도 (헤더가 있을 수 있음)
            rows = driver.find_elements(By.CSS_SELECTOR, f"{product_table_container_selector} table tr")
            # 만약 첫 행이 th로 된 헤더라면 건너뛰는 로직 추가 필요
            if rows and rows[0].find_elements(By.TAG_NAME, "th"):
                rows = rows[1:]

    except TimeoutException:
        print("상품 테이블(tbody tr)을 찾는 데 시간 초과.")
        return products
    except NoSuchElementException:
        print("상품 테이블을 찾을 수 없습니다.")
        return products

    if not rows:
        print("상품 행을 찾을 수 없습니다.")
        return products

    # 각 행의 XPath를 만들기 위한 기본 테이블 XPath (실제 구조에 따라 조정 필요)
    base_row_xpath_prefix = "//div[contains(@class, 'tbl_chk_tb')]/table/tbody"

    for idx, row_element in enumerate(rows):
        try:
            cols = row_element.find_elements(By.TAG_NAME, "td")
            if len(cols) < 5:
                continue

            product_name = cols[2].text.strip()
            sale_date = cols[3].text.strip()
            current_row_xpath = f"({base_row_xpath_prefix}/tr)[{idx + 1}]"

            terms_link_xpath = f"{current_row_xpath}/td[5]/descendant::a[contains(text(),'약관') or contains(text(),'상품약관')][1]"
            biz_method_link_xpath = f"{current_row_xpath}/td[5]/descendant::a[contains(text(),'사업방법서')][1]"
            summary_link_xpath = f"{current_row_xpath}/td[5]/descendant::a[contains(text(),'상품요약서')][1]"
            link_elements_in_cell = cols[4].find_elements(By.TAG_NAME, "a")

            terms_link_val = "N/A"
            biz_method_link_val = "N/A"
            summary_link_val = "N/A"

            # PDF 링크 추출 기능 복구 및 URL 조합
            if pdf_extractor:
                # 약관
                payload = pdf_extractor.get_pdf_download_payload(terms_link_xpath, 15)
                if payload and is_valid_heungkuk_payload(payload):
                    # 기본 URL에 페이로드를 쿼리 스트링으로 추가하여 완전한 URL 생성
                    terms_link_val = f"{HEUNGKUK_BASE_DOWNLOAD_URL}?{payload}"
                else:
                    terms_link_val = "N/A (페이로드 추출 실패)"

                # 사업방법서
                payload = pdf_extractor.get_pdf_download_payload(biz_method_link_xpath, 15)
                if payload and is_valid_heungkuk_payload(payload):
                    biz_method_link_val = f"{HEUNGKUK_BASE_DOWNLOAD_URL}?{payload}"
                else:
                    biz_method_link_val = "N/A (페이로드 추출 실패)"

                # 상품요약서
                payload = pdf_extractor.get_pdf_download_payload(summary_link_xpath, 15)
                if payload and is_valid_heungkuk_payload(payload):
                    summary_link_val = f"{HEUNGKUK_BASE_DOWNLOAD_URL}?{payload}"
                else:
                    summary_link_val = "N/A (페이로드 추출 실패)"
            else:  # PdfLinkExtractor가 없는 경우
                if len(link_elements_in_cell) > 0:
                    terms_link_val = "존재함 (Extractor 비활성)"
                else:
                    terms_link_val = "N/A (링크 요소 없음)"
                if len(link_elements_in_cell) > 1:
                    biz_method_link_val = "존재함 (Extractor 비활성)"
                else:
                    biz_method_link_val = "N/A (링크 요소 없음)"
                if len(link_elements_in_cell) > 2:
                    summary_link_val = "존재함 (Extractor 비활성)"
                else:
                    summary_link_val = "N/A (링크 요소 없음)"

            products.append({
                "product_name": product_name,
                "sale_date": sale_date,
                "terms_link": terms_link_val,
                "business_method_link": biz_method_link_val,
                "summary_link": summary_link_val
            })
        except Exception as e_row:
            print(f"  행 {idx + 1} 처리 중 오류: {e_row}")
            continue
    return products


def get_current_page_number(driver, pagination_area):
    active_page_element = None
    try:
        active_page_element = pagination_area.find_element(By.CSS_SELECTOR, "a.on")
    except NoSuchElementException:
        try:
            active_page_element = pagination_area.find_element(By.CSS_SELECTOR, "a[title='현재페이지']")
        except NoSuchElementException:
            return -1

    active_page_text = active_page_element.text.strip()
    if not active_page_text.isdigit():
        try:
            span_in_active = active_page_element.find_element(By.TAG_NAME, "span")
            active_page_text = span_in_active.text.strip()
        except NoSuchElementException:
            return -1

    if not active_page_text.isdigit():
        return -1
    return int(active_page_text)


def click_tab_and_scrape(driver, pdf_extractor, tab_name, tab_selector, product_type_selector_list, all_products_list):
    """특정 탭(판매상품/판매중지)을 클릭하고, 그 안의 상품군들을 스크래핑하는 함수"""
    print(f"{tab_name} 정보 수집 중...")
    try:
        tab_element = WebDriverWait(driver, 10).until(EC.element_to_be_clickable(tab_selector))
        driver.execute_script("arguments[0].click();", tab_element)
        time.sleep(2)
    except TimeoutException:
        print(f"'{tab_name}' 탭 ({tab_selector})을 찾거나 클릭할 수 없습니다.")
        return

    for pt_name, pt_selector in product_type_selector_list:
        print(f"  상품군 '{pt_name}' 처리 중...")
        try:
            if pt_selector:
                pt_element = WebDriverWait(driver, 10).until(EC.element_to_be_clickable(pt_selector))
                driver.execute_script("arguments[0].click();", pt_element)
                time.sleep(2)

            page_count = 0
            previous_page_num = 0
            while True:
                page_count += 1
                try:
                    pagination_area_check = driver.find_element(By.CSS_SELECTOR, "div.paginate")
                    current_page_num = get_current_page_number(driver, pagination_area_check)
                except NoSuchElementException:
                    current_page_num = 1 if page_count == 1 else previous_page_num
                    if page_count > 1 and previous_page_num == current_page_num :
                        break  # 페이지네이션 영역이 없으면 첫 페이지만 스크래핑
                if current_page_num == -1:  # 페이지 번호를 찾을 수 없는 경우
                    break

                if previous_page_num != current_page_num or page_count == 1:
                    print(f"    '{pt_name}' 상품군 페이지 {current_page_num} 스크래핑 중...")
                    page_products = get_product_info_from_page_selenium(driver, pdf_extractor)
                    if page_products:
                        for prod in page_products:
                            prod['product_type_tab'] = tab_name
                            prod['product_type_group'] = pt_name
                        all_products_list.extend(page_products)
                previous_page_num = current_page_num
                try:
                    pagination_area_nav = driver.find_element(By.CSS_SELECTOR, "div.paginate")
                    next_page_button = pagination_area_nav.find_element(By.CSS_SELECTOR, "a.go_next")
                    if next_page_button.is_displayed() and next_page_button.is_enabled():
                        driver.execute_script("arguments[0].click();", next_page_button)
                        time.sleep(3)  # 페이지 로드 대기
                        WebDriverWait(driver, 10).until(EC.staleness_of(pagination_area_nav))  # 이전 페이지네이션 요소가 사라질 때까지 대기
                    else:
                        break  # 다음 페이지 버튼이 없거나 비활성화되면 종료
                except (NoSuchElementException, TimeoutException):
                    break  # 다음 페이지 버튼을 찾을 수 없거나 타임아웃
                except Exception as e_nav:
                    print(f"    페이지 이동 중 오류: {e_nav}. 현재 상품군 종료.")
                    break
        except TimeoutException:
            print(f"    상품군 '{pt_name}' ({pt_selector})을 찾거나 클릭할 수 없습니다.")
            continue
        except Exception as e_pt:
            print(f"    상품군 '{pt_name}' 처리 중 오류: {e_pt}")
            continue
    print(f"{tab_name} 정보 수집 완료.")


def main():
    print("흥국화재 스크래핑 시작...")
    service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    prefs = {
        "download.default_directory": HEUNGKUK_DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True
    }
    options.add_experimental_option("prefs", prefs)

    driver = webdriver.Chrome(service=service, seleniumwire_options={}, options=options)
    driver.set_page_load_timeout(30)

    pdf_extractor = None
    if PdfLinkExtractor:
        # PdfLinkExtractor 초기화 시 정의된 패턴 사용
        pdf_extractor = PdfLinkExtractor(driver, HEUNGKUK_DOWNLOAD_DIR, url_filter_pattern=HEUNGKUK_PDF_DOWNLOAD_URL_BASE_PATTERN)

    url = "https://www.heungkukfire.co.kr/FRW/announce/insGoodsGongsiSale.do"
    all_products_data = []

    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "ul#id_modeTab")))

        mode_tab_elements = driver.find_elements(By.CSS_SELECTOR, "ul#id_modeTab > li > a")
        if not mode_tab_elements:
            print("상품 상태 탭(ul#id_modeTab)을 찾을 수 없습니다.")
            return all_products_data

        ins_type_tab_links_selectors = []
        try:
            ins_type_elements = driver.find_elements(By.CSS_SELECTOR, "ul#id_insTypeTab > li > a")
            for i, el in enumerate(ins_type_elements):
                el_text = el.text.strip() if el.text.strip() else f"상품군{i + 1}"
                ins_type_tab_links_selectors.append((el_text, (By.XPATH,
                                                               f"(//ul[@id='id_insTypeTab']/li/a)[{i + 1}]")))
            if not ins_type_tab_links_selectors:
                ins_type_tab_links_selectors.append(("기본 상품군", None))
        except Exception as e:
            print(f"id_insTypeTab 상품군 탭 분석 중 오류: {e}. 현재 상태로 진행합니다.")
            ins_type_tab_links_selectors.append(("기본 상품군", None))

        selling_tab_selector = (By.CSS_SELECTOR, "ul#id_modeTab > li:nth-child(1) > a")
        click_tab_and_scrape(driver, pdf_extractor, "판매상품", selling_tab_selector,
                             ins_type_tab_links_selectors, all_products_data)

        discontinued_tab_selector = (By.CSS_SELECTOR, "ul#id_modeTab > li:nth-child(2) > a")
        click_tab_and_scrape(driver, pdf_extractor, "판매중지상품", discontinued_tab_selector,
                             ins_type_tab_links_selectors, all_products_data)

    except Exception as e:
        print(f"메인 스크래핑 과정 중 오류 발생: {e}")
    finally:
        if driver:
            driver.quit()
        print("흥국화재 스크래핑 완료.")
    return all_products_data


def is_valid_heungkuk_payload(payload_str):  # 이름 변경: is_valid_heungkuk_link -> is_valid_heungkuk_payload
    # 이 함수는 get_pdf_download_payload가 반환하는 '페이로드 문자열'의 유효성을 검사합니다.
    if not payload_str or not isinstance(payload_str, str):
        return False

    invalid_markers = ["N/A", "(추출 실패)", "(링크 요소 없음)", "(Extractor 비활성)", "BINARY_PAYLOAD", "None"]
    if any(marker in payload_str for marker in invalid_markers):
        return False

    # 페이로드 길이가 너무 짧으면 유효하지 않다고 판단 (최소 5자로 설정, 필요에 따라 조정)
    if len(payload_str.strip()) < 5:
        return False

    # URL 인코딩된 폼 데이터 형식인지 추가 확인 (예: '=' 문자가 있는지)
    if '=' not in payload_str:
        return False

    return True


if __name__ == "__main__":
    collected_data = main()

    if collected_data:
        if DatabaseManager:
            print("DB 저장 진행중...")
            structured_rows_to_save = []
            scraped_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            company_name = "흥국화재"

            for item in collected_data:
                product_name_val = item.get("product_name")
                sales_period_val = item.get("sale_date")
                product_code_val = None

                doc_map = {
                    "상품요약서": item.get("summary_link"),
                    "약관": item.get("terms_link"),
                    "사업방법서": item.get("business_method_link")
                }

                has_valid_link_for_this_product = False
                current_product_docs = []
                for doc_type, link_url in doc_map.items():
                    # is_valid_heungkuk_payload 함수를 사용하여 유효성 검사
                    # link_url 변수에는 이제 'https://www.heungkukfire.co.kr/common/download.do?filePath=...' 형태의 완전한 URL이 들어 있습니다.
                    if is_valid_heungkuk_payload(link_url):  # 이제 이 함수는 완전한 URL 문자열을 검사합니다.
                        has_valid_link_for_this_product = True
                        current_product_docs.append([
                            company_name, product_name_val, product_code_val,
                            doc_type, sales_period_val, scraped_time, link_url  # 완전한 URL 저장
                        ])

                if has_valid_link_for_this_product:
                    structured_rows_to_save.extend(current_product_docs)

            if structured_rows_to_save:
                with DatabaseManager(db_name="heungkukfire_web_data.db") as db_manager:
                    saved_count = db_manager.save_data(structured_rows_to_save)
                print(f"DB 저장 완료. 총 {saved_count}건 문서 정보 저장.")
            else:
                print("DB에 저장할 유효한 문서 정보가 없습니다.")
            print(f"총 스크래핑된 상품 항목 수: {len(collected_data)}개")
        else:
            print("DatabaseManager 사용 불가. DB 저장 기능을 건너뜁니다.")
    else:
        print("스크래핑된 상품 데이터가 없습니다.")
