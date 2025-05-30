# 한화 생명
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
# db저장

# 프로젝트 루트를 sys.path에 추가 (fubonhyundai.py와 동일한 구조 가정)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from neoali.pdf_link_scraper import PdfLinkExtractor
except ImportError as e:
    PdfLinkExtractor = None
    print(f"경고: PdfLinkExtractor를 임포트할 수 없습니다 ({e}). PDF 링크 추출 기능이 비활성화됩니다.")

# 다운로드 폴더 설정 (hanwhalife 전용 또는 공용 사용 가능)
HANWHA_DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads", "hanwhalife")
if not os.path.exists(HANWHA_DOWNLOAD_DIR):
    os.makedirs(HANWHA_DOWNLOAD_DIR)


def scrape_product_details(driver, pdf_extractor, category_name_text, current_product_name):
    """상품 상세 정보 및 PDF 링크를 추출하는 헬퍼 함수. 모든 판매기간 버전을 리스트로 반환."""
    all_versions_details = []
    detail_list_selector = "tbody#List3 tr"
    try:
        WebDriverWait(driver, 10).until(EC.visibility_of_element_located(
            (By.CSS_SELECTOR, detail_list_selector)))
        detail_rows = driver.find_elements(
            By.CSS_SELECTOR, detail_list_selector)

        print(f"      tbody#List3 발견된 tr 개수: {len(detail_rows)}")

        if detail_rows:
            print(
                f"        {len(detail_rows)}개의 데이터 행 처리 시작.")
            for data_row_idx_loop in range(len(detail_rows)):  # 모든 행을 데이터로 처리
                data_row_element = detail_rows[data_row_idx_loop]
                tds_in_data_row = data_row_element.find_elements(
                    By.CSS_SELECTOR, "td")
                print(
                    f"          행 {data_row_idx_loop + 1} (인덱스 {data_row_idx_loop}): td 개수 = {len(tds_in_data_row)}")

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
                        print(f"            상품요약서 추출 시도 (XPATH: {summary_xpath})")
                        summary_link_val = pdf_extractor.get_pdf_url_via_href(summary_xpath)
                        if not summary_link_val or not summary_link_val.lower().endswith('.pdf'):
                            summary_link_val = pdf_extractor.get_pdf_url_via_network_interception(summary_xpath)
                        current_version_detail['상품요약서_링크'] = summary_link_val or "N/A (추출 실패)"
                    else:
                        current_version_detail['상품요약서_링크'] = "N/A (링크 요소 없음)"

                    if len(tds_in_data_row) > 2 and tds_in_data_row[2].find_elements(By.CSS_SELECTOR, "a, button"):
                        biz_xpath = f"{current_data_row_xpath}/td[3]/descendant::*[self::a or self::button][1]"
                        print(f"            사업방법서 추출 시도 (XPATH: {biz_xpath})")
                        biz_method_link_val = pdf_extractor.get_pdf_url_via_href(biz_xpath)
                        if not biz_method_link_val or not biz_method_link_val.lower().endswith('.pdf'):
                            biz_method_link_val = pdf_extractor.get_pdf_url_via_network_interception(biz_xpath)
                        current_version_detail['사업방법서_링크'] = biz_method_link_val or "N/A (추출 실패)"
                    else:
                        current_version_detail['사업방법서_링크'] = "N/A (링크 요소 없음)"

                    if len(tds_in_data_row) > 3 and tds_in_data_row[3].find_elements(By.CSS_SELECTOR, "a, button"):
                        terms_xpath = f"{current_data_row_xpath}/td[4]/descendant::*[self::a or self::button][1]"
                        print(f"            약관 추출 시도 (XPATH: {terms_xpath})")
                        terms_link_val = pdf_extractor.get_pdf_url_via_href(terms_xpath)
                        if not terms_link_val or not terms_link_val.lower().endswith('.pdf'):
                            terms_link_val = pdf_extractor.get_pdf_url_via_network_interception(terms_xpath)
                        current_version_detail['약관_링크'] = terms_link_val or "N/A (추출 실패)"
                    else:
                        current_version_detail['약관_링크'] = "N/A (링크 요소 없음)"
                else:
                    if len(tds_in_data_row) > 1 and tds_in_data_row[1].find_elements(By.CSS_SELECTOR, "a, button"):
                        current_version_detail['상품요약서_링크'] = "존재함 (Extractor 비활성)"
                    else:
                        current_version_detail['상품요약서_링크'] = "N/A (링크 요소 없음)"
                    if len(tds_in_data_row) > 2 and tds_in_data_row[2].find_elements(By.CSS_SELECTOR, "a, button"):
                        current_version_detail['사업방법서_링크'] = "존재함 (Extractor 비활성)"
                    else:
                        current_version_detail['사업방법서_링크'] = "N/A (링크 요소 없음)"
                    if len(tds_in_data_row) > 3 and tds_in_data_row[3].find_elements(By.CSS_SELECTOR, "a, button"):
                        current_version_detail['약관_링크'] = "존재함 (Extractor 비활성)"
                    else:
                        current_version_detail['약관_링크'] = "N/A (링크 요소 없음)"

                all_versions_details.append(current_version_detail)
                print(
                    f"            추가된 버전 데이터: 판매기간='{current_version_detail['판매기간']}', 약관='{current_version_detail['약관_링크']}', 요약서='{current_version_detail['상품요약서_링크']}', 사업방법서='{current_version_detail['사업방법서_링크']}'")
        else:
            print("      tbody#List3에 데이터 행이 없음. 상세 정보 N/A 처리.")
    except TimeoutException:
        print(f"      '{current_product_name}' 상세 정보(tbody#List3) 로드 시간 초과.")
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
        print(f"  '{category_name_text}' 내 상품 없음.")
        return
    print(f"  '{category_name_text}' 내 {num_products}개 상품명 발견.")

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
            print(f"    상품명 정보 비어있음 (인덱스 {p_idx}).")
            continue

        print(f"    [{p_idx + 1}/{num_products}] 상품명 '{current_product_name}' 처리 중...")

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

    try:
        print("--- 판매상품 정보 수집 시작 ---")
        driver.get(base_url)
        category_list_selector = "tbody#List1 tr"
        WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, category_list_selector)))
        num_categories = len(driver.find_elements(By.CSS_SELECTOR, category_list_selector))
        print(f"총 {num_categories}개의 판매상품 구분 발견.")
        for cat_idx in range(num_categories):
            print(f"판매상품 카테고리 인덱스 {cat_idx + 1}/{num_categories} 처리 시도...")
            process_product_category(driver, pdf_extractor, base_url,  # 판매상품은 base_url 사용
                                     category_list_selector, cat_idx, product_data_collected, is_discontinued_tab=False)

        print("\n--- 판매중지 상품 정보 수집 시작 ---")
        # 판매중지 탭으로 이동하기 위해 다시 base_url 로드 (탭 상태 초기화 방지 위함)
        # driver.get(base_url) # process_product_category에서 이미 base_url로 이동하므로 중복될 수 있음.
        # 판매중지 탭으로 이동하는 로직은 process_product_category 호출 전에 수행되어야 함.

        # 1. a#sel2 클릭 (판매중지상품 탭으로 추정)
        try:
            driver.get(base_url)  # 판매중지 탭 클릭 전 페이지 초기화
            time.sleep(1)
            sel2_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a#sel2"))
            )
            print("a#sel2 (판매중지상품 탭) 클릭 시도...")
            driver.execute_script("arguments[0].click();", sel2_button)
            time.sleep(2)
            print("a#sel2 클릭 완료.")
        except TimeoutException:
            print("a#sel2 (판매중지상품 탭)을 찾거나 클릭할 수 없습니다.")
            raise  # 이 부분 실패 시 더 이상 진행 불가 (또는 return)

        # 2. ul#menu2 안의 두 번째 li 안에있는 button 클릭
        try:
            discontinued_trigger_button_selector = "ul#menu2 > li:nth-child(2) > button"
            discontinued_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, discontinued_trigger_button_selector))
            )
            print(f"판매중지 상품 목록 로드 버튼 ({discontinued_trigger_button_selector}) 클릭 시도...")
            driver.execute_script("arguments[0].click();", discontinued_button)
            time.sleep(3)
            print("판매중지 상품 목록 로드 버튼 클릭 완료.")

            # 판매중지 상품 목록에 대해서도 동일한 카테고리 및 상품 처리 로직 반복
            WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, category_list_selector)))
            num_discontinued_categories = len(driver.find_elements(By.CSS_SELECTOR, category_list_selector))
            print(f"총 {num_discontinued_categories}개의 판매중지 상품 구분 발견.")

            # 판매중지 탭으로 이동한 후의 URL 또는 상태를 유지하며 카테고리 처리
            # process_product_category는 내부적으로 driver.get(base_url)을 호출하므로,
            # 판매중지 탭 상태에서 각 카테고리를 처리하려면 이 부분을 수정해야 함.
            # 여기서는 각 카테고리 처리 시 판매중지 탭을 다시 클릭하는 방식으로 접근.
            # 또는 process_product_category에 is_discontinued_tab 플래그를 전달하여 driver.get()을 건너뛰게 함.

            for cat_idx in range(num_discontinued_categories):
                print(f"판매중지 상품 카테고리 인덱스 {cat_idx + 1}/{num_discontinued_categories} 처리 시도...")
                # 판매중지 탭이 이미 활성화된 상태이므로, base_url 대신 현재 상태에서 카테고리 처리
                # process_product_category는 base_url을 인자로 받으므로, 판매중지 탭으로 이동 후의 URL을 전달하거나,
                # process_product_category가 base_url을 사용하지 않도록 수정해야 함.
                # 여기서는 is_discontinued_tab 플래그를 사용하여 process_product_category 내에서 driver.get()을 건너뛰도록 함.
                process_product_category(driver, pdf_extractor, driver.current_url,  # 현재 URL (판매중지 탭 상태)
                                         category_list_selector, cat_idx, product_data_collected, is_discontinued_tab=True)

        except TimeoutException:
            print("판매중지 상품 목록 로드 버튼을 찾거나 클릭할 수 없습니다.")
        except Exception as e_discontinued_setup:
            print(f"판매중지 상품 설정 중 오류: {e_discontinued_setup}")

    except Exception as e:
        print(f"전체 스크래핑 과정 중 오류 발생: {e}")
    finally:
        if 'driver' in locals() and driver:
            driver.quit()
        print("\n--- 스크립트 실행 완료 ---")
        if product_data_collected:
            print("--- 추출된 데이터 ---")
            for data in product_data_collected:
                print(data)
        else:
            print("추출된 데이터가 없습니다.")
    return product_data_collected


if __name__ == "__main__":
    get_hanwhalife_product_info_selenium()
