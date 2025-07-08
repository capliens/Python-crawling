# 라이나생명보험/판매중단페이지
import time
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from seleniumwire import webdriver
from webdriver_manager.chrome import ChromeDriverManager


def wait_for_spinner_to_disappear(driver, timeout=10):
    """
    (선택 사항) 로딩 스피너가 사라질 때까지 기다립니다.
    스피너 요소의 정확한 CSS 셀렉터를 파악해야 합니다.
    """
    pass


def _scrape_products_by_type(driver, select_type, pane_id_prefix):
    """
    지정된 유형(주보험/특약) 내의 모든 상품군과 그 안의 모든 상품 상세 정보를 스크랩하는 내부 함수.
    :param driver: Selenium WebDriver 인스턴스
    :param select_type: '주보험' 또는 '특약'
    :param pane_id_prefix: 해당 유형의 패널 ID 접두사 (예: 'pane-B' 또는 'pane-R')
    :return: 현재 유형에서 스크랩된 데이터 리스트
    """
    scraped_data_for_type = []

    # --- 1단계: 유형 탭 선택 ---
    type_xpath = f'//*[@id="tab-{pane_id_prefix.split("-")[1]}"]'
    print(f"\n--- '{select_type}' 탭 선택 시작 ---")
    try:
        type_element = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, type_xpath))
        )
        driver.execute_script("arguments[0].click();", type_element)
        print(f"'{select_type}' 탭 JavaScript 클릭 완료.")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, f'//*[@id="{pane_id_prefix}"]/div[1]/button'))
        )
        print("탭 클릭 후 상품군 버튼 로딩 완료.")

    except TimeoutException:
        print(f"ERROR: '{select_type}' 탭을 클릭하는 중 타임아웃이 발생했습니다. 이 유형 스크래핑을 건너뜝니다.")
        return []
    except NoSuchElementException:
        print(f"ERROR: '{select_type}' 탭 요소를 찾을 수 없습니다. XPath: {type_xpath}. 이 유형 스크래핑을 건너뜝니다.")
        return []
    except StaleElementReferenceException:
        print(f"WARNING: '{select_type}' 탭 요소에 대한 StaleElementReferenceException 발생. 다시 시도합니다.")
        # StaleElementReferenceException 발생 시 요소를 다시 찾아서 클릭 시도
        type_element = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, type_xpath))
        )
        driver.execute_script("arguments[0].click();", type_element)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, f'//*[@id="{pane_id_prefix}"]/div[1]/button'))
        )
    print(f"--- '{select_type}' 탭 선택 완료 ---")

    # --- 2단계: 모든 상품군 순회 ---
    group_buttons_xpath = f'//*[@id="{pane_id_prefix}"]/div[1]/button'
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, group_buttons_xpath))
        )

        initial_group_elements = driver.find_elements(By.XPATH, group_buttons_xpath)
        num_groups = len(initial_group_elements)
        print(f"\n총 {num_groups}개의 상품군을 찾았습니다. 각 상품군을 순회합니다.")

        for g_idx in range(num_groups):
            # 상품군 버튼이 StaleElementReferenceException을 일으킬 수 있으므로, 루프마다 새로 찾습니다.
            group_elements = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, group_buttons_xpath))
            )

            if g_idx >= len(group_elements):
                print(f"WARNING: 상품군 인덱스 {g_idx}를 찾을 수 없습니다. (리스트 크기: {len(group_elements)}). 상품군 루프를 종료합니다.")
                break

            group_element_to_click = group_elements[g_idx]
            group_text = group_element_to_click.text
            print(f"\n--- 상품군 '{group_text}' ({g_idx + 1}/{num_groups}) 순회 시작 ({select_type} 탭) ---")

            try:
                driver.execute_script("arguments[0].click();", group_element_to_click)
                print(f"상품군 '{group_text}' JavaScript 클릭 완료.")

                product_list_ul_xpath = f'//*[@id="{pane_id_prefix}"]/div[2]/div[2]/ul'
                WebDriverWait(driver, 20).until(  # 상품군 클릭 후 상품 목록 로딩 대기
                    EC.presence_of_element_located((By.XPATH, product_list_ul_xpath))
                )
                print("상품군 클릭 후 상품 목록 UL 로딩 완료.")

                # --- 3단계: 모든 상품 순회 및 상세 정보 추출 ---
                product_list_items_xpath = f'{product_list_ul_xpath}/li'
                WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.XPATH, product_list_items_xpath))
                )

                initial_product_elements = driver.find_elements(By.XPATH, product_list_items_xpath)
                num_products = len(initial_product_elements)
                print(f"\n총 {num_products}개의 상품을 찾았습니다. 각 상품의 상세 정보를 추출합니다.")

                for i in range(num_products):
                    print(f"\n--- 상품 {i + 1}/{num_products} 상세 정보 추출 시작 (상품군: {group_text}, 유형: {select_type}) ---")

                    product_elements = WebDriverWait(driver, 10).until(
                        EC.presence_of_all_elements_located((By.XPATH, product_list_items_xpath))
                    )

                    if i >= len(product_elements):
                        print(f"WARNING: 상품 목록 인덱스 {i}를 찾을 수 없습니다. (리스트 크기: {len(product_elements)}). 루프를 종료합니다.")
                        break

                    product_button = product_elements[i].find_element(By.TAG_NAME, "button")
                    product_name_on_list = product_button.text

                    print(f"상품 '{product_name_on_list}' 클릭 시도...")
                    driver.execute_script("arguments[0].click();", product_button)
                    print(f"상품 '{product_name_on_list}' JavaScript 클릭 완료. 상세 페이지로 이동합니다.")

                    WebDriverWait(driver, 15).until(  # 상세 페이지 헤더 로딩 대기
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".c-title_title.fs-24 span"))
                    )
                    print("상세 페이지 로딩 완료.")

                    # --- 4단계: 상세 페이지 내 모든 상품 섹션 정보 추출 (PDF URL 추출 포함) ---
                    all_extracted_products_data_for_current_page = []

                    all_product_sections_xpath = f'//*[@id="{pane_id_prefix}"]/div[@class="l-section gap-bottom" and not(.//div[@class="bottom-buttons single"])]'

                    try:
                        WebDriverWait(driver, 20).until(
                            EC.presence_of_all_elements_located((By.XPATH, all_product_sections_xpath))
                        )
                        product_sections = driver.find_elements(By.XPATH, all_product_sections_xpath)

                        if not product_sections:
                            print("WARNING: 상세 페이지에서 상품 섹션을 찾을 수 없습니다. XPath를 확인하세요.")

                        for section_idx, section in enumerate(product_sections):
                            current_section_data = {}

                            try:
                                product_name_element = section.find_element(By.CSS_SELECTOR, ".c-title_title.fs-24 span")
                                current_section_data["상품명"] = product_name_element.text.strip()
                            except NoSuchElementException:
                                print("WARNING: 상품 섹션에서 상품명 요소를 찾을 수 없습니다.")
                                current_section_data["상품명"] = "N/A"

                            section_tables_xpath = './/div[@class="l-table"]//table'

                            try:
                                tables_in_section = section.find_elements(By.XPATH, section_tables_xpath)

                                current_section_data["판매기간_및_문서"] = []
                                if not tables_in_section:
                                    print(f"WARNING: 상품 '{current_section_data['상품명']}' 섹션에서 테이블을 찾을 수 없습니다.")

                                for table_in_section_idx, table in enumerate(tables_in_section):
                                    try:
                                        rows = table.find_elements(By.TAG_NAME, "tr")

                                        if not rows:
                                            try:
                                                table_body = table.find_element(By.TAG_NAME, "tbody")
                                                rows = table_body.find_elements(By.TAG_NAME, "tr")
                                            except NoSuchElementException:
                                                pass

                                        for row in rows:
                                            row_data = {}
                                            try:
                                                sales_period_cell = row.find_element(By.CSS_SELECTOR, "td:nth-child(1) .cell")
                                                row_data["판매기간"] = sales_period_cell.text.strip()

                                                doc_types = ["상품요약서", "사업방법서", "약관"]
                                                for j, doc_type in enumerate(doc_types):
                                                    doc_info_key = f"{doc_type}_URL"
                                                    try:
                                                        doc_button = row.find_element(By.CSS_SELECTOR, f"td:nth-child({j + 2}) button.down-button")

                                                        original_window = driver.current_window_handle
                                                        current_window_handles = driver.window_handles

                                                        print(f"    '{doc_type}' 다운로드 버튼 클릭 시도...")
                                                        driver.execute_script("arguments[0].click();", doc_button)
                                                        time.sleep(2)  # 새 탭이 열릴 시간을 줍니다 (기존 1초에서 2초로 증가)

                                                        new_window_handles = [
                                                            handle for handle in driver.window_handles if handle not in current_window_handles]

                                                        if len(new_window_handles) == 1:
                                                            new_tab_handle = new_window_handles[0]
                                                            driver.switch_to.window(new_tab_handle)

                                                            try:
                                                                # PDF URL이 로드될 때까지 대기. .pdf 확장자를 포함하는 URL 대기
                                                                WebDriverWait(driver, 20).until(EC.url_contains(".pdf"))
                                                                # body 태그가 로드될 때까지 대기하여 페이지 로딩 완료 확인
                                                                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

                                                                pdf_url = driver.current_url
                                                                row_data[doc_type] = "PDF 다운로드 버튼 존재"
                                                                row_data[doc_info_key] = pdf_url
                                                                print(f"      '{doc_type}' URL 추출 완료: {pdf_url}")

                                                            except TimeoutException as url_timeout_e:
                                                                print(
                                                                    f"    ERROR: '{doc_type}' URL 로딩 중 타임아웃 발생 (2차 대기 오류). 다음 문서로 진행: {url_timeout_e}")
                                                                row_data[doc_type] = "PDF 다운로드 버튼 존재 (URL 추출 실패: 로딩 타임아웃)"
                                                                row_data[doc_info_key] = "ERROR: PDF URL loading timeout"
                                                            finally:  # URL 추출 실패 여부와 관계없이 새 탭을 닫고 원래 탭으로 복귀
                                                                try:
                                                                    driver.close()  # 새 탭 닫기
                                                                except Exception as close_err:
                                                                    print(f"    WARNING: 새 탭 닫기 중 오류 발생: {close_err}")
                                                                driver.switch_to.window(original_window)  # 원래 탭으로 복귀
                                                                print(f"    새 탭 닫고 원래 탭으로 복귀 완료.")

                                                        elif len(new_window_handles) > 1:
                                                            print(
                                                                f"    WARNING: '{doc_type}' 버튼 클릭 후 여러 개의 새 탭이 열렸습니다. (개수: {len(new_window_handles)}). URL 추출 실패.")
                                                            row_data[doc_type] = "PDF 다운로드 버튼 존재 (오류로 URL 추출 실패: 여러 탭 열림)"
                                                            row_data[doc_info_key] = "ERROR: Multiple tabs opened"
                                                            for handle in new_window_handles:  # 열린 모든 새 탭 닫기 시도
                                                                try:
                                                                    driver.switch_to.window(handle)
                                                                    driver.close()
                                                                except Exception as close_e:
                                                                    print(f"    WARNING: 여러 탭 닫기 중 오류 발생: {close_e}")
                                                            driver.switch_to.window(original_window)  # 원래 탭으로 복귀
                                                            print(f"    열린 모든 새 탭을 닫고 원래 탭으로 복귀 완료.")
                                                        else:
                                                            print(f"    WARNING: '{doc_type}' 버튼 클릭 후 새 탭이 열리지 않았습니다. (URL 추출 실패).")
                                                            row_data[doc_type] = "PDF 다운로드 버튼 존재 (URL 추출 실패: 새 탭 없음)"
                                                            row_data[doc_info_key] = "N/A (새 탭 없음)"

                                                    except NoSuchElementException:
                                                        row_data[doc_type] = "다운로드 링크 없음"
                                                        row_data[doc_info_key] = "N/A"
                                                    except TimeoutException as e:  # 이 부분은 이제 새 탭 감지/전환 관련 초기 타임아웃만 처리
                                                        print(f"    ERROR: '{doc_type}' 새 탭 감지 또는 탭 전환 중 초기 타임아웃 발생: {e}")
                                                        row_data[doc_type] = "PDF 다운로드 버튼 존재 (URL 추출 실패: 새 탭 감지/전환 초기 타임아웃)"
                                                        row_data[doc_info_key] = "ERROR: Tab detection/switch initial timeout"
                                                        try:  # 오류 발생 시에도 원래 탭으로 돌아가도록 안전장치 추가
                                                            driver.switch_to.window(original_window)
                                                        except Exception as re_e:
                                                            print(f"    CRITICAL WARNING: 원래 탭 복귀 중 오류 발생: {re_e}")

                                                    except Exception as e:  # 그 외 예상치 못한 오류 처리
                                                        print(f"    ERROR: '{doc_type}' URL 추출 중 예상치 못한 오류 발생: {e}")
                                                        row_data[doc_type] = "PDF 다운로드 버튼 존재 (URL 추출 실패: 알 수 없는 오류)"
                                                        row_data[doc_info_key] = "ERROR: Unknown"
                                                        try:  # 오류 발생 시에도 원래 탭으로 돌아가도록 안전장치 추가
                                                            driver.switch_to.window(original_window)
                                                        except Exception as re_e:
                                                            print(f"    CRITICAL WARNING: 원래 탭 복귀 중 오류 발생: {re_e}")
                                            except Exception as e:  # 판매기간 셀을 찾지 못하면 해당 행 건너뛰기
                                                # print(f"    WARNING: 행 데이터 추출 중 오류 발생, 행 건너뜀: {e}") # 너무 많은 로그 방지 위해 주석 처리
                                                continue

                                            if row_data.get("판매기간"):  # 판매기간이 있는 유효한 행만 추가
                                                current_section_data["판매기간_및_문서"].append(row_data)

                                    except Exception as e:
                                        print(f"WARNING: 상품 '{current_section_data['상품명']}' 테이블 {table_in_section_idx + 1} 처리 중 예상치 못한 오류 발생: {e}")

                                    for item in current_section_data["판매기간_및_문서"]:
                                        print(f"    판매기간: {item.get('판매기간', 'N/A')}")
                                        print(f"      상품요약서: {item.get('상품요약서', 'N/A')}, URL: {item.get('상품요약서_URL', 'N/A')}")
                                        print(f"      사업방법서: {item.get('사업방법서', 'N/A')}, URL: {item.get('사업방법서_URL', 'N/A')}")
                                        print(f"      약관: {item.get('약관', 'N/A')}, URL: {item.get('약관_URL', 'N/A')}")

                            except Exception as e:
                                print(f"WARNING: 상품 '{current_section_data['상품명']}' 섹션 내 테이블 추출 중 오류 발생: {e}")

                            all_extracted_products_data_for_current_page.append(current_section_data)

                    except TimeoutException:
                        print("WARNING: 상세 페이지 내 상품 섹션 로딩 중 타임아웃이 발생했습니다.")
                    except NoSuchElementException:
                        print("WARNING: 상세 페이지 내 상품 섹션 요소를 찾을 수 없습니다.")
                    except Exception as e:
                        print(f"ERROR: 상세 페이지 모든 상품 정보 추출 중 예상치 못한 오류 발생: {e}")

                    scraped_data_for_type.append({
                        "유형": select_type,
                        "상품군": group_text,
                        "클릭한_상품명_목록": product_name_on_list,
                        "상세_페이지_내_추출된_상품들": all_extracted_products_data_for_current_page
                    })

                    # --- 5단계: 이전 화면으로 돌아가기 ---
                    try:
                        back_button_xpath = f'//*[@id="{pane_id_prefix}"]//button[span[contains(text(), "이전화면")]]'
                        print(f"\n'이전화면' 버튼 클릭 시도: {back_button_xpath}")

                        back_button = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, back_button_xpath))
                        )
                        driver.execute_script("arguments[0].click();", back_button)
                        print("'이전화면' JavaScript 클릭 완료. 상품 목록 페이지로 돌아갑니다.")

                        WebDriverWait(driver, 30).until(  # 상품 목록 페이지가 완전히 로딩될 때까지 대기
                            EC.presence_of_element_located((By.XPATH, product_list_ul_xpath))
                        )
                        print(f"상품 목록 페이지 로딩 완료. 다음 상품 ({i + 2}/{num_products})으로 이동합니다.")

                    except TimeoutException:
                        print("ERROR: '이전화면' 버튼을 클릭하거나 상품 목록 페이지 로딩 중 타임아웃이 발생했습니다. 현재 상품군 순회를 중단합니다.")
                        break
                    except NoSuchElementException:
                        print("ERROR: '이전화면' 버튼 요소를 찾을 수 없습니다. XPath를 확인하세요. 현재 상품군 순회를 중단합니다.")
                        break
                    except StaleElementReferenceException:
                        print("WARNING: '이전화면' 버튼 요소에 대한 StaleElementReferenceException 발생. 다시 시도합니다.")
                        back_button = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, back_button_xpath))
                        )
                        driver.execute_script("arguments[0].click();", back_button)
                        WebDriverWait(driver, 30).until(
                            EC.presence_of_element_located((By.XPATH, product_list_ul_xpath))
                        )
                        print(f"상품 목록 페이지 로딩 완료. 다음 상품 ({i + 2}/{num_products})으로 이동합니다.")
                    except Exception as e:
                        print(f"ERROR: '이전화면' 버튼 처리 중 예상치 못한 오류 발생: {e}. 현재 상품군 순회를 중단합니다.")
                        break

                print(f"--- 상품군 '{group_text}' 내 모든 상품 추출 완료 ({select_type} 탭) ---")

            except TimeoutException:
                print(f"ERROR: 상품군 '{group_text}' 클릭 후 상품 목록 UL 로딩 중 타임아웃이 발생했습니다. 이 상품군 스크래핑을 건너뜁니다.")
            except NoSuchElementException:
                print(f"ERROR: 상품군 '{group_text}' 요소를 찾을 수 없습니다. 해당 인덱스에 상품군이 없거나 XPath가 잘못되었을 수 있습니다. 이 상품군 스크래핑을 건너뜁니다.")
            except IndexError:
                print(f"ERROR: 잘못된 상품군 인덱스({g_idx + 1})입니다. 유효한 인덱스를 입력해주세요. 이 상품군 스크래핑을 건너뜀니다.")
            except Exception as e:
                print(f"ERROR: 상품군 선택 또는 상품 목록 순회 중 예상치 못한 오류 발생: {e}. 이 상품군 스크래핑을 건너뜁니다.")

    except TimeoutException:
        print(f"ERROR: 상품군 버튼 로딩 중 타임아웃이 발생했습니다. 이 유형의 상품군 스크래핑을 건너뜁니다.")
    except NoSuchElementException:
        print(f"ERROR: 상품군 버튼 요소를 찾을 수 없습니다. XPath: {group_buttons_xpath}. 이 유형의 상품군 스크래핑을 건너뜁니다.")
    except Exception as e:
        print(f"ERROR: 상품군 순회 중 예상치 못한 오류 발생: {e}. 이 유형의 상품군 스크래핑을 건너뜁니다.")

    return scraped_data_for_type


def scrape_all_lina_products(url):
    """
    지정된 URL의 리나생명 웹사이트에서 '주보험'과 '특약' 탭의 모든 상품 정보를 스크랩하는 메인 함수.
    :param url: 스크랩할 웹사이트 URL
    :return: 모든 스크랩된 데이터를 담은 리스트
    """
    chrome_options = Options()
    # 크롤링 동작을 눈으로 확인하려면 아래 주석을 해제하세요.
    # chrome_options.add_argument("--headless") # 실제 브라우저 동작을 보려면 주석 처리
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")

    service = Service(ChromeDriverManager().install())

    driver = None
    all_scraped_data_overall = []

    try:
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get(url)

        print(f"'{url}' 페이지 로딩 중...")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        print("페이지 로딩 완료.")

        # --- 최상위 루프: '주보험' 탭과 '특약' 탭 순회 ---
        types_to_scrape = [
            ("주보험", "pane-B"),
            ("특약", "pane-R")
        ]

        for select_type, pane_id_prefix in types_to_scrape:
            print(f"\n\n============= {select_type} 탭 전체 스크랩 시작 =============")
            # 탭을 전환하기 전에 페이지 상태가 안정될 시간을 줍니다.
            time.sleep(2)

            data_from_current_type = _scrape_products_by_type(driver, select_type, pane_id_prefix)
            all_scraped_data_overall.extend(data_from_current_type)
            print(f"============= {select_type} 탭 전체 스크랩 완료 =============")

    except TimeoutException:
        print(f"ERROR: 초기 페이지 로딩 중 타임아웃이 발생했습니다: {url}")
    except Exception as e:
        print(f"ERROR: 웹 드라이버를 초기화하거나 페이지에 접근하는 중 예상치 못한 오류가 발생했습니다: {e}")
    finally:
        if driver:
            driver.quit()
            print("\n브라우저를 닫았습니다.")

    return all_scraped_data_overall


# 실행 예시
if __name__ == "__main__":
    target_url = "https://www.lina.co.kr/disclosure/product-public-announcement/product-on-sales?key=0"

    print("\n--- 리나생명 웹사이트 전체 상품 정보 추출 시작 ---")
    scraped_data = scrape_all_lina_products(target_url)

    # 추출된 모든 데이터 확인
    print("\n--- 모든 상품의 최종 스크랩 데이터 ---")
    if scraped_data:
        for product_entry in scraped_data:
            print(f"유형: {product_entry['유형']}, 상품군: {product_entry['상품군']}, 클릭한 상품명: {product_entry['클릭한_상품명_목록']}")
            for detail_item in product_entry['상세_페이지_내_추출된_상품들']:
                print(f"  추출된 상세 상품명: {detail_item.get('상품명', 'N/A')}")
                for doc_info in detail_item.get('판매기간_및_문서', []):
                    print(f"    판매기간: {doc_info.get('판매기간', 'N/A')}")
                    print(f"      상품요약서: {doc_info.get('상품요약서', 'N/A')}, URL: {doc_info.get('상품요약서_URL', 'N/A')}")
                    print(f"      사업방법서: {doc_info.get('사업방법서', 'N/A')}, URL: {doc_info.get('사업방법서_URL', 'N/A')}")
                    print(f"      약관: {doc_info.get('약관', 'N/A')}, URL: {doc_info.get('약관_URL', 'N/A')}")
            print("-" * 30)
    else:
        print("추출된 데이터가 없습니다.")

    print(f"\n총 {len(scraped_data)}개의 상품 정보를 추출했습니다.")
