from seleniumwire import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
import time
import traceback


def get_chubblife_product_info():
    options = webdriver.ChromeOptions()

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(60)  # 전체 페이지 로드 타임아웃 설정 (최대 60초)

    url = "https://www.chubblife.co.kr/front/official/sale/listSale.do"
    products_data = []

    try:
        driver.get(url)
        print(f"페이지 접속 완료: {url}")
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
            print(f"\n--- 보험 유형: {tab_text} 스크래핑 시작 ---")

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

            current_tab_product_elements = []  # 현재 탭의 상품 요소들을 담을 리스트 초기화

            if tab_idx == 0 and is_active_tab_initial_load:
                print(f"'{tab_text}' 탭은 초기 화면에서 이미 활성화되어 있습니다. 바로 상품 목록 스크래핑을 시도합니다.")
                try:
                    current_tab_product_elements = WebDriverWait(driver, 30).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, product_rows_selector))
                    )
                    if not current_tab_product_elements:
                        print(f"첫 번째 탭에 상품 목록이 없습니다. 다음 탭으로 이동합니다.")
                        continue
                    print("첫 번째 탭의 상품 목록 로드 확인.")
                    time.sleep(1)  # 추가 렌더링 대기
                except TimeoutException:
                    print(f"첫 번째 탭의 상품 목록을 찾는 데 시간 초과. 다음 탭으로 이동합니다.")
                    continue
            else:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", clickable_element)
                time.sleep(0.5)  # 스크롤 후 클릭 전 짧은 대기
                driver.execute_script("arguments[0].click();", clickable_element)
                print(f"'{tab_text}' 탭 클릭 완료. 페이지 로딩 대기...")

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
                        print(f"'{tab_text}' 탭에 상품 목록이 없습니다. 다음 탭으로 이동합니다.")
                        continue
                    print("새로운 탭의 상품 목록 로드 확인.")
                    time.sleep(1)  # 추가 렌더링 대기
                except TimeoutException:
                    print(f"'{tab_text}' 탭의 상품 목록을 찾는 데 시간 초과. 다음 탭으로 이동합니다.")
                    continue
                except StaleElementReferenceException:
                    print(f"StaleElementReferenceException 발생. '{tab_text}' 탭의 상품 목록을 다시 찾습니다.")
                    try:
                        current_tab_product_elements = WebDriverWait(driver, 30).until(
                            EC.presence_of_all_elements_located((By.CSS_SELECTOR, product_rows_selector))
                        )
                        if not current_tab_product_elements:
                            print(f"StaleElementReferenceException 후에도 상품 목록이 없습니다. 다음 탭으로 이동합니다.")
                            continue
                        print("StaleElementReferenceException 후 상품 목록 재로드 확인.")
                        time.sleep(1)
                    except TimeoutException:
                        print(f"StaleElementReferenceException 후에도 상품 목록 로드 시간 초과. 다음 탭으로 이동합니다.")
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
                        business_manual_link = "N/A"

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
                                    "page": current_page_num  # 현재 페이지 번호 사용
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
                        print(f"  페이지 번호 '{current_page_num + 1}' 클릭 완료. 새로운 페이지 로딩 대기...")
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
                    print(f"  페이지네이션 처리 중 예상치 못한 오류 발생: {e_pagination}")
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

    return products_data


if __name__ == '__main__':
    print("Chubb Life 상품 정보 스크래핑 시작...")

    final_products_data = get_chubblife_product_info()

    if final_products_data:
        print("\n--- 최종 추출된 상품 정보 ---")
        print(f"총 {len(final_products_data)}개의 상품 정보를 추출했습니다.")
    else:
        print("최종 추출된 상품 정보가 없습니다.")
