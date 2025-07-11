# 한화 생명
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
import time
import os
import sys
from datetime import datetime
import json
import re
import urllib.parse  # URL 파싱을 위해 추가

# project_root 및 neoali 모듈 임포트 관련 코드는 기존 코드를 존중하여 유지
project_root = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from neoali.DB_save import DatabaseManager
except ImportError as e:
    DatabaseManager = None
    print(f"경고: 모듈 임포트 실패 ({e}). 일부 기능이 비활성화될 수 있습니다.")

HANWHA_DOWNLOAD_DIR = os.path.join(os.path.dirname(
    os.path.abspath(__file__)), "downloads", "hanwhalife")
if not os.path.exists(HANWHA_DOWNLOAD_DIR):
    os.makedirs(HANWHA_DOWNLOAD_DIR)

# CDP 이벤트를 저장할 리스트 (전역 변수로 유지)
# 각 PDF 클릭 시 발생하는 'download_chk.asp' 정보를 여기에 추가합니다.
captured_download_chk_requests = []

# get_latest_downloaded_file 함수는 더 이상 필요 없으므로 제거합니다.


def scrape_product_details(driver, category_name_text, current_product_name):
    """상품 상세 정보 및 PDF 링크(생성된 직접 다운로드 URL)를 추출하는 헬퍼 함수. 모든 판매기간 버전을 리스트로 반환."""
    global captured_download_chk_requests  # 전역 변수 사용 명시

    all_versions_details = []
    detail_list_selector = "tbody#List3 tr"
    try:
        # 요소가 나타날 때까지 대기
        WebDriverWait(driver, 10).until(EC.visibility_of_element_located(
            (By.CSS_SELECTOR, detail_list_selector)))
        detail_rows = driver.find_elements(
            By.CSS_SELECTOR, detail_list_selector)

        if detail_rows:
            for data_row_idx_loop in range(len(detail_rows)):
                try:
                    # 루프 내에서 요소를 다시 찾음 (StaleElementReferenceException 방지)
                    detail_rows_refreshed = driver.find_elements(
                        By.CSS_SELECTOR, detail_list_selector)
                    if data_row_idx_loop >= len(detail_rows_refreshed):
                        print(
                            f"    상품명 '{current_product_name}'의 상세 정보 행 인덱스 {data_row_idx_loop} 찾기 실패 (목록 변경됨).")
                        continue

                    data_row_element = detail_rows_refreshed[data_row_idx_loop]
                    tds_in_data_row = data_row_element.find_elements(
                        By.CSS_SELECTOR, "td")
                except StaleElementReferenceException:
                    print(
                        f"    상품명 '{current_product_name}'의 상세 정보 행 {data_row_idx_loop}가 Stale 상태입니다. 다시 시도합니다.")
                    time.sleep(1)  # 잠시 대기 후 재시도
                    detail_rows_refreshed = driver.find_elements(
                        By.CSS_SELECTOR, detail_list_selector)
                    if data_row_idx_loop >= len(detail_rows_refreshed):
                        continue
                    data_row_element = detail_rows_refreshed[data_row_idx_loop]
                    tds_in_data_row = data_row_element.find_elements(
                        By.CSS_SELECTOR, "td")

                current_version_detail = {
                    '판매기간': "N/A",
                    '약관_링크': "N/A",
                    '상품요약서_링크': "N/A",
                    '사업방법서_링크': "N/A"
                }

                if len(tds_in_data_row) > 0:
                    try:
                        current_version_detail['판매기간'] = tds_in_data_row[0].text.strip(
                        )
                    except Exception:
                        pass

                # 각 PDF 링크 클릭 및 생성된 직접 다운로드 URL 가져오기
                link_selectors = {
                    '상품요약서_링크': "td:nth-child(2) > a, td:nth-child(2) > button",
                    '사업방법서_링크': "td:nth-child(3) > a, td:nth-child(3) > button",
                    '약관_링크': "td:nth-child(4) > a, td:nth-child(4) > button"
                }

                for key, selector in link_selectors.items():
                    print(
                        f"\n[DEBUG] Processing link for '{current_product_name}' - '{key}'...")
                    constructed_pdf_url = "N/A (URL 생성 실패)"  # 기본값 설정

                    try:
                        pdf_button = WebDriverWait(data_row_element, 2).until(
                            EC.element_to_be_clickable(
                                (By.CSS_SELECTOR, selector))
                        )

                        # --- CDP 로그 초기화 및 이벤트 수집 시작 ---
                        driver.execute_cdp_cmd('Log.clear', {})  # 기존 로그 지우기
                        driver.execute_cdp_cmd(
                            'Network.enable', {})  # Network 도메인 활성화

                        driver.execute_script(
                            "arguments[0].click();", pdf_button)
                        time.sleep(1)  # 요청 발생 및 응답 대기

                        # --- CDP 로그 가져와서 'download_chk.asp' 필터링 및 출력 ---
                        current_logs = driver.get_log('performance')
                        found_download_chk_request = False

                        for entry in current_logs:
                            log_data = json.loads(entry['message'])
                            message = log_data['message']

                            if message['method'] == 'Network.requestWillBeSent':
                                request_url = message['params']['request']['url']

                                if re.search(r'download_chk\.asp', request_url, re.IGNORECASE):
                                    found_download_chk_request = True
                                    request_method = message['params']['request']['method']
                                    request_headers = message['params']['request']['headers']
                                    request_post_data = message['params']['request'].get(
                                        'postData')

                                    # 사용자 요청에 따라 POST 요청 정보 출력
                                    print(
                                        f"  [NETWORK INFO - {current_product_name} - {key}]")
                                    print(f"    요청 URL: {request_url}")
                                    print(f"    메서드: {request_method}")
                                    print(
                                        f"    요청 헤더: {json.dumps(request_headers, indent=2)}")
                                    print(f"    요청 페이로드: {request_post_data}")
                                    print("-" * 40)

                                    # 전역 리스트에 POST 요청 정보 추가 (요약 보고서용)
                                    captured_download_chk_requests.append({
                                        'url': request_url,
                                        'method': request_method,
                                        'requestHeaders': request_headers,
                                        'requestPayload': request_post_data
                                    })

                                    # 여기서 GET-style URL을 구성합니다.
                                    if request_post_data and request_post_data.startswith("file_name="):
                                        # "file_name=" 부분을 제거하고 나머지 쿼리 파라미터만 가져옴 (이미 URL 인코딩 되어있음)
                                        file_name_encoded = request_post_data[len(
                                            "file_name="):]
                                        constructed_pdf_url = f"{request_url}?file_name={file_name_encoded}"
                                        # 생성된 URL 출력
                                        print(
                                            f"  [CONSTRUCTED URL] {constructed_pdf_url}")
                                    else:
                                        constructed_pdf_url = "N/A (페이로드에서 file_name 추출 실패)"
                                    break  # download_chk.asp 요청을 찾았으면 더 이상 로그를 처리할 필요 없음

                        if not found_download_chk_request:
                            print(
                                f"  [NETWORK INFO - {current_product_name} - {key}] 'download_chk.asp' 요청을 찾지 못했습니다.")

                        # 생성된 URL을 저장합니다.
                        current_version_detail[key] = constructed_pdf_url

                    except (NoSuchElementException, TimeoutException) as e:
                        current_version_detail[key] = f"N/A (링크/버튼 없음: {e})"
                        print(
                            f"  [ERROR] '{current_product_name}' - '{key}' 링크/버튼 찾기 또는 클릭 오류: {e}")
                    except StaleElementReferenceException:
                        current_version_detail[key] = "N/A (요소 Stale)"
                        print(
                            f"  [ERROR] '{current_product_name}' - '{key}' 링크 요소가 Stale 상태입니다.")
                    except Exception as e:
                        current_version_detail[key] = f"N/A (클릭/URL 생성 오류: {e})"
                        print(
                            f"  [ERROR] '{current_product_name}' - '{key}' 처리 중 오류: {e}")

                all_versions_details.append(current_version_detail)

    except TimeoutException:
        print(f"    '{current_product_name}' 상세 정보 로드 시간 초과.")
    except Exception as e_detail_extract:
        print(f"    '{current_product_name}' 상세 정보 추출 중 오류: {e_detail_extract}")
    return all_versions_details


def scrape_product_list_for_category(driver, category_name_text, product_data_collected):
    """주어진 카테고리 내의 상품 목록을 스크래핑하는 함수"""
    product_list_selector = "tbody#List2 tr"
    try:
        WebDriverWait(driver, 15).until(EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, product_list_selector)))
        time.sleep(2)  # 페이지 로드 및 JS 실행 대기
    except TimeoutException:
        print(f"    '{category_name_text}' 상품명 목록(tbody#List2) 로드 시간 초과.")
        return
    except Exception as e_prod_wait:
        print(
            f"    '{category_name_text}' 상품명 목록(tbody#List2) 로드 중 기타 오류: {e_prod_wait}")
        return

    product_rows_in_category = driver.find_elements(
        By.CSS_SELECTOR, product_list_selector)
    num_products = len(product_rows_in_category)
    if num_products == 0:
        return

    for p_idx in range(num_products):
        current_p_row = None
        current_product_name = "N/A"
        is_linkable = False

        try:
            # 요소 재탐색
            current_product_rows_refreshed = driver.find_elements(
                By.CSS_SELECTOR, product_list_selector)
            if p_idx < len(current_product_rows_refreshed):
                current_p_row = current_product_rows_refreshed[p_idx]
            else:
                print(f"    상품명 인덱스 {p_idx} 찾기 실패 (목록 변경됨).")
                continue
        except StaleElementReferenceException:
            print(f"    상품 목록 행 {p_idx}가 Stale 상태입니다. 재시도합니다.")
            time.sleep(1)
            current_product_rows_refreshed = driver.find_elements(
                By.CSS_SELECTOR, product_list_selector)
            if p_idx < len(current_product_rows_refreshed):
                current_p_row = current_product_rows_refreshed[p_idx]
            else:
                continue
        except Exception as e_get_p_row:
            print(f"    상품명 행 인덱스 {p_idx} 가져오기 오류: {e_get_p_row}.")
            continue

        try:
            prod_name_element = current_p_row.find_element(
                By.CSS_SELECTOR, "td:first-child > a")
            current_product_name = prod_name_element.text.strip()
            is_linkable = True
        except NoSuchElementException:
            try:
                current_product_name = current_p_row.find_element(
                    By.CSS_SELECTOR, "td:first-child").text.strip()
            except Exception:
                pass

        if not current_product_name or current_product_name == "N/A":
            continue

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
            # 클릭 가능한 요소가 나타날 때까지 짧게 대기
            prod_click_target = WebDriverWait(current_p_row, 5).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "td:first-child > a"))
            )
            driver.execute_script(
                "arguments[0].scrollIntoView(true);", prod_click_target)
            time.sleep(0.3)
            driver.execute_script("arguments[0].click();", prod_click_target)
            time.sleep(1)  # 페이지 전환 대기

            details_list = scrape_product_details(
                driver, category_name_text, current_product_name)

            if not details_list:
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
                    product_info.update(detail_item)
                    product_data_collected.append(product_info)

            # 세부 정보 확인 후 다시 상품 목록으로 돌아감
            driver.execute_script("history.go(-1)")
            time.sleep(2)  # 페이지 로드 대기

        except StaleElementReferenceException:
            print(
                f"    상품명 '{current_product_name}' 클릭 요소가 Stale 상태입니다. 해당 상품 건너뜁니다.")
            product_data_collected.append({
                '보험명': f"{category_name_text} - {current_product_name}",
                '판매기간': 'N/A (요소 Stale 오류)',
                '약관_링크': 'N/A', '상품요약서_링크': 'N/A', '사업방법서_링크': 'N/A'
            })
        except Exception as e_prod_click:
            print(
                f"    상품명 '{current_product_name}' 클릭 또는 상세 정보 처리 오류: {e_prod_click}.")
            product_data_collected.append({
                '보험명': f"{category_name_text} - {current_product_name}",
                '판매기간': 'N/A (클릭/상세 오류)',
                '약관_링크': 'N/A', '상품요약서_링크': 'N/A', '사업방법서_링크': 'N/A'
            })


def process_product_category(driver, base_url_or_current, category_list_selector, cat_idx, product_data_collected, is_discontinued_tab=False):
    """특정 상품 카테고리를 처리하는 함수. is_discontinued_tab 플래그 추가"""
    category_name_text = f"알 수 없는 상품구분 (인덱스 {cat_idx})"
    try:
        # 판매중지 탭이 아닌 경우에만 base_url로 이동
        if not is_discontinued_tab:
            driver.get(base_url_or_current)
            time.sleep(1)  # 페이지 로드 대기

        # 카테고리 목록이 나타날 때까지 대기
        WebDriverWait(driver, 20).until(EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, category_list_selector)))

        # 카테고리 요소 목록을 다시 가져옴 (StaleElementReferenceException 방지)
        category_elements = driver.find_elements(
            By.CSS_SELECTOR, category_list_selector)
        if cat_idx >= len(category_elements):
            print(f"    상품구분 인덱스 {cat_idx}가 현재 페이지의 카테고리 목록에 없습니다. 건너뜁니다.")
            return False

        cat_link_text_xpath = f"(//tbody[@id='List1']/tr)[{cat_idx + 1}]/td/a"
        cat_text_only_xpath = f"(//tbody[@id='List1']/tr)[{cat_idx + 1}]/td[1]"

        try:
            cat_name_element_for_text = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, cat_link_text_xpath)))
            category_name_text = cat_name_element_for_text.text.strip()
        except TimeoutException:  # a 태그가 없는 경우 td에서 텍스트 가져오기 시도
            try:
                cat_name_element_for_text = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, cat_text_only_xpath)))
                category_name_text = cat_name_element_for_text.text.strip()
            except TimeoutException:
                print(f"    상품구분 인덱스 {cat_idx}의 이름 가져오기 실패. 건너뜠습니다.")
                return False

        print(f"\n상품구분 '{category_name_text}' 처리 중...")
        element_to_click_xpath = cat_link_text_xpath

        try:
            # 클릭 가능한 요소가 나타날 때까지 대기
            element_to_click = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, element_to_click_xpath)))
            driver.execute_script(
                "arguments[0].scrollIntoView(true);", element_to_click)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", element_to_click)
            time.sleep(2)  # 페이지 전환 대기

            scrape_product_list_for_category(
                driver, category_name_text, product_data_collected)
            return True
        except TimeoutException:
            print(
                f"    상품구분 '{category_name_text}'에 대한 클릭 가능한 링크(a태그)를 찾지 못했습니다.")
            return False
        except StaleElementReferenceException:
            print(
                f"    상품구분 '{category_name_text}' 클릭 요소가 Stale 상태입니다. 해당 카테고리 건너뜠습니다.")
            return False
    except Exception as e_cat_setup:
        print(
            f"    상품구분 '{category_name_text}' (인덱스 {cat_idx}) 처리 중 오류: {e_cat_setup}")
        return False


def get_hanwhalife_product_info_selenium():
    service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()

    options.add_experimental_option("prefs", {
        "download.default_directory": HANWHA_DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True
    })

    # CDP 로깅을 활성화합니다.
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    driver = webdriver.Chrome(service=service, options=options)
    driver.maximize_window()

    base_url = "https://www.hanwhalife.com/main/disclosure/goods/disclosurenotice/DF_GDDN000_P10000.do?MENU_ID1=DF_GDGL000"
    product_data_collected = []

    # CDP 이벤트를 저장할 리스트를 초기화합니다.
    global captured_download_chk_requests
    captured_download_chk_requests = []

    print("한화생명 스크래핑 시작...")
    try:
        print("판매상품 정보 수집 중...")
        driver.get(base_url)

        # Network 도메인 활성화
        driver.execute_cdp_cmd('Network.enable', {})

        category_list_selector = "tbody#List1 tr"
        WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, category_list_selector)))
        num_categories = len(driver.find_elements(
            By.CSS_SELECTOR, category_list_selector))
        for cat_idx in range(num_categories):
            # base_url로 다시 로드하여 페이지 상태 초기화
            process_product_category(driver, base_url,
                                     category_list_selector, cat_idx, product_data_collected, is_discontinued_tab=False)
        print("판매상품 정보 수집 완료.")

        print("판매중지 상품 정보 수집 중...")
        try:
            driver.get(base_url)  # 판매중지 탭 클릭을 위해 base_url로 다시 이동
            time.sleep(1)
            sel2_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a#sel2"))
            )
            driver.execute_script("arguments[0].click();", sel2_button)
            time.sleep(2)
        except TimeoutException:
            print("판매중지상품 탭(a#sel2)을 찾거나 클릭할 수 없습니다.")
            raise
        except StaleElementReferenceException:
            print("판매중지상품 탭(a#sel2) 요소가 Stale 상태입니다. 재시도 필요.")
            raise

        try:
            discontinued_trigger_button_selector = "ul#menu2 > li:nth-child(2) > button"
            discontinued_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, discontinued_trigger_button_selector))
            )
            driver.execute_script("arguments[0].click();", discontinued_button)
            time.sleep(3)  # 데이터 로드 대기

            WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, category_list_selector)))
            num_discontinued_categories = len(driver.find_elements(
                By.CSS_SELECTOR, category_list_selector))

            for cat_idx in range(num_discontinued_categories):
                # 판매중지 탭에서는 현재 URL을 유지
                process_product_category(driver, driver.current_url,
                                         category_list_selector, cat_idx, product_data_collected, is_discontinued_tab=True)
            print("판매중지 상품 정보 수집 완료.")
        except TimeoutException:
            print("판매중지 상품 목록 로드 버튼을 찾거나 클릭할 수 없습니다.")
        except StaleElementReferenceException:
            print("판매중지 상품 목록 로드 버튼 요소가 Stale 상태입니다.")
        except Exception as e_discontinued_setup:
            print(f"판매중지 상품 설정 중 오류: {e_discontinued_setup}")

    except Exception as e:
        print(f"전체 스크래핑 과정 중 오류 발생: {e}")
    finally:
        # 모든 스크래핑이 끝난 후, 최종적으로 수집된 'download_chk.asp' 요청들을 요약하여 출력
        if captured_download_chk_requests:
            print("\n--- Summary of All Captured 'download_chk.asp' Network Requests ---")
            for i, req in enumerate(captured_download_chk_requests):
                print(f"\nOverall Captured Request {i + 1}:")
                print(f"  URL: {req.get('url')}")
                print(f"  Method: {req.get('method')}")
                print(f"  Request Payload: {req.get('requestPayload')}")
                print("-" * 60)
        else:
            print("\n전체 스크래핑 과정에서 'download_chk.asp' 네트워크 요청이 감지되지 않았습니다.")

        if 'driver' in locals() and driver:
            driver.quit()
        print("한화생명 스크래핑 완료.")
    return product_data_collected


def is_valid_hanwha_link(link_str):
    if not link_str or not isinstance(link_str, str) or not link_str.strip():
        return False

    invalid_markers = ["N/A", "(추출 실패)", "(링크 요소 없음)", "(Extractor 비활성)", "(링크/버튼 없음)", "(href 없음)",
                       "(추출 오류)", "(다운로드 실패)", "(요소 Stale)", "(다운로드 실패 또는 파일 없음)",
                       "(URL 생성 실패)", "(페이로드에서 file_name 추출 실패)"]  # 새로운 마커 추가
    for marker in invalid_markers:
        if marker in link_str:
            return False

    if link_str.strip().lower().startswith("javascript:"):
        return False

    # 이제 로컬 파일 경로가 아닌 HTTP/HTTPS 링크를 확인합니다.
    if link_str.startswith("http://") or link_str.startswith("https://"):
        return True

    return False


if __name__ == "__main__":
    collected_data = get_hanwhalife_product_info_selenium()

    if collected_data:
        if DatabaseManager:
            print("DB 저장 진행중...")
            structured_rows_to_save = []
            scraped_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            company_name = "한화생명"

            for item in collected_data:
                full_product_name = item.get('보험명', 'N/A')
                product_name_val = full_product_name.split(
                    ' - ')[-1] if ' - ' in full_product_name else full_product_name

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
                        has_valid_link_for_this_product = True
                        current_product_docs.append([
                            company_name, product_name_val, product_code_val,
                            doc_type, sales_period_val, scraped_time, link_url
                        ])

                if has_valid_link_for_this_product:
                    structured_rows_to_save.extend(current_product_docs)

            if structured_rows_to_save:
                with DatabaseManager(db_name="hanwhalife_web_data.db") as db_manager:
                    saved_count = db_manager.save_data(structured_rows_to_save)
                print(f"DB 저장 완료. 총 {saved_count}건 문서 정보 저장.")
            else:
                print("DB에 저장할 유효한 문서 정보가 없습니다.")
            print(f"총 스크래핑된 상품 항목(버전 포함) 수: {len(collected_data)}개")
        else:
            print("DatabaseManager 사용 불가. DB 저장 기능을 건너뜁니다.")
    else:
        print("스크래핑된 상품 데이터가 없습니다.")
