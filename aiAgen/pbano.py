# 수호천사동양생명/판매페이지는 페이지오류
from seleniumwire import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager
import time
import os
import sys
from datetime import datetime

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

PBANO_DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads", "pbano")
if not os.path.exists(PBANO_DOWNLOAD_DIR):
    os.makedirs(PBANO_DOWNLOAD_DIR)


def scrape_pbano_products():
    print("PBA손해보험 스크래핑 시작...")  # 함수 시작 시 로그
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    prefs = {
        "download.default_directory": PBANO_DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True,
        "profile.default_content_setting_values.automatic_downloads": 1
    }
    options.add_experimental_option("prefs", prefs)
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    wait = WebDriverWait(driver, 10)

    pdf_extractor = None
    if PdfLinkExtractor:
        pdf_extractor = PdfLinkExtractor(driver, PBANO_DOWNLOAD_DIR)

    url = "https://pbano.myangel.co.kr/paging/WE_AC_WEPAAP020100L"
    driver.get(url)

    all_products_data = []
    page_num = 1

    try:
        while True:
            print(f"페이지 {page_num} 스크래핑 중...")  # 페이지 번호 명시
            try:
                table_body_selector = "table.tableStyle > tbody"
                table_body = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, table_body_selector))
                )
                time.sleep(0.5)  # DOM 안정화 시간 단축
                rows = table_body.find_elements(By.TAG_NAME, "tr")

                base_tbody_xpath = "//table[contains(@class,'tableStyle')]/tbody"

                for row_idx, row in enumerate(rows):
                    current_row_xpath_prefix = f"({base_tbody_xpath}/tr)[{row_idx + 1}]"
                    try:
                        current_row_element = driver.find_element(By.XPATH, current_row_xpath_prefix)
                        cells = current_row_element.find_elements(By.TAG_NAME, "td")
                    except (NoSuchElementException, TimeoutException):
                        # print(f"  행 {row_idx + 1} 다시 가져오기 실패. 건너뜁니다.") # 상세 로그 제거
                        continue
                    if not cells:
                        continue

                    product_name = cells[3].text.strip() if len(cells) > 3 else "N/A"
                    sales_period = cells[4].text.strip() if len(cells) > 4 else "N/A"

                    summary_link_val = "N/A"
                    business_method_link_val = "N/A"
                    insurance_terms_link_val = "N/A"

                    if pdf_extractor:
                        # 상품요약서 (td[6] -> XPath td index 6)
                        if len(cells) > 5:
                            summary_xpath = f"{current_row_xpath_prefix}/td[6]/a"
                            summary_link_val = pdf_extractor.extract_pdf_link(None, summary_xpath)

                        # 사업방법서 (td[7] -> XPath td index 7)
                        if len(cells) > 6:
                            biz_method_xpath = f"{current_row_xpath_prefix}/td[7]/a"
                            business_method_link_val = pdf_extractor.extract_pdf_link(None, biz_method_xpath)

                        # 보험약관 (td[8] -> XPath td index 8)
                        if len(cells) > 7:
                            terms_xpath = f"{current_row_xpath_prefix}/td[8]/a"
                            insurance_terms_link_val = pdf_extractor.extract_pdf_link(None, terms_xpath)
                    else:
                        if len(cells) > 5:
                            try:
                                link_element = cells[5].find_element(By.TAG_NAME, "a")
                                summary_link_val = link_element.get_attribute("href") or "N/A (href 없음)"
                            except NoSuchElementException:
                                summary_link_val = "N/A (링크 요소 없음)"
                        if len(cells) > 6:
                            try:
                                link_element = cells[6].find_element(By.TAG_NAME, "a")
                                business_method_link_val = link_element.get_attribute("href") or "N/A (href 없음)"
                            except NoSuchElementException:
                                business_method_link_val = "N/A (링크 요소 없음)"
                        if len(cells) > 7:
                            try:
                                link_element = cells[7].find_element(By.TAG_NAME, "a")
                                insurance_terms_link_val = link_element.get_attribute("href") or "N/A (href 없음)"
                            except NoSuchElementException:
                                insurance_terms_link_val = "N/A (링크 요소 없음)"

                    all_products_data.append({
                        "상품명": product_name,
                        "판매기간": sales_period,
                        "상품요약서": summary_link_val,
                        "사업방법서": business_method_link_val,
                        "보험약관": insurance_terms_link_val
                    })
                    # print(f"  추가됨: {product_name}, 요약서: {summary_link_val}, 사업방법서: {business_method_link_val}, 약관: {insurance_terms_link_val}") # 상세 로그 제거

                current_page_element = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.paging strong"))
                )
                current_page_number = int(current_page_element.text)

                next_page_link_found = False
                page_links = driver.find_elements(By.CSS_SELECTOR, "div.paging a")
                for link in page_links:
                    try:
                        link_text = link.text.strip()
                        if link_text.isdigit():
                            page_number_in_link = int(link_text)
                            if page_number_in_link == current_page_number + 1:
                                driver.execute_script("arguments[0].click();", link)
                                page_num += 1
                                time.sleep(2)
                                next_page_link_found = True
                                break
                    except ValueError:
                        continue
                    except StaleElementReferenceException:
                        # print("페이지 링크가 stale 상태가 됨. 페이지네이션 재시도 필요할 수 있음.") # 상세 로그 제거
                        break

                if not next_page_link_found:
                    # print("다음 페이지 링크를 찾지 못했습니다. 스크래핑을 종료합니다.") # 상세 로그 제거
                    break
            except TimeoutException:
                print(f"페이지 {page_num}: 테이블/페이지네이션 요소 찾기 시간 초과. 종료합니다.")
                break
            except Exception as e:
                print(f"스크래핑 중 오류 발생 (페이지 {page_num}): {e}")
                break
    finally:
        if driver:
            driver.quit()
        print("PBA손해보험 스크래핑 완료.")  # 함수 종료 시 로그
    return all_products_data


def is_valid_pbano_link(link_str):
    if not link_str or not isinstance(link_str, str) or not link_str.strip():
        return False
    invalid_markers = ["N/A", "(추출 실패)", "(링크/버튼 없음)", "(링크 요소 없음)", "(href 없음)", "(추출 오류)"]
    if any(marker in link_str for marker in invalid_markers):
        return False
    if link_str.strip().lower().startswith("javascript:"):
        return False

    is_http_link = link_str.startswith("http")

    is_local_pdf_file = False
    # HTTP 링크가 아닌 경우, 로컬 파일 경로인지 그리고 PDF 파일인지 확인
    if not is_http_link:
        try:
            # PdfLinkExtractor가 반환하는 경로가 절대 경로라고 가정
            if os.path.exists(link_str) and link_str.lower().endswith(".pdf"):
                is_local_pdf_file = True
            # 만약 PdfLinkExtractor가 PBANO_DOWNLOAD_DIR 기준의 상대 경로(예: 파일명)를 반환한다면,
            # 아래와 같이 PBANO_DOWNLOAD_DIR와 조합하여 경로를 만들어 확인해야 할 수 있습니다.
            # elif os.path.exists(os.path.join(PBANO_DOWNLOAD_DIR, link_str)) and link_str.lower().endswith(".pdf"):
            # is_local_pdf_file = True
        except Exception:  # 경로 관련 오류 발생 시 False로 유지
            pass
    # HTTP 링크이지만 .pdf로 끝나지 않는 경우 (필요시 이 조건은 사이트 특성에 맞게 조정)
    elif is_http_link and not link_str.lower().endswith(".pdf"):
        return False  # PDF가 아닌 다른 문서 형식은 일단 제외

    return is_http_link or is_local_pdf_file


if __name__ == "__main__":
    scraped_data = scrape_pbano_products()

    if scraped_data:
        if DatabaseManager:
            print("DB 저장 진행중...")
            structured_rows_to_save = []
            scraped_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            company_name = "PBA손해보험"  # 회사명 확인 필요 (PBA Primary 한국자산평가 일수도 있음)

            for item in scraped_data:
                product_name_val = item.get("상품명")
                sales_period_val = item.get("판매기간")
                product_code_val = None

                doc_map = {
                    "상품요약서": item.get("상품요약서"),
                    "사업방법서": item.get("사업방법서"),
                    "보험약관": item.get("보험약관")
                }

                has_valid_link_for_this_product = False
                current_product_docs = []
                for doc_type, link_url in doc_map.items():
                    if is_valid_pbano_link(link_url):
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
            print(f"총 스크래핑된 상품 수: {len(scraped_data)}개")
        else:
            print("DatabaseManager 사용 불가. DB 저장 기능을 건너뜁니다.")
    else:
        print("스크래핑된 상품 데이터가 없습니다.")
