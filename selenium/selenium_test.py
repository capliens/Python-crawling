# selenium의 webdriver를 사용하기 위한 import
from selenium import webdriver
# selenium에서 요소를 찾을 때 사용하는 검색 방법을 상수로 정의한 클래스
# from selenium.webdriver.common.by import By
# 페이지 로딩을 기다리는데에 사용할 time 모듈 import
import time

# 별도의 드라이버 설정 없이 바로 Chrome 실행
driver = webdriver.Chrome()
# 크롬 드라이버에 url 주소 넣고 실행
driver.get("https://www.google.com")
# 페이지가 완전히 로딩되도록 3초동안 기다림
time.sleep(3)

#  정보사이트 https://wikidocs.net/149358
