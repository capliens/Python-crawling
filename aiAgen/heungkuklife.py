# 흫국생명
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException, TimeoutException
# from webdriver_manager.chrome import ChromeDriverManager # 사용 안 함
from selenium.webdriver.chrome.service import Service
import time
import os
import sys

# DB저장
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from neoali.pdf_link_scraper import PdfLinkExtractor
except ImportError as e:
    PdfLinkExtractor = None
    print(f"경고: PdfLinkExtractor를 임포트할 수 없습니다 ({e}). PDF 링크 추출 기능이 비활성화됩니다.")

# 다운로드 폴더 설정
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
            print(f"StaleElementReferenceException 발생 (시도 {i + 1}/{retries}).")
            time.sleep(wait_sec)
            if i == retries - 1:
                print(f"StaleElementReferenceException으로 최종 클릭 실패: {element_or_xpath}")
                return False
        except TimeoutException:
            print(f"TimeoutException: 요소를 클릭할 수 없음 (시도 {i + 1}/{retries}): {element_or_xpath}")
            if i == retries - 1:
                return False
        except Exception as e:
            print(f"safe_click 중 오류 발생 (시도 {i + 1}/{retries}): {e} ({element_or_xpath})")
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
        print(f"'{filter_dt_text_contains}' 항목 로드 시간 초과 또는 찾을 수 없음")
        return []


def get_product_name_items(driver, wait):
    """판매상품명 링크 요소들을 반환"""
    try:
        wait.until(EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, "div#publicPrtDiv ul#productList li a")))
        return driver.find_elements(
            By.CSS_SELECTOR, "div#publicPrtDiv ul#productList li a")
    except TimeoutException:
        print("판매상품명 항목 로드 시간 초과 또는 찾을 수 없음")
        return []


def extract_detail_data(driver, wait, pdf_extractor, product_name_full, is_discontinued=False):
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

        if pdf_extractor:
            print(f"    PDF 링크 추출 시도 (상품: {product_name_full})...")
            # 약관
            if len(tds_in_detail) > terms_td_list_idx:
                terms_xpath = f"{base_tr_xpath}/td[{terms_td_list_idx + 1}]/a[1]"
                try:
                    detail_info["약관_링크"] = pdf_extractor.get_pdf_url_via_href(terms_xpath) or \
                        pdf_extractor.get_pdf_url_via_network_interception(terms_xpath) or "N/A (추출 실패)"
                except Exception as e_pdf:
                    print(f"      약관 링크 추출 오류 ({terms_xpath}): {e_pdf}")
                    detail_info["약관_링크"] = "N/A (추출 오류)"
            else:
                detail_info["약관_링크"] = "N/A (td 인덱스 범위 밖)"

            # 사업방법서
            if len(tds_in_detail) > biz_method_td_list_idx:
                biz_method_xpath = f"{base_tr_xpath}/td[{biz_method_td_list_idx + 1}]/a[1]"
                try:
                    detail_info["사업방법서_링크"] = pdf_extractor.get_pdf_url_via_href(biz_method_xpath) or \
                        pdf_extractor.get_pdf_url_via_network_interception(biz_method_xpath) or "N/A (추출 실패)"
                except Exception as e_pdf:
                    print(f"      사업방법서 링크 추출 오류 ({biz_method_xpath}): {e_pdf}")
                    detail_info["사업방법서_링크"] = "N/A (추출 오류)"
            else:
                detail_info["사업방법서_링크"] = "N/A (td 인덱스 범위 밖)"

            # 상품요약서
            if len(tds_in_detail) > summary_td_list_idx:
                summary_xpath = f"{base_tr_xpath}/td[{summary_td_list_idx + 1}]/a[1]"
                try:
                    detail_info["상품요약서_링크"] = pdf_extractor.get_pdf_url_via_href(summary_xpath) or \
                        pdf_extractor.get_pdf_url_via_network_interception(summary_xpath) or "N/A (추출 실패)"
                except Exception as e_pdf:
                    print(f"      상품요약서 링크 추출 오류 ({summary_xpath}): {e_pdf}")
                    detail_info["상품요약서_링크"] = "N/A (추출 오류)"
            else:
                detail_info["상품요약서_링크"] = "N/A (td 인덱스 범위 밖)"
        else:
            if len(tds_in_detail) > terms_td_list_idx and tds_in_detail[terms_td_list_idx].find_elements(By.TAG_NAME, "a"):
                detail_info["약관_링크"] = "존재함 (Extractor 비활성)"
            if len(tds_in_detail) > biz_method_td_list_idx and tds_in_detail[biz_method_td_list_idx].find_elements(By.TAG_NAME, "a"):
                detail_info["사업방법서_링크"] = "존재함 (Extractor 비활성)"
            if len(tds_in_detail) > summary_td_list_idx and tds_in_detail[summary_td_list_idx].find_elements(By.TAG_NAME, "a"):
                detail_info["상품요약서_링크"] = "존재함 (Extractor 비활성)"

    except TimeoutException:
        print(f"  '{product_name_full}' 상세 정보 테이블(#productVoTr) 로드 시간 초과.")
    except Exception as e:
        print(f"  '{product_name_full}' 상세 정보 추출 중 오류 발생: {e}")
    return detail_info


def process_product_names(driver, wait, pdf_extractor, division_name, all_data, is_discontinued_page=False):
    """ 특정 구분 하위의 상품명들을 순회하며 상세 정보 추출 """
    product_name_items_initial = get_product_name_items(driver, wait)
    if not product_name_items_initial:
        print(f"  '{division_name}' 내 판매상품명 항목 없음.")
        return

    print(f"  '{division_name}' 내 {len(product_name_items_initial)}개의 상품명 발견. 처리 시작...")
    for k in range(len(product_name_items_initial)):
        product_name_items_refreshed = get_product_name_items(driver, wait)
        if k >= len(product_name_items_refreshed):
            print(f"    상품명 인덱스 {k}가 목록 범위를 벗어남 (재조회 후). 건너뜁니다.")
            continue

        product_element_to_click = product_name_items_refreshed[k]
        product_name_short = "N/A"
        try:
            product_name_short = product_element_to_click.text.strip()
        except Exception as e_text:
            print(f"    상품명(인덱스 {k}) 텍스트 가져오기 오류: {e_text}")
            continue

        product_name_full = f"{division_name} - {product_name_short}"
        print(f"    상품명 '{product_name_short}' (인덱스 {k}) 클릭 시도...")

        if not safe_click(driver, product_element_to_click, wait_sec=2):
            print(f"      [클릭 실패] 상품명: {product_name_short}")
            continue
        print(f"      상품명 '{product_name_short}' 클릭 성공.")

        try:
            data = extract_detail_data(driver, wait, pdf_extractor, product_name_full,
                                       is_discontinued=is_discontinued_page)
            all_data.append(data)
            print(f"      [OK] {data['보험명']} / 판매기간: {data['판매기간']} / 코드: {data['상품코드']}")
            print(f"           약관: {data['약관_링크']}, 사업방법서: {data['사업방법서_링크']}, 요약서: {data['상품요약서_링크']}")
        except Exception as e_extract:
            print(f"      [데이터 추출 실패] 상품명: {product_name_short}, 오류: {e_extract}")


def get_heungkuklife_product_info():
    chrome_options = Options()
    # chrome_options.add_argument("--headless")
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

    driver = None
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

    pdf_extractor = None
    if PdfLinkExtractor:
        pdf_extractor = PdfLinkExtractor(driver, HEUNGKUKLIFE_DOWNLOAD_DIR)

    all_data = []

    print("--- 판매상품 정보 수집 시작 ---")
    selling_url = "https://www.heungkuklife.co.kr/front/public/saleProduct.do?searchFlgSale=Y"
    driver.get(selling_url)
    time.sleep(3)

    try:
        division_items_selling = get_filter_items(driver, wait, "1. 구분선택")
        if not division_items_selling:
            print("판매상품 구분선택 항목을 찾을 수 없습니다. 단일 구분으로 처리합니다.")
            process_product_names(driver, wait, pdf_extractor, "기본 판매상품 구분", all_data, is_discontinued_page=False)
        else:
            print(f"총 {len(division_items_selling)}개의 판매상품 구분선택 발견.")
            for i in range(len(division_items_selling)):
                current_division_items = get_filter_items(driver, wait, "1. 구분선택")
                if i >= len(current_division_items):
                    continue

                division_element = current_division_items[i]
                division_name = division_element.text.strip()
                print(f"\n판매상품 구분선택: '{division_name}' (인덱스 {i}) 클릭 시도...")
                if not safe_click(driver, division_element, wait_sec=2):
                    print(f"  [클릭 실패] 판매상품 구분선택: {division_name}")
                    driver.get(selling_url)
                    time.sleep(2)
                    continue
                print(f"  판매상품 구분선택: '{division_name}' 클릭 성공.")
                process_product_names(driver, wait, pdf_extractor, division_name, all_data, is_discontinued_page=False)

                print(f"  '{division_name}' 처리 완료. 판매상품 목록 페이지로 복귀.")
                driver.get(selling_url)
                WebDriverWait(driver, 10).until(EC.presence_of_element_located(
                    (By.XPATH, "//dt[contains(text(), '1. 구분선택')]")))
                time.sleep(1)
    except Exception as e:
        print(f"판매상품 스크래핑 중 오류 발생: {e}")

    print("\n--- 판매중지 상품 정보 수집 시작 ---")
    discontinued_url = "https://www.heungkuklife.co.kr/front/public/saleProduct.do?searchFlgSale=N&beforeYn=N"
    driver.get(discontinued_url)
    time.sleep(3)

    try:
        period_items = get_filter_items(driver, wait, "1. 기간선택")
        if not period_items:
            print("판매중지 상품 기간선택 항목을 찾을 수 없습니다. '1. 구분선택'으로 바로 진행합니다.")
            division_items_discontinued = get_filter_items(driver, wait, "1. 구분선택")
            if not division_items_discontinued:
                print("판매중지 상품 구분선택 항목도 찾을 수 없습니다. 단일 구분으로 처리합니다.")
                process_product_names(driver, wait, pdf_extractor, "기본 판매중지 기간/구분", all_data, is_discontinued_page=True)
            else:
                print(f"총 {len(division_items_discontinued)}개의 판매중지 상품 구분선택 (기간선택 없음) 발견.")
                for i in range(len(division_items_discontinued)):
                    current_division_items = get_filter_items(driver, wait, "1. 구분선택")
                    if i >= len(current_division_items):
                        continue
                    div_el = current_division_items[i]
                    div_name = div_el.text.strip()
                    print(f"\n판매중지 구분선택: '{div_name}' (인덱스 {i}) 클릭 시도...")
                    if not safe_click(driver, div_el, wait_sec=2):
                        print(f"  [클릭 실패] 판매중지 구분선택: {div_name}")
                        driver.get(discontinued_url)
                        time.sleep(2)
                        continue
                    process_product_names(driver, wait, pdf_extractor,
                                          f"판매중지 - {div_name}", all_data, is_discontinued_page=True)
                    driver.get(discontinued_url)
                    WebDriverWait(driver, 10).until(EC.presence_of_element_located(
                        (By.XPATH, "//dt[contains(text(), '1. 구분선택') or contains(text(), '1. 기간선택')]")))
                    time.sleep(1)
        else:
            print(f"총 {len(period_items)}개의 판매중지 상품 기간선택 발견.")
            for i in range(len(period_items)):
                current_period_items = get_filter_items(driver, wait, "1. 기간선택")
                if i >= len(current_period_items):
                    continue

                period_element = current_period_items[i]
                period_name = period_element.text.strip()
                print(f"\n판매중지 기간선택: '{period_name}' (인덱스 {i}) 클릭 시도...")
                if not safe_click(driver, period_element, wait_sec=2):
                    print(f"  [클릭 실패] 판매중지 기간선택: {period_name}")
                    driver.get(discontinued_url)
                    time.sleep(2)
                    continue
                print(f"  판매중지 기간선택: '{period_name}' 클릭 성공.")

                division_items_after_period = get_filter_items(driver, wait, "2. 구분선택")
                if not division_items_after_period:
                    print(f"  '{period_name}' 내 구분선택 항목 없음. 현재 상태로 상품명 처리 시도.")
                    process_product_names(driver, wait, pdf_extractor,
                                          f"판매중지 - {period_name} - 기본구분", all_data, is_discontinued_page=True)
                else:
                    print(f"  '{period_name}' 내 {len(division_items_after_period)}개의 구분선택 발견.")
                    for j in range(len(division_items_after_period)):
                        current_division_items_dp = get_filter_items(driver, wait, "2. 구분선택")
                        if j >= len(current_division_items_dp):
                            continue

                        div_el_dp = current_division_items_dp[j]
                        div_name_dp = div_el_dp.text.strip()
                        print(f"    판매중지 구분선택: '{div_name_dp}' (인덱스 {j}) 클릭 시도...")
                        if not safe_click(driver, div_el_dp, wait_sec=2):
                            print(f"      [클릭 실패] 판매중지 구분선택: {div_name_dp}")
                            break

                        process_product_names(driver, wait, pdf_extractor,
                                              f"판매중지 - {period_name} - {div_name_dp}", all_data, is_discontinued_page=True)

                        print(f"    '{div_name_dp}' 처리 완료. '{period_name}' 기간선택 상태로 복귀 시도...")
                        period_xpath_to_reclick = f"(//dt[contains(text(), '1. 기간선택')]/following-sibling::dd//ul[contains(@class,'select1')]//a)[{i + 1}]"
                        if not safe_click(driver, period_xpath_to_reclick, by=By.XPATH, wait_sec=1):
                            print(f"      '{period_name}' 기간선택 상태로 복귀 실패. 판매중지 첫 페이지로 이동.")
                            driver.get(discontinued_url)
                            WebDriverWait(driver, 10).until(EC.presence_of_element_located(
                                (By.XPATH, "//dt[contains(text(), '1. 기간선택')]")))
                            time.sleep(1)
                            break
                        else:
                            print(f"      '{period_name}' 기간선택 상태로 복귀 성공.")
                            WebDriverWait(driver, 10).until(EC.presence_of_element_located(
                                (By.XPATH, "//dt[contains(text(), '2. 구분선택')]")))
                            time.sleep(1)

                print(f"  '{period_name}' 기간의 모든 구분 처리 완료. 판매중지 목록 페이지로 복귀.")
                driver.get(discontinued_url)
                WebDriverWait(driver, 10).until(EC.presence_of_element_located(
                    (By.XPATH, "//dt[contains(text(), '1. 기간선택')]")))
                time.sleep(1)

    except Exception as e:
        print(f"판매중지 상품 스크래핑 중 오류 발생: {e}")

    finally:
        if driver:
            driver.quit()

    print("\n--- 스크립트 실행 완료 ---")
    if all_data:
        print(f"총 {len(all_data)}개의 상품 상세 정보(버전 포함) 수집 완료.")
        for item in all_data:
            print(item)
    else:
        print("수집된 데이터가 없습니다.")

    return all_data


if __name__ == "__main__":
    data = get_heungkuklife_product_info()
