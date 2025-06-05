# 한화 생명 /db 확인
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException
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

HANWHA_DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads", "hanwhalife")
if not os.path.exists(HANWHA_DOWNLOAD_DIR):
    os.makedirs(HANWHA_DOWNLOAD_DIR)


def scrape_product_details(driver, pdf_extractor, category_name_text, current_product_name):
    # """상품 상세 정보 및 PDF 링크를 추출하는 헬퍼 함수. 모든 판매기간 버전을 리스트로 반환.""" # 주석 간소화
    all_versions_details = []
    detail_list_selector = "tbody#List3 tr"
    try:
        WebDriverWait(driver, 10).until(EC.visibility_of_element_located(
            (By.CSS_SELECTOR, detail_list_selector)))
        detail_rows = driver.find_elements(
            By.CSS_SELECTOR, detail_list_selector)

        # print(f"      tbody#List3 발견된 tr 개수: {len(detail_rows)}") # 상세 로그 제거

        if detail_rows:
            # print(f"        {len(detail_rows)}개의 데이터 행 처리 시작.") # 상세 로그 제거
            for data_row_idx_loop in range(len(detail_rows)):
                data_row_element = detail_rows[data_row_idx_loop]
                tds_in_data_row = data_row_element.find_elements(By.CSS_SELECTOR, "td")
                # print(f"          행 {data_row_idx_loop + 1} (인덱스 {data_row_idx_loop}): td 개수 = {len(tds_in_data_row)}") # 상세 로그 제거

                current_version_detail = {
                    '판매기간': "N/A",
                    '약관_링크': "N/A",
                    '상품요약서_링크': "N/A",
                    '사업방법서_링크': "N/A"
                }

                tbody3_base_xpath = "//tbody[@id='List3']"
                current_data_row_xpath = f"({tbody3_base_xpath}/tr)[{data_row_idx_loop + 1}]"

                if len(tds_in_data_row) > 0:
                    try:
                        current_version_detail['판매기간'] = tds_in_data_row[0].text.strip()
                    except Exception:
                        pass

                if pdf_extractor:
                    if len(tds_in_data_row) > 1 and tds_in_data_row[1].find_elements(By.CSS_SELECTOR, "a, button"):
                        summary_xpath = f"{current_data_row_xpath}/td[2]/descendant::*[self::a or self::button][1]"
                        # print(f"            상품요약서 추출 시도 (XPATH: {summary_xpath})") # 상세 로그 제거
                        summary_link_val = pdf_extractor.get_pdf_url_via_href(summary_xpath)
                        if not summary_link_val or not summary_link_val.lower().endswith('.pdf'):
                            summary_link_val = pdf_extractor.get_pdf_url_via_network_interception(summary_xpath)
                        current_version_detail['상품요약서_링크'] = summary_link_val or "N/A (추출 실패)"
                    # else: # 링크 요소 없는 경우 로그 불필요
                        # current_version_detail['상품요약서_링크'] = "N/A (링크 요소 없음)"

                    if len(tds_in_data_row) > 2 and tds_in_data_row[2].find_elements(By.CSS_SELECTOR, "a, button"):
                        biz_xpath = f"{current_data_row_xpath}/td[3]/descendant::*[self::a or self::button][1]"
                        # print(f"            사업방법서 추출 시도 (XPATH: {biz_xpath})") # 상세 로그 제거
                        biz_method_link_val = pdf_extractor.get_pdf_url_via_href(biz_xpath)
                        if not biz_method_link_val or not biz_method_link_val.lower().endswith('.pdf'):
                            biz_method_link_val = pdf_extractor.get_pdf_url_via_network_interception(biz_xpath)
                        current_version_detail['사업방법서_링크'] = biz_method_link_val or "N/A (추출 실패)"
                    # else: # 링크 요소 없는 경우 로그 불필요
                        # current_version_detail['사업방법서_링크'] = "N/A (링크 요소 없음)"

                    if len(tds_in_data_row) > 3 and tds_in_data_row[3].find_elements(By.CSS_SELECTOR, "a, button"):
                        terms_xpath = f"{current_data_row_xpath}/td[4]/descendant::*[self::a or self::button][1]"
                        # print(f"            약관 추출 시도 (XPATH: {terms_xpath})") # 상세 로그 제거
                        terms_link_val = pdf_extractor.get_pdf_url_via_href(terms_xpath)
                        if not terms_link_val or not terms_link_val.lower().endswith('.pdf'):
                            terms_link_val = pdf_extractor.get_pdf_url_via_network_interception(terms_xpath)
                        current_version_detail['약관_링크'] = terms_link_val or "N/A (추출 실패)"
                    # else: # 링크 요소 없는 경우 로그 불필요
                        # current_version_detail['약관_링크'] = "N/A (링크 요소 없음)"
                else:  # PdfLinkExtractor 없는 경우
                    if len(tds_in_data_row) > 1 and tds_in_data_row[1].find_elements(By.CSS_SELECTOR, "a, button"):
                        current_version_detail['상품요약서_링크'] = "존재함 (Extractor 비활성)"
                    if len(tds_in_data_row) > 2 and tds_in_data_row[2].find_elements(By.CSS_SELECTOR, "a, button"):
                        current_version_detail['사업방법서_링크'] = "존재함 (Extractor 비활성)"
                    if len(tds_in_data_row) > 3 and tds_in_data_row[3].find_elements(By.CSS_SELECTOR, "a, button"):
                        current_version_detail['약관_링크'] = "존재함 (Extractor 비활성)"

                all_versions_details.append(current_version_detail)
                # print(f"            추가된 버전 데이터: ...") # 상세 버전 데이터 로그 제거
        # else: # 데이터 행 없는 경우 로그 불필요
            # print("      tbody#List3에 데이터 행이 없음. 상세 정보 N/A 처리.")
    except TimeoutException:
        print(f"      '{current_product_name}' 상세 정보 로드 시간 초과.")  # 상품명 명시
    except Exception as e_detail_extract:
        print(f"      '{current_product_name}' 상세 정보 추출 중 오류: {e_detail_extract}")
    return all_versions_details


def scrape_product_list_for_category(driver, pdf_extractor, category_name_text, product_data_collected):
    """주어진 카테고리 내의 상품 목록을 스크래핑하는 함수"""
    product_list_selector = "tbody#List2 tr"
    try:
        WebDriverWait(driver, 15).until(EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, product_list_selector)))
        time.sleep(2)
    except TimeoutException:
        print(f"  '{category_name_text}' 상품명 목록(tbody#List2) 로드 시간 초과.")
        return
    except Exception as e_prod_wait:
        print(f"  '{category_name_text}' 상품명 목록(tbody#List2) 로드 중 기타 오류: {e_prod_wait}")
        return

    product_rows_in_category = driver.find_elements(By.CSS_SELECTOR, product_list_selector)
    num_products = len(product_rows_in_category)
    if num_products == 0:
        # print(f"  '{category_name_text}' 내 상품 없음.") # 상품 없는 경우 로그 불필요
        return
    # print(f"  '{category_name_text}' 내 {num_products}개 상품명 발견.") # 상세 로그 제거

    for p_idx in range(num_products):
        current_p_row = None
        current_product_name = "N/A"
        is_linkable = False

        try:
            current_product_rows_refreshed = driver.find_elements(By.CSS_SELECTOR, product_list_selector)
            if p_idx < len(current_product_rows_refreshed):
                current_p_row = current_product_rows_refreshed[p_idx]
            else:
                print(f"    상품명 인덱스 {p_idx} 찾기 실패 (목록 변경됨).")
                continue
        except Exception as e_get_p_row:
            print(f"    상품명 행 인덱스 {p_idx} 가져오기 오류: {e_get_p_row}.")
            continue

        try:
            prod_name_element = current_p_row.find_element(By.CSS_SELECTOR, "td:first-child > a")
            current_product_name = prod_name_element.text.strip()
            is_linkable = True
        except NoSuchElementException:
            try:
                current_product_name = current_p_row.find_element(By.CSS_SELECTOR, "td:first-child").text.strip()
            except Exception:
                pass

        if not current_product_name or current_product_name == "N/A":
            # print(f"    상품명 정보 비어있음 (인덱스 {p_idx}).") # 상세 로그 제거
            continue

        # print(f"    [{p_idx + 1}/{num_products}] 상품명 '{current_product_name}' 처리 중...") # 상세 로그 제거

        if not is_linkable:
            product_info_base = {
                '보험명': f"{category_name_text} - {current_product_name}",
                '판매기간': 'N/A',
                '약관_링크': 'N/A (링크 없음)',
                '상품요약서_링크': 'N/A (링크 없음)',
                '사업방법서_링크': 'N/A (링크 없음)'
            }
            product_data_collected.append(product_info_base)
            continue

        try:
            prod_click_target = current_p_row.find_element(By.CSS_SELECTOR, "td:first-child > a")
            driver.execute_script("arguments[0].scrollIntoView(true);", prod_click_target)
            time.sleep(0.3)
            driver.execute_script("arguments[0].click();", prod_click_target)
            time.sleep(1)

            details_list = scrape_product_details(driver, pdf_extractor, category_name_text, current_product_name)

            if not details_list:  # 상세 정보가 없는 경우 (scrape_product_details가 빈 리스트 반환)
                product_info = {
                    '보험명': f"{category_name_text} - {current_product_name}",
                    '판매기간': 'N/A (상세 정보 없음)',
                    '약관_링크': 'N/A', '상품요약서_링크': 'N/A', '사업방법서_링크': 'N/A'
                }
                product_data_collected.append(product_info)
            else:
                for detail_item in details_list:
                    product_info = {
                        '보험명': f"{category_name_text} - {current_product_name}",
                    }
                    product_info.update(detail_item)  # 판매기간, 링크들 포함
                    product_data_collected.append(product_info)

        except Exception as e_prod_click:
            print(f"      상품명 '{current_product_name}' 클릭 또는 상세 정보 처리 오류: {e_prod_click}.")
            product_data_collected.append({
                '보험명': f"{category_name_text} - {current_product_name}",
                '판매기간': 'N/A (클릭/상세 오류)',
                '약관_링크': 'N/A', '상품요약서_링크': 'N/A', '사업방법서_링크': 'N/A'
            })


def process_product_category(driver, pdf_extractor, base_url_or_current, category_list_selector, cat_idx, product_data_collected, is_discontinued_tab=False):
    """특정 상품 카테고리를 처리하는 함수. is_discontinued_tab 플래그 추가"""
    category_name_text = f"알 수 없는 상품구분 (인덱스 {cat_idx})"
    try:
        # 판매중지 탭에서는 base_url로 돌아가지 않도록 함
        if not is_discontinued_tab:
            driver.get(base_url_or_current)

        # 현재 페이지에서 카테고리 목록을 다시 찾음 (페이지 상태가 변경되었을 수 있으므로)
        WebDriverWait(driver, 20).until(EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, category_list_selector)))

        cat_link_text_xpath = f"(//tbody[@id='List1']/tr)[{cat_idx + 1}]/td/a"
        cat_text_only_xpath = f"(//tbody[@id='List1']/tr)[{cat_idx + 1}]/td[1]"

        try:
            cat_name_element_for_text = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, cat_link_text_xpath)))
            category_name_text = cat_name_element_for_text.text.strip()
        except TimeoutException:
            try:
                cat_name_element_for_text = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, cat_text_only_xpath)))
                category_name_text = cat_name_element_for_text.text.strip()
            except TimeoutException:
                print(f"  상품구분 인덱스 {cat_idx}의 이름 가져오기 실패. 건너뜁니다.")
                return False

        print(f"\n상품구분 '{category_name_text}' 처리 중...")
        element_to_click_xpath = cat_link_text_xpath

        try:
            element_to_click = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, element_to_click_xpath)))
            driver.execute_script("arguments[0].scrollIntoView(true);", element_to_click)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", element_to_click)
            time.sleep(2)
            scrape_product_list_for_category(driver, pdf_extractor, category_name_text, product_data_collected)
            return True
        except TimeoutException:
            print(f"  상품구분 '{category_name_text}'에 대한 클릭 가능한 링크(a태그)를 찾지 못했습니다.")
            return False  # 링크가 없으면 해당 카테고리 처리 불가
    except Exception as e_cat_setup:
        print(f"  상품구분 '{category_name_text}' (인덱스 {cat_idx}) 처리 중 오류: {e_cat_setup}")
        return False


def get_hanwhalife_product_info_selenium():
    service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    prefs = {
        "download.default_directory": HANWHA_DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True
    }
    options.add_experimental_option("prefs", prefs)
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    driver = webdriver.Chrome(service=service, options=options)
    driver.maximize_window()

    pdf_extractor = None
    if PdfLinkExtractor:
        pdf_extractor = PdfLinkExtractor(driver, HANWHA_DOWNLOAD_DIR)

    base_url = "https://www.hanwhalife.com/main/disclosure/goods/disclosurenotice/DF_GDDN000_P10000.do?MENU_ID1=DF_GDGL000"
    product_data_collected = []

    print("한화생명 스크래핑 시작...")
    try:
        print("판매상품 정보 수집 중...")
        driver.get(base_url)
        category_list_selector = "tbody#List1 tr"
        WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, category_list_selector)))
        num_categories = len(driver.find_elements(By.CSS_SELECTOR, category_list_selector))
        # print(f"총 {num_categories}개의 판매상품 구분 발견.") # 상세 로그 제거
        for cat_idx in range(num_categories):
            # print(f"판매상품 카테고리 인덱스 {cat_idx + 1}/{num_categories} 처리 시도...") # 상세 로그 제거
            process_product_category(driver, pdf_extractor, base_url,
                                     category_list_selector, cat_idx, product_data_collected, is_discontinued_tab=False)
        print("판매상품 정보 수집 완료.")

        print("판매중지 상품 정보 수집 중...")
        try:
            driver.get(base_url)
            time.sleep(1)
            sel2_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a#sel2"))
            )
            # print("a#sel2 (판매중지상품 탭) 클릭 시도...") # 상세 로그 제거
            driver.execute_script("arguments[0].click();", sel2_button)
            time.sleep(2)
            # print("a#sel2 클릭 완료.") # 상세 로그 제거
        except TimeoutException:
            print("판매중지상품 탭(a#sel2)을 찾거나 클릭할 수 없습니다.")
            raise
        try:
            discontinued_trigger_button_selector = "ul#menu2 > li:nth-child(2) > button"
            discontinued_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, discontinued_trigger_button_selector))
            )
            # print(f"판매중지 상품 목록 로드 버튼 ({discontinued_trigger_button_selector}) 클릭 시도...") # 상세 로그 제거
            driver.execute_script("arguments[0].click();", discontinued_button)
            time.sleep(3)
            # print("판매중지 상품 목록 로드 버튼 클릭 완료.") # 상세 로그 제거

            WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, category_list_selector)))
            num_discontinued_categories = len(driver.find_elements(By.CSS_SELECTOR, category_list_selector))
            # print(f"총 {num_discontinued_categories}개의 판매중지 상품 구분 발견.") # 상세 로그 제거

            for cat_idx in range(num_discontinued_categories):
                # print(f"판매중지 상품 카테고리 인덱스 {cat_idx + 1}/{num_discontinued_categories} 처리 시도...") # 상세 로그 제거
                process_product_category(driver, pdf_extractor, driver.current_url,
                                         category_list_selector, cat_idx, product_data_collected, is_discontinued_tab=True)
            print("판매중지 상품 정보 수집 완료.")
        except TimeoutException:
            print("판매중지 상품 목록 로드 버튼을 찾거나 클릭할 수 없습니다.")
        except Exception as e_discontinued_setup:
            print(f"판매중지 상품 설정 중 오류: {e_discontinued_setup}")

    except Exception as e:
        print(f"전체 스크래핑 과정 중 오류 발생: {e}")
    finally:
        if 'driver' in locals() and driver:
            driver.quit()
        print("한화생명 스크래핑 완료.")
    return product_data_collected


def is_valid_hanwha_link(link_str):
    if not link_str or not isinstance(link_str, str) or not link_str.strip():
        return False

    invalid_markers = ["N/A", "(추출 실패)", "(링크 요소 없음)", "(Extractor 비활성)", "(링크/버튼 없음)", "(href 없음)", "(추출 오류)"]  # 일반적인 마커 추가
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
            # PdfLinkExtractor가 반환하는 경로가 절대 경로이거나 HANWHA_DOWNLOAD_DIR 기준 상대 경로일 수 있음
            path_to_check = link_str
            if not os.path.isabs(path_to_check):
                # HANWHA_DOWNLOAD_DIR 기준 상대 경로인 경우
                path_to_check = os.path.join(HANWHA_DOWNLOAD_DIR, link_str)

            if os.path.exists(path_to_check) and path_to_check.lower().endswith(".pdf"):
                is_local_pdf_file = True
        except Exception:
            pass
    # HTTP 링크이지만 .pdf로 끝나지 않는 경우 (PDF만 대상으로 할 경우)
    elif is_http_link and not link_str.lower().endswith(".pdf"):
        # 한화생명 사이트가 PDF 외 다른 형식의 중요 문서를 링크할 수 있다면 이 조건을 제거하거나 수정해야 합니다.
        # 현재는 PDF만 유효하다고 가정합니다.
        return False

    return is_http_link or is_local_pdf_file


if __name__ == "__main__":
    collected_data = get_hanwhalife_product_info_selenium()

    if collected_data:
        if DatabaseManager:
            print("DB 저장 진행중...")
            structured_rows_to_save = []
            scraped_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            company_name = "한화생명"

            for item in collected_data:
                # '보험명'에서 카테고리와 실제 상품명 분리 시도 (예: "정기보험 - 한화생명 e정기보험")
                # 실제 상품명만 product_name_val로 사용
                full_product_name = item.get('보험명', 'N/A')
                product_name_val = full_product_name.split(' - ')[-1] if ' - ' in full_product_name else full_product_name

                sales_period_val = item.get('판매기간', 'N/A')
                product_code_val = None

                doc_map = {
                    "상품요약서": item.get("상품요약서_링크"),
                    "약관": item.get("약관_링크"),
                    "사업방법서": item.get("사업방법서_링크")
                }

                has_valid_link_for_this_product = False
                current_product_docs = []
                for doc_type, link_url in doc_map.items():
                    if is_valid_hanwha_link(link_url):
                        # 한화생명은 상대경로를 사용할 수 있으므로 절대경로로 변환
                        if link_url.startswith("/"):
                            link_url = "https://www.hanwhalife.com" + link_url

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
            print(f"총 스크래핑된 상품 항목(버전 포함) 수: {len(collected_data)}개")
        else:
            print("DatabaseManager 사용 불가. DB 저장 기능을 건너뜁니다.")
    else:
        print("스크래핑된 상품 데이터가 없습니다.")
