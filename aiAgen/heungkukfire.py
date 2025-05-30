# 흥국화재
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
# from bs4 import BeautifulSoup # Selenium으로 대체 예정
import time
import json
# from urllib.parse import urljoin # Selenium으로 대체 시 불필요할 수 있음
import os
import sys

# 프로젝트 루트를 sys.path에 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from neoali.pdf_link_scraper import PdfLinkExtractor
except ImportError as e:
    PdfLinkExtractor = None
    print(f"경고: PdfLinkExtractor를 임포트할 수 없습니다 ({e}). PDF 링크 추출 기능이 비활성화됩니다.")

# 다운로드 폴더 설정
HEUNGKUK_DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads", "heungkukfire")
if not os.path.exists(HEUNGKUK_DOWNLOAD_DIR):
    os.makedirs(HEUNGKUK_DOWNLOAD_DIR)

# db


def get_product_info_from_page_selenium(driver, pdf_extractor):
    """현재 페이지의 상품 정보를 Selenium과 PdfLinkExtractor를 사용하여 추출"""
    products = []
    # 상품 테이블의 각 행(tr)을 가져오는 선택자 (tbody 내의 tr들, 헤더 제외 가정)
    # 이 선택자는 실제 웹사이트 구조에 맞게 조정 필요
    # 예시: "div.tbl_chk_tb table tbody tr" (헤더가 있다면 추가 처리 필요)
    # 현재 코드는 div.tbl_chk_tb > table > tbody > tr 또는 div.tbl_chk_tb > table > tr (헤더 제외)를 가정

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
            if len(cols) < 5:  # 필요한 최소 셀 개수 확인
                print(f"  행 {idx + 1}: 셀 개수 부족 ({len(cols)}개). 건너뜁니다.")
                continue

            product_name = cols[2].text.strip()
            sale_date = cols[3].text.strip()

            # 링크 추출을 위한 XPath (현재 행 기준)
            # XPath는 1-based index, idx는 0-based
            current_row_xpath = f"({base_row_xpath_prefix}/tr)[{idx + 1}]"  # PdfLinkExtractor 사용을 위해 주석 해제

            # 링크는 보통 cols[4]에 있음
            # PdfLinkExtractor는 각 링크 요소의 XPath를 필요로 함
            # 약관, 사업방법서, 상품요약서 순서나 텍스트로 구분해야 함

            # PdfLinkExtractor 사용을 위해 주석 해제
            terms_link_xpath = f"{current_row_xpath}/td[5]/descendant::a[contains(text(),'약관') or contains(text(),'상품약관')][1]"
            # PdfLinkExtractor 사용을 위해 주석 해제
            biz_method_link_xpath = f"{current_row_xpath}/td[5]/descendant::a[contains(text(),'사업방법서')][1]"
            # PdfLinkExtractor 사용을 위해 주석 해제
            summary_link_xpath = f"{current_row_xpath}/td[5]/descendant::a[contains(text(),'상품요약서')][1]"

            # 대체 XPath (순서 기반, 만약 텍스트로 못찾을 경우)
            # 이 부분은 실제 HTML 구조를 보고 더 정확하게 만들어야 함
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
            print(
                f"  추출된 상품: {product_name}, 판매일: {sale_date}, 약관: {terms_link_val}, 사업방법서: {biz_method_link_val}, 요약서: {summary_link_val}")
        except Exception as e_row:
            print(f"  행 {idx + 1} 처리 중 오류: {e_row}")
            continue

    return products


def get_current_page_number(driver, pagination_area):
    # (기존 함수 내용 유지 - 필요시 수정)
    active_page_element = None
    try:
        active_page_element = pagination_area.find_element(By.CSS_SELECTOR, "a.on")
    except NoSuchElementException:
        try:
            active_page_element = pagination_area.find_element(By.CSS_SELECTOR, "a[title='현재페이지']")
        except NoSuchElementException:
            print("Could not find active page element for page number.")
            return -1  # 페이지 번호 확인 불가

    active_page_text = active_page_element.text.strip()
    if not active_page_text.isdigit():
        try:
            span_in_active = active_page_element.find_element(By.TAG_NAME, "span")
            active_page_text = span_in_active.text.strip()
        except NoSuchElementException:
            html_snippet = active_page_element.get_attribute('outerHTML')
            print(f"Active page text '{active_page_text}' is not a digit and no span found. HTML: {html_snippet}")
            return -1

    if not active_page_text.isdigit():
        print(f"Could not determine current page number from text: '{active_page_text}'.")
        return -1
    return int(active_page_text)


def click_tab_and_scrape(driver, pdf_extractor, tab_name, tab_selector, product_type_selector_list, all_products_list):
    """특정 탭(판매상품/판매중지)을 클릭하고, 그 안의 상품군들을 스크래핑하는 함수"""
    print(f"\n--- {tab_name} 정보 수집 시작 ---")
    try:
        tab_element = WebDriverWait(driver, 10).until(EC.element_to_be_clickable(tab_selector))
        print(f"'{tab_name}' 탭 클릭 시도...")
        driver.execute_script("arguments[0].click();", tab_element)
        time.sleep(2)  # 탭 내용 로드 대기
        print(f"'{tab_name}' 탭 클릭 완료.")
    except TimeoutException:
        print(f"'{tab_name}' 탭 ({tab_selector})을 찾거나 클릭할 수 없습니다.")
        return

    # 상품군 목록 가져오기 (product_type_selector_list는 [(상품군이름, 상품군선택자), ...] 형태의 리스트)
    for pt_name, pt_selector in product_type_selector_list:
        print(f"\n  상품군 '{pt_name}' 처리 시작...")
        try:
            # 상품군 클릭 (만약 pt_selector가 None이면 현재 상태에서 바로 진행)
            if pt_selector:
                pt_element = WebDriverWait(driver, 10).until(EC.element_to_be_clickable(pt_selector))
                print(f"    상품군 '{pt_name}' ({pt_selector}) 클릭 시도...")
                driver.execute_script("arguments[0].click();", pt_element)
                time.sleep(2)  # 상품군 목록 로드 대기
                print(f"    상품군 '{pt_name}' 클릭 완료.")
            else:
                print(f"    상품군 '{pt_name}'은(는) 현재 선택된 상태로 간주하고 진행합니다.")

            # 현재 상품군의 상품 목록 페이지네이션 처리
            page_count = 0
            previous_page_num = 0
            while True:
                page_count += 1
                print(f"    페이지 반복 {page_count} ({tab_name} - {pt_name})...")
                try:
                    pagination_area_check = driver.find_element(By.CSS_SELECTOR, "div.paginate")
                    current_page_num = get_current_page_number(driver, pagination_area_check)
                except NoSuchElementException:
                    current_page_num = 1 if page_count == 1 else previous_page_num  # 페이지네이션 없으면 1페이지 또는 이전 페이지 유지
                    if page_count > 1 and previous_page_num == current_page_num :  # 더 이상 페이지가 없다고 판단
                        print("    페이지네이션 영역 없음. 마지막 페이지로 간주.")
                        break

                if current_page_num == -1:
                    break
                print(f"    현재 페이지 번호: {current_page_num}")
                if previous_page_num == current_page_num and page_count > 1:
                    print(f"    페이지 번호 변경 없음 ({current_page_num}). 종료.")
                    break

                if previous_page_num != current_page_num or page_count == 1:
                    print(f"    페이지 {current_page_num} 스크래핑 중...")
                    page_products = get_product_info_from_page_selenium(driver, pdf_extractor)
                    if page_products:
                        for prod in page_products:  # 상품군 정보 추가
                            prod['product_type_tab'] = tab_name
                            prod['product_type_group'] = pt_name
                        all_products_list.extend(page_products)
                    else:
                        print(f"    페이지 {current_page_num}에서 상품을 찾지 못함.")

                previous_page_num = current_page_num

                try:  # 다음 페이지 이동
                    pagination_area_nav = driver.find_element(By.CSS_SELECTOR, "div.paginate")
                    next_page_button = pagination_area_nav.find_element(By.CSS_SELECTOR, "a.go_next")
                    if next_page_button.is_displayed() and next_page_button.is_enabled():
                        print("    다음 페이지 버튼(a.go_next) 클릭...")
                        driver.execute_script("arguments[0].click();", next_page_button)
                        time.sleep(3)  # 페이지 로드 대기
                        WebDriverWait(driver, 10).until(EC.staleness_of(pagination_area_nav))  # 페이지 변경 확인
                    else:
                        break  # 다음 버튼 없으면 종료
                except (NoSuchElementException, TimeoutException):  # 다음 버튼 없거나 stale
                    print("    다음 페이지 버튼을 찾을 수 없거나 페이지 변경 없음. 현재 상품군 종료.")
                    break
                except Exception as e_nav:
                    print(f"    페이지 이동 중 오류: {e_nav}. 현재 상품군 종료.")
                    break
        except TimeoutException:
            print(f"    상품군 '{pt_name}' ({pt_selector})을 찾거나 클릭할 수 없습니다.")
            continue  # 다음 상품군으로
        except Exception as e_pt:
            print(f"    상품군 '{pt_name}' 처리 중 오류: {e_pt}")
            continue


def main():
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
    driver.set_page_load_timeout(30)

    pdf_extractor = None
    if PdfLinkExtractor:
        pdf_extractor = PdfLinkExtractor(driver, HEUNGKUK_DOWNLOAD_DIR)

    url = "https://www.heungkukfire.co.kr/FRW/announce/insGoodsGongsiSale.do"
    all_products_data = []

    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "ul#id_modeTab")))  # 탭 로드 대기

        # 판매상품 상품군 선택자 (ul#id_modeTab li a) - 실제 구조에 맞게 조정 필요
        # 예시: 첫번째 li의 a는 (By.CSS_SELECTOR, "ul#id_modeTab > li:nth-child(1) > a")
        # 모든 상품군을 가져오려면 ul#id_modeTab > li > a 를 find_elements로 가져와서 반복해야 함.
        # 여기서는 사용자가 "한 상품군 정보만 구하고 있다"고 했으므로, 첫번째 상품군만 처리하는 것으로 가정.
        # 만약 모든 상품군을 처리해야 한다면, 이 부분을 루프로 변경.
        # 사용자의 최신 요청은 모든 상품군과 판매중지 상품군을 처리하는 것이므로, 루프 필요.

        mode_tab_elements = driver.find_elements(By.CSS_SELECTOR, "ul#id_modeTab > li > a")
        if not mode_tab_elements:
            print("ul#id_modeTab (상품 상태 탭) 내의 링크를 찾을 수 없습니다.")
            return

        # 판매상품 처리 (첫 번째 탭으로 가정)
        # 실제로는 각 탭의 텍스트를 확인하여 "판매상품" 탭을 찾아야 할 수 있음
        selling_tab_selector = (By.CSS_SELECTOR, "ul#id_modeTab > li:nth-child(1) > a")  # 첫번째 탭
        # 판매상품의 상품군 선택자 (ul#id_insTypeTab li a) - 이 선택자는 판매중지 상품용일 수 있음.
        # 판매상품의 상품군은 페이지 로드 시 기본 선택된 것을 사용하거나, 별도의 선택자가 있을 수 있음.
        # 여기서는 판매상품의 경우 상품군 변경 없이 현재 상태에서 스크래핑한다고 가정.
        # 만약 판매상품도 id_insTypeTab을 사용한다면 해당 로직 추가 필요.
        # 사용자는 "상품군을 바꾸기위해서는 id_insTypeTab 안에 li 요소들 안에 a태그를 클릭해야한다"고 했으므로,
        # 판매상품과 판매중지상품 모두 이 탭을 사용할 가능성이 있음.

        # 판매상품의 상품군 처리
        print("--- 판매상품의 상품군 정보 수집 ---")
        # id_insTypeTab의 li > a 요소들을 가져옴
        ins_type_tab_links_selectors = []
        try:
            ins_type_elements = driver.find_elements(By.CSS_SELECTOR, "ul#id_insTypeTab > li > a")
            for i, el in enumerate(ins_type_elements):
                # 각 요소에 대한 고유 선택자 생성 (예: XPath)
                # 이 XPath는 요소가 DOM에서 변경되지 않는다는 가정 하에 유효
                # 더 안정적인 방법은 각 루프에서 다시 찾는 것
                el_text = el.text.strip() if el.text.strip() else f"상품군{i + 1}"
                ins_type_tab_links_selectors.append((el_text, (By.XPATH, f"(//ul[@id='id_insTypeTab']/li/a)[{i + 1}]")))
            if not ins_type_tab_links_selectors:  # id_insTypeTab이 없거나 비어있으면, 현재 상태로 한번만 실행
                ins_type_tab_links_selectors.append(("기본 상품군", None))
        except Exception as e:
            print(f"id_insTypeTab 상품군 탭 분석 중 오류: {e}. 현재 상태로 진행합니다.")
            ins_type_tab_links_selectors.append(("기본 상품군", None))

        click_tab_and_scrape(driver, pdf_extractor, "판매상품", selling_tab_selector,
                             ins_type_tab_links_selectors, all_products_data)

        # 판매중지 상품 처리 (두 번째 탭으로 가정)
        # 사용자는 "ul#id_modeTab 안에 두번째 li안에 a 태그를 클릭하면 판매중지 상품이 나올것이고"
        discontinued_tab_selector = (By.CSS_SELECTOR, "ul#id_modeTab > li:nth-child(2) > a")
        # 판매중지 상품의 상품군 선택자 (ul#id_insTypeTab li a) - 판매상품과 동일한 탭을 사용한다고 가정
        click_tab_and_scrape(driver, pdf_extractor, "판매중지상품", discontinued_tab_selector,
                             ins_type_tab_links_selectors, all_products_data)

    except Exception as e:
        print(f"메인 스크래핑 과정 중 오류 발생: {e}")
    finally:
        if driver:
            driver.quit()

    if all_products_data:
        print(f"\n최종적으로 {len(all_products_data)}개의 상품 정보를 수집했습니다.")
        # print(json.dumps(all_products_data, indent=4, ensure_ascii=False)) # 필요시 주석 해제
        for item in all_products_data:
            print(item)
    else:
        print("수집된 상품 데이터가 없습니다.")


if __name__ == "__main__":
    main()
