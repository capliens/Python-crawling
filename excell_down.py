from datetime import datetime
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os
import requests
from urllib.parse import urljoin

# --- 설정 (이 부분을 필요에 따라 업데이트하세요) ---
excel_file_path = 'test_data.xlsx'      # 읽을 엑셀 파일 경로
sheet_name = '남자 40대'                   # 엑셀 시트 이름 (기본값)
insurance_company_col = '보험사'         # 보험사 이름이 있는 열
product_name_col = '보험상품명'             # 보험 상품명이 있는 열
insurance_date_col = '가입일'                 # 보험 가입일이 있는 열
DOWNLOAD_DIRECTORY = 'downloads'            # 다운로드 파일을 저장할 폴더

# 보험사별 웹사이트 URL 매핑
company_url_map = {
    '삼성화재해상보험주식회사': 'https://www.samsungfire.com/vh/page/VH.HPIF0103.do',
    '교보생명보험(주)': 'https://www.kyobo.com/dgt/web/product-official/all-product/search'
}


def download_file(url, folder_path, file_name, doc_date=None):
    """지정된 URL에서 파일을 다운로드하여 저장합니다. 실패 시 3번 재시도합니다."""
    if doc_date:
        file_name = f"{file_name}_{doc_date.strftime('%Y%m%d')}"

    safe_file_name = "".join([c for c in file_name if c not in '\\/:*?"<>|']).rstrip()
    safe_file_name = f"{safe_file_name}.pdf" if not safe_file_name.lower().endswith('.pdf') else safe_file_name

    os.makedirs(folder_path, exist_ok=True)
    file_path = os.path.join(folder_path, safe_file_name)

    if os.path.exists(file_path):
        print(f"파일이 이미 존재하여 건너뜁니다: {file_path}")
        return True

    # 3번의 재시도 로직
    for attempt in range(3):
        try:
            print(f"'{url}' 에서 파일 다운로드 시도 중... (시도 {attempt + 1}/3)")
            response = requests.get(url, stream=True, timeout=30)  # 30초 타임아웃 설정
            response.raise_for_status()

            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"파일 저장 완료: {file_path}")
            return True
        except requests.exceptions.RequestException as e:
            print(f"시도 {attempt + 1} 실패: 파일 다운로드 중 오류 발생: {e}")
            if attempt < 2:
                time.sleep(5)  # 재시도 전 5초 대기
            else:
                print("최대 재시도 횟수를 초과했습니다.")
                return False
        except Exception as e:
            print(f"파일 저장 중 오류 발생: {e}")
            return False
    return False


def extract_date_from_text(text):
    """텍스트에서 YYYYMMDD, YYYY.MM.DD 등의 날짜 형식을 찾아 datetime 객체로 반환합니다."""
    # YYYYMMDD, YYYY.MM.DD, YYYY-MM-DD, YYYY년MM월DD일 등 형식 지원
    patterns = [
        r'(\d{4})[.\-/]?(\d{2})[.\-/]?(\d{2})',
        r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일'
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                year, month, day = map(int, match.groups())
                return datetime(year, month, day)
            except ValueError:
                continue
    return None


def get_doc_type_and_folder(link_text, base_folder):
    """링크 텍스트를 기반으로 문서 유형과 저장 폴더를 결정합니다."""
    link_text = link_text.lower()
    if '약관' in link_text:
        doc_type = '약관'
        folder = os.path.join(base_folder, '약관')
    elif '요약' in link_text or '설명서' in link_text:
        doc_type = '요약서'
        folder = os.path.join(base_folder, '요약서')
    elif '방법서' in link_text:
        doc_type = '방법서'
        folder = os.path.join(base_folder, '방법서')
    else:
        doc_type = '기타'
        folder = os.path.join(base_folder, '기타')
    return doc_type, folder


def generate_search_terms(product_name):
    """전체 상품명에서 점차 짧은 검색어를 생성합니다."""
    terms = [product_name]
    temp_name = product_name
    # 괄호 또는 마지막 단어를 제거하며 검색어 생성
    while '(' in temp_name or ' ' in temp_name:
        last_paren = temp_name.rfind('(')
        last_space = temp_name.rfind(' ')
        split_index = max(last_paren, last_space)
        if split_index > 0:
            temp_name = temp_name[:split_index].strip()
            if len(temp_name) > 5:  # 너무 짧은 검색어는 제외
                terms.append(temp_name)
        else:
            break
    return terms


def handle_kyobo(driver, product_name, enrollment_date, base_download_folder):
    """교보생명 웹사이트에서 상품 정보를 검색하고 다운로드합니다."""

    search_terms = generate_search_terms(product_name)
    rows = []
    successful_term = ""

    for term in search_terms:
        print(f"'{term}'(으)로 검색 시도 중...")
        try:
            search_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'input-01')))
            search_input.clear()
            search_input.send_keys(term)
            driver.find_element(By.ID, 'searchBtn').click()
            time.sleep(3)

            rows = driver.find_elements(By.CSS_SELECTOR, '#insuList tr')
            if rows and "검색결과가 없습니다" not in driver.page_source:
                print(f"'{term}'(으)로 검색 결과 {len(rows)}건을 찾았습니다.")
                successful_term = term
                break
        except Exception as e:
            print(f"'{term}' 검색 중 오류: {e}")
            continue

    if not rows or "검색결과가 없습니다" in driver.page_source:
        print(f"'{product_name}'에 대한 최종 검색 결과가 없습니다.")
        return

    try:
        # 2. 검색 결과에서 상품 찾아 '확인' 버튼 클릭
        print(f"총 {len(rows)}개의 검색 결과에서 '{successful_term}'과(와) 일치하는 항목을 찾습니다...")
        product_found = False
        target_row = None
        # 웹사이트에서 실제 선택된 상품명
        selected_product_name = product_name

        if len(rows) == 1:
            target_row = rows[0]
            selected_product_name = target_row.find_elements(By.TAG_NAME, 'td')[1].text
            print(f"검색 결과가 1건이므로 '{selected_product_name}'을(를) 선택합니다.")
        else:
            # 1순위: 대소문자 구분하여 정확히 일치하는 항목 찾기
            for row in rows:
                cols = row.find_elements(By.TAG_NAME, 'td')
                if len(cols) > 1 and successful_term in cols[1].text:
                    target_row = row
                    selected_product_name = cols[1].text
                    break
            # 2순위: 1순위가 없으면 대소문자 무시하고 포함되는 항목 찾기
            if not target_row:
                for row in rows:
                    cols = row.find_elements(By.TAG_NAME, 'td')
                    if len(cols) > 1 and successful_term.lower() in cols[1].text.lower():
                        target_row = row
                        selected_product_name = cols[1].text
                        break

        if target_row:
            print(f"상품 '{selected_product_name}'을(를) 찾았습니다. 확인 버튼을 클릭합니다.")
            confirm_button = target_row.find_elements(By.TAG_NAME, 'td')[3].find_element(By.TAG_NAME, 'button')
            confirm_button.click()
            product_found = True

        if not product_found:
            print("검색 결과에서 일치하는 상품을 찾지 못했습니다.")
            return

        # 3. 팝업(모달) 창이 뜰 때까지 대기
        print("팝업(모달) 창이 열리기를 기다립니다...")
        modal = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, 'pop-period-down')))
        print("기간별 다운로드 팝업을 성공적으로 열었습니다.")
        time.sleep(2)

        # 4. 팝업 내에서 판매 기간에 맞는 버전 찾기
        modal_rows = modal.find_elements(By.CSS_SELECTOR, '#pop-periodDownList tr')
        print(f"팝업에서 {len(modal_rows)}개의 문서 버전을 찾았습니다. 최적 버전을 탐색합니다...")
        candidate_docs = []
        for row in modal_rows:
            period_text = row.find_elements(By.TAG_NAME, 'td')[0].text
            period_parts = [p.strip() for p in period_text.split('~')]
            if len(period_parts) == 2:
                start_date = extract_date_from_text(period_parts[0])
                end_date_str = period_parts[1]
                end_date = extract_date_from_text(end_date_str) if end_date_str else datetime(2999, 12, 31)
                if start_date and end_date:
                    candidate_docs.append({'start': start_date, 'end': end_date, 'element': row})

        best_doc_row = None
        valid_docs = [d for d in candidate_docs if d['start'] <= enrollment_date <= d['end']]
        if valid_docs:
            best_doc_row = max(valid_docs, key=lambda x: x['start'])['element']
            print(f"가입일 '{enrollment_date.strftime('%Y-%m-%d')}'이 포함되는 판매 기간을 찾았습니다.")
        else:
            before_docs = [d for d in candidate_docs if d['start'] <= enrollment_date]
            if before_docs:
                best_doc_row = max(before_docs, key=lambda x: x['start'])['element']
                print("가입일 포함 기간은 없지만, 가입일 이전 가장 최신 버전을 찾았습니다.")
            elif candidate_docs:
                best_doc_row = max(candidate_docs, key=lambda x: x['start'])['element']
                print("적합한 기간이 없어 가장 최신 버전을 선택합니다.")

        # 5. 선택된 버전의 파일 다운로드
        if best_doc_row:
            print("최적 문서 버전을 선택했습니다. 다운로드를 시작합니다.")
            period_text = best_doc_row.find_elements(By.TAG_NAME, 'td')[0].text
            doc_date = extract_date_from_text(period_text.split('~')[0])

            header_cols = modal.find_elements(By.CSS_SELECTOR, '#pop-periodColumn th')
            doc_types_in_modal = [col.text for col in header_cols]
            td_elements = best_doc_row.find_elements(By.TAG_NAME, 'td')

            for i in range(1, len(td_elements)):
                header_text = doc_types_in_modal[i]
                link_elements = td_elements[i].find_elements(By.CSS_SELECTOR, 'a.ico.file')
                if not link_elements:
                    continue
                link = link_elements[0]

                onclick_attr = link.get_attribute('onclick') or link.get_attribute('href')
                if onclick_attr:
                    match = re.search(r'fileDownload\("([^"]+)"\)', onclick_attr)
                    if match:
                        file_arg = match.group(1)
                        download_url = urljoin(driver.current_url, f"/file/ajax/download?fName=/dtc/pdf/mm/{file_arg}")
                        doc_type, target_folder = get_doc_type_and_folder(header_text, base_download_folder)
                        # 엑셀 상품명 대신 웹사이트에서 선택된 상품명으로 파일 이름 생성
                        base_filename = f"{selected_product_name}_{doc_type}"
                        download_file(download_url, target_folder, base_filename, doc_date)

        # 6. 팝업 닫기
        modal.find_element(By.CSS_SELECTOR, 'button.btn-pop-close').click()
        print("팝업을 닫았습니다.")

    except Exception as e:
        print(f"교보생명 처리 중 오류 발생: {e}")


def handle_samsung_fire(driver, product_name, enrollment_date, base_download_folder):
    """삼성화재 웹사이트에서 상품 정보를 검색하고 다운로드합니다."""

    search_terms = generate_search_terms(product_name)
    candidate_rows = []

    for term in search_terms:
        print(f"'{term}'(으)로 검색 시도 중...")
        try:
            search_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'searchBox')))
            search_input.clear()
            search_input.send_keys(term)
            search_button = driver.find_element(By.CSS_SELECTOR, 'div.input-wrap.search button.btn.ico-search')
            search_button.click()
            time.sleep(5)

            sections = driver.find_elements(By.CSS_SELECTOR, 'section.section')
            found_results = False
            for section in sections:
                try:
                    header = section.find_element(By.CSS_SELECTOR, 'h4.title-min').text
                    if '검색결과' not in header:
                        continue
                    rows = section.find_elements(By.CSS_SELECTOR, 'table.tbl-base tbody tr')
                    if rows:
                        found_results = True
                        for row in rows:
                            cols = row.find_elements(By.TAG_NAME, 'td')
                            if len(cols) >= 6:
                                row_product_name = cols[1].text
                                row_start_date_str = cols[2].text
                                if term.split('(')[0] in row_product_name:
                                    row_start_date = extract_date_from_text(row_start_date_str)
                                    if row_start_date:
                                        candidate_rows.append({
                                            'product_name': row_product_name,
                                            'start_date': row_start_date,
                                            'element': row
                                        })
                except Exception:
                    continue
            if found_results:
                print(f"'{term}'(으)로 검색 결과를 찾았습니다.")
                break
        except Exception as e:
            print(f"'{term}' 검색 중 오류: {e})")
            continue

    try:
        if not candidate_rows:
            print("최종 검색 결과에서 일치하는 상품을 찾지 못했습니다.")
            return

        print(f"총 {len(candidate_rows)}개의 후보 상품 버전을 찾았습니다. 최적 버전을 탐색합니다...")
        best_row_data = None
        # 1. 가입일 이전에 판매 시작한 버전들 필터링
        valid_candidates = [r for r in candidate_rows if r['start_date'] <= enrollment_date]

        if valid_candidates:
            # 2. 필터링된 버전 중 가장 최신(판매개시일이 가장 늦은) 버전을 선택
            best_row_data = max(valid_candidates, key=lambda x: x['start_date'])
            print(f"가입일 기준 적합 버전을 찾았습니다: {best_row_data['product_name']}")
            print(f"(판매개시일: {best_row_data['start_date'].strftime('%Y-%m-%d')})")
        else:
            # 3. 적합한 버전이 없으면, 모든 버전 중 가장 최신 버전을 선택 (대안)
            best_row_data = max(candidate_rows, key=lambda x: x['start_date'])
            print(f"가입일에 맞는 버전은 없지만, 가장 최신 버전을 선택합니다: {best_row_data['product_name']} (판매개시일: {best_row_data['start_date'].strftime('%Y-%m-%d')})")

        selected_product_name = best_row_data['product_name']

        if best_row_data:
            print("--- 상세 다운로드 정보 ---")
            print(f"선택된 상품명: {selected_product_name}")
            print(f"선택된 판매개시일: {best_row_data['start_date'].strftime('%Y-%m-%d')}")
            print("다운로드를 시작합니다.")
            doc_date = best_row_data['start_date']
            num_buttons = len(best_row_data['element'].find_elements(By.CSS_SELECTOR, 'button.download'))
            doc_types = ['사업방법서', '상품요약서', '보험약관']

            for i in range(num_buttons):
                if i >= len(doc_types):
                    break
                try:
                    # 매번 버튼을 클릭하기 전에 최신 상태의 row를 다시 찾음
                    all_rows_after_nav = WebDriverWait(driver, 10).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'table.tbl-base tbody tr'))
                    )
                    current_best_row = None
                    for r in all_rows_after_nav:
                        cols = r.find_elements(By.TAG_NAME, 'td')
                        if len(cols) >= 6:
                            is_correct_product = selected_product_name == cols[1].text
                            is_correct_date = best_row_data['start_date'] == extract_date_from_text(cols[2].text)
                            if is_correct_product and is_correct_date:
                                current_best_row = r
                                break

                    if not current_best_row:
                        print("페이지 이동 후 상품 행을 다시 찾지 못했습니다.")
                        break

                    print(f"'{doc_types[i]}' 다운로드를 위해 올바른 행(판매개시일: {best_row_data['start_date'].strftime('%Y-%m-%d')})을 다시 찾았습니다.")
                    button_to_click = current_best_row.find_elements(By.CSS_SELECTOR, 'button.download')[i]
                    doc_type_text = doc_types[i]
                    print(f"'{doc_type_text}' 다운로드 버튼({i + 1}번째) 클릭 시도...")

                    # StaleElementReferenceException 방지를 위해 JavaScript 클릭 사용
                    driver.execute_script("arguments[0].click();", button_to_click)
                    time.sleep(3)

                    # PDF 다운로드는 새 탭에서 열릴 수 있으므로 핸들 관리
                    if len(driver.window_handles) > 1:
                        driver.switch_to.window(driver.window_handles[1])
                        pdf_url = driver.current_url
                        if ".pdf" not in pdf_url.lower():
                            print("PDF URL로 이동하지 않았습니다. 다음으로 넘어갑니다.")
                            driver.close()
                            driver.switch_to.window(driver.window_handles[0])
                            continue

                        print(f"PDF URL 확인: {pdf_url}")
                        doc_type, target_folder = get_doc_type_and_folder(doc_type_text, base_download_folder)
                        # 엑셀 상품명 대신 웹사이트에서 선택된 상품명으로 파일 이름 생성
                        base_filename = f"{selected_product_name}_{doc_type}"
                        download_file(pdf_url, target_folder, base_filename, doc_date)

                        driver.close()
                        driver.switch_to.window(driver.window_handles[0])

                    else:  # 동일 탭에서 페이지가 이동된 경우
                        pdf_url = driver.current_url
                        if ".pdf" not in pdf_url.lower():
                            print("PDF URL로 이동하지 않았습니다. 다음으로 넘어갑니다.")
                            driver.back()
                            time.sleep(3)
                            continue

                        print(f"PDF URL 확인: {pdf_url}")
                        doc_type, target_folder = get_doc_type_and_folder(doc_type_text, base_download_folder)
                        base_filename = f"{selected_product_name}_{doc_type}"
                        download_file(pdf_url, target_folder, base_filename, doc_date)
                        print("검색 결과 페이지로 돌아갑니다...")
                        driver.back()

                    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'searchBox')))
                    time.sleep(2)

                except Exception as e:
                    print(f"'{doc_types[i] if i < len(doc_types) else '알 수 없는 문서'}' 다운로드 중 오류: {e}")
                    # 오류 발생 시 원래 검색 페이지로 이동하여 다음 작업 계속
                    driver.get(company_url_map['삼성화재해상보험주식회사'])
                    break
    except Exception as e:
        print(f"삼성화재 처리 중 오류 발생: {e}")


# 각 보험사 이름과 처리 함수를 매핑
scraper_map = {
    '교보생명보험(주)': handle_kyobo,
    '삼성화재해상보험주식회사': handle_samsung_fire
}


def main():
    """메인 실행 함수"""
    print(f"엑셀 파일 읽는 중: {excel_file_path}")
    try:
        # 5번째 행(index 4)을 헤더로 지정하여 엑셀 파일 읽기
        df = pd.read_excel(excel_file_path, sheet_name=sheet_name, header=4)
        total_rows = len(df)
        print(f"엑셀에서 총 {total_rows}개의 행을 성공적으로 읽었습니다.")
    except FileNotFoundError:
        print(f"오류: 엑셀 파일 '{excel_file_path}'을(를) 찾을 수 없습니다.")
        print("스크립트와 같은 폴더에 엑셀 파일을 두거나 정확한 경로를 입력해주세요.")
        return
    except KeyError as e:
        print(f"오류: 엑셀에 필요한 열이 없습니다. '{e}' 열이 파일에 있는지 확인하세요.")
        return
    except Exception as e:
        print(f"엑셀 파일 읽기 중 예상치 못한 오류 발생: {e}")
        return

    driver = None
    try:
        # Selenium WebDriver 설정 (Chrome 예시)
        options = webdriver.ChromeOptions()
        # options.add_argument('--headless')  # 백그라운드에서 실행하려면 주석 해제
        driver = webdriver.Chrome(options=options)
        driver.maximize_window()
        print("웹 드라이버를 시작했습니다.")

        for index, row in df.iterrows():
            # '보험사' 또는 '보험상품명' 열이 비어있으면(nan) 해당 행은 건너뜀
            if pd.isna(row[insurance_company_col]) or pd.isna(row[product_name_col]):
                continue

            print(f"\n[{index + 1}/{total_rows}] 번째 항목 처리 중...")
            company_name = str(row[insurance_company_col]).strip()
            product_name = str(row[product_name_col]).strip()

            # 가입일 열 읽기 (YYYYMMDD 형식 처리)
            try:
                date_val = row[insurance_date_col]
                if pd.isna(date_val):
                    raise ValueError("Date is empty")
                # YYYYMMDD 형식의 숫자를 datetime 객체로 변환
                enrollment_date = datetime.strptime(str(int(date_val)), '%Y%m%d')
            except (KeyError, TypeError, ValueError):
                print(f"경고: '{insurance_date_col}' 열을 찾을 수 없거나 날짜 형식이 잘못되었습니다. 오늘 날짜를 사용합니다.")
                enrollment_date = datetime.now()

            print(f"\n--- 처리 시작: {company_name} - {product_name} (가입일: {enrollment_date.strftime('%Y-%m-%d')}) ---")

            if company_name in company_url_map:
                target_url = company_url_map[company_name]
                print(f"'{company_name}' 웹사이트로 이동: {target_url}")
                driver.get(target_url)
                time.sleep(3)

                # 해당 보험사 처리 함수 호출
                if company_name in scraper_map:
                    # 회사 이름으로 기본 다운로드 폴더 생성 (특수문자 제거)
                    safe_company_name = "".join([c for c in company_name if c.isalnum()])
                    base_download_folder = os.path.join(DOWNLOAD_DIRECTORY, safe_company_name)
                    scraper_map[company_name](driver, product_name, enrollment_date, base_download_folder)
                else:
                    print(f"경고: '{company_name}'에 대한 처리 함수(스크레이퍼)가 정의되지 않았습니다.")

            else:
                print(f"경고: '{company_name}'에 해당하는 웹사이트 URL을 찾을 수 없습니다. company_url_map을 확인해주세요.")

            time.sleep(2)

    except Exception as e:
        print(f"자동화 작업 중 예상치 못한 오류가 발생했습니다: {e}")
    finally:
        if driver:
            driver.quit()
            print("\n브라우저를 닫았습니다.")
        print("\n모든 작업이 완료되었습니다.")


if __name__ == '__main__':
    main()
