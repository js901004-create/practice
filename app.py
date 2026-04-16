import streamlit as st
import pandas as pd

st.set_page_config(page_title="키즈 상품 분석 대시보드", layout="wide")

st.title("📊 키즈 브랜드 매출/배송 분석")

# 데이터 생성 (보고서 기반)
data = {
    "브랜드": ["A브랜드", "B브랜드", "C브랜드", "D브랜드"],
    "매출_2025": [50, 80, 40, 60],
    "매출_2026": [65, 88, 38, 90],
    "배송건수_2025": [4000, 5500, 3800, 4200],
    "배송건수_2026": [6500, 6000, 4200, 5000],
    "건단가_2025": [12500, 14500, 10500, 14200],
    "건단가_2026": [10000, 14600, 9000, 18000],
}

df = pd.DataFrame(data)

# KPI 계산
df["매출증가율(%)"] = (df["매출_2026"] - df["매출_2025"]) / df["매출_2025"] * 100
df["배송증가율(%)"] = (df["배송건수_2026"] - df["배송건수_2025"]) / df["배송건수_2025"] * 100
df["건단가증가율(%)"] = (df["건단가_2026"] - df["건단가_2025"]) / df["건단가_2025"] * 100

# 데이터 테이블
st.subheader("📌 브랜드별 데이터")
st.dataframe(df, use_container_width=True)

# 차트
col1, col2 = st.columns(2)

with col1:
    st.subheader("💰 매출 비교")
    st.bar_chart(df.set_index("브랜드")[["매출_2025", "매출_2026"]])

with col2:
    st.subheader("🚚 배송건수 비교")
    st.bar_chart(df.set_index("브랜드")[["배송건수_2025", "배송건수_2026"]])

# 인사이트
st.subheader("🔍 핵심 인사이트")

for _, row in df.iterrows():
    if row["배송증가율(%)"] > row["매출증가율(%)"]:
        st.warning(f"{row['브랜드']}: 배송 증가가 더 빠름 → 수익성 악화 가능")
    elif row["건단가증가율(%)"] > 0:
        st.success(f"{row['브랜드']}: 건단가 상승 → 수익성 개선")

# 액션 아이템
st.subheader("🚀 추천 액션")

st.markdown("""
- 최소 주문 금액 설정 → 배송건수 감소
- 묶음 배송 프로모션 → 객단가 상승
- 고단가 브랜드 집중 육성 → 마진 개선
""")
