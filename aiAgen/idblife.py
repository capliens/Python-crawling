# DB생명/판매중지 페이지
import sys
import os
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from seleniumwire import webdriver
from webdriver_manager.chrome import ChromeDriverManager
import time
from datetime import datetime

# 현재 스크립트의 상위 디렉토리 (프로젝트 루트)를 sys.path에 추가
# 이렇게 하면 neoali 패키지를 올바르게 임포트할 수 있습니다.
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from neoali.DB_save import DatabaseManager  # DatabaseManager import 추가
except ImportError as e:
    DatabaseManager = None  # DatabaseManager 초기화 추가
    print(f"DatabaseManager 임포트 오류: {e}")


class IDBLifeScraper:
    def __init__(self):
        self.base_url = "https://www.idblife.com/notice/product/sale"
        self.driver = self._init_driver()
        self.company_name = "DB생명"

    def _init_driver(self):
        options = Options()
        # options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        return driver

    def scrape_product_list(self):
        all_products_raw = []
        tab_info = {
            "개인상품": {"url_base": self.base_url, "gubn1": ""},
            "단체상품": {"url_base": "https://www.idblife.com/notice/product/sale", "gubn1": "2"},
            "방카상품": {"url_base": "https://www.idblife.com/notice/product/sale", "gubn1": "4"}
        }

        for tab_name, info in tab_info.items():
            base_url_for_tab = info["url_base"]
            gubn1_param = f"gubn1={info['gubn1']}&" if info["gubn1"] else ""

            print(f"'{tab_name}' 탭 스크래핑 중...")

            current_page = 1
            total_pages = 1

            while current_page <= total_pages:
                page_url = f"{base_url_for_tab}?{gubn1_param}page={current_page}"
                print(f"   페이지 {current_page} 스크래핑 중: {page_url}")
                self.driver.get(page_url)
                time.sleep(3)

                try:
                    if current_page == 1:
                        pagination_div = WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "div.page01.js-tag[data-role='pagination']"))
                        )
                        total_pages = int(pagination_div.get_attribute("data-total-page"))
                        print(f"   총 페이지 수: {total_pages}")

                    rows = self.driver.find_elements(By.CSS_SELECTOR, "table.tables1 tbody tr")
                    print(f"   페이지 {current_page}에서 {len(rows)}개의 상품을 찾았습니다.")

                    for row in rows:
                        product_data = {
                            "상품군": tab_name,
                            "상품명": "",
                            "판매기간": "",
                            "사업방법서_링크": "",
                            "상품요약서_링크": "",
                            "주계약_약관": [],
                            "특약_약관": []
                        }

                        try:
                            product_data["상품명"] = row.find_element(By.CSS_SELECTOR, "th.als.pl10").text.strip()
                        except NoSuchElementException:
                            pass

                        try:
                            product_data["판매기간"] = row.find_element(By.XPATH, "./td[1]").text.strip()
                        except NoSuchElementException:
                            pass

                        terms_button_url = ""
                        try:
                            business_method_element = row.find_element(By.XPATH, "./td[2]/a")
                            product_data["사업방법서_링크"] = business_method_element.get_attribute("href")
                        except NoSuchElementException:
                            pass

                        try:
                            product_summary_element = row.find_element(By.XPATH, "./td[3]/a")
                            product_data["상품요약서_링크"] = product_summary_element.get_attribute("href")
                        except NoSuchElementException:
                            pass

                        try:
                            terms_element = row.find_element(By.XPATH, "./td[4]/a")
                            terms_button_url = terms_element.get_attribute("href")
                        except NoSuchElementException:
                            pass

                        if terms_button_url:
                            main_window_handle = self.driver.current_window_handle
                            self.driver.execute_script(f"window.open('{terms_button_url}');")
                            time.sleep(2)

                            new_window_handle = None
                            for handle in self.driver.window_handles:
                                if handle != main_window_handle:
                                    new_window_handle = handle
                                    break

                            if new_window_handle:
                                self.driver.switch_to.window(new_window_handle)
                                try:
                                    WebDriverWait(self.driver, 10).until(
                                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.pops1"))
                                    )

                                    current_section = None
                                    elements_in_new_window = self.driver.find_elements(
                                        By.CSS_SELECTOR, "div.content h2.bullets11, div.content ul.lists12 li a")

                                    for element in elements_in_new_window:
                                        if element.tag_name == "h2":
                                            current_section = element.text.strip()
                                        elif element.tag_name == "a" and current_section:
                                            link_name = element.text.strip()
                                            link_url = element.get_attribute("href")

                                            if "주계약" in current_section:
                                                product_data["주계약_약관"].append({"이름": link_name, "URL": link_url})
                                            elif "특약" in current_section:
                                                product_data["특약_약관"].append({"이름": link_name, "URL": link_url})
                                except Exception as e:
                                    print(f"   새 창 약관 스크래핑 중 오류 발생: {e}")
                                finally:
                                    self.driver.close()
                                    self.driver.switch_to.window(main_window_handle)
                            else:
                                print(f"   상품명 '{product_data['상품명']}'의 새 약관 창을 찾을 수 없습니다.")

                        all_products_raw.append(product_data)

                except NoSuchElementException as e:
                    print(f"'{tab_name}' 탭 페이지 {current_page}에서 요소를 찾을 수 없습니다: {e}")
                    break
                except Exception as e:
                    print(f"'{tab_name}' 탭 페이지 {current_page} 스크래핑 중 오류 발생: {e}")
                    break

                current_page += 1
                time.sleep(1)

        return all_products_raw

    def close(self):
        self.driver.quit()


if __name__ == "__main__":
    scraper = IDBLifeScraper()

    print("상품 목록 스크래핑 중...")
    all_product_data = scraper.scrape_product_list()

    scraper.close()

    structured_rows_to_save = []
    scraped_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for product in all_product_data:
        # 사업방법서 저장
        if product["사업방법서_링크"]:
            structured_rows_to_save.append([
                scraper.company_name,
                product["상품명"],  # 상품명 유지
                None,
                "사업방법서",  # 문서 타입 고정
                product["판매기간"],
                scraped_time,
                product["사업방법서_링크"]
            ])

        # 상품요약서 저장
        if product["상품요약서_링크"]:
            structured_rows_to_save.append([
                scraper.company_name,
                product["상품명"],  # 상품명 유지
                None,
                "상품요약서",  # 문서 타입 고정
                product["판매기간"],
                scraped_time,
                product["상품요약서_링크"]
            ])

        # 주계약 약관 저장
        for doc in product["주계약_약관"]:
            structured_rows_to_save.append([
                scraper.company_name,
                doc['이름'],  # 약관 이름을 상품명으로 사용
                None,
                "약관",  # 문서 타입 고정
                product["판매기간"],
                scraped_time,
                doc["URL"]
            ])

        # 특약 약관 저장
        for doc in product["특약_약관"]:
            structured_rows_to_save.append([
                scraper.company_name,
                doc['이름'],  # 약관 이름을 상품명으로 사용
                None,
                "약관",  # 문서 타입 고정
                product["판매기간"],
                scraped_time,
                doc["URL"]
            ])

    with DatabaseManager(db_name="insurance_products.db") as db_manager:
        saved_count = db_manager.save_data(structured_rows_to_save)
        print(f"\n--- 총 {saved_count}건의 데이터가 DB에 저장되었습니다. ---")
