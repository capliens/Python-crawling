# https://www.heungkukfire.co.kr/FRW/announce/insGoodsGongsiSale.do
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import json  # For pretty printing the list of dictionaries
from urllib.parse import urljoin  # To construct absolute URLs

# 판매중지/db/상품군/pdf


def get_product_info_from_page(driver):
    current_page_url = driver.current_url
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    products = []

    product_table_container = soup.select_one('div.tbl_chk_tb')
    if not product_table_container:
        print("Product table container (div.tbl_chk_tb) not found on the current page.")
        return products

    table_body = product_table_container.find('tbody')
    if not table_body:
        table_in_container = product_table_container.find('table')
        if not table_in_container:
            print("Table element not found within div.tbl_chk_tb.")
            return products
        rows = table_in_container.find_all('tr')
        rows_to_parse = rows[1:] if rows and len(rows[0].find_all('th')) > 0 else rows
    else:
        rows_to_parse = table_body.find_all('tr')

    if not rows_to_parse:
        print("No product rows found in the table.")
        return products

    for row in rows_to_parse:
        cols = row.find_all('td')
        if len(cols) >= 5:
            product_name = cols[2].text.strip()
            sale_date = cols[3].text.strip()
            links_cell = cols[4]
            links_tags = links_cell.find_all('a')

            terms_link = None
            business_method_link = None
            summary_link = None

            for link_tag in links_tags:
                link_text = link_tag.text.strip()
                href = link_tag.get('href', '')
                absolute_href = urljoin(current_page_url, href) if href else None

                if '약관' in link_text or '상품약관' in link_text:
                    terms_link = absolute_href
                elif '사업방법서' in link_text:
                    business_method_link = absolute_href
                elif '상품요약서' in link_text:
                    summary_link = absolute_href

            if not terms_link and len(links_tags) > 0:
                terms_link = urljoin(current_page_url, links_tags[0].get(
                    'href', '')) if links_tags[0].get('href') else None
            if not business_method_link and len(links_tags) > 1:
                business_method_link = urljoin(current_page_url, links_tags[1].get(
                    'href', '')) if links_tags[1].get('href') else None
            if not summary_link and len(links_tags) > 2:
                summary_link = urljoin(current_page_url, links_tags[2].get(
                    'href', '')) if links_tags[2].get('href') else None

            products.append({
                "product_name": product_name,
                "sale_date": sale_date,
                "terms_link": terms_link,
                "business_method_link": business_method_link,
                "summary_link": summary_link
            })
    return products


def get_current_page_number(driver, pagination_area):
    active_page_element = None
    try:
        active_page_element = pagination_area.find_element(By.CSS_SELECTOR, "a.on")
    except NoSuchElementException:
        try:
            active_page_element = pagination_area.find_element(By.CSS_SELECTOR, "a[title='현재페이지']")
        except NoSuchElementException:
            print("Could not find active page element for page number.")
            return -1

    active_page_text = active_page_element.text.strip()
    if not active_page_text.isdigit():
        try:
            span_in_active = active_page_element.find_element(By.TAG_NAME, "span")
            active_page_text = span_in_active.text.strip()
        except NoSuchElementException:
            html_snippet = active_page_element.get_attribute('outerHTML')
            log_message = (
                f"Active page text '{active_page_text}' is not a digit and no span found. "
                f"HTML: {html_snippet}"
            )
            print(log_message)
            return -1

    if not active_page_text.isdigit():
        print(f"Could not determine current page number from text: '{active_page_text}'.")
        return -1
    return int(active_page_text)


def main():
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)
    driver.set_page_load_timeout(30)

    url = "https://www.heungkukfire.co.kr/FRW/announce/insGoodsGongsiSale.do"
    try:
        driver.get(url)
    except TimeoutException:
        print(f"Timeout loading page: {url}")
        driver.quit()
        return

    all_products = []
    page_count = 0
    previous_page_num = 0  # 0으로 시작하여 첫 페이지(보통 1)와 다르게 설정

    while True:
        page_count += 1
        print(f"Processing page iteration {page_count}...")  # 단순 반복 횟수

        # 현재 페이지 번호 가져오기 및 변경 여부 확인
        try:
            pagination_area_check = driver.find_element(By.CSS_SELECTOR, "div.paginate")
            current_page_num = get_current_page_number(driver, pagination_area_check)
        except NoSuchElementException:
            # 첫 페이지거나 페이지네이션이 없는 경우 (또는 마지막 페이지 이후)
            if page_count == 1:  # 첫 번째 시도에서 페이지네이션 없으면 단일 페이지로 간주
                print("Pagination not found on initial load, assuming single page or already scraped.")
                # 이 경우, 첫 페이지 스크래핑은 아래에서 수행됨
            else:  # 이전 루프에서 페이지 이동 후 페이지네이션이 사라졌다면, 마지막 페이지였을 가능성
                print("Pagination not found after page navigation attempt. Likely end of pages.")
                break
            current_page_num = 1  # 페이지네이션 없으면 현재를 1페이지로 간주 (스크래핑을 위해)

        if current_page_num == -1:
            print("Failed to get current page number. Ending pagination.")
            break

        print(f"Current active page number determined: {current_page_num}")

        if previous_page_num == current_page_num and page_count > 1 :  # 첫 루프가 아니고, 페이지 번호가 같다면
            log_message = (
                f"Page number {current_page_num} did not change from previous {previous_page_num}. "
                "Ending pagination to prevent duplicate scraping."
            )
            print(log_message)
            break

        # 테이블 로드 대기
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.tbl_chk_tb table"))
            )
        except TimeoutException:
            print(f"Timeout waiting for product table on page {current_page_num}.")
            break
        except Exception as e:
            print(f"Error waiting for table on page {current_page_num}: {e}")
            break

        # 현재 페이지 내용 스크래핑 (previous_page_num이 현재와 다를 때만)
        if previous_page_num != current_page_num or page_count == 1:  # 첫 페이지거나 페이지가 변경된 경우에만 스크랩
            print(f"Scraping content from page number {current_page_num} (Iteration: {page_count})")
            page_products = get_product_info_from_page(driver)
            if page_products:
                all_products.extend(page_products)
            else:
                print(f"No products found on page number {current_page_num}.")

        previous_page_num = current_page_num  # 현재 페이지를 이전 페이지로 기록

        # 다음 페이지로 이동 시도
        try:
            pagination_area_nav = driver.find_element(By.CSS_SELECTOR, "div.paginate")
            # "다음" 그룹 버튼 우선 시도
            try:
                next_page_button = pagination_area_nav.find_element(By.CSS_SELECTOR, "a.go_next")
                if next_page_button.is_displayed() and next_page_button.is_enabled():
                    print("Found 'a.go_next' button. Clicking...")
                    driver.execute_script("arguments[0].click();", next_page_button)
                    time.sleep(3)
                    continue
                else:
                    print("'a.go_next' button is not clickable or not displayed. Checking for individual page numbers.")
            except NoSuchElementException:
                print("'a.go_next' button not found. Checking for individual page numbers.")

            # 개별 다음 페이지 번호 링크 시도
            try:
                btn_wrap = pagination_area_nav.find_element(By.CSS_SELECTOR, "div.btn_wrap")
                page_links = btn_wrap.find_elements(By.TAG_NAME, "a")
                found_next_page_link = False
                for link in page_links:
                    page_num_text = link.text.strip()
                    if not page_num_text.isdigit():
                        try:
                            span_in_link = link.find_element(By.TAG_NAME, "span")
                            page_num_text = span_in_link.text.strip()
                        except NoSuchElementException:
                            pass

                    if page_num_text.isdigit():
                        page_num = int(page_num_text)
                        if page_num == current_page_num + 1:
                            print(f"Found next page link for page {page_num}. Clicking...")
                            driver.execute_script("arguments[0].click();", link)
                            time.sleep(3)
                            found_next_page_link = True
                            break
                if found_next_page_link:
                    continue
                else:
                    log_message = (
                        f"No direct link found for page {current_page_num + 1}. "
                        "Ending pagination as no further navigation method found."
                    )
                    print(log_message)
                    break
            except NoSuchElementException:
                print("'div.btn_wrap' not found. Ending pagination as no further navigation method found.")
                break

        except NoSuchElementException:
            print("Pagination area (div.paginate) not found for navigation. Assuming end of pages.")
            break
        except Exception as e:
            print(f"Error in pagination navigation logic: {e}. Ending pagination.")
            break

    driver.quit()

    if all_products:
        print(f"Successfully scraped {len(all_products)} products from all pages.")
        print(json.dumps(all_products, indent=4, ensure_ascii=False))
    else:
        print("No product data found or an error occurred during scraping.")


if __name__ == "__main__":
    main()
