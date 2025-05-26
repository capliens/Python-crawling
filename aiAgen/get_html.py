import requests

url = "https://www.idbins.com/FWMAIV1534.do"

try:
    response = requests.get(url)
    response.raise_for_status()  # HTTPError 발생 시 예외 처리

    html_source = response.text

    # 파일로 저장
    with open("idbins_html.txt", "w", encoding="utf-8") as f:
        f.write(html_source)

    print("HTML 소스가 idbins_html.txt 파일로 저장되었습니다.")

except requests.exceptions.RequestException as e:
    print(f"오류 발생: {e}")
