# 현대라이프생명보험
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from seleniumwire import webdriver  # selenium 대신 seleniumwire 임포트
import time
import os
import sys
from datetime import datetime  # datetime import 추가

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from neoali.pdf_link_scraper import PdfLinkExtractor
    from neoali.DB_save import DatabaseManager  # DatabaseManager import 추가
except ImportError as e:
    PdfLinkExtractor = None
    DatabaseManager = None  # DatabaseManager 초기화 추가
    print(f"경고: 모듈 임포트 실패 ({e}). 일부 기능이 비활성화될 수 있습니다.")

DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads", "fubonhyundai")  # 다운로드 폴더명 구체화
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# generate_xpath_for_element 함수는 현재 사용되지 않으므로 전체 삭제


def get_product_info():
    print("현대라이프생명보험 스크래핑 시작...")  # 함수 시작 시 로그
    chrome_options = webdriver.ChromeOptions()
    prefs = {
        "download.default_directory": DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True  # PDF를 외부에서 열도록 (다운로드 유도)
    }
    chrome_options.add_experimental_option("prefs", prefs)
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # Selenium Wire는 네트워크 요청 가로채기를 자동으로 처리하므로, 별도의 로깅 설정은 필요 없습니다.

    driver = None
    pdf_extractor = None
    try:
        service = Service(ChromeDriverManager().install())
        # Selenium Wire의 Chrome 드라이버를 사용합니다.
        driver = webdriver.Chrome(service=service, seleniumwire_options={}, options=chrome_options)
        if PdfLinkExtractor:
            pdf_extractor = PdfLinkExtractor(driver, DOWNLOAD_DIR)
            print("PdfLinkExtractor가 성공적으로 로드되었습니다.")
        else:
            print("경고: PdfLinkExtractor가 로드되지 않았습니다. PDF 링크 추출 기능이 제한될 수 있습니다.")
    except Exception as e:
        print(f"웹 드라이버 설정 중 오류 발생: {e}")
        if driver:
            driver.quit()
        return []  # 오류 발생 시 빈 리스트 반환

    base_url = "https://www.fubonhyundai.com/#CUSI150102010101"
    driver.get(base_url)
    # driver.implicitly_wait(5) # 명시적 대기를 사용하므로 제거

    all_products_data = []
    # print("푸본현대생명 '판매중지상품' 탭 정보 수집 중...") # 이미 get_product_info 시작 시 로그 있음
    try:
        search_tab_selector = "div.c-tab__list > button#tab-list3-3"
        search_tab_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, search_tab_selector))
        )
        driver.execute_script("arguments[0].click();", search_tab_button)

        clicked_panel_selector = "div#tab-panel3-3"
        WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, clicked_panel_selector))
        )

        specific_c_table_selector = f"{clicked_panel_selector} > div.c-table"
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, specific_c_table_selector))
        )

        specific_tbody_selector_after_click = f"{specific_c_table_selector} > table > tbody#tab"
        WebDriverWait(driver, 30).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, specific_tbody_selector_after_click))
        )
        time.sleep(1)  # 명시적 대기 후 짧은 추가 대기

        page_num = 1
        while True:
            print(f"페이지 {page_num} 수집 중...")
            product_rows_selector = f"{specific_tbody_selector_after_click} > tr"

            try:
                current_product_rows = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, product_rows_selector))
                )
                if not current_product_rows or \
                   (len(current_product_rows) == 1 and "데이터가 없습니다" in current_product_rows[0].text.strip()):
                    # print("현재 페이지에 상품 데이터가 없습니다.") # 상세 로그 제거
                    break
            except TimeoutException:
                print(f"페이지 {page_num}: 상품 목록을 찾을 수 없음 (Timeout)")
                break
            # print(f"{len(current_product_rows)}개의 상품을 찾았습니다.") # 상세 로그 제거

            for row_idx, row_element in enumerate(current_product_rows):
                try:
                    cells = row_element.find_elements(By.TAG_NAME, "td")
                    if not cells or len(cells) < 5:
                        # if cells and "데이터가 없습니다" in cells[0].text.strip(): # 상세 로그 제거
                        # print("데이터가 없는 행입니다.")
                        # else: # 상세 로그 제거
                        # print(f"Skipping row {row_idx + 1} due to insufficient cells or unexpected structure.")
                        continue

                    product_name = cells[0].text.strip()
                    sales_period = cells[1].text.strip()

                    tbody_base_xpath = ("//div[@id='tab-panel3-3']"
                                        + "/div[contains(@class, 'c-table')]"
                                        + "/table/tbody[@id='tab']")
                    current_row_xpath_for_links = f"({tbody_base_xpath}/tr)[{row_idx + 1}]"

                    summary_link_xpath = f"{current_row_xpath_for_links}/td[3]/a"
                    terms_link_xpath = f"{current_row_xpath_for_links}/td[4]/a"
                    biz_method_link_xpath = f"{current_row_xpath_for_links}/td[5]/a"

                    summary_pdf_url, terms_pdf_url, biz_method_pdf_url = "N/A", "N/A", "N/A"

                    # 링크 추출 로직
                    summary_pdf_url, terms_pdf_url, biz_method_pdf_url = "N/A", "N/A", "N/A"

                    def get_link(cell_index, link_xpath):
                        link = "N/A"
                        if cells[cell_index].find_elements(By.TAG_NAME, "a"):
                            if pdf_extractor:
                                try:
                                    link = pdf_extractor.extract_pdf_link(None, link_xpath)  # target_url은 현재 사용되지 않으므로 None
                                    link = link or "N/A"
                                except Exception as e:
                                    link = f"N/A (추출 오류: {e})"
                            else:  # PdfLinkExtractor 없는 경우, 단순 href 추출
                                try:
                                    link = cells[cell_index].find_element(By.TAG_NAME, "a").get_attribute('href') or "N/A"
                                except NoSuchElementException:
                                    link = "N/A (링크 없음)"
                                except Exception as e:
                                    link = f"N/A (오류: {e})"
                        # 상대 경로를 절대 경로로 변환
                        if link and link.startswith("/"):
                            link = "https://www.fubonhyundai.com" + link
                        return link

                    summary_pdf_url = get_link(2, summary_link_xpath)
                    terms_pdf_url = get_link(3, terms_link_xpath)
                    biz_method_pdf_url = get_link(4, biz_method_link_xpath)

                    product_data = {
                        "상품명": product_name, "판매기간": sales_period,
                        "상품요약서_링크": summary_pdf_url, "약관_링크": terms_pdf_url,
                        "사업방법서_링크": biz_method_pdf_url
                    }
                    all_products_data.append(product_data)
                except Exception as e_row:
                    print(f"  페이지 {page_num}, 행 {row_idx + 1} 처리 중 오류: {e_row}")

            next_page_button_selector = "nav#pagenation > a.paging__anchor--next"
            next_page_buttons = driver.find_elements(By.CSS_SELECTOR, next_page_button_selector)

            if not next_page_buttons:
                break
            try:
                next_page_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, next_page_button_selector))
                )
                stale_check_element = current_product_rows[0] if current_product_rows else None
                driver.execute_script("arguments[0].click();", next_page_button)
                if stale_check_element:
                    WebDriverWait(driver, 10).until(EC.staleness_of(stale_check_element))
                else:
                    time.sleep(0.5)
                time.sleep(0.5)
                page_num += 1
            except TimeoutException:
                break
            except ElementClickInterceptedException:
                print("다음 페이지 버튼 클릭 방해됨.")
                break
            except Exception as e_page:
                print(f"페이지 이동 중 오류: {e_page}")
                break
    except TimeoutException as e_timeout:
        print(f"페이지 초기 로드/탭 전환 시간 초과: {e_timeout}")
    except Exception as e_script:
        print(f"스크립트 실행 중 주요 오류: {e_script}")
    finally:
        if driver:
            driver.quit()
    return all_products_data


def is_valid_fubon_link(link_str):
    if not link_str or not isinstance(link_str, str) or not link_str.strip():
        return False

    invalid_markers = ["N/A", "(추출 오류)", "(<a> 태그 없음)", "(링크 없음)", "(링크/버튼 없음)", "(href 없음)"]
    for marker in invalid_markers:
        if marker in link_str:
            return False

    if link_str.strip().lower().startswith("javascript:"):
        return False

    is_http_link = link_str.startswith("http")

    is_local_pdf_file = False
    # HTTP 링크가 아닌 경우, 로컬 파일 경로인지 그리고 PDF 파일인지 확인
    if not is_http_link:
        try:
            # PdfLinkExtractor가 반환하는 경로가 절대 경로이거나 DOWNLOAD_DIR 기준 상대 경로일 수 있음
            # 1. link_str 자체가 절대 경로인 경우
            path_to_check = link_str
            if not os.path.isabs(path_to_check):
                # 2. DOWNLOAD_DIR 기준 상대 경로인 경우 (DOWNLOAD_DIR 변수 사용)
                path_to_check = os.path.join(DOWNLOAD_DIR, link_str)

            if os.path.exists(path_to_check) and path_to_check.lower().endswith(".pdf"):
                is_local_pdf_file = True
        except Exception:
            pass
    # HTTP 링크이지만 .pdf로 끝나지 않는 경우 (PDF만 대상으로 할 경우)
    elif is_http_link and not link_str.lower().endswith(".pdf"):
        # 푸본현대 사이트가 PDF 외 다른 형식의 중요 문서를 링크할 수 있다면 이 조건을 제거하거나 수정해야 합니다.
        # 현재는 PDF만 유효하다고 가정합니다.
        return False

    return is_http_link or is_local_pdf_file


if __name__ == "__main__":
    scraped_data = get_product_info()

    if scraped_data:
        if DatabaseManager:
            print("DB 저장 진행중...")
            structured_rows_to_save = []
            scraped_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            company_name = "현대라이프생명보험"

            for prod_info in scraped_data:
                product_name_val = prod_info.get("상품명")
                sales_period_val = prod_info.get("판매기간")
                product_code_val = None

                doc_map = {
                    "상품요약서": prod_info.get("상품요약서_링크"),
                    "약관": prod_info.get("약관_링크"),
                    "사업방법서": prod_info.get("사업방법서_링크")
                }

                has_valid_link_for_this_product = False
                current_product_docs = []
                for doc_type, link_url in doc_map.items():
                    # is_valid_fubon_link 호출 전에 이미 절대 경로로 변환되었으므로, 여기서는 추가 변환 불필요
                    if is_valid_fubon_link(link_url):
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
