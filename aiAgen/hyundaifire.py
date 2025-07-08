# 현대해상
from seleniumwire import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException, StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager
import time
import os
import sys
import re  # 정규표현식 사용을 위해 import
from datetime import datetime

# 프로젝트 루트 경로를 sys.path에 추가하여 모듈 임포트 가능하게 함
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# DB_save 모듈 임포트 시도 (선택 사항)
try:
    from neoali.DB_save import DatabaseManager
except ImportError as e:
    DatabaseManager = None
    print(f"경고: DB_save.py 모듈 임포트 실패 ({e}). 데이터베이스 저장은 비활성화됩니다.")


def _prepare_data_for_db(product_data_list, company_name="현대해상"):
    """
    크롤링된 상품 데이터를 DatabaseManager의 save_data 메서드 형식에 맞게 변환합니다.
    링크가 .pdf로 끝나지 않으면 저장하지 않습니다.
    """
    structured_rows = []
    scraped_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for product in product_data_list:
        product_name = product.get("상품명")
        sales_period = product.get("판매기간")

        # 상품 코드는 현재 크롤러에서 추출되지 않으므로 None으로 설정
        product_code = None

        for doc_type_key in ["약관", "사업방법서", "상품요약서"]:
            doc_info = product.get(doc_type_key, {})
            link = doc_info.get("link")

            # 유효한 링크 (N/A가 아닌)이며, .pdf로 끝나는 링크만 DB 저장 리스트에 추가
            if (product_name and sales_period and link and link != "N/A" and link.lower().endswith('.pdf')):
                structured_rows.append((
                    company_name,
                    product_name,
                    product_code,
                    doc_type_key,
                    sales_period,
                    scraped_at,
                    link
                ))
            else:
                if link and not link.lower().endswith('.pdf'):
                    print(f"  [DB 저장 제외] '{product_name}'의 '{doc_type_key}' 링크가 .pdf로 끝나지 않아 저장하지 않습니다: {link}")
                elif link == "N/A":
                    print(f"  [DB 저장 제외] '{product_name}'의 '{doc_type_key}' 링크가 'N/A'이므로 저장하지 않습니다.")
                else:
                    print(f"  [DB 저장 제외] '{product_name}'의 '{doc_type_key}'에 유효한 정보가 없어 저장하지 않습니다.")
    return structured_rows


def wait_for_loading_to_finish(driver_instance):
    """
    현대해상 웹사이트의 로딩 스피너 (divCommonLoadingArea)가 사라질 때까지 기다립니다.
    (display: none 상태가 되는 것을 기다림)
    """
    try:
        # divCommonLoadingArea가 DOM에 존재하며, 'display: none' 상태가 될 때까지 기다립니다.
        WebDriverWait(driver_instance, 15).until(
            EC.invisibility_of_element_located((By.ID, "divCommonLoadingArea"))
        )
        print("로딩 오버레이 (divCommonLoadingArea) 사라짐.")
    except TimeoutException:
        print("로딩 오버레이 (divCommonLoadingArea)가 시간 내에 사라지지 않았습니다. 계속 진행합니다.")
    except Exception as e:
        print(f"로딩 오버레이 대기 중 예기치 않은 오류 발생: {e}")


def crawl_all_hi_product_data_optimized(url):
    """
    현대해상 웹사이트의 모든 상품 정보를 순회하여 추출하는 함수.
    상품명, 판매기간, 약관, 사업방법서, 상품요약서 정보를 지정된 형식으로 출력하며,
    상품설명서 정보는 제외합니다. 브라우저 캐시를 비활성화합니다.
    """
    driver = None
    all_product_data = []

    db_manager = None
    if DatabaseManager:
        try:
            db_manager = DatabaseManager(db_name="hyundaifire_web_data.db")
            print("DB_save.py의 DatabaseManager가 성공적으로 초기화되었습니다.")
        except Exception as e:
            print(f"DatabaseManager 초기화 중 오류 발생: {e}")
            db_manager = None  # 초기화 실패 시 DB 저장 기능 비활성화

    try:
        service = Service(ChromeDriverManager().install())
        options = webdriver.ChromeOptions()
        # options.add_argument('--headless') # 헤드리스 모드 (주석 처리하여 브라우저 GUI 확인 가능)
        options.add_argument('--window-size=1920,1080')  # 브라우저 창 크기 설정
        options.add_argument('--disable-gpu')  # 일부 시스템에서 GPU 가속 비활성화

        driver = webdriver.Chrome(service=service, options=options)

        # 캐시 비활성화 인터셉터 설정
        def interceptor(request):
            request.headers['Cache-Control'] = 'no-cache'
            request.headers['Pragma'] = 'no-cache'
            request.headers['Expires'] = '0'

        driver.request_interceptor = interceptor

        print(f"[{url}] 웹페이지에 접속 중...")
        driver.get(url)

        # 초기 필터 섹션 로딩 대기
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CLASS_NAME, "select_step"))
        )
        wait_for_loading_to_finish(driver)  # 로딩 스피너 대기
        print("필터 섹션 로딩 완료.")

        # 판매형태 버튼 정보 추출
        sale_type_buttons_container = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//strong[span='1']//following-sibling::div[contains(@class, 'btn_group')]"))
        )
        sale_type_info_list = []
        for btn in sale_type_buttons_container.find_elements(By.TAG_NAME, "button"):
            sale_type_info_list.append({'text': btn.text, 'id': btn.get_attribute('id')})

        # 보험종류 버튼 정보 추출
        insurance_type_buttons_container = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//strong[span='2']//following-sibling::div[contains(@class, 'btn_group')]"))
        )
        insurance_type_info_list = []
        for btn in insurance_type_buttons_container.find_elements(By.TAG_NAME, "button"):
            insurance_type_info_list.append({'text': btn.text})

        print(f"\n총 {len(sale_type_info_list)}가지 판매형태, {len(insurance_type_info_list)}가지 보험종류를 순회합니다.")

        # 판매형태 순회
        for i_sale, sale_info in enumerate(sale_type_info_list):
            sale_type_text = sale_info['text']
            sale_type_id = sale_info['id']
            print(f"\n--- 판매형태: '{sale_type_text}' 선택 ---")

            # 해당 판매형태 버튼 클릭
            current_sale_type_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.ID, sale_type_id))
            )
            driver.execute_script("arguments[0].click();", current_sale_type_button)
            # 클릭 후 로딩 감지 함수 호출
            wait_for_loading_to_finish(driver)
            print(f"판매형태 '{sale_type_text}' 선택 후 로딩 완료.")

            # 보험종류 순회
            for i_ins, ins_type_info in enumerate(insurance_type_info_list):
                ins_type_text = ins_type_info['text']
                print(f"  --- 보험종류: '{ins_type_text}' 선택 ---")

                # 해당 보험종류 버튼 클릭
                current_insurance_type_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, f"//strong[span='2']//following-sibling::div[contains(@class, 'btn_group')]//button[span='{ins_type_text}']"))
                )
                driver.execute_script("arguments[0].click();", current_insurance_type_button)
                # 클릭 후 로딩 감지 함수 호출
                wait_for_loading_to_finish(driver)
                print(f"보험종류 '{ins_type_text}' 선택 후 로딩 완료.")

                # 보험유형 섹션 (ul_mtInsCat 또는 ul_ltInsCat) 확인 및 순회
                insurance_category_div_ids = ["ul_mtInsCat", "ul_ltInsCat"]
                found_category_info_list = []
                active_category_div_id = None

                for div_id in insurance_category_div_ids:
                    try:
                        category_div = WebDriverWait(driver, 3).until(
                            EC.visibility_of_element_located((By.ID, div_id))
                        )
                        buttons_in_div = category_div.find_elements(By.CSS_SELECTOR, "button.lv3")
                        if category_div.is_displayed() and buttons_in_div:
                            active_category_div_id = div_id
                            for btn in buttons_in_div:
                                found_category_info_list.append({'text': btn.text})
                            break  # 유효한 카테고리 div를 찾으면 더 이상 탐색하지 않음
                    except TimeoutException:
                        continue  # 해당 div가 없으면 다음 div 시도
                    except NoSuchElementException:
                        continue  # 버튼이 없으면 다음 div 시도

                if found_category_info_list:
                    print(f"    --- 보험유형 섹션 '{active_category_div_id}' 존재. 총 {len(found_category_info_list)}가지 유형 순회 ---")
                    for i_cat, category_info in enumerate(found_category_info_list):
                        category_text = category_info['text']
                        print(f"      --- 보험유형: '{category_text}' 선택 ---")

                        # 해당 보험유형 버튼 클릭
                        current_category_button = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, f"//div[@id='{active_category_div_id}']//button[span='{category_text}']"))
                        )
                        driver.execute_script("arguments[0].click();", current_category_button)
                        # 클릭 후 로딩 감지 함수 호출
                        wait_for_loading_to_finish(driver)
                        print(f"보험유형 '{category_text}' 선택 후 로딩 완료.")

                        # 상품명 필터 순회 및 데이터 추출
                        crawl_product_names_and_data_js_click(driver, all_product_data)

                else:
                    print("    --- 보험유형 섹션 없음 또는 버튼 부재. 바로 상품명 필터 순회 ---")
                    # 보험유형 섹션이 없으면 바로 상품명 필터 순회
                    crawl_product_names_and_data_js_click(driver, all_product_data)

    except TimeoutException:
        print("페이지 로딩 시간 초과 또는 초기 필터 요소를 찾지 못했습니다.")
    except WebDriverException as e:
        print(f"WebDriver 오류 발생: {e}")
    except Exception as e:
        print(f"예기치 않은 오류 발생: {e}")
    finally:
        if driver:
            driver.quit()  # 브라우저 종료
            print("\n브라우저 종료.")

        print(f"\n--- 총 {len(all_product_data)}개의 상품 정보 수집 완료 ---")

        # DB 저장
        if db_manager:
            prepared_data = _prepare_data_for_db(all_product_data)
            if prepared_data:
                with db_manager as db:  # with 문을 사용하여 DB 연결 관리
                    saved_count = db.save_data(prepared_data)
                    print(f"총 {saved_count}개의 상품 문서 정보가 DB에 저장되었습니다.")
            else:
                print("DB에 저장할 유효한 상품 문서 정보가 없습니다.")
        else:
            print("DatabaseManager가 초기화되지 않아 DB 저장을 건너뜁니다.")


def crawl_product_names_and_data_js_click(driver_instance, all_product_data_list):
    """
    현재 필터 조합에서 상품명 필터를 순회하며 테이블 데이터를 추출하는 헬퍼 함수 (JavaScript 클릭 사용)
    """
    try:
        # 상품명 필터 버튼 컨테이너 로딩 대기
        product_name_buttons_container = WebDriverWait(driver_instance, 10).until(
            EC.presence_of_element_located((By.ID, "div_goodsList"))
        )

        # 상품명 버튼 정보 추출
        product_name_info_list = []
        for btn in product_name_buttons_container.find_elements(By.TAG_NAME, "button"):
            product_name_info_list.append({'text': btn.text})

        if not product_name_info_list:
            print("        상품명 필터에 상품이 없습니다. 이 조합에서는 데이터 추출 스킵.")
            return

        print(f"      --- 상품명 필터: 총 {len(product_name_info_list)}가지 상품명 순회 ---")

        # 상품명 순회
        for i_prod, prod_info in enumerate(product_name_info_list):
            product_name_text = prod_info['text']
            print(f"        --- 상품명: '{product_name_text}' 선택 ---")

            # 해당 상품명 버튼 클릭
            current_product_name_button = WebDriverWait(driver_instance, 5).until(
                EC.element_to_be_clickable((By.XPATH, f"//div[@id='div_goodsList']//button[span='{product_name_text}']"))
            )
            driver_instance.execute_script("arguments[0].click();", current_product_name_button)
            # 클릭 후 로딩 감지 함수 호출
            wait_for_loading_to_finish(driver_instance)
            print(f"상품명 '{product_name_text}' 선택 후 로딩 완료.")

            # 테이블 데이터 추출 및 전체 리스트에 추가
            extracted_data = extract_table_data(driver_instance)
            all_product_data_list.extend(extracted_data)

    except TimeoutException:
        print("      상품명 필터 섹션 또는 버튼을 찾을 수 없습니다. 이 조합에서는 데이터 추출 스킵.")
    except NoSuchElementException:
        print("      상품명 필터 섹션은 찾았으나 버튼이 없습니다. 이 조합에서는 데이터 추출 스킵.")
    except Exception as e:
        print(f"      상품명 필터 순회 중 예기치 않은 오류 발생: {e}")


def extract_table_data(driver_instance):
    """
    현재 페이지에 보이는 테이블에서 상품 데이터를 추출하는 헬퍼 함수.
    각 상품 행(<tr>)을 처리할 때마다 상품 정보를 즉시 출력합니다.
    PDF 링크를 클릭하여 실제 URL을 가져오고 새 탭을 닫습니다.
    onclick 속성 유무를 확인하여 클릭 여부를 결정합니다. 상품설명서는 제외합니다.
    """
    local_product_data = []
    try:
        # 테이블 로딩 대기
        WebDriverWait(driver_instance, 10).until(
            EC.presence_of_element_located((By.ID, "tbd_prodList"))
        )
        wait_for_loading_to_finish(driver_instance)  # 로딩 스피너 대기

        table = driver_instance.find_element(By.CLASS_NAME, "tbl_data")
        rows = table.find_elements(By.CSS_SELECTOR, "#tbd_prodList tr")

        # 현재(원본) 창 핸들 저장
        original_window = driver_instance.current_window_handle

        for idx, row in enumerate(rows):
            try:
                cols = row.find_elements(By.TAG_NAME, "td")
                if not cols:
                    continue  # td 요소가 없으면 다음 행으로

                # 상품 기본 정보 추출
                product_name = cols[0].text
                start_date = cols[1].text
                end_date = cols[2].text

                sale_period = f"{start_date} ~ {end_date}" if end_date else f"{start_date} ~ (판매중)"

                doc_info = {
                    "약관": {"text": "", "link": ""},
                    "사업방법서": {"text": "", "link": ""},
                    "상품요약서": {"text": "", "link": ""},
                }

                # PDF 문서 링크 처리 헬퍼 함수 (중요: 새 탭 안정화 로직 포함)
                def process_doc_link(col_index, doc_type_key):
                    # 기본값은 "N/A"
                    pdf_extracted_link = "N/A"
                    new_window_handle = None
                    link_elem = None

                    try:
                        link_elem = cols[col_index].find_element(By.TAG_NAME, "a")
                        link_title = link_elem.get_attribute("title")
                        link_onclick = link_elem.get_attribute("onclick")
                        is_disabled = "disabled" in link_elem.get_attribute("class")

                        doc_info[doc_type_key]["text"] = link_title if not is_disabled else "링크 없음 (Disabled)"

                        # 링크가 유효하고 onclick 속성이 있는 경우에만 처리
                        if not is_disabled and link_onclick and link_onclick.strip() != "" and "javascript:void(0)" in link_elem.get_attribute("href"):

                            print(f"    └─ [{doc_type_key}] 링크 클릭 전 브라우저 캐시 및 저장소 초기화 시도...")
                            driver_instance.execute_script("window.localStorage.clear();")
                            driver_instance.execute_script("window.sessionStorage.clear();")
                            driver_instance.execute_script(
                                "if (caches) { caches.keys().then(names => { for (let name of names) { caches.delete(name); console.log('Cache ' + name + ' deleted.'); } }); }")
                            print(f"    └─ [{doc_type_key}] 브라우저 캐시 및 저장소 초기화 완료.")

                            driver_instance.requests.clear()
                            print(f"    └─ [{doc_type_key}] 클릭 전 seleniumwire 요청 목록 초기화 완료.")

                            current_window_handles_before_click = driver_instance.window_handles
                            print(f"    └─ [{doc_type_key}] 클릭 전 탭 수: {len(current_window_handles_before_click)}")

                            # JavaScript 클릭 시도
                            driver_instance.execute_script("arguments[0].click();", link_elem)
                            print(f"    └─ [{doc_type_key}] 링크 JavaScript 클릭 실행.")

                            try:
                                # 새 창이 열릴 때까지 기다림
                                WebDriverWait(driver_instance, 15).until(
                                    EC.number_of_windows_to_be(len(current_window_handles_before_click) + 1)
                                )
                                # 열린 모든 창 핸들 중 원래 창이 아닌 새 핸들을 찾음
                                new_window_handles = [handle for handle in driver_instance.window_handles if handle != original_window]
                                if new_window_handles:
                                    new_window_handle = new_window_handles[0]

                                    if new_window_handle in driver_instance.window_handles:
                                        driver_instance.switch_to.window(new_window_handle)
                                        print(f"    └─ [{doc_type_key}] 새 탭 '{new_window_handle}'으로 전환 완료.")

                                        pdf_url_pattern = re.compile(r'.*\.pdf$', re.IGNORECASE)
                                        print(f"    └─ [{doc_type_key}] 새 탭의 URL이 '.pdf'로 끝날 때까지 대기 시작 (최대 20초).")

                                        try:
                                            # 현재 URL이 PDF 패턴과 일치하고 'about:blank'가 아닌 경우를 기다림
                                            WebDriverWait(driver_instance, 20).until(
                                                lambda driver: pdf_url_pattern.match(driver.current_url) and driver.current_url != "about:blank"
                                            )
                                            # 성공적으로 PDF URL을 찾으면 할당
                                            pdf_extracted_link = driver_instance.current_url
                                            print(f"    └─ [{doc_type_key}] PDF 링크 추출 성공 (새 탭 URL 확인): {pdf_extracted_link}")
                                        except TimeoutException:
                                            # 타임아웃 발생 시 N/A 유지
                                            print(f"      → [{doc_type_key}] 새 탭 URL이 '.pdf'로 끝나지 않거나 타임아웃 발생. N/A로 처리.")
                                            print(f"      → 현재 새 탭 URL: {driver_instance.current_url}")
                                        except Exception as url_check_e:
                                            # URL 확인 중 예외 발생 시 N/A 유지
                                            print(f"      → [{doc_type_key}] URL 확인 중 예기치 않은 오류 발생. N/A로 처리: {url_check_e}")

                                    else:
                                        # 새 창 핸들이 유효하지 않으면 N/A 유지
                                        print(f"      → [{doc_type_key}] 새 창 핸들이 유효하지 않습니다. N/A로 처리.")
                                else:
                                    # 새 창이 열렸으나 핸들을 찾을 수 없으면 N/A 유지
                                    print(f"      → [{doc_type_key}] 새 창이 열렸으나 핸들을 찾을 수 없음. N/A로 처리.")

                            except TimeoutException as e:
                                # 새 창 열기 타임아웃 발생 시 N/A 유지
                                print(f"Error: 새 창 열기 타임아웃 발생 for {doc_type_key}. N/A로 처리: {e}")
                            except Exception as general_e:
                                # 링크 클릭 후 예기치 않은 오류 발생 시 N/A 유지
                                print(f"Error: 링크 클릭 후 예기치 않은 오류 발생 for {doc_type_key}. N/A로 처리: {general_e}")
                        else:
                            # 링크가 비활성화되거나 onclick 속성이 없으면 N/A 유지 (기본값)
                            if is_disabled:
                                print(f"    └─ [{doc_type_key}] 링크가 비활성화되어 N/A 처리됩니다.")
                            elif not link_onclick:
                                print(f"    └─ [{doc_type_key}] 링크에 onclick 속성이 없어 N/A 처리됩니다.")

                    except NoSuchElementException:
                        doc_info[doc_type_key]["text"] = "링크 없음"
                        # 링크 요소를 찾을 수 없으면 N/A 유지
                        print(f"Error: [{doc_type_key}] 링크 요소를 찾을 수 없습니다. N/A로 처리.")
                    except Exception as e:
                        # 일반 오류 발생 시 N/A 유지
                        print(f"Error: [{doc_type_key}] 링크 처리 중 일반 오류 발생. N/A로 처리: {e}")
                    finally:
                        # 새 창이 열렸었고 (new_window_handle이 None이 아니고),
                        # 현재 드라이버의 활성 창이 그 새 창이라면 닫고 원래 탭으로 전환
                        if new_window_handle and driver_instance.current_window_handle == new_window_handle:
                            try:
                                driver_instance.close()  # 새 창 닫기
                                # 현재 탭의 개수가 1개(원본 탭만 남을 때)가 될 때까지 기다립니다.
                                WebDriverWait(driver_instance, 10).until(
                                    EC.number_of_windows_to_be(1)
                                )
                                if original_window in driver_instance.window_handles:
                                    driver_instance.switch_to.window(original_window)  # 원래 창으로 전환
                                    print(f"    └─ [{doc_type_key}] 새 탭 닫고 원래 탭으로 전환 완료.")
                                else:
                                    print(f"Warning: [{doc_type_key}] 원래 창 핸들이 유효하지 않아 전환 실패. 모든 탭 확인 후 복귀 시도.")
                                    # 이 경우, 모든 탭을 확인하여 원래 탭을 찾아 다시 전환 시도
                                    for handle in driver_instance.window_handles:
                                        if handle == original_window:
                                            driver_instance.switch_to.window(original_window)
                                            print(f"    └─ [{doc_type_key}] 원래 탭으로 성공적으로 재전환 완료.")
                                            break
                            except WebDriverException as close_e:
                                print(f"Warning: 새 탭 닫기/원래 탭 전환 중 WebDriver 오류: {close_e}")
                            except Exception as close_e:
                                print(f"Warning: 새 탭 닫기/원래 탭 전환 중 예기치 않은 오류: {close_e}")
                        # 새 창 핸들이 존재하지만 현재 활성화된 창이 new_window_handle이 아니고 original_window도 아닐 때
                        # (즉, 탭이 3개 이상 열린 비정상적인 상황에 대한 비상 처리)
                        elif driver_instance.current_window_handle != original_window:
                            print(f"Warning: 비정상적인 탭 상태 감지. "
                                  f"현재 탭: {driver_instance.current_window_handle}, "
                                  f"원래 탭: {original_window}. 모든 비정상 탭 정리 시도.")
                            try:
                                # 원래 창을 제외한 모든 탭을 강제로 닫기 시도
                                for handle in driver_instance.window_handles:
                                    if handle != original_window:
                                        print(f"    └─ 비정상 탭 ({handle}) 닫기 시도.")
                                        driver_instance.switch_to.window(handle)
                                        driver_instance.close()
                                        time.sleep(0.1)  # 짧게 대기하여 브라우저가 탭을 처리할 시간 부여
                                # 마지막으로 원래 탭으로 복귀
                                if original_window in driver_instance.window_handles:
                                    driver_instance.switch_to.window(original_window)
                                    print("    └─ 비정상적인 탭 모두 닫고 원래 탭으로 복귀 완료.")
                                else:
                                    print("Warning: 비정상적인 탭 정리 후 원래 창 핸들이 유효하지 않아 복귀 실패.")
                            except Exception as clean_e:
                                print(f"Error: 비정상적인 탭 정리 중 오류 발생: {clean_e}")
                        elif new_window_handle is None:  # 새 창이 아예 열리지 않은 경우
                            print(f"    └─ [{doc_type_key}] 새 탭이 열리지 않았습니다. 원래 탭 유지.")
                    doc_info[doc_type_key]["link"] = pdf_extracted_link

                # 문서 유형별 링크 처리 호출 (상품설명서 제외)
                process_doc_link(4, "약관")
                process_doc_link(5, "사업방법서")
                process_doc_link(6, "상품요약서")

                # 추출된 상품 정보를 리스트에 추가
                current_product_data = {
                    "상품명": product_name,
                    "판매기간": sale_period,
                    "약관": doc_info["약관"],
                    "사업방법서": doc_info["사업방법서"],
                    "상품요약서": doc_info["상품요약서"],
                }
                local_product_data.append(current_product_data)

                print("\n--- 상품 정보 추출 완료 ---")
                print(f"상품명: {current_product_data['상품명']}")
                print(f"판매기간: {current_product_data['판매기간']}")
                print(f"약관: {current_product_data['약관']['link']}")
                print(f"사업방법서: {current_product_data['사업방법서']['link']}")
                print(f"상품요약서: {current_product_data['상품요약서']['link']}")
                print("-" * 40)

            except StaleElementReferenceException:
                print(f"경고: StaleElementReferenceException 발생. 행 {idx + 1} 스킵.")
                # StaleElementReferenceException 발생 시 해당 행은 스킵하고 다음 행 처리
                continue
            except Exception as e:
                print(f"개별 상품 행 처리 중 예기치 않은 오류 발생 (행 {idx + 1}): {e}")
                continue

        print(f"  현재 필터 조합에서 {len(local_product_data)}개의 상품 추출 완료.")
        return local_product_data

    except TimeoutException:
        print("  테이블 로딩 시간 초과! 현재 필터 조합에 대한 데이터를 가져올 수 없습니다.")
        return []
    except NoSuchElementException:
        print("  테이블 또는 테이블 내부 요소를 찾을 수 없습니다. 현재 필터 조합에 대한 데이터가 없거나 HTML 구조가 변경되었을 수 있습니다.")
        return []
    except Exception as e:
        print(f"  테이블 데이터 추출 중 예기치 않은 오류 발생: {e}")
        return []


# 크롤링할 웹사이트 URL 설정
target_url = "https://www.hi.co.kr/serviceAction.do?menuId=100932"

# 크롤링 함수 호출
if __name__ == "__main__":
    all_collected_data = crawl_all_hi_product_data_optimized(target_url)

    # 수집된 모든 데이터 출력 (선택 사항)
    # for data in all_collected_data:
    #     print(data)
