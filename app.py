# app.py
import streamlit as st
import pandas as pd

st.set_page_config(page_title="상품 승인 검수 앱", layout="wide")

st.title("📦 상품 승인 전 검수 자동화")

uploaded_file = st.file_uploader("엑셀 파일 업로드", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    st.subheader("원본 데이터")
    st.dataframe(df)

    # 컬럼명 가정 (필요 시 수정)
    # 상품코드, 품목고시, 인증정보, 가격

    def check_row(row):
        request_type = None
        remark = ""

        # 1. 품목고시 확인
        if "어린이" not in str(row.get("품목고시", "")):
            request_type = "재확인 요청"

        # 2. 인증 확인
        if pd.isna(row.get("인증정보")) or ("KC" not in str(row.get("인증정보"))):
            request_type = "인증 수단 재검토 요청"

        # 3. 가격 확인
        if row.get("가격", 0) < 10000:
            remark = "가격 확인 요청"

        return pd.Series([request_type, remark])

    df[["요청 유형", "비고"]] = df.apply(check_row, axis=1)

    result_df = df[df["요청 유형"].notnull()][["상품코드", "요청 유형", "비고"]]

    st.subheader("검수 결과")
    st.dataframe(result_df)

    # 다운로드
    csv = result_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="결과 다운로드",
        data=csv,
        file_name="검수결과.csv",
        mime="text/csv"
    )

else:
    st.info("엑셀 파일을 업로드해주세요")

