# 흥국화재 / db 확인
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
# from bs4 import BeautifulSoup # Selenium으로 대체 예정
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

HEUNGKUK_DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads", "heungkukfire")
if not os.path.exists(HEUNGKUK_DOWNLOAD_DIR):
    os.makedirs(HEUNGKUK_DOWNLOAD_DIR)


def get_product_info_from_page_selenium(driver, pdf_extractor):
    # """현재 페이지의 상품 정보를 Selenium과 PdfLinkExtractor를 사용하여 추출""" # 주석 간소화
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
    # 예시: //div[@class='tbl_chk_tb']/table/tbody
    base_row_xpath_prefix = "//div[contains(@class, 'tbl_chk_tb')]/table/tbody"  # PdfLinkExtractor 사용을 위해 주석 해제

    for idx, row_element in enumerate(rows):
        try:
            cols = row_element.find_elements(By.TAG_NAME, "td")
            if len(cols) < 5:
                # print(f"  행 {idx + 1}: 셀 개수 부족 ({len(cols)}개). 건너뜁니다.") # 상세 로그 제거
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

            # PDF 링크 추출 기능 복구
            if pdf_extractor:
                # 약관
                try:
                    terms_link_val = pdf_extractor.get_pdf_url_via_href(terms_link_xpath)
                    if not terms_link_val or not (terms_link_val.lower().endswith('.pdf') or 'javascript:' in terms_link_val):
                        terms_link_val = pdf_extractor.get_pdf_url_via_network_interception(terms_link_xpath)
                except Exception:
                    pass
                terms_link_val = terms_link_val or "N/A (추출 실패)"  # 실패 시 명시
                if terms_link_val == "N/A (추출 실패)" and len(link_elements_in_cell) > 0:  # 순서 기반 fallback
                    first_link_xpath = f"{current_row_xpath}/td[5]/a[1]"
                    try:
                        terms_link_val = pdf_extractor.get_pdf_url_via_href(first_link_xpath)
                        if not terms_link_val or not (terms_link_val.lower().endswith('.pdf') or 'javascript:' in terms_link_val):
                            terms_link_val = pdf_extractor.get_pdf_url_via_network_interception(first_link_xpath)
                    except Exception:
                        pass
                terms_link_val = terms_link_val or "N/A"

                # 사업방법서
                try:
                    biz_method_link_val = pdf_extractor.get_pdf_url_via_href(biz_method_link_xpath)
                    if not biz_method_link_val or not (biz_method_link_val.lower().endswith('.pdf') or 'javascript:' in biz_method_link_val):
                        biz_method_link_val = pdf_extractor.get_pdf_url_via_network_interception(biz_method_link_xpath)
                except Exception:
                    pass
                biz_method_link_val = biz_method_link_val or "N/A (추출 실패)"
                if biz_method_link_val == "N/A (추출 실패)" and len(link_elements_in_cell) > 1:
                    second_link_xpath = f"{current_row_xpath}/td[5]/a[2]"
                    try:
                        biz_method_link_val = pdf_extractor.get_pdf_url_via_href(second_link_xpath)
                        if not biz_method_link_val or not (biz_method_link_val.lower().endswith('.pdf') or 'javascript:' in biz_method_link_val):
                            biz_method_link_val = pdf_extractor.get_pdf_url_via_network_interception(second_link_xpath)
                    except Exception:
                        pass
                biz_method_link_val = biz_method_link_val or "N/A"

                # 상품요약서
                try:
                    summary_link_val = pdf_extractor.get_pdf_url_via_href(summary_link_xpath)
                    if not summary_link_val or not (summary_link_val.lower().endswith('.pdf') or 'javascript:' in summary_link_val):
                        summary_link_val = pdf_extractor.get_pdf_url_via_network_interception(summary_link_xpath)
                except Exception:
                    pass
                summary_link_val = summary_link_val or "N/A (추출 실패)"
                if summary_link_val == "N/A (추출 실패)" and len(link_elements_in_cell) > 2:
                    third_link_xpath = f"{current_row_xpath}/td[5]/a[3]"
                    try:
                        summary_link_val = pdf_extractor.get_pdf_url_via_href(third_link_xpath)
                        if not summary_link_val or not (summary_link_val.lower().endswith('.pdf') or 'javascript:' in summary_link_val):
                            summary_link_val = pdf_extractor.get_pdf_url_via_network_interception(third_link_xpath)
                    except Exception:
                        pass
                summary_link_val = summary_link_val or "N/A"
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
            # print(f"  추출된 상품: {product_name}, 판매일: {sale_date}, 약관: {terms_link_val}, 사업방법서: {biz_method_link_val}, 요약서: {summary_link_val}") # 상세 로그 제거
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
            # print("Could not find active page element for page number.") # 상세 로그 제거
            return -1

    active_page_text = active_page_element.text.strip()
    if not active_page_text.isdigit():
        try:
            span_in_active = active_page_element.find_element(By.TAG_NAME, "span")
            active_page_text = span_in_active.text.strip()
        except NoSuchElementException:
            # html_snippet = active_page_element.get_attribute('outerHTML') # 상세 로그 제거
            # print(f"Active page text '{active_page_text}' is not a digit and no span found. HTML: {html_snippet}") # 상세 로그 제거
            return -1

    if not active_page_text.isdigit():
        # print(f"Could not determine current page number from text: '{active_page_text}'.") # 상세 로그 제거
        return -1
    return int(active_page_text)


def click_tab_and_scrape(driver, pdf_extractor, tab_name, tab_selector, product_type_selector_list, all_products_list):
    # """특정 탭(판매상품/판매중지)을 클릭하고, 그 안의 상품군들을 스크래핑하는 함수""" # 주석 간소화
    print(f"{tab_name} 정보 수집 중...")
    try:
        tab_element = WebDriverWait(driver, 10).until(EC.element_to_be_clickable(tab_selector))
        # print(f"'{tab_name}' 탭 클릭 시도...") # 상세 로그 제거
        driver.execute_script("arguments[0].click();", tab_element)
        time.sleep(2)
        # print(f"'{tab_name}' 탭 클릭 완료.") # 상세 로그 제거
    except TimeoutException:
        print(f"'{tab_name}' 탭 ({tab_selector})을 찾거나 클릭할 수 없습니다.")
        return

    for pt_name, pt_selector in product_type_selector_list:
        print(f"  상품군 '{pt_name}' 처리 중...")
        try:
            if pt_selector:
                pt_element = WebDriverWait(driver, 10).until(EC.element_to_be_clickable(pt_selector))
                # print(f"    상품군 '{pt_name}' ({pt_selector}) 클릭 시도...") # 상세 로그 제거
                driver.execute_script("arguments[0].click();", pt_element)
                time.sleep(2)
                # print(f"    상품군 '{pt_name}' 클릭 완료.") # 상세 로그 제거
            # else: # 현재 선택된 상태 로그 불필요
                # print(f"    상품군 '{pt_name}'은(는) 현재 선택된 상태로 간주하고 진행합니다.")

            page_count = 0
            previous_page_num = 0
            while True:
                page_count += 1
                # print(f"    페이지 반복 {page_count} ({tab_name} - {pt_name})...") # 상세 로그 제거
                try:
                    pagination_area_check = driver.find_element(By.CSS_SELECTOR, "div.paginate")
                    current_page_num = get_current_page_number(driver, pagination_area_check)
                except NoSuchElementException:
                    current_page_num = 1 if page_count == 1 else previous_page_num
                    if page_count > 1 and previous_page_num == current_page_num :
                        # print("    페이지네이션 영역 없음. 마지막 페이지로 간주.") # 상세 로그 제거
                        break
                if current_page_num == -1:
                    break
                # print(f"    현재 페이지 번호: {current_page_num}") # 상세 로그 제거
                if previous_page_num == current_page_num and page_count > 1:
                    # print(f"    페이지 번호 변경 없음 ({current_page_num}). 종료.") # 상세 로그 제거
                    break

                if previous_page_num != current_page_num or page_count == 1:
                    print(f"    '{pt_name}' 상품군 페이지 {current_page_num} 스크래핑 중...")
                    page_products = get_product_info_from_page_selenium(driver, pdf_extractor)
                    if page_products:
                        for prod in page_products:
                            prod['product_type_tab'] = tab_name
                            prod['product_type_group'] = pt_name
                        all_products_list.extend(page_products)
                    # else: # 상품 없는 경우 로그 불필요
                        # print(f"    페이지 {current_page_num}에서 상품을 찾지 못함.")
                previous_page_num = current_page_num
                try:
                    pagination_area_nav = driver.find_element(By.CSS_SELECTOR, "div.paginate")
                    next_page_button = pagination_area_nav.find_element(By.CSS_SELECTOR, "a.go_next")
                    if next_page_button.is_displayed() and next_page_button.is_enabled():
                        # print("    다음 페이지 버튼(a.go_next) 클릭...") # 상세 로그 제거
                        driver.execute_script("arguments[0].click();", next_page_button)
                        time.sleep(3)
                        WebDriverWait(driver, 10).until(EC.staleness_of(pagination_area_nav))
                    else:
                        break
                except (NoSuchElementException, TimeoutException):
                    # print("    다음 페이지 버튼을 찾을 수 없거나 페이지 변경 없음. 현재 상품군 종료.") # 상세 로그 제거
                    break
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
    print("흥국화재 스크래핑 시작...")  # 전체 시작 로그
    service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    prefs = {
        "download.default_directory": HEUNGKUK_DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True
    }
    options.add_experimental_option("prefs", prefs)
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(30)  # 페이지 로드 타임아웃 설정

    pdf_extractor = None
    if PdfLinkExtractor:
        pdf_extractor = PdfLinkExtractor(driver, HEUNGKUK_DOWNLOAD_DIR)

    url = "https://www.heungkukfire.co.kr/FRW/announce/insGoodsGongsiSale.do"
    all_products_data = []

    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "ul#id_modeTab")))

        mode_tab_elements = driver.find_elements(By.CSS_SELECTOR, "ul#id_modeTab > li > a")
        if not mode_tab_elements:
            print("상품 상태 탭(ul#id_modeTab)을 찾을 수 없습니다.")
            return all_products_data  # 빈 리스트 반환

        # 판매상품의 상품군 처리
        # print("--- 판매상품의 상품군 정보 수집 ---") # click_tab_and_scrape 내부 로그로 대체
        ins_type_tab_links_selectors = []
        try:
            ins_type_elements = driver.find_elements(By.CSS_SELECTOR, "ul#id_insTypeTab > li > a")
            for i, el in enumerate(ins_type_elements):
                el_text = el.text.strip() if el.text.strip() else f"상품군{i + 1}"
                ins_type_tab_links_selectors.append((el_text, (By.XPATH, f"(//ul[@id='id_insTypeTab']/li/a)[{i + 1}]")))
            if not ins_type_tab_links_selectors:
                ins_type_tab_links_selectors.append(("기본 상품군", None))
        except Exception as e:
            print(f"id_insTypeTab 상품군 탭 분석 중 오류: {e}. 현재 상태로 진행합니다.")
            ins_type_tab_links_selectors.append(("기본 상품군", None))

        selling_tab_selector = (By.CSS_SELECTOR, "ul#id_modeTab > li:nth-child(1) > a")
        click_tab_and_scrape(driver, pdf_extractor, "판매상품", selling_tab_selector,
                             ins_type_tab_links_selectors, all_products_data)

        # 판매중지 상품 처리
        discontinued_tab_selector = (By.CSS_SELECTOR, "ul#id_modeTab > li:nth-child(2) > a")
        click_tab_and_scrape(driver, pdf_extractor, "판매중지상품", discontinued_tab_selector,
                             ins_type_tab_links_selectors, all_products_data)

    except Exception as e:
        print(f"메인 스크래핑 과정 중 오류 발생: {e}")
    finally:
        if driver:
            driver.quit()
        print("흥국화재 스크래핑 완료.")  # 최종 완료 로그
    return all_products_data


def is_valid_heungkuk_link(link_str):  # 새 링크 유효성 검사 함수
    if not link_str or not isinstance(link_str, str):
        return False
    invalid_markers = ["N/A", "(추출 실패)", "(링크 요소 없음)", "(Extractor 비활성)"]
    if any(marker in link_str for marker in invalid_markers):
        return False
    if link_str.strip().lower().startswith("javascript:"):
        return False
    # 흥국화재는 상대 경로를 많이 사용하므로 http 시작 조건은 제거하고, / 시작을 허용
    return link_str.startswith("http") or link_str.startswith("/")


if __name__ == "__main__":
    collected_data = main()

    if collected_data:
        if DatabaseManager:
            print("DB 저장 진행중...")
            structured_rows_to_save = []
            scraped_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            company_name = "흥국화재"

            for item in collected_data:
                product_name_val = item.get("product_name")  # 키 이름 확인 필요
                sales_period_val = item.get("sale_date")   # 키 이름 확인 필요
                product_code_val = None

                # product_type_tab, product_type_group은 DB 스키마에 없으므로 저장 안함

                doc_map = {
                    "상품요약서": item.get("summary_link"),
                    "약관": item.get("terms_link"),
                    "사업방법서": item.get("business_method_link")
                }

                has_valid_link_for_this_product = False
                current_product_docs = []
                for doc_type, link_url in doc_map.items():
                    if is_valid_heungkuk_link(link_url):
                        # 흥국화재는 상대경로를 사용할 수 있으므로 절대경로로 변환
                        if link_url.startswith("/"):
                            link_url = "https://www.heungkukfire.co.kr" + link_url

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
            print(f"총 스크래핑된 상품 항목 수: {len(collected_data)}개")
        else:
            print("DatabaseManager 사용 불가. DB 저장 기능을 건너뜁니다.")
    else:
        print("스크래핑된 상품 데이터가 없습니다.")
