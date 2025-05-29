from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time

# db저장/판매중지/pdf 링크


def get_hanwhalife_product_info_selenium():
    service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")
    driver = webdriver.Chrome(service=service, options=options)
    driver.maximize_window()

    base_url = "https://www.hanwhalife.com/main/disclosure/goods/disclosurenotice/DF_GDDN000_P10000.do?MENU_ID1=DF_GDGL000"
    product_data_collected = []

    try:
        driver.get(base_url)
        category_list_selector = "tbody#List1 tr"
        WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, category_list_selector)))
        num_categories = len(driver.find_elements(
            By.CSS_SELECTOR, category_list_selector))
        print(f"총 {num_categories}개의 상품구분 발견.")

        for cat_idx in range(num_categories):
            category_name_text = f"상품구분_인덱스_{cat_idx}"
            try:
                driver.get(base_url)
                WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, category_list_selector)))
                category_rows_refreshed = driver.find_elements(
                    By.CSS_SELECTOR, category_list_selector)
                if cat_idx >= len(category_rows_refreshed):
                    print(f"  상품구분 인덱스 {cat_idx} 찾기 실패. 건너뜁니다.")
                    continue

                category_row_to_click = category_rows_refreshed[cat_idx]
                cat_name_element = None
                try:
                    cat_name_element = category_row_to_click.find_element(
                        By.CSS_SELECTOR, "td > a")
                except NoSuchElementException:
                    cat_name_element = category_row_to_click.find_element(
                        By.CSS_SELECTOR, "td:first-child")
                category_name_text = cat_name_element.text.strip()

                print(
                    f"\n[{cat_idx+1}/{num_categories}] 상품구분 '{category_name_text}' 처리 중...")
                driver.execute_script(
                    "arguments[0].scrollIntoView(true);", cat_name_element)
                time.sleep(0.3)
                driver.execute_script(
                    "arguments[0].click();", cat_name_element)
                time.sleep(1)
            except Exception as e_cat_setup:
                print(
                    f"  상품구분 '{category_name_text}' (인덱스 {cat_idx}) 설정 중 오류: {e_cat_setup}")
                continue

            product_list_selector = "tbody#List2 tr"
            try:
                WebDriverWait(driver, 15).until(EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, product_list_selector)))
                time.sleep(2)
            except TimeoutException:
                print(f"  '{category_name_text}' 상품명 목록(tbody#List2) 로드 시간 초과.")
                continue
            except Exception as e_prod_wait:
                print(
                    f"  '{category_name_text}' 상품명 목록(tbody#List2) 로드 중 기타 오류: {e_prod_wait}")
                continue

            product_rows_in_category = driver.find_elements(
                By.CSS_SELECTOR, product_list_selector)
            num_products = len(product_rows_in_category)
            if num_products == 0:
                print(f"  '{category_name_text}' 내 상품 없음.")
                continue
            print(f"  '{category_name_text}' 내 {num_products}개 상품명 발견.")

            for p_idx in range(num_products):
                current_p_row = None
                current_product_name = "N/A"
                is_linkable = False
                try:
                    current_product_rows = driver.find_elements(
                        By.CSS_SELECTOR, product_list_selector)
                    if p_idx < len(current_product_rows):
                        current_p_row = current_product_rows[p_idx]
                    else:
                        print(f"    상품명 인덱스 {p_idx} 찾기 실패.")
                        continue
                except Exception as e_get_p_row:
                    print(f"    상품명 행 인덱스 {p_idx} 가져오기 오류: {e_get_p_row}.")
                    continue

                try:
                    prod_name_element = current_p_row.find_element(
                        By.CSS_SELECTOR, "td:first-child > a")
                    current_product_name = prod_name_element.text.strip()
                    is_linkable = True
                except NoSuchElementException:
                    try:
                        current_product_name = current_p_row.find_element(
                            By.CSS_SELECTOR, "td:first-child").text.strip()
                    except Exception:
                        pass
                if not current_product_name or current_product_name == "N/A":
                    print(f"    상품명 정보 비어있음 (인덱스 {p_idx}).")
                    continue

                print(
                    f"    [{p_idx+1}/{num_products}] 상품명 '{current_product_name}' 처리 중...")
                if not is_linkable:
                    product_data_collected.append({'보험명': f"{category_name_text} - {current_product_name}",
                                                  '판매기간': 'N/A', '약관_존재여부': 'N/A', '상품요약서_존재여부': 'N/A', '사업방법서_존재여부': 'N/A'})
                    continue

                try:
                    prod_click_target = current_p_row.find_element(
                        By.CSS_SELECTOR, "td:first-child > a")
                    driver.execute_script(
                        "arguments[0].scrollIntoView(true);", prod_click_target)
                    time.sleep(0.3)
                    driver.execute_script(
                        "arguments[0].click();", prod_click_target)
                    time.sleep(1)
                except Exception as e_prod_click:
                    print(
                        f"      상품명 '{current_product_name}' 클릭 오류: {e_prod_click}.")
                    continue

                detail_list_selector = "tbody#List3 tr"
                try:
                    WebDriverWait(driver, 10).until(EC.visibility_of_element_located(
                        (By.CSS_SELECTOR, detail_list_selector)))
                    detail_rows = driver.find_elements(
                        By.CSS_SELECTOR, detail_list_selector)

                    print(f"      tbody#List3 발견된 tr 개수: {len(detail_rows)}")

                    if len(detail_rows) > 1:  # 헤더 행 제외, 데이터 행부터 처리
                        print(
                            f"        헤더 제외 후 {len(detail_rows) - 1}개의 데이터 행 처리 시작.")
                        for data_row_idx in range(1, len(detail_rows)):
                            data_row = detail_rows[data_row_idx]
                            tds_in_data_row = data_row.find_elements(
                                By.CSS_SELECTOR, "td")
                            print(
                                f"          행 {data_row_idx}: td 개수 = {len(tds_in_data_row)}")

                            sales_period = "N/A"
                            terms_exists = "N/A"
                            summary_exists = "N/A"
                            business_method_exists = "N/A"

                            if len(tds_in_data_row) > 0:
                                try:
                                    sales_period = tds_in_data_row[0].text.strip(
                                    )
                                    print(
                                        f"            td[0] (판매기간): '{sales_period}'")
                                except Exception as e:
                                    print(f"            td[0] (판매기간) 오류: {e}")
                            if len(tds_in_data_row) > 1:
                                try:
                                    if tds_in_data_row[1].find_elements(By.CSS_SELECTOR, "a, button"):
                                        summary_exists = "존재함"
                                    print(
                                        f"            td[1] (상품요약서 존재): {summary_exists}")
                                except Exception as e:
                                    print(f"            td[1] (상품요약서) 오류: {e}")
                            if len(tds_in_data_row) > 2:
                                try:
                                    if tds_in_data_row[2].find_elements(By.CSS_SELECTOR, "a, button"):
                                        business_method_exists = "존재함"
                                    print(
                                        f"            td[2] (사업방법서 존재): {business_method_exists}")
                                except Exception as e:
                                    print(f"            td[2] (사업방법서) 오류: {e}")
                            if len(tds_in_data_row) > 3:
                                try:
                                    if tds_in_data_row[3].find_elements(By.CSS_SELECTOR, "a, button"):
                                        terms_exists = "존재함"
                                    print(
                                        f"            td[3] (약관 존재): {terms_exists}")
                                except Exception as e:
                                    print(f"            td[3] (약관) 오류: {e}")

                            product_data_collected.append({
                                '보험명': f"{category_name_text} - {current_product_name}", '판매기간': sales_period,
                                '약관_존재여부': terms_exists, '상품요약서_존재여부': summary_exists, '사업방법서_존재여부': business_method_exists
                            })
                    elif detail_rows:
                        print(
                            "      tbody#List3에 데이터 행이 1개만 존재 (아마도 헤더). 상세 정보 N/A 처리.")
                        product_data_collected.append({
                            '보험명': f"{category_name_text} - {current_product_name}", '판매기간': "N/A (헤더만 존재 가능성)",
                            '약관_존재여부': "N/A", '상품요약서_존재여부': "N/A", '사업방법서_존재여부': "N/A"
                        })
                    else:
                        print("      tbody#List3에 tr이 없음. 상세 정보 N/A 처리.")
                        product_data_collected.append({
                            '보험명': f"{category_name_text} - {current_product_name}", '판매기간': "N/A (상세 정보 없음)",
                            '약관_존재여부': "N/A", '상품요약서_존재여부': "N/A", '사업방법서_존재여부': "N/A"
                        })
                except TimeoutException:
                    print(
                        f"      '{current_product_name}' 상세 정보(tbody#List3) 로드 시간 초과.")
                    product_data_collected.append({'보험명': f"{category_name_text} - {current_product_name}",
                                                  '판매기간': "N/A (로드 실패)", '약관_존재여부': "N/A", '상품요약서_존재여부': "N/A", '사업방법서_존재여부': "N/A"})
                except Exception as e_detail_extract:
                    print(
                        f"      '{current_product_name}' 상세 정보 추출 중 오류: {e_detail_extract}")
                    product_data_collected.append({'보험명': f"{category_name_text} - {current_product_name}",
                                                  '판매기간': "N/A (추출 오류)", '약관_존재여부': "N/A", '상품요약서_존재여부': "N/A", '사업방법서_존재여부': "N/A"})
    except Exception as e:
        print(f"전체 스크래핑 과정 중 오류 발생: {e}")
    finally:
        if 'driver' in locals() and driver:
            driver.quit()
        print("\n--- 스크립트 실행 완료 ---")
        if product_data_collected:
            print("--- 추출된 데이터 ---")
            for data in product_data_collected:
                print(data)
        else:
            print("추출된 데이터가 없습니다.")
    return product_data_collected


if __name__ == "__main__":
    get_hanwhalife_product_info_selenium()
