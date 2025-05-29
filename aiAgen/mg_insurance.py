from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
# 링크,판매 페이지,sql 수정


class MGInsuranceScraper:
    def __init__(self):
        options = Options()
        # options.add_argument("--headless") # 브라우저를 백그라운드에서 실행 (선택 사항)
        options.add_argument("--start-maximized")  # 브라우저 창 최대화
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 10)
        self.base_url = "https://insure.kfcc.co.kr/#/PGE_IHJ_00003"

    def _scroll_to_end(self):
        last_height = self.driver.execute_script(
            "return document.body.scrollHeight")
        while True:
            self.driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)  # 페이지 로드를 기다림
            new_height = self.driver.execute_script(
                "return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

    def get_all_products(self):
        self.driver.get(self.base_url)

        # 페이지가 완전히 로드될 때까지 기다림 (예: 특정 요소가 나타날 때까지)
        try:
            self.wait.until(EC.presence_of_element_located(
                (By.CLASS_NAME, "mg-table-templete")))
        except TimeoutException:
            print("테이블 요소 로드 시간 초과.")
            return []

        # self._scroll_to_end()  # 페이지 끝까지 스크롤하여 모든 데이터 로드 (사용자 요청으로 제거)

        product_list = []
        try:
            table_body = self.driver.find_element(
                By.CSS_SELECTOR, ".mg-table-templete tbody")
            rows = table_body.find_elements(By.TAG_NAME, "tr")

            for row in rows:
                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) >= 4:  # 최소한 4개의 컬럼 (종류, 상품명, 판매기간, 상품요약서)
                    product_type = cols[0].text.strip().replace('\n', ' > ')
                    product_name = cols[1].text.strip()
                    sales_period = cols[2].text.strip()
                    summary_link = ""
                    try:
                        summary_element = cols[3].find_element(
                            By.TAG_NAME, "a")
                        summary_link = summary_element.get_attribute("href")
                    except NoSuchElementException:
                        pass  # 요약서 링크가 없는 경우

                    product_list.append({
                        "종류": product_type,
                        "상품명": product_name,
                        "판매기간": sales_period,
                        "상품요약서_링크": summary_link
                    })
        except NoSuchElementException:
            print("상품 테이블을 찾을 수 없습니다.")
            return []

        return product_list

    def close(self):
        self.driver.quit()


if __name__ == "__main__":
    scraper = MGInsuranceScraper()
    products = scraper.get_all_products()

    if products:
        print("--- MG새마을금고보험 상품 목록 ---")
        for product in products:
            print(f"종류: {product['종류']}")
            print(f"상품명: {product['상품명']}")
            print(f"판매기간: {product['판매기간']}")
            print(f"상품요약서 링크: {product['상품요약서_링크']}")
            print("-" * 30)
    else:
        print("상품 목록을 가져오지 못했습니다.")

    scraper.close()
