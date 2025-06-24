# 신한EZ손해보험/기능연결 db,pdf
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from seleniumwire import webdriver
from webdriver_manager.chrome import ChromeDriverManager
import time


def scrape_complex_insurance_products_final_with_logs(url):
    options = Options()
    # options.굳add_argument("--headless") # 브라우저를 백그라운드에서 실행 (GUI 없음)
    # options.add_argument("--disable-gpu")
    # options.add_argument("--no-sandbox")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    all_scraped_data = []

    try:
        driver.get(url)
        print(f"URL에 접속 중: {url}")

        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.data-body.salePrd-list[data-eid='prdBox']"))
        )
        print("페이지 로드 완료 및 최소 하나의 상품 박스(div) 확인.")

        product_box_containers_initial = driver.find_elements(By.CSS_SELECTOR, "div.data-body.salePrd-list[data-eid='prdBox']")
        container_infos = []
        for i, container in enumerate(product_box_containers_initial):
            container_infos.append({
                "index": i,
                "css_selector": f"div.data-body.salePrd-list[data-eid='prdBox']:nth-of-type({i + 1})"
            })

        for container_info in container_infos:
            container_idx = container_info["index"]
            container_selector = container_info["css_selector"]

            print(f"\n--- {container_idx + 1}번째 상품 테이블 컨테이너 처리 중 ---")

            try:
                current_container_div = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, container_selector))
                )

                tbody_element = current_container_div.find_element(By.CSS_SELECTOR, "tbody[data-eid='prdList']")
                print(f"  {container_idx + 1}번째 컨테이너 내에서 tbody[data-eid='prdList']를 찾았습니다.")

                product_name_elements_initial = tbody_element.find_elements(By.CSS_SELECTOR, "td.align-left a[data-bind='salePrdNmDepth1']")

                row_identifiers = []
                for i, elem in enumerate(product_name_elements_initial):
                    row_identifiers.append({
                        "product_name_text": elem.text.strip(),
                        "product_data_value": elem.get_attribute("data-value"),
                        "product_row_index": i
                    })

                fixed_download_button_container_selector = (
                    f"{container_selector} "
                    f"tbody[data-eid='prdList'] tr:nth-child(1) "
                    f"td.btn-col div[data-bind='salePrdNmDepth3']"
                )

                for prod_id_info in row_identifiers:
                    product_name = prod_id_info["product_name_text"]
                    product_data_value = prod_id_info["product_data_value"]
                    actual_product_row_index = prod_id_info["product_row_index"]

                    print(f"\n  --- 상품명 클릭 시도 (JS): {product_name} (실제 tr: {actual_product_row_index + 1}) ---")

                    try:
                        product_name_selector_to_click = (
                            f"{container_selector} "
                            f"tbody[data-eid='prdList'] tr:nth-child({actual_product_row_index + 1}) "
                            f"td.align-left a[data-bind='salePrdNmDepth1'][data-value='{product_data_value}']"
                        )
                        current_product_name_element = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, product_name_selector_to_click))
                        )

                        parent_td = current_product_name_element.find_element(By.XPATH, '..')
                        if 'is-active' not in parent_td.get_attribute('class'):
                            driver.execute_script("arguments[0].click();", current_product_name_element)
                            time.sleep(1)

                        sales_period_info_list = []
                        all_trs_in_tbody = tbody_element.find_elements(By.CSS_SELECTOR, "tr")

                        for tr_idx_for_sp, current_tr_element in enumerate(all_trs_in_tbody):
                            sales_period_selector_in_tr = (
                                f"{container_selector} "
                                f"tbody[data-eid='prdList'] tr:nth-child({tr_idx_for_sp + 1}) "
                                f"td:nth-child(2) a[data-bind='salePrdNmDepth2']"
                            )
                            try:
                                WebDriverWait(driver, 1).until(
                                    EC.presence_of_element_located((By.CSS_SELECTOR, sales_period_selector_in_tr))
                                )
                                WebDriverWait(driver, 1).until(
                                    EC.visibility_of_element_located((By.CSS_SELECTOR, sales_period_selector_in_tr))
                                )

                                elements_in_current_tr = driver.find_elements(By.CSS_SELECTOR, sales_period_selector_in_tr)

                                for sp_elem in elements_in_current_tr:
                                    if sp_elem.is_displayed() and sp_elem.text.strip():
                                        sales_period_info_list.append({
                                            "text": sp_elem.text.strip(),
                                            "data_value": sp_elem.get_attribute("data-value"),
                                            "data_index_number": sp_elem.get_attribute("data-index-number"),
                                            "origin_tr_index": tr_idx_for_sp + 1
                                        })
                            except (TimeoutException, NoSuchElementException):
                                pass

                        if not sales_period_info_list:
                            print(f"  상품 '{product_name}'에 대한 유효한 판매 기간을 여러 TR에서 찾을 수 없습니다.")
                            all_scraped_data.append({
                                "상품명": product_name,
                                "판매기간": "N/A (판매기간 없음)",
                                "다운로드_상품요약_가능": False,
                                "다운로드_약관_가능": False,
                                "다운로드_사업방법서_가능": False,
                                "컨테이너_인덱스": container_idx + 1
                            })
                            continue

                        for sp_info in sales_period_info_list:
                            sales_period_text = sp_info["text"]
                            sp_data_value = sp_info["data_value"]
                            sp_data_index_number = sp_info["data_index_number"]
                            origin_tr_index_for_sp = sp_info["origin_tr_index"]

                            print(f"    --- 판매 기간 클릭 시도 (JS): {sales_period_text} (상품: {product_name}, 발견 TR: {origin_tr_index_for_sp}) ---")

                            download_links_status = {
                                "상품요약": False,
                                "약관": False,
                                "사업방법서": False
                            }

                            try:
                                sales_period_link_selector_to_click = (
                                    f"{container_selector} "
                                    f"tbody[data-eid='prdList'] tr:nth-child({origin_tr_index_for_sp}) "
                                    f"td:nth-child(2) a[data-bind='salePrdNmDepth2'][data-value='{sp_data_value}']"
                                )
                                current_sales_period_element = WebDriverWait(driver, 10).until(
                                    EC.element_to_be_clickable((By.CSS_SELECTOR, sales_period_link_selector_to_click))
                                )

                                parent_td_sp = current_sales_period_element.find_element(By.XPATH, '..')
                                if 'is-active' not in parent_td_sp.get_attribute('class'):
                                    driver.execute_script("arguments[0].click();", current_sales_period_element)
                                time.sleep(1)

                                try:
                                    time.sleep(0.5)
                                    download_div = WebDriverWait(driver, 10).until(
                                        EC.visibility_of_element_located((By.CSS_SELECTOR, fixed_download_button_container_selector))
                                    )

                                    if download_div.is_displayed():
                                        buttons = download_div.find_elements(By.TAG_NAME, "button")
                                        for button in buttons:
                                            title = button.get_attribute("title")
                                            if title in download_links_status:
                                                download_links_status[title] = True
                                    else:
                                        print("      다운로드 버튼 div가 고정된 위치에 표시되지 않습니다. (is_displayed false)")

                                except TimeoutException:
                                    print(f"      판매 기간 '{sales_period_text}'에 대한 다운로드 버튼을 고정된 위치에서 찾을 수 없거나 표시되지 않음. (Timeout)")
                                except NoSuchElementException:
                                    print(f"      판매 기간 '{sales_period_text}'에 대한 다운로드 버튼 컨테이너를 고정된 위치에서 찾을 수 없음. (NoSuchElement)")

                                # --- 다운로드 가능 여부 즉시 출력 ---
                                print(
                                    f"        다운로드 상태: 상품요약={download_links_status['상품요약']}, 약관={download_links_status['약관']}, 사업방법서={download_links_status['사업방법서']}")

                                all_scraped_data.append({
                                    "상품명": product_name,
                                    "판매기간": sales_period_text,
                                    "다운로드_상품요약_가능": download_links_status["상품요약"],
                                    "다운로드_약관_가능": download_links_status["약관"],
                                    "다운로드_사업방법서_가능": download_links_status["사업방법서"],
                                    "컨테이너_인덱스": container_idx + 1
                                })

                            except TimeoutException:
                                print(f"    판매 기간 '{sales_period_text}' 클릭 실패 또는 요소를 고정된 위치에서 찾을 수 없음.")
                                all_scraped_data.append({
                                    "상품명": product_name,
                                    "판매기간": sales_period_text + " (클릭 실패/고정위치 요소 없음)",
                                    "다운로드_상품요약_가능": False,
                                    "다운로드_약관_가능": False,
                                    "다운로드_사업방법서_가능": False,
                                    "컨테이너_인덱스": container_idx + 1
                                })
                            except Exception as e:
                                print(f"    판매 기간 '{sales_period_text}' 처리 중 오류 발생 (고정 위치): {e}")
                                all_scraped_data.append({
                                    "상품명": product_name,
                                    "판매기간": sales_period_text + f" (오류 발생: {e})",
                                    "다운로드_상품요약_가능": False,
                                    "다운로드_약관_가능": False,
                                    "다운로드_사업방법서_가능": False,
                                    "컨테이너_인덱스": container_idx + 1
                                })

                    except StaleElementReferenceException:
                        print(f"  상품명 '{product_name}' 처리 중 StaleElementReferenceException 발생. DOM이 변경된 것으로 보입니다. 현재 상품은 건너뜁니다.")
                        break
                    except Exception as e:
                        print(f"  상품명 '{product_name}' 클릭 또는 처리 중 예상치 못한 오류 발생: {e}")
                        continue

            except NoSuchElementException:
                print(f"  {container_idx + 1}번째 컨테이너 내에서 tbody[data-eid='prdList']를 찾을 수 없습니다. 건너뜁니다.")
                continue
            except Exception as e:
                print(f"  컨테이너 {container_idx + 1} 처리 중 오류 발생: {e}")
                continue

    except TimeoutException:
        print("페이지 초기 요소 로드를 기다리는 중 시간 초과.")
    except Exception as e:
        print(f"전체 스크랩 중 치명적인 오류가 발생했습니다: {e}")
    finally:
        driver.quit()

    return all_scraped_data


if __name__ == "__main__":
    target_url = "https://www.shinhanez.co.kr/static/pub/PUB2000T021.html"
    scraped_data = scrape_complex_insurance_products_final_with_logs(target_url)

    if scraped_data:
        print("\n--- 모든 컨테이너에서 스크랩된 보험 상품 데이터 ---")
        for product in scraped_data:
            print(product)
        print(f"\n총 {len(scraped_data)}개의 데이터 포인트가 수집되었습니다.")
    else:
        print("스크랩된 데이터가 없습니다.")
