# 처브라이프/판매중단페이지/약관링크(개선필요)/사업방법서 없는건 안나오게
# 코드수정 확인
from seleniumwire import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, WebDriverException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import os
import time
import traceback
import sys
from datetime import datetime

# 프로젝트 루트 경로 설정 (상위 디렉토리로 이동)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# PdfLinkExtractor 및 DatabaseManager 임포트 오류 처리를 위한 try-except 블록 추가
try:
    from neoali.pdf_link_scraper import PdfLinkExtractor
    from neoali.DB_save import DatabaseManager
except ImportError as e:
    DatabaseManager = None
    PdfLinkExtractor = None
    print(f"경고:모듈 임포트 실패 ({e}). 일부 기능이 비활성화될 수 있습니다.")
    traceback.print_exc()


# 다운로드 디렉토리 설정
download_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads", "chubblife")
if not os.path.exists(download_dir):
    os.makedirs(download_dir)


def get_chubblife_product_info():
    options = webdriver.ChromeOptions()

    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True  # PDF를 브라우저에서 바로 열지 않고 다운로드
    }
    options.add_experimental_option("prefs", prefs)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(60)  # 전체 페이지 로드 타임아웃 설정 (최대 60초)

    # PdfLinkExtractor의 요소 대기 시간을 30초로 늘리고, URL 유효성 검사를 비활성화합니다.
    pdf_extractor = PdfLinkExtractor(driver, download_directory=download_dir, element_wait_timeout=30, verify_url_liveness=False)

    url = "https://www.chubblife.co.kr/front/official/sale/listSale.do"

    # DatabaseManager 인스턴스 생성
    db_name = os.path.join(project_root, "chubblife_web_data.db")  # 프로젝트 루트에 DB 파일 생성
    db_manager = DatabaseManager(db_name=db_name)

    try:
        driver.get(url)
        print("페이지 접속 완료: {}".format(url))
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.subTabType"))
        )  # 초기 페이지 로딩 및 주요 요소 대기

        # 보험 유형 탭 요소들이 나타날 때까지 대기
        tab_selectors = "div.subTabType > ul > li"
        WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, tab_selectors))
        )

        initial_tabs = driver.find_elements(By.CSS_SELECTOR, tab_selectors)
        tab_texts = [tab.text.strip() for tab in initial_tabs]  # 탭 텍스트 미리 저장

        # 상품 목록을 위한 CSS 셀렉터
        product_rows_selector = "div.tableBasicList > table > tbody > tr"

        for tab_idx, tab_text in enumerate(tab_texts):
            print("\n--- 보험 유형: {} 스크래핑 시작 ---".format(tab_text))

            # 탭 클릭을 위해 현재 탭 요소 다시 찾기 (StaleElementReferenceException 방지)
            current_tabs = driver.find_elements(By.CSS_SELECTOR, tab_selectors)
            if tab_idx >= len(current_tabs):
                print(f"탭 인덱스 {tab_idx}가 범위를 벗어났습니다. 다음 탭으로 이동합니다.")
                continue

            tab_to_process = current_tabs[tab_idx]

            # 클릭 가능한 요소 (<a> 태그 우선, 없으면 <li> 자체)
            clickable_element = tab_to_process.find_element(By.TAG_NAME, "a") if tab_to_process.find_elements(By.TAG_NAME, "a") else tab_to_process

            is_active_tab_initial_load = False
            try:
                # 활성화된 탭인지 확인 (클래스 'on' 또는 strong 태그 존재 여부)
                if 'on' in clickable_element.get_attribute('class') or tab_to_process.find_elements(By.CSS_SELECTOR, 'strong'):
                    is_active_tab_initial_load = True
            except Exception:
                pass  # get_attribute() 에러 방지

            if tab_idx == 0 and is_active_tab_initial_load:
                print(f"'{tab_text}' 탭은 초기 화면에서 이미 활성화되어 있습니다. 바로 상품 목록 스크래핑을 시도합니다.")
            else:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", clickable_element)
                WebDriverWait(driver, 5).until(EC.element_to_be_clickable(clickable_element))  # 클릭 가능할 때까지 대기
                driver.execute_script("arguments[0].click();", clickable_element)
                print(f"'{tab_text}' 탭 클릭 완료. 페이지 로딩 대기...")

            try:
                # 새로운 탭의 상품 목록이 나타날 때까지 대기 (이전 요소가 사라지고 새 요소 나타남)
                # 새로운 상품 목록의 첫 번째 요소가 나타날 때까지 기다립니다.
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, product_rows_selector))
                )
                # 이전 요소가 사라지길 기다리는 것은 필수는 아님 (새로운 요소가 나타나면 됨)
                print(f"'{tab_text}' 탭의 상품 목록 로드 확인.")
            except TimeoutException:
                print(f"'{tab_text}' 탭의 상품 목록을 찾는 데 시간 초과. 다음 탭으로 이동합니다.")
                continue
            except WebDriverException as e:
                print(f"탭 클릭 또는 로딩 중 WebDriver 오류 발생: {e}. 다음 탭으로 이동합니다.")
                traceback.print_exc()
                continue
            except Exception as e_tab_load:
                print(f"탭 로딩 중 예상치 못한 오류 발생: {e_tab_load}. 다음 탭으로 이동합니다.")
                traceback.print_exc()
                continue

            # --- 페이지네이션 처리 ---
            current_page_num = 1
            while True:
                print(f"   스크래핑 페이지: {current_page_num}")

                product_elements = driver.find_elements(By.CSS_SELECTOR, product_rows_selector)
                if not product_elements:
                    print(f"   페이지 {current_page_num}에 상품이 없습니다. 페이지네이션 종료.")
                    break
                else:
                    print(f"   현재 페이지에서 {len(product_elements)}개의 상품 발견.")

                for row_idx, row in enumerate(product_elements):
                    product_name_in_list = "N/A"
                    try:
                        product_name_element = row.find_element(By.CSS_SELECTOR, "td:nth-child(2)")
                        product_name_in_list = product_name_element.text.strip()

                        modal_trigger_selector = "td:nth-child(3) > a"  # 3번째 td 안의 a
                        modal_trigger = WebDriverWait(row, 10).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, modal_trigger_selector))
                        )

                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", modal_trigger)
                        # 이미 EC.element_to_be_clickable로 대기했으므로 추가 sleep은 불필요
                        driver.execute_script("arguments[0].click();", modal_trigger)
                        print(f"'{product_name_in_list}' 상품의 모달창 열기 시도...")

                        modal_selector = "div#pop_official_06"
                        WebDriverWait(driver, 20).until(
                            EC.visibility_of_element_located((By.CSS_SELECTOR, modal_selector))
                        )
                        print("모달창 로드 완료.")

                        modal_element = driver.find_element(By.CSS_SELECTOR, modal_selector)

                        # --- 모달 테이블 헤더 파싱 (동적 컬럼 매핑) ---
                        # thead 내에 첫 번째 tr이 헤더임을 가정
                        header_row = WebDriverWait(modal_element, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "div.tableType05 > table > thead > tr:first-child"))
                        )
                        header_cells = header_row.find_elements(By.TAG_NAME, "th")

                        column_map = {}
                        for i, th in enumerate(header_cells):
                            column_map[th.text.strip()] = i
                        print(f"   모달 컬럼 맵: {column_map}")

                        # --- 모달 테이블 데이터 행 파싱 ---
                        # 모든 tr 요소를 가져오되, 헤더 tr을 제외하고 데이터 tr만 처리
                        # thead 내에 데이터 tr이 있는 특이 케이스를 감안하여
                        # thead의 첫 번째 tr(컬럼명)만 스킵하고 나머지는 데이터로 간주
                        all_tr_elements = modal_element.find_elements(By.CSS_SELECTOR, "div.tableType05 > table tr")

                        data_rows_to_process = []
                        if len(all_tr_elements) > 1:
                            data_rows_to_process = all_tr_elements[1:]  # 첫 번째 tr (헤더)를 건너_
                        else:
                            print(f"   [{product_name_in_list}] 모달 내 데이터 행을 찾을 수 없습니다.")

                        current_modal_product_name = "N/A"  # 모달 내 현재 처리 중인 상품명 (rowspan 적용)

                        # 현재 모달에서 추출된 모든 유효한 데이터를 담을 리스트 (모달당 한 번 초기화)
                        products_data_to_save_in_modal = []

                        for modal_row_idx, m_row in enumerate(data_rows_to_process):
                            try:
                                m_td_cells = m_row.find_elements(By.TAG_NAME, "td")
                                if not m_td_cells:
                                    continue  # td가 없으면 스킵

                                # 상품명 (rowspan 처리)
                                # 첫 번째 td가 rowspan 속성을 가지고 있다면, 그게 상품명입니다.
                                if m_td_cells[0].get_attribute("rowspan"):
                                    current_modal_product_name = m_td_cells[0].text.strip()
                                    # 첫 번째 td는 상품명이므로, 판매기간과 링크 데이터는 그 다음 td부터 시작
                                    start_td_offset = 1
                                else:
                                    # rowspan이 없는 하위 행은 상품명 td가 없으므로, 모든 td는 0부터 시작
                                    start_td_offset = 0

                                # 판매 기간 추출 (컬럼 맵 활용)
                                sales_period = "N/A"
                                sales_period_col_original_idx = column_map.get("판매기간")
                                if sales_period_col_original_idx is not None:
                                    # 실제 td 인덱스는 rowspan 적용 여부에 따라 달라짐 (원본 인덱스 - offset)
                                    actual_sales_period_td_idx = sales_period_col_original_idx - start_td_offset
                                    if 0 <= actual_sales_period_td_idx < len(m_td_cells):
                                        sales_period = m_td_cells[actual_sales_period_td_idx].text.strip()
                                        print(f"   판매기간: {sales_period}")

                                scraped_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                                # 각 문서 유형별 링크 추출 및 저장 (컬럼 맵 활용)
                                # 실제 웹사이트에 존재하는 컬럼명만 여기에 포함
                                doc_types_to_extract = {
                                    "상품요약서": "summary_link",
                                    "사업방법서": "business_manual_link",
                                    "상품약관": "terms_link"
                                }

                                for doc_name, link_var_name in doc_types_to_extract.items():
                                    original_col_idx = column_map.get(doc_name)
                                    if original_col_idx is not None:
                                        # 실제 td 인덱스 계산 (rowspan 적용 여부 고려)
                                        actual_td_idx_for_link = original_col_idx - start_td_offset

                                        extracted_link = "N/A"
                                        if 0 <= actual_td_idx_for_link < len(m_td_cells):
                                            link_cell = m_td_cells[actual_td_idx_for_link]

                                            # <a> 태그가 존재하는지 먼저 확인
                                            link_element_in_cell = None
                                            try:
                                                link_element_in_cell = link_cell.find_element(By.TAG_NAME, "a")
                                            except NoSuchElementException:
                                                pass  # <a> 태그가 없으면 None으로 유지

                                            if link_element_in_cell and pdf_extractor:
                                                # XPath는 1-based index이므로 실제 td 인덱스 + 1
                                                # 모달 테이블의 xpath는 `div#pop_official_06//table`
                                                # 현재 행의 xpath를 동적으로 구성하여 PdfLinkExtractor에 전달
                                                # all_tr_elements 리스트의 첫 번째 요소가 thead의 첫 번째 tr이므로,
                                                # 현재 데이터 행의 XPath 인덱스는 (modal_row_idx + 2) 가 됨 (1-based, thead_tr + current_data_tr)
                                                link_xpath = f"//div[@id='pop_official_06']//div[contains(@class,'tableType05')]//table/tr[{modal_row_idx + 2}]/td[{actual_td_idx_for_link + 1}]/a"
                                                extracted_link = pdf_extractor.click_and_get_download_link(link_xpath) or "N/A (추출 실패)"
                                            elif not pdf_extractor:
                                                extracted_link = "N/A (Extractor 비활성)"
                                            else:  # link_element_in_cell이 없고, pdf_extractor는 활성화된 경우 (빈 td일 때)
                                                extracted_link = "N/A (링크 없음)"
                                        else:
                                            # 해당 컬럼에 대한 td 자체가 없는 경우 (예: 예상치 못한 td 개수)
                                            extracted_link = "N/A (컬럼 위치 오류)"

                                        # 유효한 링크만 저장 리스트에 추가
                                        if extracted_link not in ["N/A", "N/A (추출 실패)", "N/A (Extractor 비활성)", "N/A (링크 없음)", "N/A (컬럼 위치 오류)"]:
                                            products_data_to_save_in_modal.append([
                                                "Chubb Life",
                                                current_modal_product_name,
                                                None,  # product_code
                                                doc_name,
                                                sales_period,
                                                scraped_at,
                                                extracted_link
                                            ])
                                        else:
                                            # print(f"   [{current_modal_product_name} - {sales_period}] {doc_name} 링크가 유효하지 않아 저장하지 않습니다: {extracted_link}")
                                            pass  # 불필요한 메시지 출력 방지 (너무 많을 수 있음)
                                    else:
                                        print(f"   경고: '{doc_name}' 컬럼을 모달 헤더에서 찾을 수 없습니다. 스킵합니다.")
                                print(f"   [{current_modal_product_name} - {sales_period}] 스크래핑 결과:")
                                for item in products_data_to_save_in_modal:
                                    if item[1] == current_modal_product_name and item[4] == sales_period:
                                        print(f"     - {item[3]}: {item[6]}")

                            except Exception as e_modal_row_process:
                                print(f"   [{current_modal_product_name}] 모달 내 데이터 행 처리 중 오류 발생 (행 인덱스 {modal_row_idx}): {e_modal_row_process}")
                                traceback.print_exc()
                                continue  # 다음 행으로 계속 진행

                        # 모달 처리 완료 후 DB 저장
                        if products_data_to_save_in_modal and db_manager:
                            with db_manager as db:
                                db.save_data(products_data_to_save_in_modal)
                                print(f"   [{current_modal_product_name}] 관련 유효 링크 데이터 {len(products_data_to_save_in_modal)}개 DB에 저장 완료.")
                        else:
                            print(f"   [{current_modal_product_name}] 저장할 유효한 링크 데이터가 없거나 DB Manager가 비활성화되어 있습니다.")

                        try:
                            # 모달 닫기 버튼을 찾고 클릭 (더 명확한 셀렉터 사용)
                            close_button = WebDriverWait(driver, 5).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, modal_selector + " button#closeBtn"))
                            )
                            driver.execute_script("arguments[0].click();", close_button)
                            print("모달 닫기 버튼 클릭.")
                            # 모달이 DOM에서 사라질 때까지 대기
                            WebDriverWait(driver, 10).until_not(
                                EC.visibility_of_element_located((By.CSS_SELECTOR, modal_selector))
                            )
                            print("모달 닫힘 확인.")
                        except Exception as e_modal_close:
                            print(f"모달 닫기 중 오류: {e_modal_close}")
                            # 모달이 닫히지 않은 경우를 대비하여 브라우저 새로고침이나 다른 조치를 고려할 수 있음
                            # 하지만 여기서는 일단 다음 상품으로 넘어갑니다.

                    except TimeoutException:
                        print(f"'{product_name_in_list}' 상품의 모달창을 열거나 내용을 찾는 데 시간 초과. 다음 상품으로 넘어갑니다.")
                    except NoSuchElementException as e:
                        print(f"'{product_name_in_list}' 상품 모달 처리 중 요소({e})를 찾을 수 없음. 다음 상품으로 넘어갑니다.")
                    except Exception as e_modal:
                        print(f"'{product_name_in_list}' 상품 모달 처리 중 예상치 못한 오류: {e_modal}. 다음 상품으로 넘어갑니다.")
                        traceback.print_exc()

                # --- 다음 페이지로 이동 시도 ---
                try:
                    pagination_container = WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.pageArea.type02"))
                    )

                    try:
                        current_page_strong = pagination_container.find_element(By.CSS_SELECTOR, "strong.num span")
                        active_page_number = int(current_page_strong.text.strip())
                        print(f"   현재 활성화된 페이지 번호: {active_page_number}")
                    except Exception:
                        pass  # 현재 페이지 번호를 가져오지 못해도 진행

                    # 다음 페이지 번호 링크 찾기
                    next_page_to_click = None
                    try:
                        next_page_to_click = pagination_container.find_element(
                            By.XPATH, f".//a/span[text()='{current_page_num + 1}']/parent::a"
                        )
                    except NoSuchElementException:
                        pass  # 다음 페이지 번호 링크가 없으면 None 유지

                    # '다음' 버튼 찾기
                    next_button = None
                    try:
                        next_button = pagination_container.find_element(By.CSS_SELECTOR, "a.btnNext")
                    except NoSuchElementException:
                        pass

                    is_next_button_disabled = False
                    if next_button:
                        # '다음' 버튼이 비활성화되었는지 확인 (href="#" 또는 특정 class)
                        next_button_href = next_button.get_attribute("href")
                        if next_button_href == "#" or "javascript:goPage" not in next_button_href:  # goPage는 예시
                            is_next_button_disabled = True
                        # 활성화 클래스 'on', 비활성화 'off' 가정
                        elif 'on' not in next_button.get_attribute('class') and 'off' in next_button.get_attribute('class'):
                            is_next_button_disabled = True
                    else:  # '다음' 버튼 자체가 없으면 비활성화된 것으로 간주
                        is_next_button_disabled = True

                    if next_page_to_click:  # 다음 페이지 번호 링크가 있으면 클릭
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_page_to_click)
                        WebDriverWait(driver, 5).until(EC.element_to_be_clickable(next_page_to_click))
                        driver.execute_script("arguments[0].click();", next_page_to_click)
                        print(f"   페이지 번호 '{current_page_num + 1}' 클릭 완료. 새로운 페이지 로딩 대기...")
                        current_page_num += 1
                    elif next_button and not is_next_button_disabled:  # 다음 페이지 번호 링크는 없지만 '다음' 버튼이 활성화되어 있으면 클릭
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
                        WebDriverWait(driver, 5).until(EC.element_to_be_clickable(next_button))
                        driver.execute_script("arguments[0].click();", next_button)
                        print("   '다음' 버튼 클릭 완료. 새로운 페이지 로딩 대기...")
                        current_page_num += 1
                    else:
                        print("   더 이상 다음 페이지로 이동할 수 있는 링크 또는 버튼이 없습니다. 페이지네이션 종료.")
                        break  # 페이지네이션 종료

                    # 새 페이지의 상품 목록이 로드될 때까지 대기 (이전 상품 목록이 stale해지고 새로운 목록이 나타남)
                    if product_elements:  # 이전 페이지의 상품 요소들이 있다면 stale해질 때까지 대기
                        try:
                            WebDriverWait(driver, 15).until(
                                EC.staleness_of(product_elements[0])
                            )
                        except TimeoutException:
                            print("   이전 상품 목록이 사라지지 않았지만, 새로운 목록 로드를 시도합니다.")
                            pass  # 이전 목록이 완전히 사라지지 않아도 다음 단계로 진행

                    WebDriverWait(driver, 20).until(  # 새로운 상품 목록 요소가 나타날 때까지 대기
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, product_rows_selector))
                    )

                except TimeoutException:
                    print("   새 페이지 로드 또는 페이지네이션 요소 대기 중 시간 초과. 페이지네이션 종료.")
                    break
                except StaleElementReferenceException:
                    print("   StaleElementReferenceException 발생. 페이지네이션 요소를 다시 찾고 다음 페이지로 시도합니다.")
                    time.sleep(1)  # 잠시 대기 후 재시도 (다음 루프에서 다시 요소 찾기)
                except Exception as e_pagination:
                    print(f"   페이지네이션 처리 중 예상치 못한 오류 발생: {e_pagination}")
                    traceback.print_exc()
                    break

            print(f"--- 보험 유형: {tab_text} 스크래핑 완료 ---")

    except Exception as e_main:
        print(f"스크래핑 중 주요 오류 발생: {e_main}")
        traceback.print_exc()
    finally:
        print("스크래핑 시도 종료. 브라우저를 닫습니다.")
        if 'driver' in locals() and driver is not None:
            driver.quit()


if __name__ == '__main__':
    print("Chubb Life 상품 정보 스크래핑 시작...")

    get_chubblife_product_info()

    print("Chubb Life 상품 정보 스크래핑 완료. 데이터는 'chubblife_web_data.db'에 저장되었습니다.")
