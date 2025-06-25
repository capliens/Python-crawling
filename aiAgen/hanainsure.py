# 하나손해보험/판매중지페이지/db확인
from seleniumwire import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time


def crawl_hanainsure_documents_robust_detailed_output():  # 함수명 변경 (상세 출력 강조)
    """
    하나손해보험 판매 상품 공시 페이지에서 단계별 클릭을 통해
    각 상품의 약관, 사업방법서, 상품요약서 링크를 크롤링합니다.
    Selenium 3.x 환경 호환, 정확한 CSS 선택자 유지,
    그리고 4단계 정보 추출 시 상세 출력문을 추가하여 진행 상황을 명확히 합니다.
    """
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless") # 백그라운드 실행 시 주석 해제
    # options.add_argument("--disable-gpu")
    # options.add_argument("--no-sandbox")
    options.add_argument("--start-maximized")  # 브라우저 창 최대화
    options.add_experimental_option('excludeSwitches', ['enable-logging'])  # 불필요한 초기 로그 메시지 억제

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    url = "https://www.hanainsure.co.kr/w/disclosure/product/saleProduct"
    all_extracted_data = []

    try:
        driver.get(url)

        print("페이지 로드 중...")
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CLASS_NAME, "box-wrap"))
        )
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        print("페이지 로드 완료.")

        # --- STEP 1: 보험상품 선택 (divStep01) ---
        step01_divs = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#divStep01 > div"))
        )

        for i in range(len(step01_divs)):
            current_step01_divs = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#divStep01 > div"))
            )
            ins_type_link = current_step01_divs[i].find_element(By.TAG_NAME, "a")
            ins_type_text = ins_type_link.text

            print(f"\n[STEP 1] 클릭: {ins_type_text}")
            driver.execute_script("arguments[0].click();", ins_type_link)

            WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.ID, "divStep01_1"))
            )
            time.sleep(0.5)

            # --- STEP 1-1: 보험상품 상세 유형 (divStep01_1) ---
            step01_1_divs = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#divStep01_1 > div"))
            )

            for j in range(len(step01_1_divs)):
                current_step01_1_divs = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#divStep01_1 > div"))
                )
                dtl_type_link = current_step01_1_divs[j].find_element(By.TAG_NAME, "a")
                dtl_type_text = dtl_type_link.text

                print(f"  [STEP 1-1] 클릭: {dtl_type_text}")
                driver.execute_script("arguments[0].click();", dtl_type_link)

                WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located((By.ID, "divStep02"))
                )
                time.sleep(0.5)

                # --- STEP 2: 보험상품목록 (divStep02) ---
                step02_divs = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#divStep02 > div"))
                )

                for k in range(len(step02_divs)):
                    current_step02_divs = WebDriverWait(driver, 10).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#divStep02 > div"))
                    )
                    product_link = current_step02_divs[k].find_element(By.TAG_NAME, "a")
                    product_name_text = product_link.text

                    print(f"    [STEP 2] 클릭: {product_name_text}")
                    driver.execute_script("arguments[0].click();", product_link)

                    WebDriverWait(driver, 10).until(
                        EC.visibility_of_element_located((By.ID, "divStep03"))
                    )
                    time.sleep(0.5)

                    # --- STEP 3: 판매기간 (divStep03) ---
                    step03_divs = WebDriverWait(driver, 10).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#divStep03 > div"))
                    )

                    for l in range(len(step03_divs)):
                        current_sale_period_text = ""
                        try:
                            current_step03_divs = WebDriverWait(driver, 10).until(
                                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#divStep03 > div"))
                            )
                            sale_period_link = current_step03_divs[l].find_element(By.TAG_NAME, "a")
                            current_sale_period_text = sale_period_link.text

                            print(f"      [STEP 3] 클릭: {current_sale_period_text}")
                            driver.execute_script("arguments[0].click();", sale_period_link)

                            # --- STEP 4: 선택항목 (divStep04) - 데이터 추출 시작 ---
                            print(f"        [STEP 4] '{product_name_text}' 상품의 '{current_sale_period_text}' 판매기간 정보 추출 시작...")

                            # divStep04의 컨테이너가 보이는 것을 기다림
                            print("          - divStep04 컨테이너 가시성 대기 중...")
                            WebDriverWait(driver, 10).until(
                                EC.visibility_of_element_located((By.CSS_SELECTOR, "#divStep04 .pd-info-box"))
                            )
                            print("          - divStep04 컨테이너 확인 완료.")

                            # Selenium 3.x 호환: 두 dd.p_name 요소를 순차적으로 대기
                            print("          - 상품명 요소 대기 중 (CSS: #divStep04 dl:nth-of-type(1) dd.p_name)...")
                            WebDriverWait(driver, 15).until(
                                EC.visibility_of_element_located((By.CSS_SELECTOR, "#divStep04 dl:nth-of-type(1) dd.p_name"))
                            )
                            print("          - 판매기간 요소 대기 중 (CSS: #divStep04 dl:nth-of-type(2) dd.p_name)...")
                            WebDriverWait(driver, 15).until(
                                EC.visibility_of_element_located((By.CSS_SELECTOR, "#divStep04 dl:nth-of-type(2) dd.p_name"))
                            )
                            print("          - 상품명 및 판매기간 요소 확인 완료.")

                            # 추가적인 안정성을 위한 짧은 지연 (필요 시)
                            time.sleep(0.5)

                            # 상품명 및 판매기간 추출 시도
                            displayed_product_name = "추출 실패"
                            displayed_sale_period = "추출 실패"
                            try:
                                displayed_product_name = driver.find_element(By.CSS_SELECTOR, "#divStep04 dl:nth-of-type(1) dd.p_name").text
                                print(f"          - 상품명 추출 성공: '{displayed_product_name}'")
                                displayed_sale_period = driver.find_element(By.CSS_SELECTOR, "#divStep04 dl:nth-of-type(2) dd.p_name").text
                                print(f"          - 판매기간 추출 성공: '{displayed_sale_period}'")
                            except Exception as inner_e:
                                print(f"        [오류] 상품명/판매기간 텍스트 추출 중 오류 발생: {inner_e}")
                                time.sleep(1)  # 오류 시 잠시 대기 후 재시도
                                try:  # 재시도
                                    displayed_product_name = driver.find_element(By.CSS_SELECTOR, "#divStep04 dl:nth-of-type(1) dd.p_name").text
                                    displayed_sale_period = driver.find_element(By.CSS_SELECTOR, "#divStep04 dl:nth-of-type(2) dd.p_name").text
                                    print(f"        [재시도 성공] 상품명: '{displayed_product_name}', 판매기간: '{displayed_sale_period}'")
                                except Exception as retry_e:
                                    print(f"        [재시도 실패] 상품명/판매기간 텍스트 추출 재시도 실패: {retry_e}")

                            # 다운로드 링크 추출
                            print("          - 문서 링크 그룹 대기 중 (CSS: #divStep04 .btn_group a.btn)...")
                            WebDriverWait(driver, 10).until(
                                EC.visibility_of_element_located((By.CSS_SELECTOR, "#divStep04 .btn_group a.btn"))
                            )
                            print("          - 문서 링크 그룹 확인 완료. 링크 추출 시작.")
                            link_elements = driver.find_elements(By.CSS_SELECTOR, "#divStep04 .btn_group a.btn")

                            if not link_elements:
                                print("          - 경고: 문서 링크를 찾을 수 없습니다.")

                            for idx, link_elem in enumerate(link_elements):
                                link_type = link_elem.text.strip()
                                link_href = link_elem.get_attribute("href")

                                extracted_item = {
                                    "보험상품 유형": ins_type_text,
                                    "상세 보험상품 유형": dtl_type_text,
                                    "상품명": displayed_product_name,
                                    "판매기간": displayed_sale_period,
                                    "문서타입": link_type,
                                    "링크": link_href
                                }
                                all_extracted_data.append(extracted_item)
                                print(f"            [링크 추출 {idx + 1}] 문서타입: '{link_type}', 링크: '{link_href}'")

                        except Exception as e:
                            print(f"        [오류] STEP 4 전체 데이터 추출 중 예상치 못한 오류 발생 (판매기간: {current_sale_period_text}): {e}")
                            # 문제의 HTML 출력은 제거됨
                            continue  # 다음 판매기간으로 이동하여 크롤링 계속

    except Exception as e:
        print(f"[주요 오류] 크롤링 과정 중 예상치 못한 오류 발생: {e}")

    finally:
        driver.quit()
        print("\n--- 전체 크롤링 완료 ---")
        for data in all_extracted_data:
            print(data)
        print(f"\n총 {len(all_extracted_data)}개의 문서 정보가 추출되었습니다.")


if __name__ == "__main__":
    # 이 함수를 호출하여 실행하세요.
    crawl_hanainsure_documents_robust_detailed_output()
