import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

# --- Gemini API 설정 (맨 위로 이동) ---
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError(
        "GEMINI_API_KEY 환경 변수가 설정되지 않았습니다. .env 파일을 확인하거나 직접 설정해주세요.")

genai.configure(api_key=GEMINI_API_KEY)

# --- EpostScraper 클래스 정의 (여기에 그대로 복사) ---


class EpostScraper:
    def __init__(self, driver, tf: bool):
        self.driver = driver
        self.tf = tf  # True: tbody name=list / False: tbody id=stopPrdTbody0

    def get_all_data(self):
        data_list = []
        list_index = 1
        while True:
            if self.tf:
                tbody_xpath = f"//tbody[@name='list{list_index}']"
            else:
                tbody_xpath = f"//tbody[@id='stopPrdTbody0{list_index}']"
            try:
                tbody_element = self.driver.find_element(By.XPATH, tbody_xpath)
                rows = tbody_element.find_elements(By.TAG_NAME, "tr")

                if not rows:
                    break

                print(f"DEBUG: Found {len(rows)} rows in {tbody_xpath}")
                self._extract_rows(rows, data_list)
                list_index += 1
            except NoSuchElementException:
                print(
                    f"DEBUG: No more tbody found with xpath: {tbody_xpath}. Breaking loop.")
                break
            except Exception as e:
                print(
                    f"DEBUG: An unexpected error occurred while processing {tbody_xpath}: {e}")
                break

        return data_list

    def _extract_rows(self, rows, data_list):
        rowspan_cache = {}

        for row_index, row_element in enumerate(rows):
            row_data = []
            col_idx = 0
            cell_idx = 0

            all_cells_in_row = row_element.find_elements(
                By.XPATH, "./td | ./th")

            actual_cells_in_row_data = []
            for cell_element_raw in all_cells_in_row:
                actual_cells_in_row_data.append(cell_element_raw)

            current_col_idx = 0
            for cell_element in actual_cells_in_row_data:
                while (current_col_idx, row_index) in rowspan_cache:
                    row_data.append(
                        rowspan_cache[(current_col_idx, row_index)])
                    del rowspan_cache[(current_col_idx, row_index)]
                    current_col_idx += 1

                text = cell_element.get_attribute(
                    "textContent").strip().replace("\n", " ")
                link = None
                link_text = None
                link_element = None
                data_href_value = None

                try:
                    link_element = cell_element.find_element(By.TAG_NAME, "a")
                    link = link_element.get_attribute("href")
                    if link is None:
                        data_href_value = link_element.get_attribute(
                            "data-href")
                except NoSuchElementException:
                    pass

                if link_element is not None:
                    link_text = link_element.get_attribute(
                        "textContent").strip()

                value = text

                if link or data_href_value:
                    processed_link_value = None
                    if self.tf is True:
                        if text == "약관보기":
                            processed_link_value = ("약관", link)
                        else:
                            processed_link_value = (text, link)
                    else:
                        base_url = "https://epostlife.go.kr"
                        if data_href_value:
                            full_url = base_url + data_href_value
                        else:
                            full_url = link

                        if not link_text:
                            processed_link_value = ("약관", full_url)
                        else:
                            processed_link_value = (link_text, full_url)

                    if processed_link_value:
                        value = processed_link_value

                row_data.append(value)

                rowspan = cell_element.get_attribute("rowspan")
                if rowspan and int(rowspan) > 1:
                    rowspan_int = int(rowspan)
                    for i in range(1, rowspan_int):
                        key = (current_col_idx, row_index + i)
                        rowspan_cache[key] = value

                current_col_idx += 1

            while (current_col_idx, row_index) in rowspan_cache:
                row_data.append(rowspan_cache[(current_col_idx, row_index)])
                del rowspan_cache[(current_col_idx, row_index)]
                current_col_idx += 1

            if row_data:
                data_list.append(row_data)

# --- EpostScraper 클래스 정의 끝 ---


# --- analyze_epost_data_with_gemini 함수 정의 (여기에 그대로 복사) ---
def analyze_epost_data_with_gemini(epost_data: list, user_query: str):
    """
    EpostScraper에서 수집된 데이터를 Gemini API를 사용하여 분석합니다.
    """
    if not epost_data:
        return "분석할 데이터가 없습니다."

    serialized_data_lines = []
    for row_idx, row_data in enumerate(epost_data):
        row_str_parts = []
        for item in row_data:
            if isinstance(item, tuple):
                row_str_parts.append(f"('{item[0]}', '{item[1]}')")
            else:
                row_str_parts.append(f"'{item}'")
        serialized_data_lines.append(
            f"행 {row_idx+1}: " + ", ".join(row_str_parts))

    data_for_gemini = "\n".join(serialized_data_lines)

    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')

        prompt = f"""
        다음은 우체국보험 웹사이트에서 추출한 테이블 데이터입니다. 각 '행 X'는 테이블의 한 행을 나타내며,
        그 뒤에 해당 행의 셀 내용들이 순서대로 나열되어 있습니다. 텍스트 값은 작은따옴표로 묶여 있고,
        링크 정보는 (링크 텍스트, URL) 튜플 형태로 표시되어 있습니다.
        
        당신은 이 데이터를 분석하여 사용자 질문에 가장 적합한 정보를 제공하는 에이전트입니다.
        사용자의 질문에 명확하고 간결하게 답변해주세요.
        
        --- 추출된 테이블 데이터 시작 ---
        {data_for_gemini}
        --- 추출된 테이블 데이터 끝 ---
        
        사용자 질문: {user_query}
        
        답변:
        """

        print("\nGemini에 데이터 분석 요청 중...")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Gemini API 오류 발생: {e}")
        return f"데이터 분석 중 오류가 발생했습니다: {e}"

# --- analyze_epost_data_with_gemini 함수 정의 끝 ---


# ───── 3. 메인 실행 부분 (여기에 그대로 복사) ─────
options = Options()
# options.add_argument("--headless") # 백그라운드에서 실행 (선택 사항)
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--start-maximized")

driver = None
try:
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    wait = WebDriverWait(driver, 10)

    all_scraped_data = []

    print("--- 첫 번째 페이지 스크래핑 시작 ---")
    target_url_1 = "https://epostlife.go.kr/ASISDM00AT.do"
    driver.get(target_url_1)
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.XPATH, "//tbody[@name='list1']"))
    )
    scraper1 = EpostScraper(driver, tf=True)
    all_scraped_data.extend(scraper1.get_all_data())
    print("--- 첫 번째 페이지 스크래핑 완료 ---")

    print("\n--- 두 번째 페이지 스크래핑 시작 ---")
    target_url_2 = "https://epostlife.go.kr/ASISDM00BT.do"
    driver.get(target_url_2)
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located(
            (By.XPATH, "//tbody[@id='stopPrdTbody01']"))
    )
    scraper2 = EpostScraper(driver, tf=False)
    all_scraped_data.extend(scraper2.get_all_data())
    print("--- 두 번째 페이지 스크래핑 완료 ---")

    print("\n--- Gemini 에이전트 분석 시작 ---")
    while True:
        user_question = input("\n수집된 데이터에 대해 궁금한 점을 질문해주세요 (종료하려면 'q' 입력): ")
        if user_question.lower() == 'q':
            break

        analysis_result = analyze_epost_data_with_gemini(
            all_scraped_data, user_question)
        print("\n--- Gemini 분석 결과 ---")
        print(analysis_result)
        print("---------------------------")

except Exception as main_e:
    print(f"메인 실행 중 오류 발생: {main_e}")
finally:
    if driver:
        print("브라우저 종료 중...")
        driver.quit()
