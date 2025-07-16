import yaml
import pandas as pd
from sqlalchemy import create_engine  # SQLite와 함께 사용하기 위해 필요합니다.
import argparse
import os


def generate_yaml_from_db(db_path, output_filename="products_by_company.yaml"):
    """
    SQLite3 데이터베이스에서 보험 상품 데이터를 조회하여 YAML 파일로 저장합니다.

    Args:
        db_path (str): SQLite3 데이터베이스 파일 경로.
        output_filename (str): 생성될 YAML 파일의 이름.
    """
    # SQLite3 DB 파일 존재 여부 확인
    if not os.path.exists(db_path):
        print(f"오류: 지정된 SQLite3 데이터베이스 파일이 존재하지 않습니다: {db_path}")
        return

    # SQLAlchemy를 위한 SQLite 연결 문자열 생성
    # 'sqlite:///' 뒤에 파일 경로를 붙여줍니다.
    db_connection_string = f'sqlite:///{db_path}'

    try:
        print(f"SQLite3 데이터베이스에 연결 중: {db_connection_string}")
        # SQLAlchemy 엔진 생성
        engine = create_engine(db_connection_string)

        # DB에서 데이터 조회 쿼리 (회사명, 상품명, 개수)
        # 이 쿼리는 회사별로 상품명과 해당 상품의 COUNT를 가져옵니다.
        # 'insurance_docs' 테이블에 'company_name'과 'product_name' 컬럼이 있어야 합니다.
        query = """
        SELECT company_name, product_name, COUNT(*) as cnt
        FROM insurance_docs
        GROUP BY company_name, product_name
        ORDER BY company_name, product_name;
        """

        print("데이터베이스에서 데이터를 조회하고 있습니다...")
        # pandas의 read_sql 함수를 사용하여 쿼리 실행
        df = pd.read_sql(query, engine)

        if df.empty:
            print("데이터베이스에서 조회된 데이터가 없습니다. YAML 파일이 생성되지 않습니다.")
            return

        print(f"총 {len(df)}개의 고유 상품 레코드를 조회했습니다.")

        # YAML 구조에 맞게 데이터 가공
        yaml_data = []
        for company_name, company_df in df.groupby('company_name'):
            products = []
            total_count = 0
            for _, row in company_df.iterrows():
                products.append({
                    "count": int(row['cnt']),  # int로 변환하여 YAML에 숫자로 저장되도록 합니다.
                    "name": row['product_name']
                })
                total_count += int(row['cnt'])

            yaml_data.append({
                "company_name": company_name,
                "products": products,
                "total": total_count
            })

        # YAML 파일로 저장
        with open(output_filename, 'w', encoding='utf-8') as file:
            yaml.dump(yaml_data, file, allow_unicode=True, indent=2, sort_keys=False)

        print(f"성공적으로 '{output_filename}' 파일이 생성되었습니다!")

    except Exception as e:
        print(f"오류가 발생했습니다: {e}")
        print("데이터베이스 경로, 테이블 이름 또는 컬럼 이름을 확인해주세요.")


# --- 사용 예시 (터미널에서 인자 받기) ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SQLite3 DB에서 보험 상품 정보를 가져와 YAML 파일을 생성합니다.")
    parser.add_argument("--db_path", required=True,
                        help="SQLite3 데이터베이스 파일 경로 (예: 'my_insurance.db')")
    parser.add_argument("--output_file", default="insurance_products.yaml",
                        help="생성될 YAML 파일의 이름 (기본값: insurance_products.yaml)")

    args = parser.parse_args()

    # 함수 호출
    generate_yaml_from_db(args.db_path, args.output_file)
