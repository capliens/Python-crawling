from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 웹 드라이버 초기화 (예: Chrome)
driver = webdriver.Chrome()

# 웹 페이지 접속
driver.get("https://www.idbins.com/FWMAIV1534.do")

try:
    # 1단계: "자동차보험" 상품군 선택 (예시)
    driver.find_element(By.XPATH, "//span[text()='자동차보험']").click()

    # 2단계: "개인용" 상품 선택 (예시)
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//a[text()='개인용']"))
    ).click()

    # 3단계: 판매기간 선택 (가장 최근 판매기간 선택)
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located(
            (By.XPATH, "//div[@class='step s3']//a"))
    ).click()

    # 4단계: 선택항목 정보 추출
    product_name = driver.find_element(By.ID, "step4_name").text
    # pdf_link = driver.find_element(By.XPATH, "//ul[@class='btn_list']/li/a[@class='pdf']").get_attribute("href")
    pdf_link = driver.find_element(By.ID, "step4Btn3").get_attribute("onclick")
    # onclick 속성에서 PDF 파일명을 추출하는 정규식
    import re
    match = re.search(r"goPdf\('(.*?)','(.*?)'\)", pdf_link)
    if match:
        pdf_link = match.group(2)
        print(f"상품명: {product_name}, PDF 링크: {pdf_link}")

except Exception as e:
    print(f"오류 발생: {e}")

finally:
    # 웹 드라이버 종료
    driver.quit()
