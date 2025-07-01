# 롯데손해보험
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from seleniumwire import webdriver
from webdriver_manager.chrome import ChromeDriverManager
import time
import sys
import os
import json

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from neoali.DB_save import DatabaseManager
except ImportError as e:
    DatabaseManager = None
    print(f"경고: 모듈 임포트 실패 ({e}). 일부 기능이 비활성화될 수 있습니다.")


def scrape_lotte_insurance_table(url):
    """
    롯데손해보험 웹사이트의 동적 테이블에서 데이터를 스크랩합니다.
    클릭 이벤트를 JavaScript를 통해 실행합니다.

    Args:
        url (str): 스크랩할 롯데손해보험 페이지의 URL.
    """
    options = Options()
    # options.add_argument("--headless") # 주석을 해제하면 UI 없이 백그라운드에서 브라우저가 실행됩니다. (디버깅 시에는 주석 처리 권장)
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--start-maximized")  # 브라우저 창을 최대화합니다.

    print("Chrome WebDriver를 초기화 중입니다...")
    driver = None
    all_product_data = []  # 추출된 모든 데이터를 저장할 리스트 (딕셔너리들의 리스트)

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        print("WebDriver가 성공적으로 초기화되었습니다.")

        print(f"URL: {url} 로 이동 중입니다...")
        driver.get(url)

        try:
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CLASS_NAME, "tbl_publication"))
            )
            print("메인 테이블이 성공적으로 로드되었습니다.")
        except TimeoutException:
            print("메인 테이블 로드를 기다리는 중 타임아웃이 발생했습니다.")
            return []

        product_groups_ul = driver.find_element(By.XPATH, "//table[@class='tbl_publication']//td[1]/ul")
        product_group_lis = product_groups_ul.find_elements(By.TAG_NAME, "li")

        for i in range(len(product_group_lis)):
            # StaleElementReferenceException을 피하기 위해 요소를 다시 찾습니다.
            product_groups_ul = driver.find_element(By.XPATH, "//table[@class='tbl_publication']//td[1]/ul")
            product_group_lis = product_groups_ul.find_elements(By.TAG_NAME, "li")
            current_product_group_li = product_group_lis[i]

            try:
                main_category_name = current_product_group_li.find_element(By.TAG_NAME, "p").text
                print(f"\n--- 카테고리 스크랩 중: {main_category_name} ---")

                sub_category_links = current_product_group_li.find_elements(By.CSS_SELECTOR, "ol.dep02 li a")

                for j in range(len(sub_category_links)):
                    sub_category_links = current_product_group_li.find_elements(By.CSS_SELECTOR, "ol.dep02 li a")
                    current_sub_category_link = sub_category_links[j]

                    sub_category_name = current_sub_category_link.text
                    print(f"  > 하위 카테고리 클릭 중 (JS): {sub_category_name}")

                    try:
                        # JavaScript를 사용하여 클릭 이벤트 발생
                        driver.execute_script("arguments[0].click();", current_sub_category_link)
                        time.sleep(1)

                        WebDriverWait(driver, 10).until(
                            EC.visibility_of_element_located((By.ID, "step2view"))
                        )

                        product_list_ul = driver.find_element(By.ID, "step2view").find_element(By.CLASS_NAME, "product_list")
                        product_items = product_list_ul.find_elements(By.TAG_NAME, "li")

                        for k in range(len(product_items)):
                            product_list_ul = driver.find_element(By.ID, "step2view").find_element(By.CLASS_NAME, "product_list")
                            product_items = product_list_ul.find_elements(By.TAG_NAME, "li")
                            current_product_item = product_items[k]

                            product_name = current_product_item.find_element(By.TAG_NAME, "span").text
                            print(f"    >> 상품 처리 중 (JS): {product_name}")

                            try:
                                # JavaScript를 사용하여 클릭 이벤트 발생
                                driver.execute_script("arguments[0].click();", current_product_item.find_element(By.TAG_NAME, "a"))
                                time.sleep(1)

                                WebDriverWait(driver, 10).until(
                                    EC.visibility_of_element_located((By.ID, "step3view"))
                                )

                                sales_period_ul = driver.find_element(By.ID, "step3view").find_element(By.CLASS_NAME, "product_list")
                                sales_period_items = sales_period_ul.find_elements(By.TAG_NAME, "li")

                                for l in range(len(sales_period_items)):
                                    sales_period_ul = driver.find_element(By.ID, "step3view").find_element(By.CLASS_NAME, "product_list")
                                    sales_period_items = sales_period_ul.find_elements(By.TAG_NAME, "li")
                                    current_sales_period_item = sales_period_items[l]

                                    sales_period_text = current_sales_period_item.find_element(By.TAG_NAME, "span").text
                                    print(f"      >>> 판매 기간 처리 중 (JS): {sales_period_text}")

                                    try:
                                        # JavaScript를 사용하여 클릭 이벤트 발생
                                        driver.execute_script("arguments[0].click();", current_sales_period_item.find_element(By.TAG_NAME, "a"))
                                        time.sleep(1)

                                        WebDriverWait(driver, 10).until(
                                            EC.visibility_of_element_located((By.ID, "step4view"))
                                        )

                                        step4_view = driver.find_element(By.ID, "step4view")
                                        displayed_product_name = step4_view.find_element(
                                            By.XPATH, ".//dt[text()='상품명']/following-sibling::dd[1]/span").text
                                        displayed_sales_period = step4_view.find_element(
                                            By.XPATH, ".//dt[text()='판매기간']/following-sibling::dd[1]/span").text

                                        pdf_links = step4_view.find_elements(By.CSS_SELECTOR, "ul.pdf_btn li a")
                                        pdf_data = {}
                                        for pdf_link in pdf_links:
                                            img_alt = pdf_link.find_element(By.TAG_NAME, "img").get_attribute("alt")
                                            pdf_href = pdf_link.get_attribute("href")
                                            pdf_data[img_alt + " PDF"] = pdf_href

                                        product_info = {
                                            "대분류": main_category_name,
                                            "소분류": sub_category_name,
                                            "상품명": displayed_product_name,
                                            "판매기간": displayed_sales_period,
                                            "사업방법서 PDF": pdf_data.get("사업방법서 PDF", ""),
                                            "상품요약서 PDF": pdf_data.get("상품요약서 PDF", ""),
                                            "약관 PDF": pdf_data.get("약관 PDF", "")
                                        }
                                        all_product_data.append(product_info)

                                    except StaleElementReferenceException:
                                        print(f"      >>> 판매 기간 항목에서 StaleElementReferenceException 발생. 재시도 또는 건너뛰기.")
                                        continue
                                    except NoSuchElementException as e:
                                        print(f"      >>> step4view에서 요소를 찾을 수 없습니다: {e}")
                                    except Exception as e:
                                        print(f"      >>> 판매 기간 처리 중 오류 발생: {e}")

                            except StaleElementReferenceException:
                                print(f"    >> 상품 항목에서 StaleElementReferenceException 발생. 재시도 또는 건너뛰기.")
                                continue
                            except NoSuchElementException as e:
                                print(f"    >> 상품에 대한 step3view에서 요소를 찾을 수 없습니다: {e}")
                            except Exception as e:
                                print(f"    >> 상품 처리 중 오류 발생: {e}")

                    except StaleElementReferenceException:
                        print(f"  > 하위 카테고리 링크에서 StaleElementReferenceException 발생. 재시도 또는 건너뛰기.")
                        continue
                    except NoSuchElementException as e:
                        print(f"  > 하위 카테고리 클릭 후 요소를 찾을 수 없습니다: {e}")
                    except Exception as e:
                        print(f"  > 하위 카테고리 처리 중 오류 발생: {e}")

            except StaleElementReferenceException:
                print(f"--- 메인 카테고리에서 StaleElementReferenceException 발생. 재시도 또는 건너뛰기.")
                continue
            except NoSuchElementException as e:
                print(f"--- 메인 카테고리에서 요소를 찾을 수 없습니다: {e}")
            except Exception as e:
                print(f"--- 메인 카테고리 처리 중 오류 발생: {e}")

        print("\n스크랩 완료.")
        return all_product_data

    except Exception as e:
        print(f"스크랩 중 오류가 발생했습니다: {e}")
        return []
    finally:
        if driver:
            print("WebDriver를 닫는 중입니다...")
            driver.quit()
            print("WebDriver가 닫혔습니다.")


if __name__ == "__main__":
    lotte_insurance_url = "https://www.lotteins.co.kr/web/C/D/H/cdh190.jsp"
    scraped_data = scrape_lotte_insurance_table(lotte_insurance_url)

    if scraped_data:
        print("\n--- 스크랩된 데이터 (JSON 형식) ---")
        json_output_string = json.dumps(scraped_data, indent=4, ensure_ascii=False)
        print(json_output_string)

        with open("lotte_insurance_product_data.json", "w", encoding="utf-8") as f:
            json.dump(scraped_data, f, indent=4, ensure_ascii=False)
        print("\n데이터가 lotte_insurance_product_data.json 파일에 저장되었습니다.")
    else:
        print("\n스크랩된 데이터가 없습니다.")
