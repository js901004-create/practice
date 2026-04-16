import io
from typing import Optional

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

st.set_page_config(page_title="배송 데이터 AI 분석", layout="wide")


@st.cache_data(show_spinner=False)
def load_table(uploaded_file) -> pd.DataFrame:
    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        return pd.read_csv(uploaded_file)
    return pd.read_excel(uploaded_file)


def normalize_tracking_number(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip()
    s = s.replace({"": pd.NA, "nan": pd.NA, "None": pd.NA, "none": pd.NA})
    s = s.str.replace(r"\.0$", "", regex=True)
    return s


def normalize_text(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip()


def find_numeric_candidate(df: pd.DataFrame, preferred_keywords: list[str]) -> Optional[str]:
    candidates = []
    for col in df.columns:
        col_l = str(col).lower()
        if any(k in col_l for k in preferred_keywords):
            candidates.append(col)
    if candidates:
        return candidates[0]
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    return numeric_cols[0] if numeric_cols else None


def prep_shipping_df(df: pd.DataFrame, year_label: str, brand_col: str, tracking_col: str) -> pd.DataFrame:
    work = df.copy()
    work[brand_col] = normalize_text(work[brand_col])
    work[tracking_col] = normalize_tracking_number(work[tracking_col])
    work = work.dropna(subset=[brand_col, tracking_col])
    work = work.drop_duplicates(subset=[brand_col, tracking_col])
    out = (
        work.groupby(brand_col, dropna=False)
        .agg(배송건수=(tracking_col, "nunique"))
        .reset_index()
        .rename(columns={brand_col: "브랜드"})
    )
    out["연도"] = year_label
    return out


def prep_sales_df(df: pd.DataFrame, brand_col: str, sales_col: str) -> pd.DataFrame:
    work = df.copy()
    work[brand_col] = normalize_text(work[brand_col])
    work[sales_col] = pd.to_numeric(work[sales_col], errors="coerce")
    work = work.dropna(subset=[brand_col])
    out = (
        work.groupby(brand_col, dropna=False)
        .agg(매출=(sales_col, "sum"))
        .reset_index()
        .rename(columns={brand_col: "브랜드"})
    )
    return out


def build_summary(curr_ship: pd.DataFrame, prev_ship: pd.DataFrame, sales: pd.DataFrame) -> pd.DataFrame:
    merged = pd.merge(curr_ship[["브랜드", "배송건수"]], prev_ship[["브랜드", "배송건수"]], on="브랜드", how="outer", suffixes=("_금년", "_전년"))
    merged = pd.merge(merged, sales, on="브랜드", how="left")
    merged[["배송건수_금년", "배송건수_전년", "매출"]] = merged[["배송건수_금년", "배송건수_전년", "매출"]].fillna(0)
    merged["배송건수 증감"] = merged["배송건수_금년"] - merged["배송건수_전년"]
    merged["배송건수 증감률(%)"] = merged.apply(
        lambda r: ((r["배송건수_금년"] - r["배송건수_전년"]) / r["배송건수_전년"] * 100) if r["배송건수_전년"] > 0 else pd.NA,
        axis=1,
    )
    merged["매출대비 배송건수"] = merged.apply(
        lambda r: (r["배송건수_금년"] / r["매출"]) if r["매출"] > 0 else pd.NA,
        axis=1,
    )
    merged["위험도 점수"] = (
        merged["배송건수_금년"].fillna(0) * 0.5
        + merged["배송건수 증감"].clip(lower=0).fillna(0) * 0.3
        + merged["매출대비 배송건수"].fillna(0) * 1000 * 0.2
    )
    merged = merged.sort_values(["위험도 점수", "배송건수_금년"], ascending=[False, False]).reset_index(drop=True)
    return merged


def download_excel(df: pd.DataFrame) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="analysis")
    return output.getvalue()


def single_bar_chart(df: pd.DataFrame, x_col: str, y_col: str, title: str):
    fig, ax = plt.subplots(figsize=(10, 4))
    top = df.head(10)
    ax.bar(top[x_col].astype(str), top[y_col])
    ax.set_title(title)
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    return fig


st.title("온라인 배송 데이터 AI 분석 앱")
st.caption("브랜드 내 동일 운송장번호는 1건으로 중복 제거하여 분석합니다.")

with st.sidebar:
    st.header("1) 파일 업로드")
    current_file = st.file_uploader("금년 배송데이터 업로드", type=["xlsx", "xls", "csv"], key="current")
    previous_file = st.file_uploader("전년 배송데이터 업로드", type=["xlsx", "xls", "csv"], key="previous")
    sales_file = st.file_uploader("매출분석자료 업로드", type=["xlsx", "xls", "csv"], key="sales")

if not (current_file and previous_file and sales_file):
    st.info("왼쪽 사이드바에 금년 배송데이터, 전년 배송데이터, 매출분석자료 3개를 업로드해 주세요.")
    st.stop()

try:
    current_df = load_table(current_file)
    previous_df = load_table(previous_file)
    sales_df = load_table(sales_file)
except Exception as e:
    st.error(f"파일을 읽는 중 오류가 발생했습니다: {e}")
    st.stop()

st.subheader("업로드 데이터 미리보기")
col_a, col_b, col_c = st.columns(3)
with col_a:
    st.write("금년 배송데이터")
    st.dataframe(current_df.head(), use_container_width=True)
with col_b:
    st.write("전년 배송데이터")
    st.dataframe(previous_df.head(), use_container_width=True)
with col_c:
    st.write("매출분석자료")
    st.dataframe(sales_df.head(), use_container_width=True)

st.subheader("컬럼 매핑")
map1, map2, map3 = st.columns(3)
with map1:
    curr_brand_col = st.selectbox("금년 배송 - 브랜드 컬럼", current_df.columns.tolist(), index=0)
    curr_tracking_default = current_df.columns.get_loc("운송장번호") if "운송장번호" in current_df.columns else 0
    curr_tracking_col = st.selectbox("금년 배송 - 운송장번호 컬럼", current_df.columns.tolist(), index=curr_tracking_default)
with map2:
    prev_brand_col = st.selectbox("전년 배송 - 브랜드 컬럼", previous_df.columns.tolist(), index=0)
    prev_tracking_default = previous_df.columns.get_loc("운송장번호") if "운송장번호" in previous_df.columns else 0
    prev_tracking_col = st.selectbox("전년 배송 - 운송장번호 컬럼", previous_df.columns.tolist(), index=prev_tracking_default)
with map3:
    sales_brand_col = st.selectbox("매출 자료 - 브랜드 컬럼", sales_df.columns.tolist(), index=0)
    sales_guess = find_numeric_candidate(sales_df, ["매출", "sales", "amount", "revenue"])
    sales_default = sales_df.columns.get_loc(sales_guess) if sales_guess in sales_df.columns else 0
    sales_amount_col = st.selectbox("매출 자료 - 매출 금액 컬럼", sales_df.columns.tolist(), index=sales_default)

analyze = st.button("분석 실행", type="primary")

if analyze:
    curr_ship = prep_shipping_df(current_df, "금년", curr_brand_col, curr_tracking_col)
    prev_ship = prep_shipping_df(previous_df, "전년", prev_brand_col, prev_tracking_col)
    sales_prep = prep_sales_df(sales_df, sales_brand_col, sales_amount_col)
    summary = build_summary(curr_ship, prev_ship, sales_prep)

    total_curr = int(summary["배송건수_금년"].sum())
    total_prev = int(summary["배송건수_전년"].sum())
    total_sales = float(summary["매출"].sum())
    growth = ((total_curr - total_prev) / total_prev * 100) if total_prev > 0 else None

    st.subheader("핵심 요약")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("금년 배송건수", f"{total_curr:,}")
    m2.metric("전년 배송건수", f"{total_prev:,}")
    m3.metric("배송건수 증감률", "-" if growth is None else f"{growth:.1f}%")
    m4.metric("총 매출", f"{int(total_sales):,}")

    st.subheader("브랜드별 분석 결과")
    st.dataframe(summary, use_container_width=True)

    excel_bytes = download_excel(summary)
    st.download_button(
        "분석 결과 다운로드 (Excel)",
        data=excel_bytes,
        file_name="delivery_brand_analysis.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    left, right = st.columns(2)
    with left:
        st.pyplot(single_bar_chart(summary, "브랜드", "배송건수_금년", "금년 브랜드별 배송건수 TOP10"))
    with right:
        metric_df = summary.dropna(subset=["매출대비 배송건수"]).sort_values("매출대비 배송건수", ascending=False)
        st.pyplot(single_bar_chart(metric_df, "브랜드", "매출대비 배송건수", "매출대비 배송건수 TOP10"))

    st.subheader("핵심 인사이트")
    risk_top = summary.head(5)
    for _, row in risk_top.iterrows():
        change_rate = row["배송건수 증감률(%)"]
        rate_text = "신규/비교불가" if pd.isna(change_rate) else f"{change_rate:.1f}%"
        sales_ratio = row["매출대비 배송건수"]
        ratio_text = "N/A" if pd.isna(sales_ratio) else f"{sales_ratio:.4f}"
        st.write(
            f"- {row['브랜드']}: 금년 배송건수 {int(row['배송건수_금년']):,}건, 전년 대비 {rate_text}, 매출대비 배송건수 {ratio_text}"
        )

    st.subheader("분석 기준")
    st.markdown(
        """
- 브랜드 내 동일 운송장번호는 1건으로 계산
- 금년/전년 배송데이터는 브랜드별 고유 운송장번호 수로 집계
- 매출분석자료는 브랜드 기준으로 합산 후 배송건수와 결합
- 위험도 점수는 배송건수, 전년 대비 증가폭, 매출대비 배송건수를 결합한 내부 지표
        """
    )
