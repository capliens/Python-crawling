# 처브라이프/판매중단페이지/약관링크(개선필요)/사업방법서 없는거 제외
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
import sys  # sys 모듈 추가
from datetime import datetime  # datetime 모듈 추가

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# PdfLinkExtractor 및 DatabaseManager 임포트 오류 처리를 위한 try-except 블록 추가
try:
    from neoali.pdf_link_scraper import PdfLinkExtractor
except ImportError as e:
    PdfLinkExtractor = None
    print(f"경고: neoali.pdf_link_scraper.PdfLinkExtractor 모듈 임포트 실패 ({e}). 일부 기능이 비활성화될 수 있습니다.")
    traceback.print_exc()  # 스택 트레이스 출력

try:
    from neoali.DB_save import DatabaseManager
except ImportError as e:
    DatabaseManager = None
    print(f"경고: neoali.DB_save.DatabaseManager 모듈 임포트 실패 ({e}). DB 저장 기능이 비활성화될 수 있습니다.")
    traceback.print_exc()  # 스택 트레이스 출력

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
    # products_data = [] # 더 이상 리스트에 저장하지 않고 DB에 직접 저장

    # DatabaseManager 인스턴스 생성
    db_name = os.path.join(project_root, "insurance_products.db")  # 프로젝트 루트에 DB 파일 생성
    db_manager = DatabaseManager(db_name=db_name)

    try:
        driver.get(url)
        print("페이지 접속 완료: {}".format(url))
        time.sleep(2)  # 초기 페이지 로딩 대기 시간을 넉넉히 가집니다.

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
                print("탭 인덱스 {}가 범위를 벗어났습니다. 다음 탭으로 이동합니다.".format(tab_idx))
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

            current_tab_product_elements = []  # 현재 탭의 상품 요소들을 담을 리스트 초기화

            if tab_idx == 0 and is_active_tab_initial_load:
                print("'{0}' 탭은 초기 화면에서 이미 활성화되어 있습니다. 바로 상품 목록 스크래핑을 시도합니다.".format(tab_text))
                try:
                    current_tab_product_elements = WebDriverWait(driver, 30).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, product_rows_selector))
                    )
                    if not current_tab_product_elements:
                        print("첫 번째 탭에 상품 목록이 없습니다. 다음 탭으로 이동합니다.")
                        continue
                    print("첫 번째 탭의 상품 목록 로드 확인.")
                    time.sleep(1)  # 추가 렌더링 대기
                except TimeoutException:
                    print("첫 번째 탭의 상품 목록을 찾는 데 시간 초과. 다음 탭으로 이동합니다.")
                    continue
            else:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", clickable_element)
                time.sleep(0.5)  # 스크롤 후 클릭 전 짧은 대기
                driver.execute_script("arguments[0].click();", clickable_element)
                print("'{0}' 탭 클릭 완료. 페이지 로딩 대기...".format(tab_text))

                try:
                    # 이전 상품 목록 요소들 가져오기
                    old_product_elements = driver.find_elements(By.CSS_SELECTOR, product_rows_selector)
                    if old_product_elements:
                        try:
                            # 이전 요소가 DOM에서 사라질 때까지 짧게 대기 (없어도 진행)
                            WebDriverWait(driver, 10).until(EC.staleness_of(old_product_elements[0]))
                        except TimeoutException:
                            print("  이전 상품 목록이 사라지지 않았지만, 새로운 목록 로드를 시도합니다.")
                            pass  # 이전 목록이 완전히 사라지지 않아도 다음 단계로 진행

                    # 새로운 탭의 상품 목록이 나타날 때까지 대기
                    current_tab_product_elements = WebDriverWait(driver, 30).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, product_rows_selector))
                    )

                    if not current_tab_product_elements:
                        print("'{0}' 탭에 상품 목록이 없습니다. 다음 탭으로 이동합니다.".format(tab_text))
                        continue
                    print("새로운 탭의 상품 목록 로드 확인.")
                    time.sleep(1)  # 추가 렌더링 대기
                except TimeoutException:
                    print("'{0}' 탭의 상품 목록을 찾는 데 시간 초과. 다음 탭으로 이동합니다.".format(tab_text))
                    continue
                except StaleElementReferenceException:
                    print("StaleElementReferenceException 발생. '{0}' 탭의 상품 목록을 다시 찾습니다.".format(tab_text))
                    try:
                        current_tab_product_elements = WebDriverWait(driver, 30).until(
                            EC.presence_of_all_elements_located((By.CSS_SELECTOR, product_rows_selector))
                        )
                        if not current_tab_product_elements:
                            print("StaleElementReferenceException 후에도 상품 목록이 없습니다. 다음 탭으로 이동합니다.")
                            continue
                        print("StaleElementReferenceException 후 상품 목록 재로드 확인.")
                        time.sleep(1)
                    except TimeoutException:
                        print("StaleElementReferenceException 후에도 상품 목록 로드 시간 초과. 다음 탭으로 이동합니다.")
                        continue
                except WebDriverException as e:
                    print("탭 클릭 또는 로딩 중 WebDriver 오류 발생: {}. 다음 탭으로 이동합니다.".format(e))
                    traceback.print_exc()
                    continue
                except Exception as e_tab_load:
                    print("탭 로딩 중 예상치 못한 오류 발생: {}. 다음 탭으로 이동합니다.".format(e_tab_load))
                    traceback.print_exc()
                    continue

            # --- 페이지네이션 처리 ---
            current_page_num = 1
            while True:
                print(f"  스크래핑 페이지: {current_page_num}")

                product_elements = driver.find_elements(By.CSS_SELECTOR, product_rows_selector)
                if not product_elements:
                    print(f"  페이지 {current_page_num}에 상품이 없습니다. 페이지네이션 종료.")
                    break
                else:
                    print(f"  현재 페이지에서 {len(product_elements)}개의 상품 발견.")

                for row_idx, row in enumerate(product_elements):
                    try:
                        product_name_element = row.find_element(By.CSS_SELECTOR, "td:nth-child(2)")
                        product_name_in_list = product_name_element.text.strip()

                        # 모달창 열기 및 정보 가져오는 기능 주석 처리 (테스트를 위해)
                        modal_trigger_selector = "td:nth-child(3) > a"  # 3번째 td 안의 a
                        modal_trigger = row.find_element(By.CSS_SELECTOR, modal_trigger_selector)

                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", modal_trigger)
                        time.sleep(0.5)
                        driver.execute_script("arguments[0].click();", modal_trigger)
                        print("'{}' 상품의 모달창 열기 시도...".format(product_name_in_list))

                        modal_selector = "div#pop_official_06"
                        WebDriverWait(driver, 20).until(
                            EC.visibility_of_element_located((By.CSS_SELECTOR, modal_selector))
                        )
                        print("모달창 로드 완료.")
                        # time.sleep(1) # 불필요한 sleep 제거

                        modal_element = driver.find_element(By.CSS_SELECTOR, modal_selector)
                        modal_table_all_rows = modal_element.find_elements(By.CSS_SELECTOR, "div.tableType05 > table  tr")

                        # 모달 내 첫 번째 데이터 행의 첫 번째 링크가 나타날 때까지 대기 (tbody 제거)
                        try:
                            WebDriverWait(driver, 5).until(
                                EC.visibility_of_element_located(
                                    (By.XPATH, f"//div[@id='pop_official_06']//div[contains(@class,'tableType05')]//table/tr[2]/td[2]/a"))
                            )
                            print("모달 내 첫 번째 링크 요소 로드 확인.")
                        except TimeoutException:
                            print("모달 내 첫 번째 링크 요소 로드 시간 초과. 계속 진행합니다.")
                        except Exception as e:
                            print(f"모달 내 링크 요소 대기 중 오류: {e}")

                        sales_period = "N/A"
                        summary_link = "N/A"
                        terms_link = "N/A"
                        business_manual_link = "N/A"

                        current_modal_product_name = "N/A"

                        data_rows_in_modal = []
                        # modal_table_all_rows는 tr 요소들의 리스트입니다.
                        # 각 tr 요소의 인덱스를 추적하여 XPath를 구성합니다.
                        for r_idx, m_row in enumerate(modal_table_all_rows):
                            m_th_cells = m_row.find_elements(By.TAG_NAME, "th")
                            m_td_cells = m_row.find_elements(By.TAG_NAME, "td")

                            # 헤더 행 스킵 (상품명 컬럼이 th에 있을 경우)
                            if m_th_cells and m_th_cells[0].text.strip() == "상품명":
                                continue

                            if m_td_cells:
                                # 실제 데이터 행의 인덱스를 저장 (1부터 시작하는 XPath용)
                                data_rows_in_modal.append((r_idx + 1, m_td_cells))

                        if not data_rows_in_modal:
                            print("모달 내에서 데이터 행을 찾지 못했습니다.")
                        else:
                            current_modal_product_name = "N/A"  # 상품명 초기화

                            for data_row_xpath_idx, m_td_cells in data_rows_in_modal:
                                # 각 행의 td 개수를 확인하여 인덱스 조정
                                num_td_cells = len(m_td_cells)

                                sales_period = "N/A"
                                summary_link = "N/A"
                                business_manual_link = "N/A"
                                terms_link = "N/A"

                                # 상품명 셀이 rowspan을 가지고 있는지 확인 (새로운 상품 시작)
                                is_new_product_row = False
                                if m_td_cells[0].get_attribute("rowspan"):
                                    current_modal_product_name = m_td_cells[0].text.strip()
                                    is_new_product_row = True

                                # 모달 내 테이블의 기본 XPath (tbody 제거)
                                modal_table_base_xpath = f"//div[@id='pop_official_06']//div[contains(@class,'tableType05')]//table/thead/tr[{data_row_xpath_idx}]"

                                if is_new_product_row:
                                    # 새로운 상품명이 시작되는 행
                                    if num_td_cells == 5:  # 상품명(rowspan) + 판매기간 + 상품요약서 + 사업방법서 + 상품약관
                                        sales_period = m_td_cells[1].text.strip()
                                        if pdf_extractor:
                                            summary_link_xpath = f"{modal_table_base_xpath}/td[3]/a"
                                            summary_link = pdf_extractor.click_and_get_download_link(summary_link_xpath) or "N/A (추출 실패)"
                                            business_manual_link_xpath = f"{modal_table_base_xpath}/td[4]/a"
                                            business_manual_link = pdf_extractor.click_and_get_download_link(
                                                business_manual_link_xpath) or "N/A (추출 실패)"
                                            terms_link_xpath = f"{modal_table_base_xpath}/td[5]/a"
                                            terms_link = pdf_extractor.click_and_get_download_link(terms_link_xpath) or "N/A (추출 실패)"
                                        else:
                                            summary_link = "N/A (Extractor 비활성)"
                                            business_manual_link = "N/A (Extractor 비활성)"
                                            terms_link = "N/A (Extractor 비활성)"
                                    elif num_td_cells == 4:  # 상품명(rowspan) + 판매기간 + 사업방법서 + 상품약관 (상품요약서 컬럼 없음)
                                        sales_period = m_td_cells[1].text.strip()
                                        summary_link = "N/A"  # 상품요약서 컬럼 자체가 없으므로 N/A
                                        if pdf_extractor:
                                            business_manual_link_xpath = f"{modal_table_base_xpath}/td[3]/a"
                                            business_manual_link = pdf_extractor.click_and_get_download_link(
                                                business_manual_link_xpath) or "N/A (추출 실패)"
                                            terms_link_xpath = f"{modal_table_base_xpath}/td[4]/a"
                                            terms_link = pdf_extractor.click_and_get_download_link(terms_link_xpath) or "N/A (추출 실패)"
                                        else:
                                            business_manual_link = "N/A (Extractor 비활성)"
                                            terms_link = "N/A (Extractor 비활성)"
                                    else:
                                        print("새로운 상품 행의 td 개수가 예상과 다릅니다: {}개. 건너뜁니다.".format(num_td_cells))
                                        continue
                                else:
                                    # 기존 상품의 하위 행 (상품명이 없는 행)
                                    if num_td_cells == 4:  # 판매기간 + 상품요약서 + 사업방법서 + 상품약관
                                        sales_period = m_td_cells[0].text.strip()
                                        if pdf_extractor:
                                            summary_link_xpath = f"{modal_table_base_xpath}/td[2]/a"
                                            summary_link = pdf_extractor.click_and_get_download_link(summary_link_xpath) or "N/A (추출 실패)"
                                            business_manual_link_xpath = f"{modal_table_base_xpath}/td[3]/a"
                                            business_manual_link = pdf_extractor.click_and_get_download_link(
                                                business_manual_link_xpath) or "N/A (추출 실패)"
                                            terms_link_xpath = f"{modal_table_base_xpath}/td[4]/a"
                                            terms_link = pdf_extractor.click_and_get_download_link(terms_link_xpath) or "N/A (추출 실패)"
                                        else:
                                            summary_link = "N/A (Extractor 비활성)"
                                            business_manual_link = "N/A (Extractor 비활성)"
                                            terms_link = "N/A (Extractor 비활성)"
                                    elif num_td_cells == 3:  # 판매기간 + 사업방법서 + 상품약관 (상품요약서 컬럼 없음)
                                        sales_period = m_td_cells[0].text.strip()
                                        summary_link = "N/A"  # 상품요약서 컬럼 자체가 없으므로 N/A
                                        if pdf_extractor:
                                            business_manual_link_xpath = f"{modal_table_base_xpath}/td[2]/a"
                                            business_manual_link = pdf_extractor.click_and_get_download_link(
                                                business_manual_link_xpath) or "N/A (추출 실패)"
                                            terms_link_xpath = f"{modal_table_base_xpath}/td[3]/a"
                                            terms_link = pdf_extractor.click_and_get_download_link(terms_link_xpath) or "N/A (추출 실패)"
                                        else:
                                            business_manual_link = "N/A (Extractor 비활성)"
                                            terms_link = "N/A (Extractor 비활성)"
                                    else:
                                        print("하위 데이터 행의 td 개수가 예상과 다릅니다: {}개. 건너뜁니다.".format(num_td_cells))
                                        continue

                                products_data_to_save = []
                                scraped_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                                # 상품요약서 링크가 유효하면 추가
                                if summary_link and summary_link != "N/A (추출 실패)" and summary_link != "N/A (Extractor 비활성)":
                                    products_data_to_save.append([
                                        "Chubb Life",
                                        current_modal_product_name,
                                        None,  # product_code
                                        "상품요약서",
                                        sales_period,
                                        scraped_at,
                                        summary_link
                                    ])
                                # 사업방법서 링크가 유효하면 추가
                                if business_manual_link and business_manual_link != "N/A (추출 실패)" and business_manual_link != "N/A (Extractor 비활성)":
                                    products_data_to_save.append([
                                        "Chubb Life",
                                        current_modal_product_name,
                                        None,  # product_code
                                        "사업방법서",
                                        sales_period,
                                        scraped_at,
                                        business_manual_link
                                    ])
                                # 약관 링크가 유효하면 추가
                                if terms_link and terms_link != "N/A (추출 실패)" and terms_link != "N/A (Extractor 비활성)":
                                    products_data_to_save.append([
                                        "Chubb Life",
                                        current_modal_product_name,
                                        None,  # product_code
                                        "약관",
                                        sales_period,
                                        scraped_at,
                                        terms_link
                                    ])

                                if products_data_to_save and db_manager:
                                    with db_manager as db:
                                        db.save_data(products_data_to_save)
                                else:
                                    print("  저장할 데이터가 없거나 DB Manager가 비활성화되어 있습니다.")

                                # products_data.append({ # 더 이상 리스트에 저장하지 않음
                                #     "product_name": current_modal_product_name,
                                #     "sales_period": sales_period,
                                #     "summary_link": summary_link,
                                #     "terms_link": terms_link,
                                #     "business_manual_link": business_manual_link,
                                #     "tab_type": tab_text,
                                #     "page": current_page_num  # 현재 페이지 번호 사용
                                # })

                                print("  판매기간: {}".format(sales_period))
                                print("  상품요약서: {}".format(summary_link))
                                print("  사업방법서: {}".format(business_manual_link))
                                print("  약관: {}".format(terms_link))

                            try:
                                close_button = WebDriverWait(driver, 5).until(
                                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button#closeBtn"))
                                )
                                driver.execute_script("arguments[0].click();", close_button)
                                print("모달 닫기 버튼 클릭.")
                                WebDriverWait(driver, 10).until_not(
                                    EC.visibility_of_element_located((By.CSS_SELECTOR, modal_selector))
                                )
                                print("모달 닫힘 확인.")
                                time.sleep(1)
                            except Exception as e_modal_close:
                                print(f"모달 닫기 중 오류: {e_modal_close}")

                            except TimeoutException:
                                print("'{}' 상품의 모달창을 열거나 내용을 찾는 데 시간 초과.".format(product_name_in_list))
                            except NoSuchElementException:
                                print("'{}' 상품의 모달창 열기 버튼 또는 내부 요소를 찾을 수 없음.".format(product_name_in_list))
                            except Exception as e_modal:
                                print("'{}' 상품 모달 처리 중 오류: {}".format(product_name_in_list, e_modal))

                    except Exception as e_row:
                        print(f"    상품명 요소를 찾을 수 없거나 상품 행 처리 중 오류: {e_row} (행 {row_idx + 1})")
                        traceback.print_exc()
                        continue

                # 다음 페이지로 이동 시도
                try:
                    pagination_container = WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.pageArea.type02"))
                    )

                    # 현재 활성화된 페이지 번호 추출 (<strong> 태그 사용)
                    # 이 값은 로그용이며, 로직에 직접적인 영향을 주지 않음
                    try:
                        current_page_strong = pagination_container.find_element(By.CSS_SELECTOR, "strong.num span")
                        active_page_number = int(current_page_strong.text.strip())
                    except Exception:
                        pass

                    # 클릭 가능한 페이지 번호 (클래스 없는 <a> 태그) 추출
                    clickable_page_links = pagination_container.find_elements(By.CSS_SELECTOR, "div.pageArea.type02 a:not([class])")

                    next_page_to_click = None
                    for link in clickable_page_links:
                        try:
                            page_num_text = link.find_element(By.TAG_NAME, "span").text.strip()
                            num = int(page_num_text)
                            if num == current_page_num + 1:
                                next_page_to_click = link
                                break
                        except Exception:
                            continue

                    # '다음' 버튼 찾기
                    next_button = None
                    try:
                        next_button = pagination_container.find_element(By.CSS_SELECTOR, "a.btnNext")
                    except Exception:
                        pass

                    # '다음' 버튼 비활성화 여부 판단
                    is_next_button_disabled = False
                    if next_button:
                        next_button_href = next_button.get_attribute("href")
                        if next_button_href == "#" or "javascript:goPage" not in next_button_href:
                            is_next_button_disabled = True
                    else:
                        is_next_button_disabled = True

                    # 페이지네이션 종료 조건: 다음 페이지 링크도 없고 '다음' 버튼도 비활성화된 경우
                    if next_page_to_click is None and is_next_button_disabled:
                        print("  더 이상 다음 페이지 링크 또는 활성화된 '다음' 버튼이 없습니다. 페이지네이션 종료.")
                        break

                    # 다음 페이지로 이동: 다음 번호 링크 우선, 없으면 '다음' 버튼 클릭
                    if next_page_to_click:
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_page_to_click)
                        time.sleep(0.5)
                        driver.execute_script("arguments[0].click();", next_page_to_click)
                        print("  페이지 번호 '{}' 클릭 완료. 새로운 페이지 로딩 대기...".format(current_page_num + 1))
                        current_page_num += 1
                    elif next_button and not is_next_button_disabled:
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
                        time.sleep(0.5)
                        driver.execute_script("arguments[0].click();", next_button)
                        print("  '다음' 버튼 클릭 완료. 새로운 페이지 로딩 대기...")
                        current_page_num += 1
                    else:
                        print("  다음 페이지로 이동할 수 있는 링크 또는 버튼을 찾을 수 없습니다. 페이지네이션 종료.")
                        break

                    # 새로운 상품 목록이 로드될 때까지 기다림
                    if product_elements:  # 이전 상품 목록이 있었을 경우에만 staleness 대기
                        WebDriverWait(driver, 20).until(
                            EC.staleness_of(product_elements[0])
                        )
                    WebDriverWait(driver, 20).until(  # 새로운 상품 목록이 나타날 때까지 대기
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, product_rows_selector))
                    )
                    time.sleep(1)  # 추가 렌더링 대기

                except TimeoutException:
                    print("  새 페이지 로드 대기 중 시간 초과. 페이지네이션 종료.")
                    break
                except StaleElementReferenceException:
                    print("  StaleElementReferenceException 발생. 페이지네이션 요소를 다시 찾고 다음 페이지로 시도합니다.")
                    time.sleep(1)  # 짧은 대기 후 재시도
                except Exception as e_pagination:
                    print("  페이지네이션 처리 중 예상치 못한 오류 발생: {}".format(e_pagination))
                    traceback.print_exc()
                    break

            print("--- 보험 유형: {} 스크래핑 완료 ---".format(tab_text))

    except Exception as e_main:
        print("스크래핑 중 주요 오류 발생: {}".format(e_main))
        traceback.print_exc()
    finally:
        print("스크래핑 시도 종료. 브라우저를 닫습니다.")
        if 'driver' in locals() and driver is not None:
            driver.quit()

    # return products_data # 더 이상 리스트를 반환하지 않음


if __name__ == '__main__':
    print("Chubb Life 상품 정보 스크래핑 시작...")

    get_chubblife_product_info()

    print("Chubb Life 상품 정보 스크래핑 완료. 데이터는 'insurance_products.db'에 저장되었습니다.")
