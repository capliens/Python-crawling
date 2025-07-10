# 수호천사동양생명/판매페이지는 페이지오류/링크가져오기 수정함
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
import re  # 정규표현식 사용을 위해 re 모듈 임포트
from datetime import datetime

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from neoali.DB_save import DatabaseManager
except ImportError as e:
    DatabaseManager = None
    print(f"경고: 모듈 임포트 실패 ({e}). 일부 기능이 비활성화될 수 있습니다.")


def scrape_pbano_products():
    print("PBA손해보험 스크래핑 시작...")
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    wait = WebDriverWait(driver, 10)

    url = "https://pbano.myangel.co.kr/paging/WE_AC_WEPAAP020100L"
    driver.get(url)

    all_products_data = []
    page_num = 1

    try:
        while True:
            print(f"페이지 {page_num} 스크래핑 중...")
            try:
                table_body_selector = "table.tableStyle > tbody"
                table_body = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, table_body_selector))
                )
                time.sleep(0.5)
                rows = table_body.find_elements(By.TAG_NAME, "tr")

                base_tbody_xpath = "//table[contains(@class,'tableStyle')]/tbody"

                for row_idx, row in enumerate(rows):
                    current_row_xpath_prefix = f"({base_tbody_xpath}/tr)[{row_idx + 1}]"
                    try:
                        current_row_element = driver.find_element(By.XPATH, current_row_xpath_prefix)
                        cells = current_row_element.find_elements(By.TAG_NAME, "td")
                    except (NoSuchElementException, TimeoutException):
                        continue
                    if not cells:
                        continue

                    product_name = cells[3].text.strip() if len(cells) > 3 else "N/A"
                    sales_period = cells[4].text.strip() if len(cells) > 4 else "N/A"

                    summary_link_val = "N/A"
                    business_method_link_val = "N/A"
                    insurance_terms_link_val = "N/A"

                    # --- 수정된 부분 시작 ---
                    def extract_and_construct_link(cell_index):
                        if len(cells) > cell_index:
                            try:
                                link_element = cells[cell_index].find_element(By.TAG_NAME, "a")
                                href = link_element.get_attribute("href")
                                if href and "javascript:MasFiledownload" in href:
                                    # 정규 표현식을 사용하여 FILE_GRP_ID 추출
                                    match = re.search(r"MasFiledownload\('_N', '(.*?)'\)", href)
                                    if match:
                                        file_grp_id = match.group(1)
                                        # 추출된 FILE_GRP_ID로 완전한 다운로드 URL 구성
                                        return f"https://pbano.myangel.co.kr/process/CO_ComDownload?_biz_op_code=FDL&FILE_GRP_ID={file_grp_id}"
                                    else:
                                        return "N/A (FILE_GRP_ID 추출 실패)"
                                elif href:  # href가 있으나 javascript 함수가 아닌 경우
                                    return href
                                else:  # href가 없는 경우
                                    return "N/A (href 없음)"
                            except NoSuchElementException:  # 링크 요소가 없는 경우
                                return "N/A (링크 요소 없음)"
                        return "N/A"

                    # 상품요약서 (td[6] -> cells 인덱스 5)
                    summary_link_val = extract_and_construct_link(5)

                    # 사업방법서 (td[7] -> cells 인덱스 6)
                    business_method_link_val = extract_and_construct_link(6)

                    # 보험약관 (td[8] -> cells 인덱스 7)
                    insurance_terms_link_val = extract_and_construct_link(7)
                    # --- 수정된 부분 끝 ---

                    all_products_data.append({
                        "상품명": product_name,
                        "판매기간": sales_period,
                        "상품요약서": summary_link_val,
                        "사업방법서": business_method_link_val,
                        "보험약관": insurance_terms_link_val
                    })

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
                        break

                if not next_page_link_found:
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
        print("PBA손해보험 스크래핑 완료.")
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
    if not is_http_link:
        try:
            if os.path.exists(link_str) and link_str.lower().endswith(".pdf"):
                is_local_pdf_file = True
        except Exception:
            pass
    elif is_http_link and not link_str.lower().endswith(".pdf"):
        return False

    return is_http_link or is_local_pdf_file


if __name__ == "__main__":
    scraped_data = scrape_pbano_products()

    if scraped_data:
        if DatabaseManager:
            print("DB 저장 진행중...")
            structured_rows_to_save = []
            scraped_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            company_name = "PBA손해보험"

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
