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
                WebDriverWait(driver, 20).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, product_rows_selector))
                )
                print("새로운 탭의 상품 목록 로드 확인.")
                time.sleep(2)  # 추가 대기
            except TimeoutException:
                print(f"'{tab_text}' 탭의 상품 목록을 찾는 데 시간 초과. 다음 탭으로 이동합니다.")
                continue  # 다음 탭으로 넘어감

                # 모달창 열기 및 정보 가져오는 기능 주석 처리 (사용자 요청)
                try:
                    modal_trigger_selector = "td:nth-child(3) > a"  # 3번째 td 안의 a
                    modal_trigger = row.find_element(By.CSS_SELECTOR, modal_trigger_selector)

                    # 클릭 전 요소가 보이도록 스크롤
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", modal_trigger)
                    time.sleep(0.5)

                    # ElementClickInterceptedException 방지를 위해 JavaScript 클릭 시도
                    driver.execute_script("arguments[0].click();", modal_trigger)
                    print(f"'{product_name_in_list}' 상품의 모달창 열기 시도...")

                    # 모달창 로딩 대기
                    modal_selector = "div#pop_official_06"
                    WebDriverWait(driver, 20).until(
                        EC.visibility_of_element_located((By.CSS_SELECTOR, modal_selector))
                    )
                    print("모달창 로드 완료.")
                    time.sleep(1)  # 모달 내부 컨텐츠 로딩 추가 대기

                    modal_element = driver.find_element(By.CSS_SELECTOR, modal_selector)

                    # 모달 내부 정보 추출
                    # 사용자 정보: div.tableType05 > table > thead 안에 tr 들안에 td들이며 첫번째 tr 은 th로 이루어져 있음
                    # tbody가 없으므로 table 바로 아래 tr들을 찾고, 첫번째 tr이 헤더인지 확인
                    modal_table_all_rows = modal_element.find_elements(By.CSS_SELECTOR, "div.tableType05 > table  tr")

                    sales_period = "N/A"
                    summary_link = "N/A"
                    business_manual_link = "N/A"
                    terms_link = "N/A"

                    current_modal_product_name = "N/A"  # 모달 내 rowspan 상품명 추적

                    # 모달 내 테이블의 실제 데이터 행(td로 구성된 행)을 찾습니다.
                    # 첫번째 tr은 th로 이루어져 있으므로 건너뛰거나, th_cells로 확인
                    data_rows_in_modal = []
                    for r_idx, m_row in enumerate(modal_table_all_rows):
                        m_th_cells = m_row.find_elements(By.TAG_NAME, "th")
                        m_td_cells = m_row.find_elements(By.TAG_NAME, "td")

                        if m_th_cells and m_th_cells[0].text.strip() == "상품명":  # 헤더 행 (첫번째 tr)
                            continue  # 헤더는 건너뜀

                        # 실제 데이터 행 (td로 시작)
                        if m_td_cells:
                            data_rows_in_modal.append(m_td_cells)

                    if not data_rows_in_modal:
                        print("모달 내에서 데이터 행을 찾지 못했습니다.")
                        # 모달 닫기 로직으로 바로 이동
                    else:
                        # 첫번째 데이터 행의 첫번째 td가 상품명이고 rowspan을 가질 수 있음
                        # 이 상품명을 current_modal_product_name으로 설정하고, 이후 행에서 재사용
                        first_data_row_cells = data_rows_in_modal[0]
                        if first_data_row_cells and first_data_row_cells[0].get_attribute("rowspan"):
                            current_modal_product_name = first_data_row_cells[0].text.strip()
                        else:  # rowspan이 없으면 해당 행의 상품명 사용
                            current_modal_product_name = first_data_row_cells[0].text.strip()  # 첫번째 td가 상품명

                        for m_td_cells in data_rows_in_modal:
                            # 상품명 (모달 내): m_td_cells[0] (rowspan 가능성)
                            # 판매기간: m_td_cells[1] (일반 상품) 또는 m_td_cells[0] (특약)
                            # 상품요약서: m_td_cells[2] > a (일반 상품)
                            # 사업방법서: m_td_cells[3] > a (일반 상품) 또는 m_td_cells[2] > a (특약)
                            # 약관: m_td_cells[4] > a (일반 상품) 또는 m_td_cells[3] > a (특약)

                            # 현재 행의 상품명 (rowspan 처리)
                            if m_td_cells[0].get_attribute("rowspan"):  # 현재 td가 rowspan을 가지면 새로운 상품명
                                current_modal_product_name = m_td_cells[0].text.strip()
                                # 이 경우, 판매기간은 m_td_cells[1]부터 시작
                                sales_period_idx = 1
                                summary_idx = 2
                                bm_idx = 3
                                terms_idx = 4
                            else:  # rowspan이 없으면 이전 상품명 사용
                                sales_period_idx = 0  # 판매기간이 첫번째 td
                                summary_idx = 1
                                bm_idx = 2
                                terms_idx = 3

                            # 특약과 일반 상품의 td 개수 차이 처리
                            if len(m_td_cells) >= 5:  # 일반 상품 (상품요약서, 사업방법서 모두 있음)
                                sales_period = m_td_cells[sales_period_idx].text.strip()
                                summary_links_modal = m_td_cells[summary_idx].find_elements(By.TAG_NAME, "a")
                                summary_link = summary_links_modal[0].get_attribute('href') if summary_links_modal else "N/A"
                                bm_links_modal = m_td_cells[bm_idx].find_elements(By.TAG_NAME, "a")
                                business_manual_link = bm_links_modal[0].get_attribute('href') if bm_links_modal else "N/A"
                                terms_links_modal = m_td_cells[terms_idx].find_elements(By.TAG_NAME, "a")
                                terms_link = terms_links_modal[0].get_attribute('href') if terms_links_modal else "N/A"
                            elif len(m_td_cells) == 4:  # 특약 (상품요약서 없음)
                                sales_period = m_td_cells[sales_period_idx].text.strip()
                                summary_link = "N/A"  # 특약은 상품요약서 없음
                                bm_links_modal = m_td_cells[bm_idx - 1].find_elements(By.TAG_NAME, "a")  # 인덱스 조정
                                business_manual_link = bm_links_modal[0].get_attribute('href') if bm_links_modal else "N/A"
                                terms_links_modal = m_td_cells[terms_idx - 1].find_elements(By.TAG_NAME, "a")  # 인덱스 조정
                                terms_link = terms_links_modal[0].get_attribute('href') if terms_links_modal else "N/A"
                            else:
                                print(f"모달 내 데이터 행의 td 개수가 예상과 다릅니다: {len(m_td_cells)}개. 건너뜁니다.")
                                continue  # 이 행은 건너뛰고 다음 상품으로

                            products_data.append({
                                "product_name": current_modal_product_name,  # 모달 내 상품명 사용
                                "sales_period": sales_period,
                                "summary_link": summary_link,
                                "terms_link": terms_link,
                                "business_manual_link": business_manual_link
                            })

                            print(f"  판매기간: {sales_period}")
                            print(f"  상품요약서: {summary_link}")
                            print(f"  사업방법서: {business_manual_link}")
                            print(f"  약관: {terms_link}")

                    # 모달 닫기 (사용자 제공 선택자: button#closeBtn)
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
                        time.sleep(1)  # 모달 닫히는 시간 대기
                    except Exception as e_modal_close:
                        print(f"모달 닫기 중 오류: {e_modal_close}")
                        # 모달이 안 닫혀도 다음으로 진행 시도

                except TimeoutException:
                    print(f"'{product_name_in_list}' 상품의 모달창을 열거나 내용을 찾는 데 시간 초과.")
                except NoSuchElementException:
                    print(f"'{product_name_in_list}' 상품의 모달창 열기 버튼 또는 내부 요소를 찾을 수 없음.")
                except Exception as e_modal:
                    print(f"'{product_name_in_list}' 상품 모달 처리 중 오류: {e_modal}")

                # --- 페이지네이션 처리 ---
                pagination_container_selector = "div.pageArea.type02"
                next_button_selector = "a.btnNext"

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
