from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import sqlite3
import re  # 정규표현식 사용을 위해 추가


# db수정,link수정,최적화,디버깅,실행결과 확인만하면 끝
# SQLite 데이터베이스 연결 함수


def get_db_connection():
    conn = sqlite3.connect('idbins_data.db')
    conn.row_factory = sqlite3.Row  # 결과를 딕셔너리 접근
    return conn

# 테이블 생성 함수


def create_table(conn):
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS idbins_products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT,
            sales_period TEXT,
            terms_url TEXT,
            summary_url TEXT,
            business_method_url TEXT,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()

# 데이터 저장 함수


def save_data(conn, product_name, sales_period, terms_url,
              summary_url, business_method_url):
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO idbins_products (
            product_name, sales_period, terms_url,
            summary_url, business_method_url
        )
        VALUES (?, ?, ?, ?, ?)
    ''', (product_name, sales_period, terms_url,
          summary_url, business_method_url))
    conn.commit()


def main():
    # Chrome WebDriver 설정
    service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")  # 필요시 headless 모드 활성화
    driver = webdriver.Chrome(service=service, options=options)

    # 웹 페이지 URL
    url = "https://www.idbins.com/FWMAIV1534.do"
    driver.get(url)

    conn = get_db_connection()
    create_table(conn)

    try:
        # 모든 카테고리 링크 찾기 (getStep2 함수를 호출하는 링크)
        category_links_xpath = "//li[@class='dp1']//a[contains(@onclick, 'getStep2')]"

        category_elements = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located(
                (By.XPATH, category_links_xpath))
        )
        print(f"총 {len(category_elements)}개의 카테고리 링크 발견.")

        for category_element in category_elements:
            onclick_attr = category_element.get_attribute("onclick")
            # onclick 속성에서 getStep2 함수의 인자 추출
            match = re.search(
                r"getStep2\('([^']*)','([^']*)','([^']*)'\)", onclick_attr)
            if match:
                lnm, snm, mnm = match.groups()
                print(f"\n카테고리 클릭: lnm={lnm}, snm={snm}, mnm={mnm}")

                # JavaScript 실행하여 getStep2 함수 호출
                driver.execute_script(onclick_attr)

                # step2_list 로딩 대기
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "step2_list"))
                )
                print("step2_list 로딩 완료.")

                # step2_list에서 모든 상품명 링크 찾기
                product_links_xpath = "//ul[@id='step2_list']/li/a"
                product_elements = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located(
                        (By.XPATH, product_links_xpath))
                )
                print(f"총 {len(product_elements)}개의 상품 링크 발견.")

                for product_element in product_elements:
                    product_onclick_attr = product_element.get_attribute(
                        "onclick")
                    product_name_match = re.search(
                        r"step2Click\(this,'([^']*)'\)", product_onclick_attr)
                    if product_name_match:
                        product_name_text = product_name_match.group(1)
                        print(f"상품명 클릭: {product_name_text}")

                        # JavaScript 실행하여 step2Click 함수 호출
                        driver.execute_script(product_onclick_attr)

                        # step3_list 로딩 대기
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located(
                                (By.ID, "step3_list"))
                        )
                        print("step3_list 로딩 완료.")

                        # step3_list에서 모든 판매기간 링크 찾기
                        sales_period_links_xpath = "//ul[@id='step3_list']/li/a"
                        sales_period_elements = WebDriverWait(driver, 10).until(
                            EC.presence_of_all_elements_located(
                                (By.XPATH, sales_period_links_xpath))
                        )
                        print(f"총 {len(sales_period_elements)}개의 판매기간 링크 발견.")

                        for sales_period_element in sales_period_elements:
                            sales_period_onclick_attr = sales_period_element.get_attribute(
                                "onclick")
                            sales_period_match = re.search(
                                r"step3Click\(this,'([^']*)'\)", sales_period_onclick_attr)
                            if sales_period_match:
                                sqno = sales_period_match.group(1)
                                print(f"판매기간 클릭 (SQNO: {sqno})")

                                # JavaScript 실행하여 step3Click 함수 호출
                                driver.execute_script(
                                    sales_period_onclick_attr)

                                # step4 정보 로딩 대기
                                WebDriverWait(driver, 10).until(
                                    EC.presence_of_element_located(
                                        (By.ID, "step4_name"))
                                )
                                print("step4 정보 로딩 완료.")

                                # 정보 추출
                                product_name = driver.find_element(
                                    By.ID, "step4_name").text.strip()
                                sales_period = driver.find_element(
                                    By.ID, "step4_date").text.strip()

                                business_method_url = ""
                                summary_url = ""
                                terms_url = ""

                                try:
                                    biz_method_element = driver.find_element(
                                        By.ID, "step4Btn1")
                                    onclick_attr_pdf = biz_method_element.get_attribute(
                                        "onclick")
                                    if onclick_attr_pdf and "goPdf" in onclick_attr_pdf:
                                        start_index = onclick_attr_pdf.find(
                                            "','") + 3
                                        end_index = onclick_attr_pdf.find(
                                            "');")
                                        file_name = onclick_attr_pdf[start_index:end_index]
                                        business_method_url = f"/cYakgwanDown.do?FilePath=InsProduct/{file_name}"
                                except Exception as e:
                                    print(f"사업방법서 링크 추출 오류: {e}")

                                try:
                                    summary_element = driver.find_element(
                                        By.ID, "step4Btn2")
                                    onclick_attr_pdf = summary_element.get_attribute(
                                        "onclick")
                                    if onclick_attr_pdf and "goPdf" in onclick_attr_pdf:
                                        start_index = onclick_attr_pdf.find(
                                            "','") + 3
                                        end_index = onclick_attr_pdf.find(
                                            "');")
                                        file_name = onclick_attr_pdf[start_index:end_index]
                                        summary_url = f"/cYakgwanDown.do?FilePath=InsProduct/{file_name}"
                                except Exception as e:
                                    print(f"상품요약서 링크 추출 오류: {e}")

                                try:
                                    terms_element = driver.find_element(
                                        By.ID, "step4Btn3")
                                    onclick_attr_pdf = terms_element.get_attribute(
                                        "onclick")
                                    if onclick_attr_pdf and "goPdf" in onclick_attr_pdf:
                                        start_index = onclick_attr_pdf.find(
                                            "','") + 3
                                        end_index = onclick_attr_pdf.find(
                                            "');")
                                        file_name = onclick_attr_pdf[start_index:end_index]
                                        terms_url = f"/cYakgwanDown.do?FilePath=InsProduct/{file_name}"
                                except Exception as e:
                                    print(f"약관 링크 추출 오류: {e}")

                                print("\n추출된 정보:")
                                print(f"상품명: {product_name}")
                                print(f"판매기간: {sales_period}")
                                print(f"사업방법서 URL: {business_method_url}")
                                print(f"상품요약서 URL: {summary_url}")
                                print(f"약관 URL: {terms_url}")

                                # 데이터베이스에 저장
                                save_data(conn, product_name, sales_period, terms_url,
                                          summary_url, business_method_url)
                                print(f"'{product_name}' 정보 데이터베이스 저장 완료.")

                                # 다음 판매기간을 위해 step4 초기화 (필요시)
                                # driver.execute_script("reset4Step();")
                                # time.sleep(1) # 초기화 대기

                        # 다음 상품을 위해 step3 초기화 (필요시)
                        # driver.execute_script("reset3Step();")
                        # time.sleep(1) # 초기화 대기

                # 다음 카테고리를 위해 step2 초기화 (필요시)
                # driver.execute_script("reset2Step();")
                # time.sleep(1) # 초기화 대기

    except Exception as e:
        print(f"오류 발생: {e}")

    finally:
        if conn:
            conn.close()
        driver.quit()
        print("\n스크립트 실행 완료. idbins_data.db 파일을 확인하세요.")


if __name__ == "__main__":
    main()
