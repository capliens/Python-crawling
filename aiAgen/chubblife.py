# Chubb Life /판매중단페이지/db 연결/ 링크 연결
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import time
import traceback


def get_chubblife_product_info():
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless')
    # options.add_argument('--disable-gpu')
    # options.add_argument("--window-size=1920,1080")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(60)

    url = "https://www.chubblife.co.kr/front/official/sale/listSale.do"
    products_data = []

    try:
        driver.get(url)
        print(f"페이지 접속 완료: {url}")
        time.sleep(3)  # 초기 페이지 로딩 대기

        # 보험 유형 탭 순회 (보장성, 연금, 변액, 특약 등)
        tab_selectors = "div.subTabType > ul > li"
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, tab_selectors))
        )
        tabs = driver.find_elements(By.CSS_SELECTOR, tab_selectors)

        # 탭 텍스트와 클릭 가능한 요소 매핑
        tab_info = []
        for tab_idx, tab_element in enumerate(tabs):
            tab_text = tab_element.text.strip()
            tab_info.append({"text": tab_text, "element_index": tab_idx})

        for tab_idx, tab_data in enumerate(tab_info):
            tab_text = tab_data["text"]
            print(f"\n--- 보험 유형: {tab_text} 스크래핑 시작 ---")

            # 탭 클릭 (StaleElementReferenceException 방지를 위해 매번 다시 찾음)
            current_tabs = driver.find_elements(By.CSS_SELECTOR, tab_selectors)
            if tab_idx >= len(current_tabs):
                print(f"탭 인덱스 {tab_idx}가 범위를 벗어났습니다. 다음 탭으로 이동합니다.")
                continue

            tab_to_click = current_tabs[tab_idx]

            # 탭 클릭 전에 현재 상품 목록의 텍스트를 저장
            product_rows_selector = "div.tableBasicList > table > tbody > tr"
            old_product_list_text = ""
            try:
                old_product_elements = driver.find_elements(By.CSS_SELECTOR, product_rows_selector)
                if old_product_elements:
                    old_product_list_text = old_product_elements[0].text  # 첫 번째 상품의 텍스트를 저장
            except Exception:
                pass  # 상품이 없을 수도 있음

            # 클릭할 실제 요소 찾기: li 내부에 a 태그가 있으면 a 태그를 클릭, 없으면 li 자체를 클릭
            clickable_element = None
            try:
                # li 내부에 a 태그가 있는지 시도
                clickable_element = tab_to_click.find_element(By.TAG_NAME, "a")
            except NoSuchElementException:
                # a 태그가 없으면 li 자체를 클릭 (strong 태그로 활성화된 경우 등)
                clickable_element = tab_to_click

            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", clickable_element)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", clickable_element)
            print(f"'{tab_text}' 탭 클릭 완료. 페이지 로딩 대기...")

            # 탭 클릭 후 상품 목록이 새로 로드될 때까지 기다림
            try:
                WebDriverWait(driver, 30).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, product_rows_selector))
                )
                print("새로운 탭의 상품 목록 로드 확인.")
                time.sleep(3)  # 추가 대기
            except TimeoutException:
                print(f"'{tab_text}' 탭의 상품 목록을 찾는 데 시간 초과. 다음 탭으로 이동합니다.")
                continue  # 다음 탭으로 넘어감

            # --- 페이지네이션 처리 ---
            pagination_container_selector = "div.pageArea.type02"
            next_button_selector = "a.btnNext"
            prev_button_selector = "a.btnPrev"
            page_link_selector = "div.pageArea.type02 > a.btnPage"  # 페이지 번호 링크

            while True:  # 전체 페이지 묶음을 순회하는 루프
                print("  새로운 페이지 묶음 스크래핑 시작...")  # Flake8 오류 수정

                # 현재 보이는 페이지 번호 링크들을 가져옴
                all_page_elements = driver.find_elements(By.CSS_SELECTOR, "div.pageArea.type02 > strong.num, div.pageArea.type02 > a.btnPage")

                # 페이지 번호와 해당 요소 매핑
                page_info_list = []
                for elem in all_page_elements:
                    try:
                        page_num = int(elem.text.strip())
                        page_info_list.append({"num": page_num, "element": elem})
                    except ValueError:
                        pass  # 숫자가 아닌 요소는 무시 (예: 이전/다음 버튼)

                # 페이지 번호를 숫자로 정렬
                page_info_list.sort(key=lambda x: x["num"])

                # 각 페이지 번호를 순회하며 클릭
                for i, page_info in enumerate(page_info_list):
                    page_num = page_info["num"]
                    page_element = page_info["element"]

                    # 이미 활성화된 페이지 (strong.num)는 클릭하지 않음
                    if page_element.tag_name == "strong" and "num" in page_element.get_attribute("class"):
                        print(f"  현재 활성화된 페이지: {page_num}")
                        # 현재 페이지의 상품 목록 스크래핑 (모달창 활성화)
                        product_rows_selector = "div.tableBasicList > table > tbody > tr"
                        try:
                            WebDriverWait(driver, 10).until(
                                EC.presence_of_all_elements_located((By.CSS_SELECTOR, product_rows_selector))
                            )
                            product_elements = driver.find_elements(By.CSS_SELECTOR, product_rows_selector)
                            if not product_elements:
                                print("  현재 페이지에 상품이 없습니다.")
                            else:
                                print(f"  현재 페이지에서 {len(product_elements)}개의 상품 발견.")

                            for row_idx, row in enumerate(product_elements):
                                try:
                                    product_name_element = row.find_element(By.CSS_SELECTOR, "td:nth-child(2)")  # a 태그 제거
                                    product_name_in_list = product_name_element.text.strip()
                                    print(f"    상품명 (목록): {product_name_in_list}")

                                    # 모달창 열기 및 정보 가져오는 기능 주석 처리 (테스트를 위해)
                                    # modal_trigger_selector = "td:nth-child(3) > a"  # 3번째 td 안의 a
                                    # modal_trigger = row.find_element(By.CSS_SELECTOR, modal_trigger_selector)

                                    # driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", modal_trigger)
                                    # time.sleep(0.5)
                                    # driver.execute_script("arguments[0].click();", modal_trigger)
                                    # print(f"'{product_name_in_list}' 상품의 모달창 열기 시도...")

                                    # modal_selector = "div#pop_official_06"
                                    # WebDriverWait(driver, 20).until(
                                    #     EC.visibility_of_element_located((By.CSS_SELECTOR, modal_selector))
                                    # )
                                    # print("모달창 로드 완료.")
                                    # time.sleep(1)

                                    # modal_element = driver.find_element(By.CSS_SELECTOR, modal_selector)
                                    # modal_table_all_rows = modal_element.find_elements(By.CSS_SELECTOR, "div.tableType05 > table  tr")

                                    # sales_period = "N/A"
                                    # summary_link = "N/A"
                                    # terms_link = "N/A"
                                    # business_manual_link = "N/A"

                                    # current_modal_product_name = "N/A"

                                    # data_rows_in_modal = []
                                    # for r_idx, m_row in enumerate(modal_table_all_rows):
                                    #     m_th_cells = m_row.find_elements(By.TAG_NAME, "th")
                                    #     m_td_cells = m_row.find_elements(By.TAG_NAME, "td")
                                    #     if m_th_cells and m_th_cells[0].text.strip() == "상품명":
                                    #         continue
                                    #     if m_td_cells:
                                    #         data_rows_in_modal.append(m_td_cells)

                                    # if not data_rows_in_modal:
                                    #     print("모달 내에서 데이터 행을 찾지 못했습니다.")
                                    # else:
                                    #     first_data_row_cells = data_rows_in_modal[0]
                                    #     if first_data_row_cells and first_data_row_cells[0].get_attribute("rowspan"):
                                    #         current_modal_product_name = first_data_row_cells[0].text.strip()
                                    #     else:
                                    #         current_modal_product_name = first_data_row_cells[0].text.strip()

                                    #     for m_td_cells in data_rows_in_modal:
                                    #         if m_td_cells[0].get_attribute("rowspan"):
                                    #             current_modal_product_name = m_td_cells[0].text.strip()
                                    #             sales_period_idx = 1
                                    #             summary_idx = 2
                                    #             bm_idx = 3
                                    #             terms_idx = 4
                                    #         else:
                                    #             sales_period_idx = 0
                                    #             summary_idx = 1
                                    #             bm_idx = 2
                                    #             terms_idx = 3

                                    #         if len(m_td_cells) >= 5:
                                    #             sales_period = m_td_cells[sales_period_idx].text.strip()
                                    #             summary_links_modal = m_td_cells[summary_idx].find_elements(By.TAG_NAME, "a")
                                    #             summary_link = summary_links_modal[0].get_attribute('href') if summary_links_modal else "N/A"
                                    #             bm_links_modal = m_td_cells[bm_idx].find_elements(By.TAG_NAME, "a")
                                    #             business_manual_link = bm_links_modal[0].get_attribute('href') if bm_links_modal else "N/A"
                                    #             terms_links_modal = m_td_cells[terms_idx].find_elements(By.TAG_NAME, "a")
                                    #             terms_link = terms_links_modal[0].get_attribute('href') if terms_links_modal else "N/A"
                                    #         elif len(m_td_cells) == 4:
                                    #             sales_period = m_td_cells[sales_period_idx].text.strip()
                                    #             summary_link = "N/A"
                                    #             bm_links_modal = m_td_cells[bm_idx - 1].find_elements(By.TAG_NAME, "a")
                                    #             business_manual_link = bm_links_modal[0].get_attribute('href') if bm_links_modal else "N/A"
                                    #             terms_links_modal = m_td_cells[terms_idx - 1].find_elements(By.TAG_NAME, "a")
                                    #             terms_link = terms_links_modal[0].get_attribute('href') if terms_links_modal else "N/A"
                                    #         else:
                                    #             print(f"모달 내 데이터 행의 td 개수가 예상과 다릅니다: {len(m_td_cells)}개. 건너뜁니다.")
                                    #             continue

                                    #         products_data.append({
                                    #             "product_name": current_modal_product_name,
                                    #             "sales_period": sales_period,
                                    #             "summary_link": summary_link,
                                    #             "terms_link": terms_link,
                                    #             "business_manual_link": business_manual_link,
                                    #             "tab_type": tab_text,
                                    #             "page": page_num # 현재 페이지 번호 사용
                                    #         })

                                    #         print(f"  판매기간: {sales_period}")
                                    #         print(f"  상품요약서: {summary_link}")
                                    #         print(f"  사업방법서: {business_manual_link}")
                                    #         print(f"  약관: {terms_link}")

                                    # try:
                                    #     close_button = WebDriverWait(driver, 5).until(
                                    #         EC.element_to_be_clickable((By.CSS_SELECTOR, "button#closeBtn"))
                                    #     )
                                    #     driver.execute_script("arguments[0].click();", close_button)
                                    #     print("모달 닫기 버튼 클릭.")
                                    #     WebDriverWait(driver, 10).until_not(
                                    #         EC.visibility_of_element_located((By.CSS_SELECTOR, modal_selector))
                                    #     )
                                    #     print("모달 닫힘 확인.")
                                    #     time.sleep(1)
                                    # except Exception as e_modal_close:
                                    #     print(f"모달 닫기 중 오류: {e_modal_close}")

                                    # except TimeoutException:
                                    #     print(f"'{product_name_in_list}' 상품의 모달창을 열거나 내용을 찾는 데 시간 초과.")
                                    # except NoSuchElementException:
                                    #     print(f"'{product_name_in_list}' 상품의 모달창 열기 버튼 또는 내부 요소를 찾을 수 없음.")
                                    # except Exception as e_modal:
                                    #     print(f"'{product_name_in_list}' 상품 모달 처리 중 오류: {e_modal}")

                                except NoSuchElementException:
                                    print(f"    상품명 요소를 찾을 수 없습니다. (행 {row_idx + 1})")
                                    continue
                                except Exception as e_row:
                                    print(f"    상품 행 처리 중 오류: {e_row} (행 {row_idx + 1})")
                                    traceback.print_exc()
                                    continue

                                # 모달 기능 주석 처리 후 products_data에 기본 정보 추가
                                products_data.append({
                                    "product_name": product_name_in_list,
                                    "tab_type": tab_text,
                                    "page": page_num
                                })

                        except TimeoutException:
                            print("  상품 목록을 찾는 데 시간 초과.")
                        except Exception as e_product_list:
                            print(f"  상품 목록 스크래핑 중 오류: {e_product_list}")
                            traceback.print_exc()

                    else:  # 페이지 번호 링크 클릭
                        print(f"  페이지 {page_num} 클릭 시도...")
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", page_element)
                        time.sleep(0.5)

                        # 클릭 가능할 때까지 기다림
                        WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, f"//div[@class='pageArea type02']//a[span[text()='{page_num}']]"))
                        )
                        # StaleElementReferenceException 방지를 위해 클릭 직전에 다시 찾음
                        page_element_to_click = driver.find_element(By.XPATH, f"//div[@class='pageArea type02']//a[span[text()='{page_num}']]")

                        driver.execute_script("arguments[0].click();", page_element_to_click)
                        print(f"  페이지 {page_num} 클릭 완료. 페이지 로딩 대기...")

                        # 페이지 로딩 대기 (상품 목록이 새로 로드될 때까지)
                        try:
                            WebDriverWait(driver, 10).until(
                                EC.presence_of_all_elements_located((By.CSS_SELECTOR, product_rows_selector))
                            )
                            print(f"  페이지 {page_num}의 상품 목록 로드 확인.")
                        except TimeoutException:
                            print(f"  페이지 {page_num}의 상품 목록을 찾는 데 시간 초과. 다음 페이지로 이동합니다.")
                            continue
                        time.sleep(2)  # 추가 대기

                        # 현재 페이지의 상품 목록 스크래핑 (모달창 활성화)
                        product_rows_selector = "div.tableBasicList > table > tbody > tr"
                        try:
                            WebDriverWait(driver, 10).until(
                                EC.presence_of_all_elements_located((By.CSS_SELECTOR, product_rows_selector))
                            )
                            product_elements = driver.find_elements(By.CSS_SELECTOR, product_rows_selector)
                            if not product_elements:
                                print("  현재 페이지에 상품이 없습니다.")
                            else:
                                print(f"  현재 페이지에서 {len(product_elements)}개의 상품 발견.")

                            for row_idx, row in enumerate(product_elements):
                                try:
                                    product_name_element = row.find_element(By.CSS_SELECTOR, "td:nth-child(2)")  # a 태그 제거
                                    product_name_in_list = product_name_element.text.strip()
                                    print(f"    상품명 (목록): {product_name_in_list}")

                                    # 모달창 열기 및 정보 가져오는 기능 활성화
                                    modal_trigger_selector = "td:nth-child(3) > a"  # 3번째 td 안의 a
                                    modal_trigger = row.find_element(By.CSS_SELECTOR, modal_trigger_selector)

                                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", modal_trigger)
                                    time.sleep(0.5)
                                    driver.execute_script("arguments[0].click();", modal_trigger)
                                    print(f"'{product_name_in_list}' 상품의 모달창 열기 시도...")

                                    modal_selector = "div#pop_official_06"
                                    WebDriverWait(driver, 20).until(
                                        EC.visibility_of_element_located((By.CSS_SELECTOR, modal_selector))
                                    )
                                    print("모달창 로드 완료.")
                                    time.sleep(1)

                                    modal_element = driver.find_element(By.CSS_SELECTOR, modal_selector)
                                    modal_table_all_rows = modal_element.find_elements(By.CSS_SELECTOR, "div.tableType05 > table  tr")

                                    sales_period = "N/A"
                                    summary_link = "N/A"
                                    terms_link = "N/A"
                                    business_manual_link = "N/A"  # 초기화 추가

                                    current_modal_product_name = "N/A"

                                    data_rows_in_modal = []
                                    for r_idx, m_row in enumerate(modal_table_all_rows):
                                        m_th_cells = m_row.find_elements(By.TAG_NAME, "th")
                                        m_td_cells = m_row.find_elements(By.TAG_NAME, "td")
                                        if m_th_cells and m_th_cells[0].text.strip() == "상품명":
                                            continue
                                        if m_td_cells:
                                            data_rows_in_modal.append(m_td_cells)

                                    if not data_rows_in_modal:
                                        print("모달 내에서 데이터 행을 찾지 못했습니다.")
                                    else:
                                        first_data_row_cells = data_rows_in_modal[0]
                                        if first_data_row_cells and first_data_row_cells[0].get_attribute("rowspan"):
                                            current_modal_product_name = first_data_row_cells[0].text.strip()
                                        else:
                                            current_modal_product_name = first_data_row_cells[0].text.strip()

                                        for m_td_cells in data_rows_in_modal:
                                            if m_td_cells[0].get_attribute("rowspan"):
                                                current_modal_product_name = m_td_cells[0].text.strip()
                                                sales_period_idx = 1
                                                summary_idx = 2
                                                bm_idx = 3
                                                terms_idx = 4
                                            else:
                                                sales_period_idx = 0
                                                summary_idx = 1
                                                bm_idx = 2
                                                terms_idx = 3

                                            if len(m_td_cells) >= 5:
                                                sales_period = m_td_cells[sales_period_idx].text.strip()
                                                summary_links_modal = m_td_cells[summary_idx].find_elements(By.TAG_NAME, "a")
                                                summary_link = summary_links_modal[0].get_attribute('href') if summary_links_modal else "N/A"
                                                bm_links_modal = m_td_cells[bm_idx].find_elements(By.TAG_NAME, "a")
                                                business_manual_link = bm_links_modal[0].get_attribute('href') if bm_links_modal else "N/A"
                                                terms_links_modal = m_td_cells[terms_idx].find_elements(By.TAG_NAME, "a")
                                                terms_link = terms_links_modal[0].get_attribute('href') if terms_links_modal else "N/A"
                                            elif len(m_td_cells) == 4:
                                                sales_period = m_td_cells[sales_period_idx].text.strip()
                                                summary_link = "N/A"
                                                bm_links_modal = m_td_cells[bm_idx - 1].find_elements(By.TAG_NAME, "a")
                                                business_manual_link = bm_links_modal[0].get_attribute('href') if bm_links_modal else "N/A"
                                                terms_links_modal = m_td_cells[terms_idx - 1].find_elements(By.TAG_NAME, "a")
                                                terms_link = terms_links_modal[0].get_attribute('href') if terms_links_modal else "N/A"
                                            else:
                                                print(f"모달 내 데이터 행의 td 개수가 예상과 다릅니다: {len(m_td_cells)}개. 건너뜁니다.")
                                                continue

                                            products_data.append({
                                                "product_name": current_modal_product_name,
                                                "sales_period": sales_period,
                                                "summary_link": summary_link,
                                                "terms_link": terms_link,
                                                "business_manual_link": business_manual_link,
                                                "tab_type": tab_text,
                                                "page": page_num  # 현재 페이지 번호 사용
                                            })

                                            print(f"  판매기간: {sales_period}")
                                            print(f"  상품요약서: {summary_link}")
                                            print(f"  사업방법서: {business_manual_link}")
                                            print(f"  약관: {terms_link}")

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
                                    print(f"'{product_name_in_list}' 상품의 모달창을 열거나 내용을 찾는 데 시간 초과.")
                                except NoSuchElementException:
                                    print(f"'{product_name_in_list}' 상품의 모달창 열기 버튼 또는 내부 요소를 찾을 수 없음.")
                                except Exception as e_modal:
                                    print(f"'{product_name_in_list}' 상품 모달 처리 중 오류: {e_modal}")

                                except NoSuchElementException:
                                    print(f"    상품명 요소를 찾을 수 없습니다. (행 {row_idx + 1})")
                                    continue
                                except Exception as e_row:
                                    print(f"    상품 행 처리 중 오류: {e_row} (행 {row_idx + 1})")
                                    traceback.print_exc()
                                    continue

                        except TimeoutException:
                            print("  상품 목록을 찾는 데 시간 초과.")
                        except Exception as e_product_list:
                            print(f"  상품 목록 스크래핑 중 오류: {e_product_list}")
                            traceback.print_exc()

                    # 현재 페이지 묶음의 마지막 페이지에 도달했을 때만 다음 버튼 클릭
                    if i == len(page_info_list) - 1:
                        next_button = None
                        try:
                            pagination_container = driver.find_element(By.CSS_SELECTOR, pagination_container_selector)
                            next_button = pagination_container.find_element(By.CSS_SELECTOR, next_button_selector)
                        except NoSuchElementException:
                            print("  페이지네이션 컨테이너 또는 다음 버튼을 찾을 수 없습니다. 페이지네이션 종료.")
                            break  # 다음 버튼이 없으면 페이지네이션 종료

                        is_next_button_disabled = next_button.get_attribute("href") == "#"

                        if is_next_button_disabled:
                            print("  다음 페이지 버튼이 비활성화되었습니다. 페이지네이션 종료.")
                            break  # 다음 버튼이 비활성화되면 페이지네이션 종료

                        # 다음 페이지 묶음으로 이동
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
                        time.sleep(0.5)
                        WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, next_button_selector))
                        )
                        next_button = driver.find_element(By.CSS_SELECTOR, next_button_selector)  # StaleElementReferenceException 방지
                        driver.execute_script("arguments[0].click();", next_button)
                        print("  다음 페이지 묶음 버튼 클릭. 페이지 로딩 대기...")

                        # 다음 페이지 묶음 로딩 대기 (현재 활성화된 페이지 번호가 변경될 때까지)
                        # 이전 페이지 묶음의 첫 번째 페이지 번호 (page_info_list[0]["num"])를 기준으로
                        # 새로운 페이지 묶음의 첫 번째 페이지 번호가 더 커졌는지 확인
                        try:
                            # 현재 활성화된 페이지 번호 요소를 다시 찾음
                            current_active_page_element = WebDriverWait(driver, 10).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, "div.pageArea.type02 > strong.num > span"))
                            )
                            WebDriverWait(driver, 10).until(
                                lambda d: int(d.find_element(By.CSS_SELECTOR, "div.pageArea.type02 > strong.num > span").text.strip()
                                              ) > page_info_list[0]["num"]
                            )
                            print("  새로운 페이지 묶음 로드 확인.")
                        except TimeoutException:
                            print("  새로운 페이지 묶음을 찾는 데 시간 초과. 페이지네이션 종료.")
                            break
                        time.sleep(2)  # 추가 대기
            print(f"--- 보험 유형: {tab_text} 스크래핑 완료 ---")

    except Exception as e_main:
        print(f"스크래핑 중 주요 오류 발생: {e_main}")
        traceback.print_exc()
    finally:
        print("스크래핑 시도 종료. 브라우저를 닫습니다.")
        if 'driver' in locals() and driver is not None:
            driver.quit()

    return products_data


if __name__ == '__main__':
    print("Chubb Life 상품 정보 스크래핑 시작...")
    product_list = get_chubblife_product_info()

    if product_list:
        for idx, info in enumerate(product_list):
            print(f"\n--- 상품 {idx + 1} ---")
            print(f"상품명: {info.get('product_name', 'N/A')}")
            print(f"판매기간: {info.get('sales_period', 'N/A')}")
            print(f"상품요약서: {info.get('summary_link', 'N/A')}")
            print(f"사업방법서: {info.get('business_manual_link', 'N/A')}")
            print(f"약관: {info.get('terms_link', 'N/A')}")
    else:
        print("최종 추출된 상품 정보가 없습니다.")
