# a href=다운로드링크 /링크기능 태스트/db 연동/판매페이지
from selenium import webdriver
from selenium.webdriver.common.by import By
# from selenium.common.exceptions import NoSuchElementException, TimeoutException # 사용되지 않음
# from selenium.webdriver.chrome.options import Options # 사용되지 않음, webdriver.ChromeOptions() 사용
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time  # time 임포트가 누락되어 추가합니다.


def get_metlife_product_info(scrape_target="주보험", click_all_history=False):
    """
    MetLife 웹사이트에서 주보험 또는 특약 정보를 가져옵니다.

    Args:
        scrape_target (str): "주보험" 또는 "특약"을 지정합니다. 기본값은 "주보험".
        click_all_history (bool): 모든 '이전 판매기간 펼치기' 버튼을 클릭할지 여부.
                                   True로 설정하면 모든 이전 판매기간 정보도 가져오려고 시도합니다.

    Returns:
        list: 상품 정보 딕셔너리의 리스트.
              주보험: 'product_name', 'sales_period', 'business_manual_link', 'summary_link', 'terms_link', 'type'
              특약: 'product_name', 'sales_period', 'terms_link', 'type'
    """
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless')  # 브라우저 창을 띄우지 않으려면 주석 해제
    # options.add_argument('--no-sandbox')
    # options.add_argument('--disable-dev-shm-usage')

    # Selenium 4.x 이상에서는 Service 객체를 사용하는 것이 권장됩니다.
    # service = webdriver.chrome.service.Service(executable_path=driver_path) # webdriver_manager 사용으로 변경
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    url = "https://brand.metlife.co.kr/pn/mcvrgProd/retrieveMcvrgProdMain.do"
    driver.get(url)
    time.sleep(1)  # 페이지 기본 로딩 대기

    products_data = []
    product_type = scrape_target  # "주보험" 또는 "특약"

    try:
        if scrape_target == "특약":
            try:
                # "ul.uiDropCont > li"의 두 번째 li 클릭 (특약 탭으로 가정)
                # CSS 선택자: ul.uiDropCont li:nth-child(2)
                # 또는 XPath: //ul[contains(@class, 'uiDropCont')]/li[2]
                # 실제 웹사이트의 정확한 선택자 확인 필요. 우선은 제공된 정보로 시도.
                special_terms_tab = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "ul.uiDropCont > li:nth-child(2) > a"))  # a 태그까지 지정
                )
                # 스크롤 후 JavaScript 클릭
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", special_terms_tab)
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", special_terms_tab)
                print("특약 탭 클릭 시도 완료.")
                time.sleep(3)  # 특약 테이블 로딩 대기
            except Exception as e:
                print(f"특약 탭 클릭 중 오류 발생: {e}")
                driver.quit()
                return []

        # 페이지 로딩 대기 (테이블이 나타날 때까지) - 사용자 제공 선택자로 변경
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.table_fix_wrapper > table.tblList > tbody > tr"))
        )

        if click_all_history:
            # "이전 판매기간 펼치기" 버튼 모두 클릭 시도 - 사용자 제공 정보 기반으로 XPath 수정
            # td > button 형태이며, 텍스트 내용을 포함하도록 가정 (예: "이전 판매기간 펼치기")
            # 실제 버튼 텍스트나 다른 속성을 확인하여 더 정확하게 만들 수 있습니다.
            try:
                # XPath 수정: td 안에 있는 button 중 특정 텍스트를 포함하는 버튼
                # 사용자가 제공한 클래스 정보 "button toggler"를 사용하여 XPath 수정
                expand_buttons = driver.find_elements(By.XPATH, "//button[@class='button toggler']")

                # 만약 위 XPath로 찾지 못할 경우, 텍스트 기반 검색도 시도 (Fallback)
                if not expand_buttons:
                    expand_buttons = driver.find_elements(
                        By.XPATH, "//button[contains(normalize-space(), '이전 판매기간 펼치기') or contains(normalize-space(), '펼치기')]")
                if not expand_buttons:
                    expand_buttons = driver.find_elements(By.XPATH, "//a[contains(text(), '이전 판매기간 펼치기')]")

                for button in expand_buttons:
                    try:
                        # 요소를 뷰의 중앙으로 스크롤하거나 하단으로 스크롤하여 헤더와의 충돌을 피함
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                        time.sleep(0.5)  # 스크롤 후 잠시 대기
                        # Selenium 클릭 대신 JavaScript 클릭 사용
                        driver.execute_script("arguments[0].click();", button)
                        time.sleep(1)  # 내용이 펼쳐질 때까지 대기
                    except Exception as e:
                        print(f"이전 판매기간 펼치기 버튼 클릭 중 오류: {e}")
            except Exception as e:
                print(f"이전 판매기간 펼치기 버튼 검색 중 오류: {e}")

        # 데이터가 로드될 시간을 충분히 줍니다.
        time.sleep(3)

        # 상품 목록 행을 찾는 CSS 선택자를 사용자 제공 정보로 변경
        rows = driver.find_elements(By.CSS_SELECTOR, "div.table_fix_wrapper > table.tblList > tbody > tr")

        current_main_product_name = "N/A"  # rowspan을 가진 th 또는 td에서 가져온 현재 주 상품명

        for i, row in enumerate(rows):
            th_cells = row.find_elements(By.TAG_NAME, "th")
            td_cells = row.find_elements(By.TAG_NAME, "td")

            # 초기화
            product_name = "N/A"
            sales_period = "N/A"
            business_manual_link = "N/A"
            summary_link = "N/A"
            terms_link = "N/A"

            # Case 1: 상품 구분(th) + 상품명(td rowspan) + 펼치기버튼(td colspan) 행
            # 주보험: th(rowspan), td(rowspan, 상품명), td(colspan, 버튼)
            # 특약: th(rowspan, 구분), td(rowspan, 상품명), td(colspan, 버튼) - td 개수는 동일하게 2개
            if th_cells and "rowspan" in th_cells[0].get_attribute("outerHTML") and \
               len(td_cells) == 2 and \
               td_cells[0].get_attribute("rowspan") and \
               td_cells[1].get_attribute("colspan"):  # 첫번째 td가 상품명, 두번째 td가 버튼
                current_main_product_name = td_cells[0].text.strip()
                # 이 행은 상품명 선언 및 버튼만 있으므로 데이터 저장 안 함.
                continue

            # Case 2: 최신 판매 정보 행 (상품명 td 없음, current_main_product_name 사용)
            # 주보험 HTML 구조: td(판매기간), td(사업방법서), td(상품요약서), td(약관), td, td, td(특약) - 총 7개 td
            # 특약 HTML 구조: td(판매기간), td(약관) - 총 2개 td
            elif not th_cells and \
                ((product_type == "주보험" and len(td_cells) == 7)
                 or (product_type == "특약" and len(td_cells) == 2)):
                product_name = current_main_product_name
                sales_period = td_cells[0].text.strip()

                if product_type == "주보험":
                    # 주보험 필드 추출
                    bm_links = td_cells[1].find_elements(By.TAG_NAME, "a")
                    business_manual_link = bm_links[0].get_attribute('href') if bm_links and bm_links[0].text.strip() != "-" else "N/A"

                    s_links = td_cells[2].find_elements(By.TAG_NAME, "a")
                    summary_link = s_links[0].get_attribute('href') if s_links and s_links[0].text.strip() != "-" else "N/A"

                    t_links = td_cells[3].find_elements(By.TAG_NAME, "a")
                    terms_link = t_links[0].get_attribute('href') if t_links and t_links[0].text.strip() != "-" else "N/A"

                    products_data.append({
                        "product_name": product_name, "sales_period": sales_period,
                        "business_manual_link": business_manual_link, "summary_link": summary_link, "terms_link": terms_link,
                        "type": product_type
                    })
                elif product_type == "특약":
                    # 특약: 상품명(current_main_product_name), 판매기간(td_cells[0]), 약관(td_cells[1])
                    t_links = td_cells[1].find_elements(By.TAG_NAME, "a")  # 약관 링크는 두 번째 td
                    terms_link = t_links[0].get_attribute('href') if t_links and t_links[0].text.strip() != "-" else "N/A"
                    products_data.append({
                        "product_name": product_name, "sales_period": sales_period,
                        "terms_link": terms_link, "type": product_type
                    })

            # Case 3: 펼쳐진 과거 정보 행 (숨겨진 th + 상품명 td + 나머지 정보 td들)
            # 주보험 HTML 구조: (숨겨진 th), td(상품명), td(판매기간), td(사업방법서), td(상품요약서 또는 -), td(약관), td, td, td(특약) - 총 8개 td
            # 특약 HTML 구조: (숨겨진 th), td(상품명), td(판매기간), td(약관) - 총 3개 td (상품명, 판매기간, 약관)
            elif th_cells and "display: none" in th_cells[0].get_attribute("outerHTML") and \
                ((product_type == "주보험" and len(td_cells) == 8)
                 or (product_type == "특약" and len(td_cells) == 3)):  # 특약은 td 3개 (상품명, 판매기간, 약관)
                product_name = td_cells[0].text.strip()
                current_main_product_name = product_name  # 펼쳐진 행도 자체 상품명을 가짐
                sales_period = td_cells[1].text.strip()

                if product_type == "주보험":
                    # 주보험 필드 추출
                    bm_links = td_cells[2].find_elements(By.TAG_NAME, "a")
                    business_manual_link = bm_links[0].get_attribute('href') if bm_links and bm_links[0].text.strip() != "-" else "N/A"
                    s_links = td_cells[3].find_elements(By.TAG_NAME, "a")
                    summary_text = td_cells[3].text.strip()
                    summary_link = s_links[0].get_attribute('href') if s_links and summary_text != "-" else "N/A"
                    t_links = td_cells[4].find_elements(By.TAG_NAME, "a")
                    terms_link = t_links[0].get_attribute('href') if t_links and t_links[0].text.strip() != "-" else "N/A"
                    products_data.append({
                        "product_name": product_name, "sales_period": sales_period,
                        "business_manual_link": business_manual_link, "summary_link": summary_link, "terms_link": terms_link,
                        "type": product_type
                    })
                elif product_type == "특약":
                    # 특약: 상품명(td_cells[0]), 판매기간(td_cells[1]), 약관(td_cells[2])
                    t_links = td_cells[2].find_elements(By.TAG_NAME, "a")  # 약관 링크는 세 번째 td
                    terms_link = t_links[0].get_attribute('href') if t_links and t_links[0].text.strip() != "-" else "N/A"
                    products_data.append({
                        "product_name": product_name, "sales_period": sales_period,
                        "terms_link": terms_link, "type": product_type
                    })
            else:
                # print(f"Skipping row for {product_type} with unhandled structure (th: {len(th_cells)}, td: {len(td_cells)}) in row {i}")
                # print(row.get_attribute("outerHTML"))
                continue

            # 이전 판매기간 정보가 있는 행 처리 (클래스명 등으로 구분 필요) - 이 로직은 위에서 통합됨
            # 현재는 이전 판매기간 행을 구분하는 명확한 CSS 선택자가 없어 기본 로직에 포함되지 않음.
                # print(row.get_attribute("outerHTML")) # 잘못된 부분 제거
                continue  # 잘못된 부분 제거

    except Exception as e:
        print(f"데이터 추출 중 오류 발생: {e}")
    finally:
        driver.quit()

    return products_data


if __name__ == '__main__':
    # === 사용자 설정 필요 ===
    # WebDriver 경로는 webdriver_manager가 자동으로 처리합니다.

    # 2. 모든 "이전 판매기간 펼치기"를 시도할지 여부 (True 또는 False)
    click_history = True  # 사용자가 "모두 가져오기"를 선택했으므로 기본값 True

    # 3. 어떤 정보를 스크래핑할지 ("주보험" 또는 "특약")
    # 스크립트 실행 시 인자로 받거나, 여기서 직접 설정할 수 있습니다.
    # 예시: target_info = "주보험" 또는 target_info = "특약"
    # 우선은 주보험과 특약을 모두 가져오도록 호출 예시를 만듭니다.

    print("--- 주보험 정보 ---")
    main_insurance_list = get_metlife_product_info(scrape_target="주보험", click_all_history=click_history)
    if main_insurance_list:
        for idx, info in enumerate(main_insurance_list):
            print(f"\n--- 주보험 {idx + 1} ({info.get('type', 'N/A')}) ---")
            print(f"상품명: {info.get('product_name', 'N/A')}")
            print(f"판매기간: {info.get('sales_period', 'N/A')}")
            print(f"사업방법서 링크: {info.get('business_manual_link', 'N/A')}")
            print(f"상품요약서 링크: {info.get('summary_link', 'N/A')}")
            print(f"약관 링크: {info.get('terms_link', 'N/A')}")
    else:
        print("추출된 주보험 정보가 없습니다.")

    print("\n\n--- 특약 정보 ---")
    special_terms_list = get_metlife_product_info(scrape_target="특약", click_all_history=click_history)
    if special_terms_list:
        for idx, info in enumerate(special_terms_list):
            print(f"\n--- 특약 {idx + 1} ({info.get('type', 'N/A')}) ---")
            print(f"상품명: {info.get('product_name', 'N/A')}")
            print(f"판매기간: {info.get('sales_period', 'N/A')}")
            # 특약은 사업방법서, 상품요약서가 없을 수 있음
            print(f"약관 링크: {info.get('terms_link', 'N/A')}")
    else:
        print("추출된 상품 정보가 없습니다.")
