# 새마을금고중앙회/db확인
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import os
import sys
from datetime import datetime  # datetime import 활성화

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from neoali.pdf_link_scraper import PdfLinkExtractor
    from neoali.DB_save import DatabaseManager  # DatabaseManager import 추가
except ImportError as e:
    PdfLinkExtractor = None
    DatabaseManager = None  # DatabaseManager 초기화 추가
    print(f"경고: 모듈 임포트 실패 ({e}). 일부 기능이 비활성화될 수 있습니다.")

MG_DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads", "mg_insurance")
if not os.path.exists(MG_DOWNLOAD_DIR):
    os.makedirs(MG_DOWNLOAD_DIR)


class MGInsuranceScraper:
    def __init__(self):
        options = Options()
        # options.add_argument("--headless")  # headless 옵션 활성화
        options.add_argument("--start-maximized")
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        prefs = {
            "download.default_directory": MG_DOWNLOAD_DIR,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True,
            "profile.default_content_setting_values.automatic_downloads": 1
        }
        options.add_experimental_option("prefs", prefs)
        options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.wait = WebDriverWait(self.driver, 10)
        self.base_url = "https://insure.kfcc.co.kr/#/PGE_IHJ_00003"

        self.pdf_extractor = None
        if PdfLinkExtractor:
            self.pdf_extractor = PdfLinkExtractor(self.driver, MG_DOWNLOAD_DIR)

    def safe_click(self, element_or_xpath, by=By.XPATH, wait_sec=5):
        """
        요소를 안전하게 클릭합니다. 요소가 준비될 때까지 기다린 후 클릭을 시도하고,
        클릭 중 발생할 수 있는 일반적인 예외를 처리합니다.
        """
        try:
            if isinstance(element_or_xpath, str):  # XPath 문자열인 경우
                element = WebDriverWait(self.driver, wait_sec).until(
                    EC.element_to_be_clickable((by, element_or_xpath))
                )
            else:  # WebElement 객체인 경우
                element = WebDriverWait(self.driver, wait_sec).until(
                    EC.element_to_be_clickable(element_or_xpath)
                )

            # JavaScript를 사용하여 클릭 (일부 가려진 요소 클릭에 도움될 수 있음)
            self.driver.execute_script("arguments[0].click();", element)
            return True
        except TimeoutException:
            print(f"클릭 시간 초과: {element_or_xpath if isinstance(element_or_xpath, str) else 'WebElement'}")
            return False
        except NoSuchElementException:
            print(f"요소를 찾을 수 없음: {element_or_xpath if isinstance(element_or_xpath, str) else 'WebElement'}")
            return False
        except Exception as e:
            print(f"클릭 중 예기치 않은 오류 발생 ({element_or_xpath if isinstance(element_or_xpath, str) else 'WebElement'}): {e}")
            return False

    def _scroll_to_end(self):
        last_height = self.driver.execute_script(
            "return document.body.scrollHeight")
        while True:
            self.driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_height = self.driver.execute_script(
                "return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

    def _extract_product_details_from_modal(self):
        product_name = ""
        sales_period = ""
        terms_link_val = "N/A"
        business_method_link_val = "N/A"

        modal_table_body_selector = "div.ur-modal__container table tbody"
        modal_base_tr_xpath = "//div[contains(@class,'ur-modal__container')]//table/tbody/tr[1]"

        terms_button_xpath_modal = f"{modal_base_tr_xpath}/td[3]/descendant::button[1]"
        biz_method_button_xpath_modal = f"{modal_base_tr_xpath}/td[4]/descendant::button[1]"

        try:
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, modal_table_body_selector)))
            time.sleep(0.5)

            try:
                product_name_element = self.wait.until(EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, f"{modal_table_body_selector} tr:first-child td:nth-child(1)")))
                product_name = product_name_element.text.strip()
            except Exception as e:
                print(f"모달 상품명 추출 오류: {e}")

            try:
                sales_period_element = self.wait.until(EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, f"{modal_table_body_selector} tr:first-child td:nth-child(2)")))
                sales_period = sales_period_element.text.strip()
            except Exception as e:
                print(f"모달 판매기간 추출 오류: {e}")

            if self.pdf_extractor:
                try:
                    self.wait.until(EC.presence_of_element_located((By.XPATH, terms_button_xpath_modal)))
                    terms_link_val = self.pdf_extractor.get_pdf_url_via_network_interception(terms_button_xpath_modal) or "N/A (추출 실패)"
                except TimeoutException:
                    terms_link_val = "N/A (버튼 없음)"
                except Exception as e_pdf:
                    print(f"모달 약관 링크 추출 오류: {e_pdf}")
                    terms_link_val = "N/A (추출 오류)"

                try:
                    self.wait.until(EC.presence_of_element_located((By.XPATH, biz_method_button_xpath_modal)))
                    business_method_link_val = self.pdf_extractor.get_pdf_url_via_network_interception(biz_method_button_xpath_modal) or "N/A (추출 실패)"
                except TimeoutException:
                    business_method_link_val = "N/A (버튼 없음)"
                except Exception as e_pdf:
                    print(f"모달 사업방법서 링크 추출 오류: {e_pdf}")
                    business_method_link_val = "N/A (추출 오류)"
            else:
                try:
                    if self.driver.find_elements(By.XPATH, terms_button_xpath_modal):
                        terms_link_val = "존재함 (Extractor 비활성)"
                except Exception:
                    pass
                try:
                    if self.driver.find_elements(By.XPATH, biz_method_button_xpath_modal):
                        business_method_link_val = "존재함 (Extractor 비활성)"
                except Exception:
                    pass

        except TimeoutException:
            print("모달 내부 테이블(tbody) 로드 시간 초과.")
        except Exception as e:
            print(f"모달 정보 추출 중 오류 발생: {e}")

        return product_name, sales_period, terms_link_val, business_method_link_val

    def _get_products_from_current_tab(self, product_list, status):
        try:
            table_body_selector = ".mg-table-templete tbody"
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, table_body_selector)))

            initial_rows = self.driver.find_elements(By.CSS_SELECTOR, f"{table_body_selector} tr")
            # num_rows = len(initial_rows) # 상세 행 개수 출력 제거
            # print(f"'{status}' 탭에서 {num_rows}개의 행 발견.") # 상세 행 개수 출력 제거
            print(f"'{status}' 탭 상품 정보 수집 중...")  # 간소화된 메시지

            base_tbody_xpath = "//table[contains(@class,'mg-table-templete')]/tbody"

            for i in range(len(initial_rows)):  # num_rows 대신 len(initial_rows) 사용
                current_row_xpath = f"({base_tbody_xpath}/tr)[{i + 1}]"
                try:
                    row_element = self.wait.until(EC.presence_of_element_located((By.XPATH, current_row_xpath)))
                    cols = row_element.find_elements(By.TAG_NAME, "td")
                except TimeoutException:
                    print(f"행 {i + 1} 로드 시간 초과. 건너뜁니다.")
                    continue
                except Exception as e_row_find:
                    print(f"행 {i + 1} 찾는 중 오류: {e_row_find}. 건너뜁니다.")
                    continue

                product_type = "N/A"
                product_name = "N/A"
                sales_period = "N/A"
                summary_link_val = "N/A"
                terms_link_val = "N/A"
                business_method_link_val = "N/A"

                if status == "판매중":
                    if len(cols) >= 3:
                        product_type = cols[0].text.strip().replace('\n', ' > ')
                        product_name = cols[1].text.strip()
                        sales_period = cols[2].text.strip()

                        if len(cols) > 3:
                            summary_button_xpath = f"{current_row_xpath}/td[4]/button[1]"
                            if self.pdf_extractor:
                                try:
                                    self.wait.until(EC.presence_of_element_located((By.XPATH, summary_button_xpath)))
                                    summary_link_val = self.pdf_extractor.get_pdf_url_via_network_interception(summary_button_xpath) or "N/A (추출 실패)"
                                except TimeoutException:
                                    summary_link_val = "N/A (버튼 없음)"
                                except Exception as e_sl:
                                    print(f"  상품요약서 링크 추출 오류 ({product_name}): {e_sl}")
                                    summary_link_val = "N/A (추출 오류)"
                            elif cols[3].find_elements(By.XPATH, ".//button"):
                                summary_link_val = "존재함 (Extractor 비활성)"

                        if len(cols) > 4:
                            terms_button_xpath = f"{current_row_xpath}/td[5]/button[1]"
                            if self.pdf_extractor:
                                try:
                                    self.wait.until(EC.presence_of_element_located((By.XPATH, terms_button_xpath)))
                                    terms_link_val = self.pdf_extractor.get_pdf_url_via_network_interception(terms_button_xpath) or "N/A (추출 실패)"
                                except TimeoutException:
                                    terms_link_val = "N/A (버튼 없음)"
                                except Exception as e_tl:
                                    print(f"  약관 링크 추출 오류 ({product_name}): {e_tl}")
                                    terms_link_val = "N/A (추출 오류)"
                            elif cols[4].find_elements(By.XPATH, ".//button"):
                                terms_link_val = "존재함 (Extractor 비활성)"

                        if len(cols) > 5:
                            biz_button_xpath = f"{current_row_xpath}/td[6]/button[1]"
                            if self.pdf_extractor:
                                try:
                                    self.wait.until(EC.presence_of_element_located((By.XPATH, biz_button_xpath)))
                                    business_method_link_val = self.pdf_extractor.get_pdf_url_via_network_interception(
                                        biz_button_xpath) or "N/A (추출 실패)"
                                except TimeoutException:
                                    business_method_link_val = "N/A (버튼 없음)"
                                except Exception as e_bl:
                                    print(f"  사업방법서 링크 추출 오류 ({product_name}): {e_bl}")
                                    business_method_link_val = "N/A (추출 오류)"
                            elif cols[5].find_elements(By.XPATH, ".//button"):
                                business_method_link_val = "존재함 (Extractor 비활성)"

                    product_list.append({
                        "판매상태": status, "종류": product_type, "상품명": product_name,
                        "판매기간": sales_period, "상품요약서_링크": summary_link_val,
                        "약관": terms_link_val, "사업방법서": business_method_link_val
                    })
                    # print(f"  판매중 추가: {product_name}, 요약서: {summary_link_val}, 약관: {terms_link_val}, 사업방법서: {business_method_link_val}") # 상세 추가 로그 제거

                elif status == "판매중지":
                    if len(cols) >= 1:
                        try:
                            detail_button = None
                            button_td_idx = -1
                            for td_idx_btn, td_elem_btn in enumerate(cols):
                                try:
                                    btn = td_elem_btn.find_element(By.TAG_NAME, "button")
                                    detail_button = btn
                                    button_td_idx = td_idx_btn
                                    break
                                except NoSuchElementException:
                                    continue

                            if detail_button:
                                button_xpath = f"{current_row_xpath}/td[{button_td_idx + 1}]/button[1]"
                                # print(f"    판매중지 상품 '{cols[0].text.strip() if cols else '이름모름'}' 상세 버튼 클릭 시도 (XPath: {button_xpath})") # 상세 클릭 로그 제거
                                clicked_successfully = self.safe_click(button_xpath, by=By.XPATH, wait_sec=1.5)
                                if not clicked_successfully:
                                    # print(f"      상세 버튼 클릭 실패: {cols[0].text.strip() if cols else '이름모름'}") # 상세 실패 로그 제거
                                    continue

                                modal_data = self._extract_product_details_from_modal()
                                modal_product_name = modal_data[0]
                                modal_sales_period = modal_data[1]
                                terms_link_val = modal_data[2]
                                business_method_link_val = modal_data[3]

                                product_name = modal_product_name if modal_product_name else (cols[0].text.strip() if cols else "N/A")
                                sales_period = modal_sales_period if modal_sales_period else "N/A"
                                product_type = "N/A (판매중지)"
                                try:
                                    close_button_selector = ".ur-modal__close.ur-icon.ur-icon--line.opus-icon__close"
                                    close_button = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, close_button_selector)))
                                    self.driver.execute_script("arguments[0].click();", close_button)
                                    self.wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, "div.ur-modal__container")))
                                except Exception as e_close:
                                    print(f"모달 닫기 오류: {e_close}. ESC 시도.")
                                    from selenium.webdriver.common.keys import Keys
                                    webdriver.ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                                    try:
                                        self.wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, "div.ur-modal__container")))
                                    except TimeoutException:
                                        print("ESC로도 모달 닫기 실패.")
                                product_list.append({
                                    "판매상태": status, "종류": product_type, "상품명": product_name,
                                    "판매기간": sales_period, "상품요약서_링크": "N/A (판매중지)",  # 판매중지 상품은 요약서 없음
                                    "약관": terms_link_val, "사업방법서": business_method_link_val
                                })
                                # print(f"  판매중지 추가: {product_name}, 약관: {terms_link_val}, 사업방법서: {business_method_link_val}") # 상세 추가 로그 제거
                            else:
                                if len(cols) == 1 and "데이터가 없습니다" in cols[0].text:
                                    # print("판매중지 탭에 상품 데이터가 없습니다.") # 데이터 없음 로그는 유지해도 좋음
                                    break
                                # else: # 버튼 못찾는 경우는 오류 로그로 남기지 않음
                                    # print(f"판매중지 상품 테이블의 행에서 상세 보기 버튼을 찾을 수 없습니다: {cols[0].text if cols else '내용 없음'}")
                        except Exception as e_detail_btn:
                            print(f"판매중지 상품 '{product_name}' 처리 중 오류: {e_detail_btn}")  # 오류 발생 상품명 명시
        except Exception as e_tab:
            print(f"'{status}' 탭 상품 목록 처리 중 오류: {e_tab}")
        print(f"'{status}' 탭 상품 정보 수집 완료.")  # 탭 완료 메시지
        return product_list

    def get_all_products(self):
        self.driver.get(self.base_url)
        all_products = []
        print("MG새마을금고보험 스크래핑 시작...")  # 전체 시작 메시지
        try:
            # print("판매 중인 상품 정보를 가져옵니다...") # _get_products_from_current_tab 내부 메시지로 대체
            self.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, ".mg-table-templete tbody")))
            all_products = self._get_products_from_current_tab(all_products, "판매중")
            print("판매중 상품 스크래핑 완료.")  # 각 탭 완료 메시지
        except Exception as e:
            print(f"판매중 상품 스크래핑 중 오류: {e}")

        try:
            print("판매중지 상품 스크래핑 진행중...")  # 다음 탭 진행 메시지
            tab_selector = "div.ur-tab__label-wrapper > a#sur-tab-box__37__label__1"
            discontinued_tab_button = self.wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, tab_selector)))
            self.driver.execute_script("arguments[0].click();", discontinued_tab_button)
            # print("판매 중지 탭 클릭 시도 완료.") # 상세 로그 제거
            active_tab_css_selector = "a#sur-tab-box__37__label__1.ur-tab__label--active"
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, active_tab_css_selector)))
            # print("판매 중지 탭 활성화 확인.") # 상세 로그 제거
            time.sleep(1)
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".mg-table-templete tbody")))
            # print("판매 중지 탭으로 이동 및 새 테이블 로드 확인.") # 상세 로그 제거
            # print("판매 중지된 상품 정보를 가져옵니다...") # _get_products_from_current_tab 내부 메시지로 대체
            all_products = self._get_products_from_current_tab(all_products, "판매중지")
            print("판매중지 상품 스크래핑 완료.")  # 각 탭 완료 메시지
        except Exception as e:
            print(f"판매중지 상품 스크래핑 중 오류: {e}")
        print("MG새마을금고보험 스크래핑 완료.")  # 전체 완료 메시지
        return all_products

    def close(self):
        if self.driver:
            self.driver.quit()


def is_valid_link(link_str):
    print(f"is_valid_link 검사 시작: '{link_str}'")  # 디버깅 로그
    if not link_str or not isinstance(link_str, str):
        print(f"  결과: False (유효하지 않은 문자열 또는 None)")  # 디버깅 로그
        return False

    invalid_markers = ["N/A", "Extractor 비활성", "추출 실패", "추출 오류", "버튼 없음"]
    for marker in invalid_markers:
        if marker in link_str:
            print(f"  결과: False (부적절한 마커 '{marker}' 포함)")  # 디버깅 로그
            return False

    if not link_str.startswith("http"):
        print(f"  결과: False (http로 시작하지 않음)")  # 디버깅 로그
        return False

    print(f"  결과: True (유효한 링크)")  # 디버깅 로그
    return True


if __name__ == "__main__":
    scraper = MGInsuranceScraper()
    products_data = []
    try:
        products_data = scraper.get_all_products()
    except Exception as e_main:
        print(f"스크래핑 실행 중 오류: {e_main}")
    finally:
        scraper.close()

    if products_data:
        if DatabaseManager:
            print("DB 저장 진행중...")
            structured_rows_to_save = []
            scraped_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            company_name = "MG새마을금고보험"

            for product in products_data:
                product_name_val = product.get('상품명', 'N/A')
                sales_period_val = product.get('판매기간', 'N/A')
                product_code_val = None  # product_code는 NULL로 저장

                # 각 문서 타입에 대해 링크 유효성 검사 및 저장 데이터 생성
                # 판매중: 상품요약서, 약관, 사업방법서
                # 판매중지: 약관, 사업방법서 (요약서는 없음)

                links_to_process = []
                if product.get('판매상태') == '판매중':
                    links_to_process.append({'type': '상품요약서', 'url': product.get('상품요약서_링크')})
                    links_to_process.append({'type': '약관', 'url': product.get('약관')})
                    links_to_process.append({'type': '사업방법서', 'url': product.get('사업방법서')})
                elif product.get('판매상태') == '판매중지':
                    links_to_process.append({'type': '약관', 'url': product.get('약관')})
                    links_to_process.append({'type': '사업방법서', 'url': product.get('사업방법서')})

                has_valid_link_for_this_product = False
                current_product_docs = []
                for link_info in links_to_process:
                    doc_type = link_info['type']
                    link_url = link_info['url']
                    if is_valid_link(link_url):
                        has_valid_link_for_this_product = True
                        current_product_docs.append([
                            company_name,
                            product_name_val,
                            product_code_val,
                            doc_type,
                            sales_period_val,
                            scraped_time,
                            link_url
                        ])

                if has_valid_link_for_this_product:
                    structured_rows_to_save.extend(current_product_docs)

            if structured_rows_to_save:
                with DatabaseManager(db_name="insurance_products.db") as db_manager:
                    saved_count = db_manager.save_data(structured_rows_to_save)
                print(f"DB 저장 완료. 총 {saved_count}건 문서 정보 저장.")
            else:
                print("DB에 저장할 유효한 문서 정보가 없습니다.")
            print(f"총 스크래핑된 상품 수: {len(products_data)}개")
        else:
            print("DatabaseManager 사용 불가. DB 저장 기능을 건너뜁니다.")
    else:
        print("스크래핑된 상품 데이터가 없습니다.")
