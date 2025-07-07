# 라이나생명보험/판매중단페이지
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from seleniumwire import webdriver
from webdriver_manager.chrome import ChromeDriverManager
import time
import re

# crawl_lina_product_announcements_by_type 함수는 드라이버를 인자로 받도록 변경


def crawl_lina_product_announcements_by_type(driver, url, main_or_rider_tab="주보험"):
    """
    리나 생명보험 웹사이트에서 판매 중인 상품 공시 정보를 크롤링합니다.
    "주보험" 또는 "특약" 탭을 선택한 후, 모든 보험 유형 탭을 순회하며
    각 상품을 클릭하여 상세 정보를 가져오고, 테이블 내 PDF 다운로드 링크를 추출한 후
    '이전 화면' 버튼을 클릭하여 목록으로 돌아옵니다.

    Args:
        driver (webdriver.Chrome): 이미 초기화된 Selenium WebDriver 인스턴스.
        url (str): 크롤링할 웹 페이지의 URL.
        main_or_rider_tab (str): 상위 탭 ('주보험' 또는 '특약').

    Returns:
        dict: 각 보험 유형별 상품 리스트를 포함하는 딕셔너리.
              각 상품은 상세 페이지의 정확한 상품명, 링크, 그리고 모든 상세 테이블 정보('details_tables')를 포함합니다.
    """
    all_product_data = {}

    try:
        # 초기 페이지 로딩 대기 시간: 'wrapper' 클래스를 가진 div가 로드될 때까지 기다립니다.
        # 이 요소는 페이지의 큰 컨테이너이므로, 전체 페이지가 준비되었음을 나타내는 데 더 적합합니다.
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.wrapper"))
        )
        print("초기 페이지 로딩 완료.")
        time.sleep(2)  # 추가적인 안정화를 위한 대기

        # 4. 상위 탭 선택 ('주보험' 또는 '특약') - 새 선택자 적용
        # 메인 탭: a.tab-item
        main_tab_xpath = f"//a[@class='tab-item' and normalize-space(text())='{main_or_rider_tab}']"
        try:
            target_main_tab = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, main_tab_xpath))
            )
            target_main_tab.click()
            print(f"'{main_or_rider_tab}' 탭을 클릭했습니다.")
            time.sleep(3)  # 탭 전환 후 페이지 안정화 대기
        except TimeoutException:
            print(f"'{main_or_rider_tab}' 상위 탭을 찾거나 클릭할 수 없습니다. (시간 초과)")
            return {}
        except Exception as e:
            print(f"상위 탭 클릭 중 오류 발생: {e}")
            return {}

        # 5. 모든 보험 유형 탭 순회 - 새 선택자 적용
        # 보험 유형 탭: ul.tab-type-list a.btn-item
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "ul.tab-type-list a.btn-item"))
        )

        tab_buttons_raw = driver.find_elements(By.CSS_SELECTOR, "ul.tab-type-list a.btn-item")
        tab_names = []
        for btn in tab_buttons_raw:
            tab_text = btn.text.strip()
            if tab_text:
                tab_names.append(tab_text)

        print(f"발견된 보험 유형 탭: {tab_names}")

        for tab_name in tab_names:
            print(f"\n--- '{tab_name}' 탭 크롤링 시작 ---")
            products_in_type = []
            try:
                # 탭을 클릭하기 위해 다시 해당 탭 요소를 찾습니다.
                current_type_tab_xpath = f"//ul[@class='tab-type-list']/li/a[@class='btn-item' and normalize-space(text())='{tab_name}']"
                current_tab_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, current_type_tab_xpath))
                )
                current_tab_button.click()
                print(f"'{tab_name}' 유형 탭을 클릭했습니다.")
                time.sleep(3)  # 유형 탭 전환 후 페이지 안정화 대기

                # 6. 각 유형 탭 내의 상품 목록 찾기 - 새 선택자 적용
                # 개별 상품 목록 버튼: a.prod-item
                WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.prod-list-group a.prod-item"))
                )
                product_list_elements = driver.find_elements(By.CSS_SELECTOR, "div.prod-list-group a.prod-item")

                initial_product_info = []
                for a_elem in product_list_elements:
                    try:
                        product_name_elem = a_elem.find_element(By.CSS_SELECTOR, "div.prod-name")
                        product_name = product_name_elem.text.strip()
                        initial_product_info.append({'name': product_name, 'link': url})
                    except NoSuchElementException:
                        print(f"상품명 (div.prod-name)을 찾을 수 없습니다: {a_elem.text}")
                        continue
                    except Exception as e:
                        print(f"초기 상품 정보 추출 중 오류 발생: {e}")
                        continue

                print(f"'{tab_name}' 탭에서 {len(initial_product_info)}개의 상품 발견.")

                # 각 상품을 클릭하여 상세 정보 추출
                for i, product_info in enumerate(initial_product_info):
                    current_product_details = {
                        'name': "상품명 없음",  # 상세 페이지에서 정확한 상품명으로 업데이트될 예정
                        'link': product_info['link'],
                        'details_tables': []  # 여러 테이블 데이터를 담을 리스트
                    }
                    try:
                        # 상품 버튼을 다시 찾아서 클릭 (StaleElementReferenceException 방지)
                        # 여기서는 initial_product_info의 이름을 사용해 버튼을 찾습니다.
                        # 상품명 `div.prod-name`을 포함하는 `a.prod-item`을 찾습니다.
                        product_button_xpath = f"//a[@class='prod-item'][.//div[@class='prod-name' and normalize-space(text())='{product_info['name']}']]"
                        product_button = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, product_button_xpath))
                        )

                        print(f"\n  클릭: {product_info['name']}")

                        # 상품 클릭 (현재 prod-item은 링크이므로 바로 클릭합니다. is-open 클래스 확인 불필요)
                        product_button.click()
                        time.sleep(3)  # 상세 내용 로딩 대기

                        # 상세 페이지 상단의 정확한 상품명 가져오기 - 새 선택자 적용
                        try:
                            detail_page_product_name_element = WebDriverWait(driver, 5).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, "h2.h-title"))
                            )
                            current_product_details['name'] = detail_page_product_name_element.text.strip()
                            print(f"  상세 페이지에서 확인된 상품명: {current_product_details['name']}")
                        except TimeoutException:
                            print("  상세 페이지 상품명 (h2.h-title) 로드 시간 초과.")
                        except NoSuchElementException:
                            print("  상세 페이지 상품명 (h2.h-title) 요소를 찾을 수 없습니다.")
                        except Exception as e:
                            print(f"  상세 페이지 상품명 추출 중 오류 발생: {e}")

                        # 7. 상세 내용 **모든** 테이블 추출 - 새 선택자 적용
                        # div.tbl-list-box 내의 모든 table 찾기
                        all_detail_tables_selector = "div.tbl-list-box table"

                        try:
                            detail_table_elements = WebDriverWait(driver, 5).until(
                                EC.presence_of_all_elements_located((By.CSS_SELECTOR, all_detail_tables_selector))
                            )
                            print(f"  총 {len(detail_table_elements)}개의 상세 테이블 발견.")

                            for table_idx, table_elem in enumerate(detail_table_elements):
                                table_data = []
                                try:
                                    table_body = table_elem.find_element(By.TAG_NAME, "tbody")
                                    rows = table_body.find_elements(By.TAG_NAME, "tr")

                                    for row_idx, row in enumerate(rows):
                                        row_info = {}
                                        cells = row.find_elements(By.TAG_NAME, "td")
                                        # 셀의 개수가 최소한 판매기간 + 3가지 PDF 버튼을 포함하는지 확인
                                        if len(cells) >= 4:
                                            row_info['판매기간'] = cells[0].text.strip()

                                            doc_types = ['상품요약서', '사업방법서', '약관']
                                            # 각 문서 타입에 대한 PDF 다운로드 링크 추출
                                            for j, doc_type in enumerate(doc_types):
                                                # PDF 버튼은 <td> 안에 있는 a.btn-down 입니다.
                                                try:
                                                    pdf_link_elem = cells[j + 1].find_element(By.CSS_SELECTOR, "a.btn-down")
                                                    pdf_link = pdf_link_elem.get_attribute("href")
                                                    row_info[doc_type] = pdf_link if pdf_link else "다운로드 링크 없음"
                                                except NoSuchElementException:
                                                    row_info[doc_type] = "PDF 다운로드 버튼 없음"
                                                except Exception as err:
                                                    print(f"      테이블 {table_idx + 1}, 행 {row_idx + 1} - '{doc_type}' PDF 링크 추출 중 오류: {err}")
                                                    row_info[doc_type] = f"링크 추출 오류: {err}"
                                        table_data.append(row_info)
                                    current_product_details['details_tables'].append(table_data)

                                except NoSuchElementException:
                                    print(f"  테이블 {table_idx + 1}의 tbody 또는 tr/td를 찾을 수 없습니다.")
                                    current_product_details['details_tables'].append(f"테이블 {table_idx + 1} 내용 없음")
                                except Exception as e:
                                    print(f"  테이블 {table_idx + 1} 처리 중 오류 발생: {e}")
                                    current_product_details['details_tables'].append(f"테이블 {table_idx + 1} 오류: {e}")

                        except TimeoutException:
                            print(f"  '{current_product_details['name']}' 상세 테이블 로드 시간 초과.")
                            current_product_details['details_tables'] = "상세 테이블 로드 실패 (시간 초과)"
                        except NoSuchElementException:
                            print(f"  '{current_product_details['name']}' 상세 테이블 요소를 찾을 수 없습니다.")
                            current_product_details['details_tables'] = "상세 테이블 요소 없음"
                        except Exception as e:
                            print(f"  '{current_product_details['name']}' 상세 테이블 처리 중 오류 발생: {e}")
                            current_product_details['details_tables'] = f"상세 테이블 오류: {e}"

                        # 8. '이전 화면' 버튼 클릭하여 목록으로 돌아가기 - 새 선택자 적용
                        # 이전화면 버튼: a.btn-prev
                        back_button_selector = "a.btn-prev"
                        try:
                            back_button = WebDriverWait(driver, 10).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, back_button_selector))
                            )
                            back_button.click()
                            print(f"  '{current_product_details['name']}' 상세 페이지에서 '이전화면'으로 돌아갑니다.")
                            time.sleep(3)

                            # 이전 화면으로 돌아온 후, 상품 목록이 다시 로드될 때까지 기다립니다.
                            WebDriverWait(driver, 10).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, "div.prod-list-group"))
                            )

                        except TimeoutException:
                            print(f"  '이전화면' 버튼을 찾거나 클릭할 수 없습니다 (시간 초과). 현재 페이지에 머무릅니다.")
                        except NoSuchElementException:
                            print(f"  '이전화면' 버튼 요소를 찾을 수 없습니다. 현재 페이지에 머무릅니다.")
                        except Exception as e:
                            print(f"  '이전화면' 버튼 클릭 중 예상치 못한 오류 발생: {e}. 현재 페이지에 머무릅니다.")

                    except StaleElementReferenceException:
                        print(f"  상품 버튼 참조가 만료되었습니다. 스킵합니다. (이전 상품명: {product_info['name']})")
                        continue
                    except TimeoutException:
                        print(f"  상품 클릭 또는 로딩 시간 초과. (상품명: {product_info['name']})")
                    except NoSuchElementException:
                        print(f"  상품 클릭 시 요소를 찾을 수 없습니다. (상품명: {product_info['name']})")
                    except Exception as e:
                        print(f"  상품 상세 처리 중 예상치 못한 오류 발생: {e}. (상품명: {product_info['name']})")

                    products_in_type.append(current_product_details)

                all_product_data[tab_name] = products_in_type
                print(f"'{tab_name}' 탭 크롤링 완료. 상품 수: {len(products_in_type)}")

            except TimeoutException:
                print(f"'{tab_name}' 탭을 찾거나 클릭할 수 없습니다 (시간 초과).")
            except NoSuchElementException:
                print(f"'{tab_name}' 탭 내의 요소를 찾을 수 없습니다.")
            except Exception as e:
                print(f"'{tab_name}' 탭 처리 중 예상치 못한 오류 발생: {e}")

        return all_product_data

    except TimeoutException:
        print("초기 페이지 로딩 시간 초과.")
        return {}
    except NoSuchElementException:
        print("초기 페이지에서 필요한 요소를 찾을 수 없습니다. 셀렉터를 확인하세요.")
        return {}
    except Exception as e:
        print(f"크롤링 중 예상치 못한 치명적인 오류 발생: {e}")
        return {}


# 메인 실행 부분
if __name__ == "__main__":
    target_url = "https://www.lina.co.kr/disclosure/product-public-announcement/product-on-sales?key=0"

    # 1. Chrome 옵션 설정
    chrome_options = Options()
    # 크롤링 시 브라우저 창을 띄우지 않으려면 다음 주석을 해제하세요.
    # chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920x1080")

    # 2. WebDriver 설정 및 초기화 (메인 블록에서 한 번만)
    service = Service(ChromeDriverManager().install())
    driver = None
    try:
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get(target_url)  # 초기 URL 접속

        print(f"'{target_url}' 에서 '주보험' 탭의 모든 보험 유형을 순회하며 상품 공시 정보를 크롤링합니다.")
        # 드라이버 인스턴스를 함수에 전달
        main_insurance_by_type_data = crawl_lina_product_announcements_by_type(driver, target_url, main_or_rider_tab="주보험")

        if main_insurance_by_type_data:
            print("\n--- 주보험 각 유형별 크롤링 결과 ---")
            for type_name, products in main_insurance_by_type_data.items():
                print(f"\n### 보험 유형: {type_name} ({len(products)}개 상품)")
                if products:
                    for product in products:
                        print(f"  상품명: {product['name']}")
                        if product.get('details_tables') and isinstance(product['details_tables'], list):
                            for table_idx, table_data in enumerate(product['details_tables']):
                                if isinstance(table_data, list):
                                    print(f"    테이블 {table_idx + 1} (행 수: {len(table_data)})")
                                    for row_idx, row_info in enumerate(table_data):
                                        print(f"      행 {row_idx + 1}:")
                                        print(f"        판매기간: {row_info.get('판매기간', 'N/A')}")
                                        print(f"        상품요약서 PDF: {row_info.get('상품요약서', 'N/A')}")
                                        print(f"        사업방법서 PDF: {row_info.get('사업방법서', 'N/A')}")
                                        print(f"        약관 PDF: {row_info.get('약관', 'N/A')}")
                                else:
                                    print(f"    테이블 {table_idx + 1} 데이터: {table_data}")
                        else:
                            print(f"  상세 테이블 데이터 없음: {product.get('details_tables', 'N/A')}")
                else:
                    print("  해당 유형에 상품이 없습니다.")
        else:
            print("주보험 각 유형별 크롤링된 데이터가 없습니다.")

        print(f"\n{'-' * 50}\n")

        # 특약 탭 크롤링은 페이지가 새로고침되는 등의 문제가 있을 수 있으므로
        # 주보험 크롤링 후 드라이버 상태를 재설정하거나,
        # 경우에 따라 새로운 드라이버 인스턴스를 사용하는 것이 안정적일 수 있습니다.
        # 여기서는 기존 드라이버를 재사용합니다.

        print(f"'{target_url}' 에서 '특약' 탭의 모든 보험 유형을 순회하며 상품 공시 정보를 크롤링합니다.")
        special_agreement_by_type_data = crawl_lina_product_announcements_by_type(driver, target_url, main_or_rider_tab="특약")

        if special_agreement_by_type_data:
            print("\n--- 특약 각 유형별 크롤링 결과 ---")
            for type_name, products in special_agreement_by_type_data.items():
                print(f"\n### 보험 유형: {type_name} ({len(products)}개 상품)")
                if products:
                    for product in products:
                        print(f"  상품명: {product['name']}")
                        if product.get('details_tables') and isinstance(product['details_tables'], list):
                            for table_idx, table_data in enumerate(product['details_tables']):
                                if isinstance(table_data, list):
                                    print(f"    테이블 {table_idx + 1} (행 수: {len(table_data)})")
                                    for row_idx, row_info in enumerate(table_data):
                                        print(f"      행 {row_idx + 1}:")
                                        print(f"        판매기간: {row_info.get('판매기간', 'N/A')}")
                                        print(f"        상품요약서 PDF: {row_info.get('상품요약서', 'N/A')}")
                                        print(f"        사업방법서 PDF: {row_info.get('사업방법서', 'N/A')}")
                                        print(f"        약관 PDF: {row_info.get('약관', 'N/A')}")
                                else:
                                    print(f"    테이블 {table_idx + 1} 데이터: {table_data}")
                        else:
                            print(f"  상세 테이블 데이터 없음: {product.get('details_tables', 'N/A')}")
                else:
                    print("  해당 유형에 상품이 없습니다.")
        else:
            print("특약 각 유형별 크롤링된 데이터가 없습니다.")

    except Exception as e:
        print(f"메인 크롤링 프로세스 중 치명적인 오류 발생: {e}")
    finally:
        if driver:
            driver.quit()
            print("WebDriver 종료.")
