import streamlit as st
import pandas as pd

st.set_page_config(page_title="상품 승인 자동 검토", layout="wide")

st.title("📦 상품 승인 사전 검토 자동화")
st.write("엑셀 파일을 업로드하면 상품 검토 결과를 자동으로 생성합니다.")

# 파일 업로드
uploaded_file = st.file_uploader("엑셀 파일 업로드", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    st.subheader("📊 원본 데이터")
    st.dataframe(df)

    # 컬럼명 정의 (필요 시 수정)
    price_col = "가격"
    category_col = "품목고시"
    kc_col = "KC인증"
    cert_col = "안전인증번호"
    product_code_col = "상품코드"

    # 컬럼 존재 체크
    required_cols = [price_col, category_col, kc_col, cert_col]
    missing_cols = [col for col in required_cols if col not in df.columns]

    if missing_cols:
        st.error(f"다음 컬럼이 필요합니다: {missing_cols}")
    else:
        # 검토 컬럼 생성
        def check_price(price):
            try:
                if price < 10000:
                    return "가격 재검토 요청"
            except:
                return ""
            return ""

        def check_kc(kc, cert):
            if (pd.isna(kc) or kc == "") and (pd.isna(cert) or cert == ""):
                return "인증 수단 재검토 요청"
            return ""

        def check_category(category):
            if pd.notna(category) and "어린이" not in str(category):
                return "품목고시 재확인 요청"
            return ""

        df["가격검토"] = df[price_col].apply(check_price)
        df["인증검토"] = df.apply(lambda x: check_kc(x[kc_col], x[cert_col]), axis=1)
        df["품목고시검토"] = df[category_col].apply(check_category)

        # 최종 결과
        df["검토결과"] = df[["가격검토", "인증검토", "품목고시검토"]] \
            .apply(lambda x: " / ".join([i for i in x if i]), axis=1)

        # 승인 추천
        df["승인여부"] = df["검토결과"].apply(lambda x: "승인 가능" if x == "" else "검토 필요")

        st.subheader("✅ 검토 결과")
        st.dataframe(df)

        # 다운로드
        def convert_df(df):
            return df.to_excel(index=False)

        output_file = "검토결과.xlsx"
        df.to_excel(output_file, index=False)

        with open(output_file, "rb") as file:
            st.download_button(
                label="📥 결과 엑셀 다운로드",
                data=file,
                file_name=output_file,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
