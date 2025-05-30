from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium import webdriver
import time
import os
import sys

# 프로젝트 루트를 sys.path에 추가하여 'neoali' 패키지를 찾을 수 있도록 함
# 현재 파일 (fubonhyundai.py) -> .../neoali/aiAgen/fubonhyundai.py
# os.path.dirname(__file__) -> .../neoali/aiAgen
# os.path.join(..., '..') -> .../neoali
# os.path.join(..., '..', '..') -> .../ (프로젝트 루트)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


# PdfLinkExtractor 클래스를 neoali 패키지 내의 pdf_link_scraper 모듈에서 절대 경로로 가져옵니다.
try:
    from neoali.pdf_link_scraper import PdfLinkExtractor
except ImportError as e:
    # 만약 위 import가 실패하면 (예: 스크립트가 다른 방식으로 실행될 때),
    # PdfLinkExtractor를 찾을 수 있는 다른 경로를 시도하거나 오류를 발생시킬 수 있습니다.
    # 여기서는 간단히 PdfLinkExtractor가 없으면 PDF 링크 추출 기능을 사용하지 않도록 처리합니다.
    PdfLinkExtractor = None
    print(f"경고: PdfLinkExtractor를 임포트할 수 없습니다 ({e}). PDF 링크 추출 기능이 비활성화됩니다.")


DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# db저장


def generate_xpath_for_element(driver, element):
    """특정 웹 요소에 대한 고유한 XPath를 생성하려고 시도합니다."""
    # 간단한 XPath 생성 (id, name, class 등 활용) - 실제로는 더 견고한 방법 필요
    # 이 함수는 매우 기본적인 예시이며, 복잡한 DOM 구조에서는 실패할 수 있습니다.
    # JavaScript를 사용하여 XPath를 얻는 것이 더 안정적일 수 있습니다.
    # 예: driver.execute_script("function getPathTo(element) { ... } return getPathTo(arguments[0]);", element)
    if element.get_attribute("id"):
        return f"//*[@id='{element.get_attribute('id')}']"
    # 여기서는 간단히 태그 이름만 반환하거나, 더 복잡한 로직을 구현해야 합니다.
    # 실제 사용 시에는 이 부분을 견고하게 만들어야 합니다.
    # 지금은 플레이스홀더로 남겨두고, 직접 XPATH를 구성하는 방식을 사용합니다.
    print("경고: generate_xpath_for_element는 현재 매우 제한적입니다.")
    return None  # 견고한 XPath 생성 로직 필요


def get_product_info():
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
    # 네트워크 요청 가로채기를 위해 로깅 활성화 (PdfLinkExtractor의 방법3에 필요할 수 있음)
    chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    driver = None
    pdf_extractor = None
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        if PdfLinkExtractor:
            # PdfLinkExtractor 인스턴스 생성 시 DOWNLOAD_DIR 전달
            pdf_extractor = PdfLinkExtractor(driver, DOWNLOAD_DIR)
        else:
            print("PdfLinkExtractor가 없으므로 PDF 링크 추출을 시도하지 않습니다.")

    except Exception as e:
        print(f"웹 드라이버 설정 중 오류 발생: {e}")
        if driver:
            driver.quit()
        return

    base_url = "https://www.fubonhyundai.com/#CUSI150102010101"
    driver.get(base_url)
    driver.implicitly_wait(5)

    all_products_data = []

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
        time.sleep(2)

        page_num = 1
        while True:
            print(f"\n--- {page_num} 페이지 데이터 수집 중 ---")
            # 상품 행을 이전 방식인 CSS 선택자로 찾도록 수정
            product_rows_selector = f"{specific_tbody_selector_after_click} > tr"

            try:
                # 현재 페이지의 모든 tr 요소를 가져옵니다.
                current_product_rows = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, product_rows_selector))
                )
                if not current_product_rows or \
                   (len(current_product_rows) == 1 and "데이터가 없습니다" in current_product_rows[0].text.strip()):
                    print("현재 페이지에 상품 데이터가 없습니다.")
                    break
            except TimeoutException:
                print("상품 목록을 찾을 수 없습니다. (Timeout)")  # 이 부분에서 오류 발생
                break

            print(f"{len(current_product_rows)}개의 상품을 찾았습니다.")

            for row_idx, row_element in enumerate(current_product_rows):
                # PdfLinkExtractor를 위한 XPath 생성은 잠시 보류 (CSS 선택자로 행을 찾았으므로)
                # current_row_xpath = f"({product_rows_xpath_prefix})[{row_idx + 1}]" # 이 XPATH는 더 이상 정확하지 않음

                try:
                    cells = row_element.find_elements(By.TAG_NAME, "td")
                    if not cells or len(cells) < 5:
                        if cells and "데이터가 없습니다" in cells[0].text.strip():
                            print("데이터가 없는 행입니다.")
                        else:
                            print(f"Skipping row {row_idx + 1} due to insufficient cells or unexpected structure.")
                        continue

                    product_name = cells[0].text.strip()
                    sales_period = cells[1].text.strip()

                    # PdfLinkExtractor에 전달할 XPath 구성
                    # specific_tbody_selector_after_click 를 기반으로 tbody의 XPath를 만듭니다.
                    # specific_tbody_selector_after_click = "div#tab-panel3-3 > div.c-table > table > tbody#tab"
                    # 이를 XPath로 변환하면: //div[@id='tab-panel3-3']/div[contains(@class, 'c-table')]/table/tbody[@id='tab']
                    tbody_base_xpath = ("//div[@id='tab-panel3-3']"
                                        + "/div[contains(@class, 'c-table')]"
                                        + "/table/tbody[@id='tab']")
                    current_row_xpath_for_links = f"({tbody_base_xpath}/tr)[{row_idx + 1}]"

                    summary_link_xpath_method2 = f"{current_row_xpath_for_links}/td[3]/a"
                    terms_link_xpath_method2 = f"{current_row_xpath_for_links}/td[4]/a"
                    biz_method_link_xpath_method2 = f"{current_row_xpath_for_links}/td[5]/a"

                    summary_trigger_xpath_method3 = summary_link_xpath_method2
                    terms_trigger_xpath_method3 = terms_link_xpath_method2
                    biz_method_trigger_xpath_method3 = biz_method_link_xpath_method2

                    summary_pdf_url, terms_pdf_url, biz_method_pdf_url = "N/A", "N/A", "N/A"

                    if pdf_extractor:
                        print(f"  상품명 '{product_name}': PDF 링크 추출 시도...")

                        # 상품요약서 (cells[2])
                        summary_links = cells[2].find_elements(By.TAG_NAME, "a")
                        if summary_links:
                            print(f"    상품요약서 링크 추출 시도 (HREF XPATH: {summary_link_xpath_method2})")
                            try:
                                summary_pdf_url = pdf_extractor.get_pdf_url_via_href(summary_link_xpath_method2)
                                if not summary_pdf_url or not summary_pdf_url.lower().endswith('.pdf'):
                                    print(f"    상품요약서 HREF 실패/PDF아님. 네트워크 시도 "
                                          f"(XPATH: {summary_trigger_xpath_method3})")
                                    summary_pdf_url = pdf_extractor.get_pdf_url_via_network_interception(
                                        summary_trigger_xpath_method3)
                                summary_pdf_url = summary_pdf_url or "N/A"
                            except TimeoutException:
                                print(
                                    f"    상품요약서 링크 요소 찾기 시간 초과 (XPATH: {summary_link_xpath_method2} 또는 {summary_trigger_xpath_method3})")
                                summary_pdf_url = "N/A (요소 찾기 시간 초과)"
                            except Exception as e_extract:
                                print(f"    상품요약서 링크 추출 중 오류: {e_extract}")
                                summary_pdf_url = "N/A (추출 오류)"
                        else:
                            summary_pdf_url = "N/A (<a> 태그 없음)"

                        # 약관 (cells[3])
                        terms_links = cells[3].find_elements(By.TAG_NAME, "a")
                        if terms_links:
                            print(f"    약관 링크 추출 시도 (HREF XPATH: {terms_link_xpath_method2})")
                            try:
                                terms_pdf_url = pdf_extractor.get_pdf_url_via_href(terms_link_xpath_method2)
                                if not terms_pdf_url or not terms_pdf_url.lower().endswith('.pdf'):  # javascript:LinkFile() 같은 경우
                                    print(f"    약관 HREF/PDF 오류. 네트워크 시도")
                                    print(f"      Trigger XPATH: {terms_trigger_xpath_method3}")
                                    terms_pdf_url = pdf_extractor.get_pdf_url_via_network_interception(
                                        terms_trigger_xpath_method3)
                                terms_pdf_url = terms_pdf_url or "N/A"
                            except TimeoutException:
                                print(
                                    f"    약관 링크 요소 찾기 시간 초과 (XPATH: {terms_link_xpath_method2} 또는 {terms_trigger_xpath_method3})")
                                terms_pdf_url = "N/A (요소 찾기 시간 초과)"
                            except Exception as e_extract:
                                print(f"    약관 링크 추출 중 오류: {e_extract}")
                                terms_pdf_url = "N/A (추출 오류)"
                        else:
                            terms_pdf_url = "N/A (<a> 태그 없음)"

                        # 사업방법서 (cells[4])
                        biz_method_links = cells[4].find_elements(By.TAG_NAME, "a")
                        if biz_method_links:
                            print(f"    사업방법서 링크 추출 시도 (HREF XPATH: {biz_method_link_xpath_method2})")
                            try:
                                biz_method_pdf_url = pdf_extractor.get_pdf_url_via_href(biz_method_link_xpath_method2)
                                if not biz_method_pdf_url or not biz_method_pdf_url.lower().endswith('.pdf'):
                                    print(f"    사업방법서 HREF/PDF 오류. 네트워크 시도")
                                    print(f"      Trigger XPATH for 사업방법서: {biz_method_trigger_xpath_method3}")
                                    biz_method_pdf_url = pdf_extractor.get_pdf_url_via_network_interception(
                                        biz_method_trigger_xpath_method3)
                                biz_method_pdf_url = biz_method_pdf_url or "N/A"
                            except TimeoutException:
                                print(
                                    f"    사업방법서 링크 요소 찾기 시간 초과 (XPATH: {biz_method_link_xpath_method2} 또는 {biz_method_trigger_xpath_method3})")
                                biz_method_pdf_url = "N/A (요소 찾기 시간 초과)"
                            except Exception as e_extract:
                                print(f"    사업방법서 링크 추출 중 오류: {e_extract}")
                                biz_method_pdf_url = "N/A (추출 오류)"
                        else:
                            biz_method_pdf_url = "N/A (<a> 태그 없음)"
                    else:  # PdfLinkExtractor가 없는 경우
                        try:
                            summary_pdf_url = cells[2].find_element(By.TAG_NAME, "a").get_attribute('href') or "N/A"
                        except NoSuchElementException:
                            summary_pdf_url = "N/A (링크 없음)"
                        try:
                            terms_pdf_url = cells[3].find_element(By.TAG_NAME, "a").get_attribute('href') or "N/A"
                        except NoSuchElementException:
                            terms_pdf_url = "N/A (링크 없음)"
                        try:
                            biz_method_pdf_url = cells[4].find_element(By.TAG_NAME, "a").get_attribute('href') or "N/A"
                        except NoSuchElementException:
                            biz_method_pdf_url = "N/A (링크 없음)"

                    product_data = {
                        "상품명": product_name,
                        "판매기간": sales_period,
                        "상품요약서_링크": summary_pdf_url,
                        "약관_링크": terms_pdf_url,
                        "사업방법서_링크": biz_method_pdf_url
                    }
                    # 사용자가 지적한 출력문에 판매기간 추가
                    print(f"  - 상품명: {product_name}, 판매기간: {sales_period}, "
                          f"요약서: {summary_pdf_url}, 약관: {terms_pdf_url}, "
                          f"사업방법서: {biz_method_pdf_url}")
                    all_products_data.append(product_data)

                except NoSuchElementException as e_nse:
                    print(f"  상품 정보 중 일부를 찾을 수 없습니다 (행 {row_idx + 1}): {e_nse}")
                except Exception as e_general:
                    print(f"  상품 정보 추출 중 오류 (행 {row_idx + 1}): {e_general}")

            next_page_button_selector = "nav#pagenation > a.paging__anchor--next"
            next_page_buttons = driver.find_elements(By.CSS_SELECTOR, next_page_button_selector)

            if not next_page_buttons:
                print("다음 페이지 버튼을 찾을 수 없습니다. 마지막 페이지입니다.")
                break

            try:
                next_page_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, next_page_button_selector))
                )
                # 다음 페이지로 넘어가기 전에 현재 행들의 참조가 stale 해지도록 하기 위함
                stale_check_element = current_product_rows[0] if current_product_rows else None

                print("다음 페이지로 이동합니다.")
                driver.execute_script("arguments[0].click();", next_page_button)

                if stale_check_element:
                    WebDriverWait(driver, 10).until(
                        EC.staleness_of(stale_check_element)
                    )
                else:  # 만약 현재 페이지에 행이 없었다면, 새 페이지 로드를 다른 방식으로 기다려야 할 수 있음
                    time.sleep(1)  # 간단한 대기

                time.sleep(1)  # 추가 안정성
                page_num += 1
            except TimeoutException:
                print("다음 페이지 버튼 클릭 후 페이지 로드 확인 시간 초과. 마지막 페이지일 수 있습니다.")
                break
            except ElementClickInterceptedException:
                print("다음 페이지 버튼 클릭이 가로막혔습니다.")
                break
            except Exception as e:
                print(f"페이지 이동 중 오류 발생: {e}")
                break

    except TimeoutException as e_timeout:
        print(f"페이지 로드 시간 초과 또는 특정 요소를 찾을 수 없습니다: {e_timeout}")
    except Exception as e_script:
        print(f"스크립트 실행 중 오류 발생: {e_script}")
    finally:
        if driver:
            driver.quit()
        print("\n--- 전체 상품 데이터 (PDF 링크 포함) ---")
        for data in all_products_data:
            print(data)
        print(f"총 {len(all_products_data)}개의 상품 정보를 수집했습니다.")


if __name__ == "__main__":
    get_product_info()
