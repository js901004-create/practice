import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# ── 페이지 설정 ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="롯데백화점몰 키즈 MD 분석",
    page_icon="🛍️",
    layout="wide",
)

# ── 데이터 ────────────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    brands = ["A브랜드", "B브랜드", "C브랜드", "D브랜드"]

    df = pd.DataFrame({
        "브랜드": brands,
        "매출_25": [50, 80, 40, 60],          # 단위: M
        "매출_26": [65, 88, 38, 90],
        "배송_25": [4000, 5500, 3800, 4200],
        "배송_26": [6500, 6000, 4200, 5000],
        "건단가_25": [12500, 14500, 10500, 14200],
        "건단가_26": [10000, 14600, 9000, 18000],
    })

    df["매출_신장률"] = ((df["매출_26"] - df["매출_25"]) / df["매출_25"] * 100).round(1)
    df["배송_신장률"] = ((df["배송_26"] - df["배송_25"]) / df["배송_25"] * 100).round(1)
    df["건단가_신장률"] = ((df["건단가_26"] - df["건단가_25"]) / df["건단가_25"] * 100).round(1)

    return df

df = load_data()

# ── 헤더 ──────────────────────────────────────────────────────────────────────
st.title("🛍️ 롯데백화점몰 키즈 상품군")
st.subheader("브랜드별 배송/매출 분석 보고서")
st.caption("기간: 2026년 1~3월 vs 2025년 1~3월 | 더미 데이터 기반")
st.divider()

# ── 브랜드 필터 ───────────────────────────────────────────────────────────────
selected = st.multiselect(
    "브랜드 선택",
    options=df["브랜드"].tolist(),
    default=df["브랜드"].tolist(),
)
dff = df[df["브랜드"].isin(selected)]

# ── KPI 카드 ──────────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
metrics = [
    ("총 매출 (26년)", f"{dff['매출_26'].sum()}M", f"{(dff['매출_26'].sum() - dff['매출_25'].sum()) / dff['매출_25'].sum() * 100:.1f}%"),
    ("총 배송건수 (26년)", f"{dff['배송_26'].sum():,}건", f"{(dff['배송_26'].sum() - dff['배송_25'].sum()) / dff['배송_25'].sum() * 100:.1f}%"),
    ("평균 건단가 (26년)", f"₩{int(dff['건단가_26'].mean()):,}", f"{(dff['건단가_26'].mean() - dff['건단가_25'].mean()) / dff['건단가_25'].mean() * 100:.1f}%"),
    ("브랜드 수", f"{len(dff)}개", None),
]
for col, (label, val, delta) in zip([col1, col2, col3, col4], metrics):
    with col:
        if delta:
            st.metric(label, val, delta)
        else:
            st.metric(label, val)

st.divider()

# ── 차트 행 1: 매출 & 배송건수 ────────────────────────────────────────────────
c1, c2 = st.columns(2)

with c1:
    st.markdown("#### 📊 브랜드별 매출 비교 (M)")
    fig_sales = go.Figure()
    fig_sales.add_bar(name="2025년", x=dff["브랜드"], y=dff["매출_25"],
                      marker_color="#A8C8E8", text=dff["매출_25"].astype(str)+"M",
                      textposition="outside")
    fig_sales.add_bar(name="2026년", x=dff["브랜드"], y=dff["매출_26"],
                      marker_color="#2E6DB4", text=dff["매출_26"].astype(str)+"M",
                      textposition="outside")
    fig_sales.update_layout(
        barmode="group", height=350,
        margin=dict(t=20, b=20),
        legend=dict(orientation="h", y=1.1),
        yaxis_title="매출 (M)",
    )
    st.plotly_chart(fig_sales, use_container_width=True)

with c2:
    st.markdown("#### 📦 브랜드별 배송건수 비교")
    fig_del = go.Figure()
    fig_del.add_bar(name="2025년", x=dff["브랜드"], y=dff["배송_25"],
                    marker_color="#F4C2A1",
                    text=dff["배송_25"].apply(lambda x: f"{x:,}"),
                    textposition="outside")
    fig_del.add_bar(name="2026년", x=dff["브랜드"], y=dff["배송_26"],
                    marker_color="#E07B39",
                    text=dff["배송_26"].apply(lambda x: f"{x:,}"),
                    textposition="outside")
    fig_del.update_layout(
        barmode="group", height=350,
        margin=dict(t=20, b=20),
        legend=dict(orientation="h", y=1.1),
        yaxis_title="배송건수 (건)",
    )
    st.plotly_chart(fig_del, use_container_width=True)

# ── 차트 행 2: 건단가 & 신장률 ────────────────────────────────────────────────
c3, c4 = st.columns(2)

with c3:
    st.markdown("#### 💰 브랜드별 건단가 비교 (₩)")
    fig_upv = go.Figure()
    fig_upv.add_bar(name="2025년", x=dff["브랜드"], y=dff["건단가_25"],
                    marker_color="#B8D8B8",
                    text=dff["건단가_25"].apply(lambda x: f"₩{x:,}"),
                    textposition="outside")
    fig_upv.add_bar(name="2026년", x=dff["브랜드"], y=dff["건단가_26"],
                    marker_color="#3A8A3A",
                    text=dff["건단가_26"].apply(lambda x: f"₩{x:,}"),
                    textposition="outside")
    fig_upv.update_layout(
        barmode="group", height=350,
        margin=dict(t=20, b=20),
        legend=dict(orientation="h", y=1.1),
        yaxis_title="건단가 (₩)",
    )
    st.plotly_chart(fig_upv, use_container_width=True)

with c4:
    st.markdown("#### 📈 신장률 비교 (%)")
    fig_growth = go.Figure()
    for col_key, label, color in [
        ("매출_신장률", "매출", "#2E6DB4"),
        ("배송_신장률", "배송건수", "#E07B39"),
        ("건단가_신장률", "건단가", "#3A8A3A"),
    ]:
        fig_growth.add_bar(
            name=label, x=dff["브랜드"], y=dff[col_key],
            marker_color=color,
            text=dff[col_key].apply(lambda x: f"{x:+.1f}%"),
            textposition="outside",
        )
    fig_growth.update_layout(
        barmode="group", height=350,
        margin=dict(t=20, b=20),
        legend=dict(orientation="h", y=1.1),
        yaxis_title="신장률 (%)",
        yaxis=dict(zeroline=True, zerolinewidth=2, zerolinecolor="gray"),
    )
    st.plotly_chart(fig_growth, use_container_width=True)

# ── 산점도: 매출 신장률 vs 배송 신장률 ────────────────────────────────────────
st.divider()
st.markdown("#### 🔍 매출 신장률 vs 배송 신장률 (수익성 포지셔닝)")
st.caption("우하단(매출↑ 배송↓): 수익성 최적 / 우상단(매출↑ 배송↑): 성장 주의 / 좌상단(매출↓ 배송↑): 위험")

fig_scatter = px.scatter(
    dff,
    x="배송_신장률",
    y="매출_신장률",
    size="건단가_26",
    color="브랜드",
    text="브랜드",
    size_max=60,
    color_discrete_sequence=px.colors.qualitative.Set2,
)
fig_scatter.add_hline(y=0, line_dash="dash", line_color="gray")
fig_scatter.add_vline(x=0, line_dash="dash", line_color="gray")
fig_scatter.update_traces(textposition="top center")
fig_scatter.update_layout(
    height=420,
    xaxis_title="배송건수 신장률 (%)",
    yaxis_title="매출 신장률 (%)",
    margin=dict(t=20, b=20),
)
st.plotly_chart(fig_scatter, use_container_width=True)

# ── 상세 데이터 테이블 ────────────────────────────────────────────────────────
st.divider()
st.markdown("#### 📋 브랜드별 상세 데이터")

display_df = dff[[
    "브랜드",
    "매출_25", "매출_26", "매출_신장률",
    "배송_25", "배송_26", "배송_신장률",
    "건단가_25", "건단가_26", "건단가_신장률",
]].copy()

display_df.columns = [
    "브랜드",
    "매출(25년)M", "매출(26년)M", "매출신장률%",
    "배송(25년)", "배송(26년)", "배송신장률%",
    "건단가(25년)₩", "건단가(26년)₩", "건단가신장률%",
]

def highlight_growth(val):
    if isinstance(val, float):
        color = "#d4edda" if val > 0 else "#f8d7da" if val < 0 else ""
        return f"background-color: {color}"
    return ""

styled = display_df.style.applymap(
    highlight_growth,
    subset=["매출신장률%", "배송신장률%", "건단가신장률%"]
).format({
    "매출신장률%": "{:+.1f}%",
    "배송신장률%": "{:+.1f}%",
    "건단가신장률%": "{:+.1f}%",
    "배송(25년)": "{:,}",
    "배송(26년)": "{:,}",
    "건단가(25년)₩": "₩{:,}",
    "건단가(26년)₩": "₩{:,}",
})

st.dataframe(styled, use_container_width=True, hide_index=True)

# ── 위협/기회 & Action Items ──────────────────────────────────────────────────
st.divider()
col_left, col_right = st.columns(2)

with col_left:
    st.markdown("#### ⚠️ 위협 vs 기회 요인")
    threat_opp = pd.DataFrame({
        "위협 요인": [
            "저가 브랜드 배송건수 과다 → 물류비 증가",
            "건단가 하락 브랜드 증가",
        ],
        "기회 요인": [
            "고단가 브랜드 성장 → 수익성 개선 가능",
            "묶음배송/최소주문금액 정책 도입 가능",
        ],
    })
    st.dataframe(threat_opp, use_container_width=True, hide_index=True)

with col_right:
    st.markdown("#### ✅ Action Items")
    with st.expander("1️⃣ 저단가 브랜드 최소주문금액 설정", expanded=True):
        st.write("**기대효과:** 배송건수 감소 및 물류비 절감")
        st.write("**필요자원:** 정책 설정, 시스템 개발")
    with st.expander("2️⃣ 묶음배송 프로모션 운영"):
        st.write("**기대효과:** 건단가 상승 및 고객 구매수량 증가")
        st.write("**필요자원:** 마케팅 기획, 프로모션 비용")
    with st.expander("3️⃣ 고단가 브랜드 집중 육성"):
        st.write("**기대효과:** 전체 마진율 상승")
        st.write("**필요자원:** 브랜드 협상, 광고비")

st.caption("© 롯데백화점몰 MD분석팀 | 더미 데이터 기반 시뮬레이션")
