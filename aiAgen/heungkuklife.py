# 흥국생명/안쓰는 코드제거
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.chrome.service import Service
import time
import os
import sys
import datetime

# project_root 경로 설정 (기존 코드 유지)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# PdfLinkExtractor 관련 임포트 제거
try:
    from neoali.DB_save import DatabaseManager  # DatabaseManager는 유지
except ImportError as e:
    DatabaseManager = None
    print(f"경고: DatabaseManager 모듈 임포트 실패 ({e}). DB 저장 기능이 비활성화됩니다.")

HEUNGKUKLIFE_DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads", "heungkuklife")
if not os.path.exists(HEUNGKUKLIFE_DOWNLOAD_DIR):
    os.makedirs(HEUNGKUKLIFE_DOWNLOAD_DIR)


def safe_click(driver, element_or_xpath, by=By.XPATH, retries=3, wait_sec=1):
    """요소를 안전하게 클릭 (StaleElementReferenceException 처리 포함)"""
    for i in range(retries):
        try:
            if isinstance(element_or_xpath, str):
                element = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((by, element_or_xpath)))
            else:
                element = WebDriverWait(driver, 5).until(EC.element_to_be_clickable(element_or_xpath))

            driver.execute_script("arguments[0].scrollIntoView(true);", element)
            time.sleep(0.3)
            driver.execute_script("arguments[0].click();", element)
            time.sleep(wait_sec)
            return True
        except StaleElementReferenceException:
            print(f"StaleElementReferenceException (클릭 시도 {i + 1}/{retries}).")
            time.sleep(wait_sec)
            if i == retries - 1:
                return False
        except TimeoutException:
            print(f"TimeoutException (클릭 시도 {i + 1}/{retries}): {element_or_xpath}")
            if i == retries - 1:
                return False
        except Exception as e:
            print(f"safe_click 중 오류 (클릭 시도 {i + 1}/{retries}): {e} ({element_or_xpath})")
            if i == retries - 1:
                return False
    return False


def get_filter_items(driver, wait, filter_dt_text_contains, list_ul_class='select1'):
    """지정된 필터링 항목(구분선택, 기간선택 등)의 링크 요소들을 반환"""
    try:
        xpath = f"//dt[contains(text(), '{filter_dt_text_contains}')]/following-sibling::dd//ul[contains(@class,'{list_ul_class}')]//a"
        wait.until(EC.presence_of_all_elements_located((By.XPATH, xpath)))
        return driver.find_elements(By.XPATH, xpath)
    except TimeoutException:
        return []


def get_product_name_items(driver, wait):
    """판매상품명 링크 요소들을 반환"""
    try:
        wait.until(EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, "div#publicPrtDiv ul#productList li a")))
        return driver.find_elements(
            By.CSS_SELECTOR, "div#publicPrtDiv ul#productList li a")
    except TimeoutException:
        return []


def extract_detail_data(driver, wait, product_name_full, is_discontinued=False):
    """상품 상세 정보 및 PDF 링크 추출 (판매중지 여부에 따라 열 인덱스 조정)"""
    detail_info = {
        "보험명": product_name_full,
        "판매기간": "정보 없음",
        "상품코드": "정보 없음",
        "약관_링크": "N/A",
        "사업방법서_링크": "N/A",
        "상품요약서_링크": "N/A"
    }
    try:
        wait.until(EC.visibility_of_element_located((By.ID, "productVoTr")))
        product_detail_row_element = driver.find_element(By.CSS_SELECTOR, "#productVoTr tr")

        tds_in_detail = product_detail_row_element.find_elements(By.TAG_NAME, "td")

        # 열 인덱스 결정 (0-based for list access, 1-based for XPath)
        # 판매상품: 판매기간(td[0]), 상품코드(td[1]), 약관(td[2]), 사업방법서(td[3]), 상품요약서(td[4])
        # 판매중지: (기간선택 td[0]), 판매기간(td[1]), 상품코드(td[2]), 약관(td[3]), 사업방법서(td[4]), 상품요약서(td[5])

        sales_period_td_list_idx = 1 if is_discontinued else 0
        product_code_td_list_idx = 2 if is_discontinued else 1
        terms_td_list_idx = 3 if is_discontinued else 2
        biz_method_td_list_idx = 4 if is_discontinued else 3
        summary_td_list_idx = 5 if is_discontinued else 4

        if len(tds_in_detail) > sales_period_td_list_idx:
            try:
                detail_info["판매기간"] = tds_in_detail[sales_period_td_list_idx].text.strip()
            except Exception:
                pass
        if len(tds_in_detail) > product_code_td_list_idx:
            try:
                detail_info["상품코드"] = tds_in_detail[product_code_td_list_idx].text.strip()
            except Exception:
                pass

        # PDF 링크 추출 XPath (tbody#productVoTr/tr[1] 기준으로 td 인덱스 사용)
        base_tr_xpath = "//tbody[@id='productVoTr']/tr[1]"

        # pdf_extractor 관련 조건문 제거, 항상 href 속성만 가져옵니다.
        if len(tds_in_detail) > terms_td_list_idx:
            terms_xpath = f"{base_tr_xpath}/td[{terms_td_list_idx + 1}]/a[1]"
            try:
                link_element = driver.find_element(By.XPATH, terms_xpath)
                href = link_element.get_attribute('href')
                if href and href.startswith('/'):
                    href = "https://www.heungkuklife.co.kr" + href
                    print("약관:" + href)
                detail_info["약관_링크"] = href
            except Exception:
                detail_info["약관_링크"] = "N/A (추출 오류)"

        if len(tds_in_detail) > biz_method_td_list_idx:
            biz_method_xpath = f"{base_tr_xpath}/td[{biz_method_td_list_idx + 1}]/a[1]"
            try:
                link_element = driver.find_element(By.XPATH, biz_method_xpath)
                href = link_element.get_attribute('href')
                if href and href.startswith('/'):
                    href = "https://www.heungkuklife.co.kr" + href
                detail_info["사업방법서_링크"] = href
                print("사업업:" + href)
            except Exception:
                detail_info["사업방법서_링크"] = "N/A (추출 오류)"

        if len(tds_in_detail) > summary_td_list_idx:
            summary_xpath = f"{base_tr_xpath}/td[{summary_td_list_idx + 1}]/a[1]"
            try:
                link_element = driver.find_element(By.XPATH, summary_xpath)
                href = link_element.get_attribute('href')
                if href and href.startswith('/'):
                    href = "https://www.heungkuklife.co.kr" + href
                detail_info["상품요약서_링크"] = href
                print("요약서:" + href)
            except Exception:
                detail_info["상품요약서_링크"] = "N/A (추출 오류)"

    except TimeoutException:
        print(f"  '{product_name_full}' 상세 정보 테이블(#productVoTr) 로드 시간 초과.")
    except Exception as e:
        print(f"  '{product_name_full}' 상세 정보 추출 중 오류 발생: {e}")
    return detail_info


def process_product_names(driver, wait, division_name, all_data, is_discontinued_page=False):
    """ 특정 구분 하위의 상품명들을 순회하며 상세 정보 추출 """
    product_name_items_initial = get_product_name_items(driver, wait)
    if not product_name_items_initial:
        return

    for k in range(len(product_name_items_initial)):
        product_name_items_refreshed = get_product_name_items(driver, wait)  # Stale 방지 위해 매번 조회
        if k >= len(product_name_items_refreshed):
            continue

        product_element_to_click = product_name_items_refreshed[k]
        product_name_short = "N/A"
        try:
            product_name_short = product_element_to_click.text.strip()
        except Exception:
            continue

        product_name_full = f"{division_name} - {product_name_short}"

        if not safe_click(driver, product_element_to_click, wait_sec=1):
            continue

        try:
            # pdf_extractor 인자 제거
            data = extract_detail_data(driver, wait, product_name_full, is_discontinued=is_discontinued_page)
            all_data.append(data)
        except Exception as e_extract:
            print(f"    '{product_name_short}' 데이터 추출 실패: {e_extract}")


def get_heungkuklife_product_info():
    print("흥국생명 스크래핑 시작...")
    driver = None
    try:
        chrome_options = Options()

        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        prefs = {
            "download.default_directory": HEUNGKUKLIFE_DOWNLOAD_DIR,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True
        }
        chrome_options.add_experimental_option("prefs", prefs)
        chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

        try:
            print("WebDriver 초기화 시도 (시스템 PATH 의존)...")
            driver = webdriver.Chrome(options=chrome_options)
            print("WebDriver 초기화 성공 (시스템 PATH 의존).")
        except Exception as e_init:
            print(f"WebDriver 초기화 실패 (시스템 PATH 의존): {e_init}")
            print("webdriver_manager를 사용한 초기화를 시도합니다.")
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=chrome_options)
                print("webdriver_manager를 사용하여 WebDriver 초기화 성공.")
            except Exception as e_wdm:
                print(f"webdriver_manager 사용 초기화도 실패: {e_wdm}")
                print("ChromeDriver가 시스템 PATH에 설정되어 있거나, webdriver_manager가 올바르게 설치되었는지 확인해주세요.")
                return []

        if driver is None:
            print("WebDriver를 초기화할 수 없습니다.")
            return []

        wait = WebDriverWait(driver, 15)

        # pdf_extractor 객체 생성 및 관련 로직 제거
        # pdf_extractor = None
        # if PdfLinkExtractor:
        #     pdf_extractor = PdfLinkExtractor(driver, HEUNGKUKLIFE_DOWNLOAD_DIR)

        all_data = []

        print("판매상품 정보 수집 중...")
        selling_url = "https://www.heungkuklife.co.kr/front/public/saleProduct.do?searchFlgSale=Y"
        driver.get(selling_url)
        time.sleep(2)

        try:
            division_items_selling = get_filter_items(driver, wait, "1. 구분선택")
            if not division_items_selling:
                # pdf_extractor 인자 제거
                process_product_names(driver, wait, "기본 판매상품 구분", all_data, is_discontinued_page=False)
            else:
                for i in range(len(division_items_selling)):
                    current_division_items = get_filter_items(driver, wait, "1. 구분선택")
                    if i >= len(current_division_items):
                        continue
                    division_element = current_division_items[i]
                    division_name = division_element.text.strip()
                    print(f"  판매상품 구분: '{division_name}' 처리 중...")
                    if not safe_click(driver, division_element, wait_sec=1):
                        driver.get(selling_url)
                        time.sleep(1)
                        continue
                    # pdf_extractor 인자 제거
                    process_product_names(driver, wait, division_name, all_data, is_discontinued_page=False)
                    driver.get(selling_url)
                    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//dt[contains(text(), '1. 구분선택')]")))
                    time.sleep(0.5)
        except Exception as e:
            print(f"판매상품 스크래핑 중 오류: {e}")
        print("판매상품 정보 수집 완료.")

        print("판매중지 상품 정보 수집 중...")
        discontinued_url = "https://www.heungkuklife.co.kr/front/public/saleProduct.do?searchFlgSale=N&beforeYn=N"
        driver.get(discontinued_url)
        time.sleep(2)

        try:
            period_items = get_filter_items(driver, wait, "1. 기간선택")
            if not period_items:
                division_items_discontinued = get_filter_items(driver, wait, "1. 구분선택")
                if not division_items_discontinued:
                    # pdf_extractor 인자 제거
                    process_product_names(driver, wait, "기본 판매중지 기간/구분", all_data, is_discontinued_page=True)
                else:
                    for i in range(len(division_items_discontinued)):
                        current_division_items = get_filter_items(driver, wait, "1. 구분선택")
                        if i >= len(current_division_items):
                            continue
                        div_el = current_division_items[i]
                        div_name = div_el.text.strip()
                        print(f"  판매중지 구분: '{div_name}' 처리 중...")
                        if not safe_click(driver, div_el, wait_sec=1):
                            driver.get(discontinued_url)
                            time.sleep(1)
                            continue
                        # pdf_extractor 인자 제거
                        process_product_names(driver, wait, f"판매중지 - {div_name}", all_data, is_discontinued_page=True)
                        driver.get(discontinued_url)
                        WebDriverWait(driver, 10).until(EC.presence_of_element_located(
                            (By.XPATH, "//dt[contains(text(), '1. 구분선택') or contains(text(), '1. 기간선택')]")))
                        time.sleep(0.5)
            else:
                for i in range(len(period_items)):
                    current_period_items = get_filter_items(driver, wait, "1. 기간선택")
                    if i >= len(current_period_items):
                        continue
                    period_element = current_period_items[i]
                    period_name = period_element.text.strip()
                    print(f"  판매중지 기간: '{period_name}' 처리 중...")
                    if not safe_click(driver, period_element, wait_sec=1):
                        driver.get(discontinued_url)
                        time.sleep(1)
                        continue

                    division_items_after_period = get_filter_items(driver, wait, "2. 구분선택")
                    if not division_items_after_period:
                        # pdf_extractor 인자 제거
                        process_product_names(driver, wait, f"판매중지 - {period_name} - 기본구분", all_data, is_discontinued_page=True)
                    else:
                        for j in range(len(division_items_after_period)):
                            current_division_items_dp = get_filter_items(driver, wait, "2. 구분선택")
                            if j >= len(current_division_items_dp):
                                continue
                            div_el_dp = current_division_items_dp[j]
                            div_name_dp = div_el_dp.text.strip()
                            print(f"    판매중지 구분: '{div_name_dp}' (기간: {period_name}) 처리 중...")
                            if not safe_click(driver, div_el_dp, wait_sec=1):
                                break
                            # pdf_extractor 인자 제거
                            process_product_names(driver, wait,
                                                  f"판매중지 - {period_name} - {div_name_dp}", all_data, is_discontinued_page=True)

                            period_xpath_to_reclick = (
                                f"(//dt[contains(text(), '1. 기간선택')]/following-sibling::dd"
                                f"//ul[contains(@class,'select1')]//a)[{i + 1}]"
                            )
                            if not safe_click(driver, period_xpath_to_reclick, by=By.XPATH, wait_sec=1):
                                driver.get(discontinued_url)
                                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//dt[contains(text(), '1. 기간선택')]")))
                                time.sleep(0.5)
                                break
                            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//dt[contains(text(), '2. 구분선택')]")))
                            time.sleep(0.5)
                    driver.get(discontinued_url)
                    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//dt[contains(text(), '1. 기간선택')]")))
                    time.sleep(0.5)
        except Exception as e:
            print(f"판매중지 상품 스크래핑 중 오류: {e}")
        print("판매중지 상품 정보 수집 완료.")
        return all_data
    finally:
        if driver:
            driver.quit()


if __name__ == "__main__":
    all_scraped_data = get_heungkuklife_product_info()

    if all_scraped_data:
        if DatabaseManager:
            print("DB 저장 진행중...")
            structured_rows_to_save = []
            scraped_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            company_name = "흥국생명"

            for item_data in all_scraped_data:
                product_name_val = item_data.get("보험명")
                sales_period_val = item_data.get("판매기간")
                product_code_val = item_data.get("상품코드")
                if not product_code_val or "정보 없음" in product_code_val:
                    product_code_val = None

                doc_map = {
                    "상품요약서": item_data.get("상품요약서_링크"),
                    "약관": item_data.get("약관_링크"),
                    "사업방법서": item_data.get("사업방법서_링크")
                }

                current_product_docs = []
                for doc_type, link_url in doc_map.items():
                    if link_url and "N/A" not in link_url:
                        current_product_docs.append([
                            company_name, product_name_val, product_code_val,
                            doc_type, sales_period_val, scraped_time, link_url
                        ])

                if current_product_docs:
                    structured_rows_to_save.extend(current_product_docs)

            if structured_rows_to_save:
                with DatabaseManager(db_name="insurance_products.db") as db_manager:
                    saved_count = db_manager.save_data(structured_rows_to_save)
                print(f"DB 저장 완료. 총 {saved_count}건 문서 정보 저장.")
            else:
                print("DB에 저장할 유효한 문서 정보가 없습니다.")
            print(f"총 스크래핑된 상품 항목(버전 포함) 수: {len(all_scraped_data)}개")
        else:
            print("DatabaseManager 사용 불가. DB 저장 기능을 건너뜁니다.")
    else:
        print("스크래핑된 상품 데이터가 없습니다.")
