# kdb생명  href 값만 가져오기
import json
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException, ElementClickInterceptedException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from seleniumwire import webdriver  # seleniumwire 사용 시
# from selenium import webdriver # 일반 selenium 사용 시
from webdriver_manager.chrome import ChromeDriverManager
import time
import re


def setup_driver():
    """Chrome WebDriver 인스턴스를 설정하고 반환합니다."""
    chrome_options = Options()
    # 개발 중에는 --headless를 주석 처리하여 브라우저 동작을 직접 확인하는 것을 강력히 권장합니다.
    # chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev_shm_usage")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--start-maximized")

    # ChromeDriverManager().install()은 최신 크롬 드라이버를 자동으로 다운로드 및 관리합니다.
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    return driver


def handle_ie_compatibility_popup(driver):
    """
    익스플로러(IE) 환경 호환성 오류 안내 팝업을 닫고, 딤드 레이어가 사라질 때까지 기다립니다.
    """
    print("팝업창을 찾아서 닫으려고 시도합니다...")

    try:
        popup_wrapper = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "infopop_wrap"))
        )
        print("팝업창이 나타났음을 확인했습니다.")

        close_button = WebDriverWait(popup_wrapper, 10).until(
            EC.element_to_be_clickable((By.XPATH, ".//button[@class='btn-close' and @title='확인창 닫기']"))
        )

        try:
            close_button.click()
            print("팝업창의 '확인창 닫기' 버튼을 클릭했습니다.")
        except Exception as e:
            print(f"일반 클릭 실패, JavaScript 클릭 시도: {e}")
            driver.execute_script("arguments[0].click();", close_button)
            print("팝업창의 '확인창 닫기' 버튼을 JavaScript로 클릭했습니다.")

        WebDriverWait(driver, 10).until(
            EC.invisibility_of_element_located((By.CLASS_NAME, "ly-pop-dim"))
        )
        WebDriverWait(driver, 10).until(
            EC.invisibility_of_element_located((By.ID, "infopop_wrap"))
        )
        print("팝업창과 딤드 레이어가 성공적으로 사라졌습니다.")
        time.sleep(1)  # 추가적인 안정화를 위한 대기

    except TimeoutException:
        print("팝업창 또는 '확인창 닫기' 버튼을 시간 내에 찾지 못했거나, 팝업이 나타나지 않았습니다. (팝업이 나타나지 않았거나 다른 형태일 수 있음)")
    except NoSuchElementException:
        print("지정된 XPath의 팝업 닫기 버튼을 찾을 수 없습니다. (HTML 구조가 변경되었을 수 있음)")
    except Exception as e:
        print(f"팝업 처리 중 예상치 못한 오류 발생: {e}")


def extract_table_data(driver, panel_id):
    """
    주어진 패널 ID 내에서 테이블 데이터를 추출합니다.
    <th>를 파싱하여 동적으로 열 인덱스를 파악하고 데이터를 가져옵니다.
    rowspan이 적용된 셀을 처리합니다. '상품유형' 정보는 제외합니다.
    약관, 사업방법서, 상품요약서 링크가 HTML 팝업인 경우 팝업 내부로 진입하여 최종 문서(PDF 등) 링크를 찾아냅니다.
    '기타' 약관 정보는 새로운 상품으로 추가하지 않습니다.
    """
    print(f"패널 '{panel_id}'에서 테이블 데이터 추출 시도 중...")
    extracted_rows = []

    max_retries = 3

    for attempt in range(max_retries):
        try:
            match = re.search(r'tab-panel(\d+)', panel_id)
            if not match:
                print(f"오류: 패널 ID '{panel_id}'에서 테이블 ID를 추출할 수 없습니다.")
                return []
            tab_number = match.group(1)

            # 1. 패널 요소가 활성화(active)되고 가시적으로 될 때까지 기다립니다.
            panel_element = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.ID, panel_id))
            )

            WebDriverWait(driver, 10).until(
                lambda driver: 'active' in driver.find_element(By.ID, panel_id).get_attribute('class')
            )
            print(f"패널 '{panel_id}' 활성화 확인.")

            # 2. 패널 내부에서 `<table>` 요소를 정확한 XPath로 찾습니다.
            table_element = WebDriverWait(panel_element, 10).until(
                EC.presence_of_element_located((By.XPATH, "./div[@class='sec']/div[@class='basic-table-1']/table"))
            )
            print(f"패널 '{panel_id}' 내에서 테이블 요소를 찾았습니다.")

            # 3. thead와 그 안의 th 요소들이 로드되고 가시적으로 될 때까지 기다립니다.
            header_elements = WebDriverWait(table_element, 10).until(
                EC.visibility_of_all_elements_located((By.XPATH, "./thead/tr/th"))
            )

            if not header_elements:
                print(f"경고: 테이블 헤더(th)를 찾지 못했습니다. (시도 {attempt + 1}/{max_retries})")
                time.sleep(2)
                continue

            # 4. 열 인덱스 매핑 (<td> 인덱스를 기반으로 합니다)
            col_indices = {}
            current_td_idx_counter = 0

            found_headers_text = []
            for th_elem in header_elements:
                header_text = th_elem.text.replace('\n', ' ').strip()
                found_headers_text.append(th_elem.text.strip())
                colspan = int(th_elem.get_attribute("colspan") or 1)

                if header_text == "상품명":
                    col_indices["상품명"] = current_td_idx_counter + 1
                    current_td_idx_counter += colspan
                elif header_text == "보험료설계 (상품설명)":
                    col_indices["보험료설계_link"] = current_td_idx_counter
                    current_td_idx_counter += colspan
                elif header_text == "판매기간":
                    col_indices["판매기간"] = current_td_idx_counter
                    current_td_idx_counter += colspan
                elif header_text == "약관":
                    col_indices["약관"] = current_td_idx_counter
                    current_td_idx_counter += colspan
                elif header_text == "사업방법서":
                    col_indices["사업방법서"] = current_td_idx_counter
                    current_td_idx_counter += colspan
                elif header_text == "상품요약서":
                    col_indices["상품요약서"] = current_td_idx_counter
                    current_td_idx_counter += colspan
                else:
                    current_td_idx_counter += colspan

            print(f"테이블 헤더: {found_headers_text}")
            print(f"매핑된 열 인덱스 (상품유형 제외): {col_indices}")

            # '상품유형'을 제외한 필수 열만 확인
            required_cols = ["상품명", "판매기간", "약관", "사업방법서", "상품요약서"]
            if not all(col in col_indices for col in required_cols):
                print(f"경고: 필수 열 중 일부를 찾을 수 없습니다: {required_cols}. (시도 {attempt + 1}/{max_retries})")
                time.sleep(2)
                continue

            # 5. 이제 `<tbody>`를 찾습니다. `table_grid_X`는 `<tbody>`의 ID입니다.
            tbody_id = f"table_grid_{tab_number}"
            tbody_element = WebDriverWait(table_element, 10).until(
                EC.presence_of_element_located((By.ID, tbody_id))
            )
            print(f"패널 '{panel_id}' 내에서 tbody '{tbody_id}'를 찾았습니다.")

            # 6. tbody 내에 `<tr>` (테이블 행) 요소가 최소한 하나 존재할 때까지 기다립니다.
            rows = WebDriverWait(tbody_element, 20).until(
                EC.presence_of_all_elements_located((By.TAG_NAME, "tr"))
            )

            if not rows:
                print(f"정보: '{panel_id}' 패널의 tbody에 데이터 행(tr)이 없습니다.")
                return []

            print(f"총 {len(rows)}개의 행(tr) 중 데이터 추출 시작.")

            # --- rowspan 처리를 위한 변수 초기화 ---
            rowspan_tracker = {}

            # 7. 각 행을 순회하며 데이터 추출
            for i, row in enumerate(rows):
                current_row_data = {}
                td_elements_in_row = row.find_elements(By.TAG_NAME, "td")

                # 이전 행에서 처리된 rowspan 값 업데이트
                for col_idx in sorted(list(rowspan_tracker.keys())):
                    if rowspan_tracker[col_idx]['rowspan_count'] > 0:
                        rowspan_tracker[col_idx]['rowspan_count'] -= 1
                    else:
                        del rowspan_tracker[col_idx]

                # 현재 행의 전체 셀 데이터를 임시로 저장할 리스트
                # rowspan으로 인해 현재 DOM에 없는 셀도 고려하여 TH 개수만큼 초기화
                full_row_data_temp = [None] * current_td_idx_counter

                # rowspan이 남아있는 셀의 값 채워넣기
                for tracked_col_idx, info in rowspan_tracker.items():
                    if tracked_col_idx < len(full_row_data_temp):  # 인덱스 범위 확인
                        full_row_data_temp[tracked_col_idx] = info['value']

                # 현재 DOM에 있는 td 요소들을 full_row_data_temp에 채워넣기
                current_temp_fill_idx = 0
                for cell_in_dom in td_elements_in_row:
                    while current_temp_fill_idx < len(full_row_data_temp) and full_row_data_temp[current_temp_fill_idx] is not None:
                        current_temp_fill_idx += 1

                    if current_temp_fill_idx >= len(full_row_data_temp):
                        break

                    rowspan_val = int(cell_in_dom.get_attribute("rowspan") or 1)
                    if rowspan_val > 1:
                        rowspan_tracker[current_temp_fill_idx] = {
                            'value': cell_in_dom.text.strip(),
                            'rowspan_count': rowspan_val - 1
                        }

                    full_row_data_temp[current_temp_fill_idx] = cell_in_dom

                    current_temp_fill_idx += 1

                # 상품명과 판매기간 추출 (rowspan 처리된 값 또는 현재 셀 값)
                if "상품명" in col_indices and col_indices["상품명"] < len(full_row_data_temp) and full_row_data_temp[col_indices["상품명"]] is not None:
                    # full_row_data_temp[col_indices["상품명"]]이 문자열(rowspan 처리된 값)이거나 WebElement일 수 있음
                    if isinstance(full_row_data_temp[col_indices["상품명"]], str):
                        current_row_data["상품명"] = full_row_data_temp[col_indices["상품명"]]
                    else:  # WebElement인 경우
                        current_row_data["상품명"] = full_row_data_temp[col_indices["상품명"]].text.strip()
                else:
                    current_row_data["상품명"] = ""

                if "판매기간" in col_indices and col_indices["판매기간"] < len(full_row_data_temp) and full_row_data_temp[col_indices["판매기간"]] is not None:
                    if isinstance(full_row_data_temp[col_indices["판매기간"]], str):
                        current_row_data["판매기간"] = full_row_data_temp[col_indices["판매기간"]]
                    else:  # WebElement인 경우
                        current_row_data["판매기간"] = full_row_data_temp[col_indices["판매기간"]].text.strip()
                else:
                    current_row_data["판매기간"] = ""

                base_url = "https://www.kdblife.co.kr"
                additional_rows_from_popup = []

                for col_name in ["약관", "사업방법서", "상품요약서"]:
                    idx = col_indices.get(col_name)
                    # 해당 컬럼 인덱스가 유효하고, 해당 위치에 td 요소가 있을 경우에만 처리
                    if idx is not None and idx < len(full_row_data_temp) and full_row_data_temp[idx] is not None:
                        link_element_or_text = full_row_data_temp[idx]

                        link_element = None
                        extracted_url = ""

                        if isinstance(link_element_or_text, str):  # rowspan으로 채워진 경우
                            extracted_url = link_element_or_text  # 이 경우 링크가 아니라 텍스트일 가능성 있음
                            current_row_data[col_name] = extracted_url  # 일단 텍스트로 저장

                        else:  # WebElement인 경우 링크 추출 시도
                            try:
                                # <a> 태그가 존재할 때까지 짧게 기다림 (없으면 TimeoutException)
                                link_element = WebDriverWait(link_element_or_text, 0.5).until(
                                    EC.presence_of_element_located((By.TAG_NAME, "a"))
                                )

                                raw_href = link_element.get_attribute("href")
                                onclick_attr = link_element.get_attribute("onclick")

                                if raw_href and raw_href.startswith("javascript:"):
                                    match_mm = re.search(r"MM_openBrWindow\('([^']+)'", raw_href)
                                    match_pop = re.search(r"popWindowCenter\('([^']+)'", raw_href)

                                    if match_mm:
                                        extracted_url = match_mm.group(1)
                                    elif match_pop:
                                        extracted_url = match_pop.group(1)
                                    elif re.search(r"openPdfViewer\('([^']+)'", raw_href):
                                        extracted_url = re.search(r"openPdfViewer\('([^']+)'", raw_href).group(1)
                                elif raw_href:
                                    extracted_url = raw_href

                                if not extracted_url and onclick_attr:
                                    match_onclick_pdf = re.search(r"openPdfViewer\('([^']+)'", onclick_attr)
                                    if match_onclick_pdf:
                                        extracted_url = match_onclick_pdf.group(1)
                                    elif re.search(r"window.open\('([^']+)'", onclick_attr):
                                        extracted_url = re.search(r"window.open\('([^']+)'", onclick_attr).group(1)

                                if extracted_url:  # URL이 성공적으로 추출된 경우에만 팝업/링크 처리 로직 진행
                                    # --- HTML 팝업/새 창 열고 내부 정보 추출 로직 ---
                                    if extracted_url.lower().endswith('.html') or '/popup/' in extracted_url.lower():
                                        print(f"  HTML 팝업/새 창 URL 감지: {extracted_url}. 내부 약관 정보를 찾으려고 시도합니다.")

                                        main_window_handle = driver.current_window_handle
                                        pop_up_main_product_doc_url = ""

                                        try:
                                            # 팝업을 띄우는 링크 요소를 클릭 (클릭 가능할 때까지 기다림)
                                            WebDriverWait(link_element_or_text, 5).until(EC.element_to_be_clickable((By.TAG_NAME, "a"))).click()

                                            WebDriverWait(driver, 10).until(EC.number_of_windows_to_be(2))

                                            new_window_handle = [handle for handle in driver.window_handles if handle != main_window_handle][0]
                                            driver.switch_to.window(new_window_handle)
                                            print(f"    새 창으로 전환 완료: {driver.current_url}")

                                            WebDriverWait(driver, 10).until(
                                                EC.presence_of_element_located((By.CLASS_NAME, "kumho"))
                                            )
                                            print("    팝업 내부 HTML 요소 로드 확인 (.kumho).")

                                            for dl_elem in driver.find_elements(By.TAG_NAME, "dl"):
                                                try:
                                                    dt_text = dl_elem.find_element(By.TAG_NAME, "dt").text.strip()

                                                    for dd_elem in dl_elem.find_elements(By.TAG_NAME, "dd"):
                                                        try:
                                                            a_tag_in_popup = dd_elem.find_element(By.TAG_NAME, "a")
                                                            pdf_link_raw = a_tag_in_popup.get_attribute("href")
                                                            link_text = a_tag_in_popup.text.strip()

                                                            if pdf_link_raw and pdf_link_raw.startswith('/'):
                                                                pdf_full_url = base_url + pdf_link_raw
                                                            elif pdf_link_raw and not pdf_link_raw.startswith('http'):
                                                                pdf_full_url = f"{base_url}/{pdf_link_raw.lstrip('./')}"
                                                            else:
                                                                pdf_full_url = pdf_link_raw

                                                            if dt_text == "주보험":
                                                                if col_name == "약관":
                                                                    pop_up_main_product_doc_url = pdf_full_url
                                                            elif dt_text in ["선택특약", "제도성특약"]:
                                                                new_product_row = {
                                                                    "상품명": link_text,
                                                                    "판매기간": current_row_data.get("판매기간", ""),
                                                                    "약관": pdf_full_url,
                                                                    "사업방법서": "",
                                                                    "상품요약서": ""
                                                                }
                                                                additional_rows_from_popup.append(new_product_row)
                                                            elif dt_text == "기타":
                                                                pass  # '기타' 정보는 추출하지 않음

                                                        except NoSuchElementException:
                                                            pass  # 팝업 내 a 태그 없음
                                                        except Exception as dl_a_e:
                                                            print(f"      {dt_text} 내 링크 추출 오류 (팝업): {dl_a_e}")
                                                except NoSuchElementException:
                                                    pass  # dl 내 dt 또는 dd 태그 없음
                                                except Exception as dl_e:
                                                    print(f"    dl 요소 처리 중 오류 (팝업): {dl_e}")

                                            current_row_data[col_name] = pop_up_main_product_doc_url if pop_up_main_product_doc_url else (
                                                extracted_url if extracted_url else "")

                                        except Exception as pop_e:
                                            print(f"    새 창에서 정보 추출 중 오류 발생: {pop_e}. 원본 HTML 팝업 URL을 사용합니다.")
                                            if extracted_url.startswith('/'):
                                                current_row_data[col_name] = base_url + extracted_url
                                            elif not extracted_url.startswith('http'):
                                                current_row_data[col_name] = f"{base_url}/{extracted_url.lstrip('./')}"
                                            else:
                                                current_row_data[col_name] = extracted_url
                                        finally:
                                            if driver.current_window_handle != main_window_handle:
                                                driver.close()
                                            driver.switch_to.window(main_window_handle)
                                            print("    새 창 닫고 메인 창으로 복귀 완료.")
                                    else:
                                        # HTML 팝업이 아닌 일반 PDF 링크인 경우
                                        if extracted_url.startswith('/'):
                                            current_row_data[col_name] = base_url + extracted_url
                                        elif not extracted_url.startswith('http'):
                                            current_row_data[col_name] = f"{base_url}/{extracted_url.lstrip('./')}"
                                        else:
                                            current_row_data[col_name] = extracted_url
                                else:  # a 태그는 찾았지만 유효한 URL/onclick이 없는 경우
                                    current_row_data[col_name] = ""
                                    print(f"  경고: '{col_name}' 링크가 유효한 URL을 포함하지 않습니다. 빈 문자열로 처리됩니다.")

                            except TimeoutException:  # <a> 태그를 짧은 시간 내에 찾지 못한 경우
                                current_row_data[col_name] = ""
                                print(f"  정보: '{col_name}' 링크(a 태그)를 찾을 수 없습니다 (Timeout). 빈 문자열로 처리됩니다.")
                            except Exception as e:
                                # 그 외 예상치 못한 오류 발생 시 (td 요소 문제 등)
                                print(f"링크 추출 또는 처리 중 예상치 못한 오류 (행 {i + 1}, 컬럼 {col_name}): {e}")
                                current_row_data[col_name] = "링크 처리 중 알 수 없는 오류 발생"
                    else:
                        # td 요소 자체가 없거나 비어있는 경우
                        current_row_data[col_name] = ""

                if any(value for value in current_row_data.values() if value):
                    extracted_rows.append(current_row_data)

                if additional_rows_from_popup:
                    extracted_rows.extend(additional_rows_from_popup)
                    print(f"    팝업에서 {len(additional_rows_from_popup)}개의 특약 상품이 추가되었습니다.")

            print(f"추출된 데이터 ({len(extracted_rows)}개 항목):")
            return extracted_rows

        except TimeoutException as e:
            print(f"패널 '{panel_id}' 또는 테이블 또는 TH/TR 요소를 시간 내에 찾을 수 없습니다: {e}. (시도 {attempt + 1}/{max_retries})")
            time.sleep(2)
        except NoSuchElementException as e:
            print(f"필수 요소(테이블, TH, TR)를 찾을 수 없습니다: {e}. (시도 {attempt + 1}/{max_retries})")
            time.sleep(2)
        except StaleElementReferenceException as e:
            print(f"테이블 요소 StaleElementReferenceException 발생. 재시도 중... (시도 {attempt + 1}/{max_retries})")
            time.sleep(2)
        except Exception as e:
            print(f"테이블 데이터 추출 중 예상치 못한 오류 발생: {e}")
            return []

    print(f"최대 재시도 횟수를 초과했습니다. 패널 '{panel_id}'에서 데이터를 추출할 수 없습니다.")
    return []


def click_selected_insurance_tabs(driver, tabs_to_exclude):
    """
    주어진 제외 목록에 없는 보험 유형 탭들을 순환하며 클릭하고 테이블 데이터를 추출합니다.
    """
    print("\n선택된 보험 유형 탭을 순환하며 클릭하고 데이터를 추출합니다...")
    all_extracted_data = {}
    try:  # 이 try는 함수 전체의 주요 로직을 감쌉니다.
        # 초기 탭 목록을 한 번 찾습니다.
        tab_list_ul = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "tab_category"))
        )

        tabs_info_to_process = []
        for tab_li in tab_list_ul.find_elements(By.TAG_NAME, "li"):
            try:
                tab_link = tab_li.find_element(By.TAG_NAME, "a")
                tab_name = tab_link.text.strip()
                tab_id = tab_link.get_attribute("id")
                href = tab_link.get_attribute("href")
                panel_id = href.split("#")[1] if href and "#" in href else None

                if tab_name and tab_name not in tabs_to_exclude and panel_id:
                    tabs_info_to_process.append({"name": tab_name, "id": tab_id, "panel_id": panel_id})
                else:
                    if tab_name in tabs_to_exclude:
                        print(f"탭 '{tab_name}'은 제외 목록에 있으므로 건너뜀.")
                    else:
                        print(f"경고: 탭 '{tab_name}'의 panel_id가 유효하지 않거나 이름이 비어있어 건너뜀.")

            except NoSuchElementException:
                print("경고: 탭 내부의 링크(a 태그)를 찾을 수 없습니다.")
            except Exception as e:
                print(f"탭 정보 추출 중 오류 발생: {e}")

        if not tabs_info_to_process:
            print("클릭할 유효한 탭이 없습니다. 제외 목록을 확인해주세요.")
            return {}  # 유효한 탭이 없으면 빈 딕셔너리 반환

        print(f"총 {len(tabs_info_to_process)}개의 유효한 탭을 처리할 예정입니다.")

        # tabs_info_to_process에 저장된 정보를 기반으로 탭을 클릭하고 데이터 추출
        for tab_info in tabs_info_to_process:
            tab_name = tab_info["name"]
            tab_id = tab_info["id"]
            panel_id = tab_info["panel_id"]

            try:  # 각 탭 처리 루프 내의 try-except 블록
                # 탭을 클릭하기 전에 다시 요소를 찾아서 StaleElementReferenceException 방지
                current_tab_link = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.ID, tab_id))
                )

                print(f"\n----- 탭 '{tab_name}' ({panel_id}) 클릭 시도 중 -----")
                time.sleep(2)
                # 이전 탭의 첫 번째 상품명 (있다면) 가져오기 로직
                previous_tab_first_product_name = None
                if all_extracted_data and all_extracted_data.get(list(all_extracted_data.keys())[-1]):
                    if len(all_extracted_data[list(all_extracted_data.keys())[-1]]) > 0:
                        previous_tab_first_product_name = all_extracted_data[list(all_extracted_data.keys())[-1]][0].get("상품명")
                        print(f"    이전 탭의 첫 번째 상품명: '{previous_tab_first_product_name}'")

                driver.execute_script("arguments[0].click();", current_tab_link)

                # **** 핵심 추가/수정 부분: 클릭 방해 요소가 사라질 때까지 대기 ****
                print("    클릭 방해 요소(로딩 스피너/오버레이)가 사라질 때까지 대기 중...")
                try:
                    # 팝업 딤드 레이어 (가장 흔한 방해 요소)
                    WebDriverWait(driver, 3).until(
                        EC.invisibility_of_element_located((By.CLASS_NAME, 'ly-pop-dim'))
                    )
                    # 에러 메시지에서 '<span>...</span>' 태그가 클릭을 가로챘다고 했으므로,
                    # 해당 탭의 바로 다음 형제 <span>을 가정하고 기다립니다.
                    # 만약 이것으로 해결되지 않으면, 개발자 도구(F12)로 해당 <span>의 정확한 CSS Selector 또는 XPath를 찾아야 합니다.
                    WebDriverWait(driver, 3).until(
                        EC.invisibility_of_element_located((By.XPATH, f"//a[@id='{tab_id}']/following-sibling::span[1]"))
                    )

                    print("    클릭 방해 요소 사라짐 확인 또는 없음.")
                except TimeoutException:
                    print("    정보: 클릭 방해 요소가 시간 내에 사라지지 않았거나 존재하지 않습니다.")
                except Exception as e:
                    print(f"    클릭 방해 요소 대기 중 예상치 못한 오류 발생: {e}")

                # 로딩이 확실히 끝나도록 짧은 대기 추가 (선택 사항이지만 도움이 될 수 있음)
                time.sleep(0.5)

                target_tbody_id = f"table_grid_{re.search(r'tab-panel(\d+)', panel_id).group(1)}"

                # 탭 클릭 후 해당 패널이 활성화되고 테이블이 로드될 때까지 기다림
                WebDriverWait(driver, 15).until(
                    EC.visibility_of_element_located((By.ID, panel_id))
                )
                WebDriverWait(driver, 10).until(
                    lambda driver: 'active' in driver.find_element(By.ID, panel_id).get_attribute('class')
                )
                table_xpath = f"//div[@id='{panel_id}']/div[@class='sec']/div[@class='basic-table-1']/table"
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.XPATH, table_xpath))
                )

                # tbody 내의 tr이 최소 하나 이상 존재할 때까지 기다림
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.XPATH, f"{table_xpath}/tbody[@id='{target_tbody_id}']/tr"))
                )

                # 이전 탭의 상품명이 사라질 때까지 기다리는 로직
                if previous_tab_first_product_name:
                    print(f"    이전 상품명 '{previous_tab_first_product_name}'이 사라질 때까지 기다리는 중...")
                    try:
                        WebDriverWait(driver, 10).until(
                            EC.invisibility_of_element_located(
                                (By.XPATH, f"{table_xpath}//td[contains(text(), '{previous_tab_first_product_name}')]"))
                        )
                        print(f"    이전 상품명 '{previous_tab_first_product_name}' 사라짐 확인.")
                    except TimeoutException:
                        print(f"    경고: 이전 상품명 '{previous_tab_first_product_name}'이 시간 내에 사라지지 않았습니다. 페이지 로딩에 문제가 있을 수 있습니다.")
                    except NoSuchElementException:
                        print(f"    이전 상품명 '{previous_tab_first_product_name}'을 더 이상 찾을 수 없어 사라진 것으로 간주합니다.")
                else:
                    print("    이전 탭 정보가 없어 이전 상품명 사라짐을 확인할 수 없습니다.")

                time.sleep(1)  # 추가적인 안정화를 위한 짧은 대기
                print(f"탭 '{tab_name}' 클릭 완료 및 패널/데이터 로드 확인.")

                tab_data = extract_table_data(driver, panel_id)
                all_extracted_data[tab_name] = tab_data

            except TimeoutException:
                print(f"오류: 탭 '{tab_name}'의 링크 클릭 또는 패널/데이터 로드에 시간 초과.")
            except StaleElementReferenceException:
                print(f"오류: 탭 '{tab_name}' 요소 참조가 오래되었습니다. 재시도하거나 다음 탭으로 진행합니다.")
            except ElementClickInterceptedException as e:
                print(f"오류: 탭 '{tab_name}' 클릭이 다른 요소에 의해 가로채졌습니다: {e}. 다음 탭으로 진행합니다.")
            except NoSuchElementException:
                print(f"오류: 탭 '{tab_name}'의 링크를 찾을 수 없습니다 (ID: {tab_id}).")
            except Exception as e:
                print(f"오류: 탭 '{tab_name}' 클릭 및 데이터 추출 중 예상치 못한 오류 발생: {e}")

    except Exception as e:  # 함수 전체의 주요 로직에서 발생할 수 있는 예상치 못한 오류 처리
        print(f"탭 목록 순회 및 처리 중 예상치 못한 오류 발생: {e}")
        # 오류 발생 시 빈 딕셔너리 또는 부분적으로 추출된 데이터 반환
        return all_extracted_data

    return all_extracted_data  # 최종 추출된 모든 데이터 반환


def crawl_page(driver, url):
    """
    지정된 URL로 이동하여 팝업을 처리하고 페이지 내용을 크롤링합니다.
    """
    extracted_data = {}
    try:
        print(f"URL '{url}'로 직접 이동합니다.")
        driver.get(url)

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        print("페이지 로딩 완료.")

        handle_ie_compatibility_popup(driver)

        tabs_to_exclude = ["퇴직연금"]
        extracted_data = click_selected_insurance_tabs(driver, tabs_to_exclude)

        print("\n--- 모든 지정된 보험 유형 탭 순환 및 데이터 추출 완료 ---")
        print(f"최종 페이지 제목: {driver.title}")
        print(f"최종 페이지 URL: {driver.current_url}")

    except TimeoutException:
        print(f"'{url}' 로딩 중 또는 요소 찾기 중 시간 초과 오류가 발생했습니다. 페이지가 예상대로 로드되지 않았을 수 있습니다.")
    except Exception as e:
        print(f"크롤링 중 예상치 못한 오류 발생: {e}")
    finally:
        driver.quit()  # 드라이버는 항상 종료되어야 합니다.

    return extracted_data


if __name__ == "__main__":
    target_url = "https://www.kdblife.co.kr/ajax.do?scrId=HDLMA002M02P"
    output_filename = "extracted_insurance_data.json"

    driver = setup_driver()
    all_crawled_data = crawl_page(driver, target_url)

    print("\n--- 최종 추출된 모든 데이터 요약 ---")
    if all_crawled_data:
        for tab_name, data_rows in all_crawled_data.items():
            print(f"\n### {tab_name} (총 {len(data_rows)}개 항목)\n")
            if data_rows:
                for row in data_rows:
                    print(f"--- 상품 데이터 ---")
                    for key, value in row.items():
                        # 값이 너무 길면 잘라서 출력 (가독성 향상)
                        display_value = str(value)
                        if len(display_value) > 100:
                            display_value = display_value[:100] + "..."
                        print(f"- {key}: {display_value}")
                    print("--------------------")
            else:
                print(f"  {tab_name}에서 추출된 상품 데이터가 없습니다.")

        try:
            with open(output_filename, 'w', encoding='utf-8') as f:
                json.dump(all_crawled_data, f, ensure_ascii=False, indent=4)
            print(f"\n모든 추출 데이터가 '{output_filename}' 파일에 성공적으로 저장되었습니다.")
        except IOError as e:
            print(f"\nJSON 파일 저장 중 오류 발생: {e}")
    else:
        print("어떤 탭에서도 추출된 데이터가 없습니다. JSON 파일이 생성되지 않습니다.")
