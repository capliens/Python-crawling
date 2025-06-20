# KB라이프/판매중단페이지/pdf는 그냥 통합시킴/db 확인
from webdriver_manager.chrome import ChromeDriverManager
from seleniumwire import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
from selenium.webdriver.common.by import By
import os
import time
import re
import requests
import logging
from datetime import datetime  # datetime 모듈에서 datetime 클래스 임포트
from neoali.DB_save import DatabaseManager  # DatabaseManager 임포트

# 로깅 설정: INFO 레벨 이상만 출력 (DEBUG는 기본적으로 출력 안 됨)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Selenium 및 WebDriver Manager 임포트

# --- 다운로드 디렉토리 설정 ---
DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads", "kblife")
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)
logger.info(f"다운로드 디렉토리 설정됨: {DOWNLOAD_DIR}")

# --- PDF 추출 관련 함수 ---


def _is_url_live(url, timeout=5):
    """주어진 URL이 유효하고 접근 가능한지 확인합니다."""
    try:
        response = requests.head(url, timeout=timeout, allow_redirects=True)
        return 200 <= response.status_code < 400
    except requests.exceptions.RequestException as e:
        logger.debug(f"  URL '{url}' 확인 중 오류 발생: {e}")
        return False


def get_pdf_url_via_network_interception(driver, download_button_element, request_timeout=10, download_directory=None, verify_url_liveness=True):
    """
    주어진 WebElement를 클릭하여 발생하는 네트워크 요청을 가로채 PDF 다운로드 URL을 추출하거나
    로컬 다운로드 디렉토리에서 PDF 파일을 감지합니다.
    """
    pdf_url = None
    files_before_click = set()

    try:
        del driver.requests

        if download_directory and os.path.isdir(download_directory):
            files_before_click = set(os.listdir(download_directory))

        driver.execute_script("arguments[0].click();", download_button_element)
        # 이 로그는 디버깅 시에만 필요하므로 DEBUG 레벨로 설정
        logger.debug(f"    [PDF Extractor] 전달받은 WebElement 클릭 시도 완료. OuterHTML: {download_button_element.get_attribute('outerHTML')[:100]}...")

        start_time = time.time()
        found_request = False
        while time.time() - start_time < request_timeout:
            for request in driver.requests:
                if request.response:
                    response_url = request.url
                    content_type = request.response.headers.get('Content-Type', '').lower()

                    if (request.response.status_code == 200 and 'application/pdf' in content_type) or \
                       response_url.lower().endswith('.pdf') or \
                       ('Viewer' in response_url and '.pdf' in response_url):

                        if verify_url_liveness and not _is_url_live(response_url):
                            logger.debug(f"    [PDF Extractor] 비활성 PDF URL 감지 (URL 유효성 검사 실패): {response_url}. 건너뜀.")
                            continue

                        pdf_url = response_url
                        found_request = True
                        logger.info(f"    [PDF Extractor] PDF URL 발견: {pdf_url}")  # PDF 발견은 중요한 정보이므로 INFO 유지
                        break
            if found_request:
                break
            time.sleep(0.5)

        if not pdf_url and download_directory and os.path.isdir(download_directory):
            logger.debug("    [PDF Extractor] 네트워크에서 PDF URL을 찾지 못함. 로컬 다운로드 디렉토리 확인 시도.")
            download_check_timeout = 10
            download_start_time = time.time()
            new_pdf_file_path = None
            while time.time() - download_start_time < download_check_timeout:
                current_files = set(os.listdir(download_directory))
                new_files = current_files - files_before_click

                potential_pdfs = [f for f in new_files if f.lower().endswith(".pdf")]

                if potential_pdfs:
                    new_pdf_file_path = os.path.join(download_directory, potential_pdfs[0])
                    if os.path.getsize(new_pdf_file_path) > 0:
                        pdf_url = new_pdf_file_path
                        logger.info(f"    [PDF Extractor] 로컬 다운로드 감지 성공: {new_pdf_file_path}")  # 로컬 다운로드 감지도 INFO 유지
                        break
                    else:
                        logger.debug(f"    [PDF Extractor] 0바이트 파일 감지: {new_pdf_file_path}. 잠시 후 재시도.")
                        os.remove(new_pdf_file_path)
                        files_before_click.add(potential_pdfs[0])
                time.sleep(1)

    except StaleElementReferenceException:
        logger.error("    [PDF Extractor] 전달받은 WebElement가 Stale 상태 (더 이상 유효하지 않음). PDF 추출 실패.")
        return None
    except Exception as e:
        logger.error(f"    [PDF Extractor] PDF 추출 중 예외 발생: {type(e).__name__} - {e}")
        return None

    return pdf_url


def _convert_to_db_format(product_data, company_name="KB라이프"):
    """
    스크래핑된 상품 데이터를 DatabaseManager의 save_data 메서드에 적합한 형식으로 변환합니다.
    """
    structured_rows = []
    scraped_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    product_name = product_data.get("상품명", "알 수 없음")
    # product_code는 KB라이프 스크래퍼에서 직접 추출되지 않으므로, 임시로 'N/A' 또는 다른 규칙 적용
    product_code = "N/A"

    # 현재 버전 문서 처리
    current_docs = product_data.get("현재 버전 문서 링크 정보", {})
    sales_period_current = product_data.get("판매기간 (현재)", "상시")
    for doc_type, link_info in current_docs.items():
        if link_info and link_info.get("href"):
            structured_rows.append((
                company_name,
                product_name,
                product_code,
                doc_type,
                sales_period_current,
                scraped_at,
                link_info["href"]
            ))

    # 이전 판매기간 버전 문서 처리
    for historical_version in product_data.get("이전 판매기간 버전", []):
        sales_period_history = historical_version.get("판매기간", "알 수 없음")
        history_docs = historical_version.get("문서링크", {})
        for doc_type, link_info in history_docs.items():
            if link_info and link_info.get("href"):
                structured_rows.append((
                    company_name,
                    product_name,
                    product_code,
                    doc_type,
                    sales_period_history,
                    scraped_at,
                    link_info["href"]
                ))
    return structured_rows


# --- WebDriver 설정 ---


def setup_driver(headless=True, download_dir=None):
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")

    if download_dir:
        prefs = {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True
        }
        chrome_options.add_experimental_option("prefs", prefs)

    if headless:

        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.set_page_load_timeout(30)
    return driver


def _get_element_text_by_js(driver, element):
    try:
        return driver.execute_script("return arguments[0].textContent;", element).strip()
    except Exception:
        return ""


def _extract_document_links(driver, parent_element, html_doc_types_map):
    doc_links = {}
    document_cells = parent_element.find_elements(By.CSS_SELECTOR, "div.cell-3")

    for idx, cell in enumerate(document_cells):
        doc_type_key = html_doc_types_map.get(idx)
        if doc_type_key == "설명서_제외":
            continue

        try:
            download_button = cell.find_element(By.CSS_SELECTOR, "a.downFile")

            logger.debug(f"  [DEBUG] {doc_type_key} - Found download_button outerHTML: {download_button.get_attribute('outerHTML')[:300]}...")

            pdf_url = get_pdf_url_via_network_interception(
                driver,
                download_button,
                download_directory=DOWNLOAD_DIR,
                verify_url_liveness=True
            )

            if pdf_url:
                doc_links[doc_type_key] = {
                    "href": pdf_url,
                    "data_params": {
                        "fileno": download_button.get_attribute("data-fileno"),
                        "seqno": download_button.get_attribute("data-seqno"),
                        "boxno": download_button.get_attribute("data-boxno")
                    }
                }
            else:
                doc_links[doc_type_key] = None
                logger.warning(f"  [PDF Extractor] {doc_type_key}에 대한 PDF URL을 찾지 못함.")

        except NoSuchElementException:
            doc_links[doc_type_key] = None
            logger.warning(f"  [PDF Extractor] {doc_type_key} 다운로드 버튼을 찾을 수 없음 (NoSuchElementException).")
        except Exception as e:
            doc_links[doc_type_key] = None
            logger.error(f"  [PDF Extractor] {doc_type_key} PDF 링크 추출 중 오류 발생: {type(e).__name__} - {e}")

    return doc_links


def extract_product_info_from_current_page(driver, html_doc_types_map):
    current_page_products_data = []

    try:
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "rslist1")))
    except TimeoutException:
        logger.warning("경고: 'rslist1' 테이블 로드 시간 초과. 현재 페이지의 상품 정보를 가져올 수 없습니다. 다음 페이지로 이동합니다.")
        return []

    product_category_rows = driver.find_elements(By.CSS_SELECTOR, "#rslist1 > tbody > tr")

    for row_index, row_element in enumerate(product_category_rows):
        accordions = row_element.find_elements(By.CSS_SELECTOR, "ul.accordion > li.accordion-item.prd-item")

        for product_item_index, product_item_element in enumerate(accordions):
            product_full_data = {}
            try:
                head_element = WebDriverWait(product_item_element, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.head"))
                )

                product_name_element = head_element.find_element(By.CSS_SELECTOR, "div.cell-1")
                product_name_raw = _get_element_text_by_js(driver, product_name_element)
                product_full_data["상품명"] = re.sub(r'\s*\(?\s*닫힘\s*\)?\s*', '', product_name_raw).strip()

                sale_period_element = head_element.find_element(By.CSS_SELECTOR, "div.cell-2")
                product_full_data["판매기간 (현재)"] = _get_element_text_by_js(driver, sale_period_element)

                current_version_doc_links_raw = _extract_document_links(
                    driver, head_element, html_doc_types_map
                )
                product_full_data["현재 버전 문서 링크 정보"] = {
                    "요약서": current_version_doc_links_raw.get("요약서"),
                    "방법서": current_version_doc_links_raw.get("방법서"),
                    "약관": current_version_doc_links_raw.get("약관")
                }

                historical_versions = []
                try:
                    re_found_product_item_element = WebDriverWait(row_element, 3).until(
                        EC.presence_of_element_located(
                            (By.XPATH, f".//li[contains(@class, 'prd-item') and .//div[@class='head']//div[@class='cell-1']/text()[contains(.,'{product_full_data['상품명']}')]]"))
                    )
                    re_found_head_element = re_found_product_item_element.find_element(By.CSS_SELECTOR, "div.head")

                    driver.execute_script("arguments[0].click();", re_found_head_element)

                    panel_element = WebDriverWait(re_found_product_item_element, 3).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.panel"))
                    )

                    WebDriverWait(panel_element, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.row"))
                    )
                    time.sleep(0.3)

                    historical_rows = panel_element.find_elements(By.CSS_SELECTOR, "div.row")

                    for history_row_idx, history_row_element in enumerate(historical_rows):
                        history_data = {}

                        try:
                            history_period_element = history_row_element.find_element(By.CSS_SELECTOR, "div.cell-2")
                            history_data["판매기간"] = _get_element_text_by_js(driver, history_period_element)
                        except NoSuchElementException:
                            history_data["판매기간"] = None

                        history_data["문서링크"] = _extract_document_links(
                            driver, history_row_element, html_doc_types_map
                        )
                        historical_versions.append(history_data)

                except TimeoutException:
                    pass
                except NoSuchElementException:
                    pass
                except StaleElementReferenceException:
                    logger.warning(f"  [경고] 상품 '{product_full_data['상품명']}': 아코디언 처리 중 StaleElementReferenceException 발생. "
                                   "이 상품의 과거 버전 정보 건너뜀.")
                except Exception as e:
                    logger.error(f"  [오류] 상품 '{product_full_data['상품명']}': 이전 판매 기간 처리 중 예상치 못한 오류 발생: "
                                 f"{type(e).__name__} - {e}")

                product_full_data["이전 판매기간 버전"] = historical_versions
                current_page_products_data.append(product_full_data)

            except StaleElementReferenceException:
                logger.warning("  [경고] 상품 아이템 처리 중 StaleElementReferenceException 발생. 이 상품 건너뜀.")
                continue
            except NoSuchElementException as e:
                logger.warning(f"  [경고] 필수 상품 정보(이름, 판매기간)를 찾을 수 없음. 상품 건너뜀. ({e})")
            except Exception as e:
                logger.error(f"  [오류] 상품 아이템 처리 중 예상치 못한 오류 발생: {type(e).__name__} - {e}")

    return current_page_products_data


def scrape_all_pages(driver, base_url):
    all_products_data = []

    driver.get(base_url)

    try:
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "rslist1")))
    except TimeoutException:
        logger.critical(f"치명적 오류: '{base_url}' 초기 페이지에서 'rslist1' 테이블을 찾지 못했습니다. 스크래핑을 중단합니다.")
        return []

    html_doc_types_map = {
        0: "요약서", 1: "설명서_제외", 2: "방법서", 3: "약관"
    }

    current_page_num = 1
    while True:
        logger.info(f"\n--- 페이지 {current_page_num} 스크래핑 시작 ---")

        products_on_current_page = extract_product_info_from_current_page(
            driver, html_doc_types_map
        )
        all_products_data.extend(products_on_current_page)

        logger.info(f"--- 페이지 {current_page_num} 스크래핑 완료. 추출된 상품 수: {len(products_on_current_page)} ---")

        try:
            pagination_div = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.ID, "ajaxPaging1"))
            )

            next_page_num_expected = current_page_num + 1
            next_page_link_locator = By.CSS_SELECTOR, f"#ajaxPaging1 a[data-pagingevent='{next_page_num_expected}']"

            next_page_link_element = None
            try:
                next_page_link_element = WebDriverWait(pagination_div, 3).until(
                    EC.element_to_be_clickable(next_page_link_locator)
                )
            except TimeoutException:
                logger.info(f"정보: 다음 페이지({next_page_num_expected}) 링크를 찾을 수 없습니다. 마지막 페이지에 도달한 것으로 간주합니다.")
                break

            if next_page_link_element:
                logger.info(f"다음 페이지({next_page_num_expected})로 이동합니다.")

                old_tbody = driver.find_element(By.CSS_SELECTOR, "#rslist1 > tbody")

                driver.execute_script("arguments[0].click();", next_page_link_element)
                current_page_num = next_page_num_expected

                try:
                    WebDriverWait(driver, 10).until(EC.staleness_of(old_tbody))
                except TimeoutException:
                    logger.warning("경고: 이전 상품 목록 tbody가 stale해지지 않음. 페이지 갱신이 예상보다 느리거나 다르게 발생했을 수 있습니다.")

                WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "rslist1")))

            else:
                logger.info("정보: 마지막 페이지에 도달했습니다. 더 이상 다음 페이지가 없습니다.")
                break

        except StaleElementReferenceException:
            logger.warning("경고: 페이지네이션 요소가 갱신되어 StaleElementReferenceException 발생. 다음 루프에서 재시도합니다.")
            continue
        except Exception as e:
            logger.critical(f"치명적 오류: 페이지네이션 처리 중 예상치 못한 오류 발생: {type(e).__name__} - {e}. 스크래핑을 중단합니다.")
            break

    return all_products_data


# --- 스크래핑 실행 부분 ---
if __name__ == "__main__":
    url = "https://www.kblife.co.kr/customer-common/productList.do"

    driver = None
    try:
        driver = setup_driver(headless=False, download_dir=DOWNLOAD_DIR)

        all_products_data = scrape_all_pages(driver, url)

        logger.info("\n" + "=" * 50)
        logger.info("모든 페이지에서 최종 추출된 상품 정보 요약")
        logger.info(f"총 추출된 상품 수: {len(all_products_data)}")
        logger.info("=" * 50)

        if not all_products_data:
            logger.info("추출된 상품 정보가 없습니다.")
        else:
            # 최종 결과 요약은 그대로 INFO 레벨로 출력하여 스크래핑 완료 후 내용을 확인할 수 있도록 합니다.
            for i, product in enumerate(all_products_data[:5]):  # 상위 5개 상품만 출력 예시
                logger.info(f"\n--- 상품 {i + 1}: {product.get('상품명', '이름 없음')} ---")
                logger.info(f"판매기간 (현재): {product.get('판매기간 (현재)', '정보 없음')}")
                logger.info("  현재 버전 문서 링크 (요약서, 방법서, 약관):")
                for doc_type in ["요약서", "방법서", "약관"]:
                    link_info = product.get('현재 버전 문서 링크 정보', {}).get(doc_type)
                    if link_info:
                        logger.info(f"    - {doc_type}: {link_info.get('href', '링크 없음')}")
                    else:
                        logger.info(f"    - {doc_type}: 없음")
                logger.info(f"  이전 판매기간 버전 수: {len(product.get('이전 판매기간 버전', []))}")
                logger.info("-" * 30)

            # DB 저장 로직 추가
            db_name = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_web_data.db")
            with DatabaseManager(db_name=db_name) as db_manager:
                total_saved_count = 0
                for product in all_products_data:
                    structured_rows = _convert_to_db_format(product, company_name="KB라이프")
                    if structured_rows:
                        saved_count = db_manager.save_data(structured_rows)
                        total_saved_count += saved_count
                logger.info(f"\n총 {total_saved_count}건의 상품 문서 정보가 DB에 저장되었습니다.")

    except Exception as e:
        logger.critical(f"스크래핑 실행 중 전역 예외 발생: {type(e).__name__} - {e}")
    finally:
        if driver:
            driver.quit()
