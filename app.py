
import streamlit as st
import pandas as pd

st.set_page_config(page_title="상품 승인 검수 대시보드", layout="wide")

st.title("📦 상품 승인 검수 자동화")

uploaded_file = st.file_uploader("엑셀 파일 업로드", type=["xlsx"])

def check_conditions(df):
    results = []

    for _, row in df.iterrows():
        code = row.get("상품코드", "")
        notice = str(row.get("품목고시", ""))
        cert = str(row.get("안전인증유형", ""))
        price = row.get("가격", 0)

        request_type = None
        remark = ""

        # 조건 1: 품목고시
        if "어린이" not in notice:
            request_type = "재확인 요청"

        # 조건 2: 인증유형
        valid_cert = ["안전인증", "안전확인", "공급자적합성확인"]
        if not any(v in cert for v in valid_cert):
            request_type = "인증 수단 재검토 요청"

        # 조건 3: 가격
        if price < 10000:
            remark = "가격 확인 요청"

        if request_type:
            results.append({
                "상품코드": code,
                "요청유형": request_type,
                "비고": remark
            })

    return pd.DataFrame(results)


if uploaded_file:
    df = pd.read_excel(uploaded_file)

    st.subheader("📊 원본 데이터")
    st.dataframe(df)

    result_df = check_conditions(df)

    st.subheader("🚨 검수 필요 상품")
    st.dataframe(result_df)

    csv = result_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("📥 결과 다운로드", data=csv, file_name="검수결과.csv")
