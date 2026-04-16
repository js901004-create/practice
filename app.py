import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest
import io
import warnings
warnings.filterwarnings("ignore")

# ────────────────────────────────────────────────
# 페이지 설정
# ────────────────────────────────────────────────
st.set_page_config(
    page_title="온라인 배송 AI 분석 툴",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ────────────────────────────────────────────────
# CSS 스타일
# ────────────────────────────────────────────────
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 12px;
        padding: 20px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 15px rgba(102,126,234,0.3);
    }
    .metric-card h2 { margin: 0; font-size: 2rem; }
    .metric-card p  { margin: 4px 0 0; opacity: 0.85; font-size: 0.9rem; }

    .insight-box {
        background: #f0f7ff;
        border-left: 4px solid #667eea;
        border-radius: 6px;
        padding: 14px 18px;
        margin: 8px 0;
        font-size: 0.95rem;
    }
    .danger-box {
        background: #fff5f5;
        border-left: 4px solid #e53e3e;
        border-radius: 6px;
        padding: 14px 18px;
        margin: 8px 0;
        font-size: 0.95rem;
    }
    .success-box {
        background: #f0fff4;
        border-left: 4px solid #38a169;
        border-radius: 6px;
        padding: 14px 18px;
        margin: 8px 0;
        font-size: 0.95rem;
    }
    section[data-testid="stSidebar"] { background: #1a1a2e; }
    section[data-testid="stSidebar"] * { color: #e0e0e0 !important; }
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stMultiselect label { color: #aaa !important; }
</style>
""", unsafe_allow_html=True)


# ────────────────────────────────────────────────
# 유틸 함수
# ────────────────────────────────────────────────
@st.cache_data
def load_excel(file_bytes: bytes, sheet_name=0) -> pd.DataFrame:
    return pd.read_excel(io.BytesIO(file_bytes), sheet_name=sheet_name)


def detect_columns(df: pd.DataFrame) -> dict:
    """컬럼명을 자동 감지해 역할 매핑."""
    col_map = {}
    lower = {c: c.lower() for c in df.columns}

    # 날짜/기간
    for c, l in lower.items():
        if any(k in l for k in ["날짜", "date", "기간", "period", "월", "month", "year", "연도"]):
            col_map.setdefault("date", c)

    # 브랜드
    for c, l in lower.items():
        if any(k in l for k in ["브랜드", "brand", "카테고리", "category", "상품군"]):
            col_map.setdefault("brand", c)

    # 매출
    for c, l in lower.items():
        if any(k in l for k in ["매출", "sales", "revenue", "금액"]):
            col_map.setdefault("sales", c)

    # 배송비
    for c, l in lower.items():
        if any(k in l for k in ["배송비", "delivery", "shipping", "물류비"]):
            col_map.setdefault("delivery_cost", c)

    # 주문건수
    for c, l in lower.items():
        if any(k in l for k in ["주문", "order", "건수", "count"]):
            col_map.setdefault("order_count", c)

    return col_map


def compute_kpi(df: pd.DataFrame, col: dict) -> pd.DataFrame:
    """핵심 KPI 파생 컬럼 계산."""
    if col.get("sales") and col.get("delivery_cost"):
        df["배송비율(%)"] = (df[col["delivery_cost"]] / df[col["sales"]].replace(0, np.nan) * 100).round(2)
    if col.get("delivery_cost") and col.get("order_count"):
        df["주문당배송비"] = (df[col["delivery_cost"]] / df[col["order_count"]].replace(0, np.nan)).round(0)
    if col.get("sales") and col.get("order_count"):
        df["객단가"] = (df[col["sales"]] / df[col["order_count"]].replace(0, np.nan)).round(0)
    return df


def fmt_won(val) -> str:
    if pd.isna(val):
        return "-"
    if abs(val) >= 1e8:
        return f"{val/1e8:.1f}억"
    if abs(val) >= 1e4:
        return f"{val/1e4:.0f}만"
    return f"{val:,.0f}"


# ────────────────────────────────────────────────
# 사이드바
# ────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🚚 배송 AI 분석")
    st.markdown("---")

    uploaded = st.file_uploader(
        "📂 엑셀 파일 업로드",
        type=["xlsx", "xls"],
        help="기간별 배송비·매출 데이터를 업로드하세요.",
    )

    if uploaded:
        raw_bytes = uploaded.read()
        xls = pd.ExcelFile(io.BytesIO(raw_bytes))
        sheet = st.selectbox("시트 선택", xls.sheet_names)
        df_raw = load_excel(raw_bytes, sheet_name=sheet)

        st.markdown("### 컬럼 역할 지정")
        all_cols = ["(없음)"] + list(df_raw.columns)

        col_date   = st.selectbox("📅 날짜/기간", all_cols)
        col_brand  = st.selectbox("🏷 브랜드/카테고리", all_cols)
        col_sales  = st.selectbox("💰 매출", all_cols)
        col_del    = st.selectbox("🚚 배송비", all_cols)
        col_order  = st.selectbox("📦 주문건수", all_cols)

        user_col = {
            "date":          None if col_date  == "(없음)" else col_date,
            "brand":         None if col_brand == "(없음)" else col_brand,
            "sales":         None if col_sales == "(없음)" else col_sales,
            "delivery_cost": None if col_del   == "(없음)" else col_del,
            "order_count":   None if col_order == "(없음)" else col_order,
        }

        st.markdown("---")
        st.caption("ⓒ 온라인 배송 AI 분석 툴")

# ────────────────────────────────────────────────
# 메인 화면 — 파일 미업로드
# ────────────────────────────────────────────────
if not uploaded:
    st.title("🚚 온라인 배송 데이터 AI 분석 툴")
    st.markdown("""
    > 배송비 구조를 데이터 기반으로 분석하여 **비효율 제거 및 매출/이익 개선**을 지원합니다.

    #### 사용법
    1. 왼쪽 사이드바에서 **엑셀 파일을 업로드**하세요.
    2. 시트와 컬럼 역할을 지정합니다.
    3. 자동으로 KPI 계산 · 이상 탐지 · 클러스터링 분석이 시작됩니다.

    #### 지원 분석
    | 분석 항목 | 설명 |
    |-----------|------|
    | 📊 KPI 요약 | 배송비율, 주문당 배송비, 객단가, 이익률 |
    | 📈 추이 분석 | 기간별 매출 vs 배송비 트렌드 |
    | 🔍 이상 탐지 | Isolation Forest 기반 배송비 이상 구간 탐지 |
    | 🔵 클러스터링 | K-Means 브랜드/상품군 군집화 |
    | ⚠️ 위험 브랜드 | 배송비율 상위 브랜드 자동 식별 |
    """)

    st.info("👈 사이드바에서 엑셀 파일을 업로드하세요.", icon="📂")
    st.stop()


# ────────────────────────────────────────────────
# 데이터 전처리
# ────────────────────────────────────────────────
col = user_col

# 자동 감지 보완
auto = detect_columns(df_raw)
for k, v in auto.items():
    if not col.get(k):
        col[k] = v

df = df_raw.copy()

# 날짜 파싱
if col.get("date"):
    try:
        df[col["date"]] = pd.to_datetime(df[col["date"]], errors="coerce")
    except Exception:
        pass

# 숫자형 변환
for k in ["sales", "delivery_cost", "order_count"]:
    c = col.get(k)
    if c:
        df[c] = pd.to_numeric(df[c].astype(str).str.replace(",", ""), errors="coerce")

# KPI 계산
df = compute_kpi(df, col)

# 필터 (날짜 범위)
if col.get("date") and pd.api.types.is_datetime64_any_dtype(df[col["date"]]):
    min_d = df[col["date"]].min()
    max_d = df[col["date"]].max()
    with st.sidebar:
        date_range = st.date_input("📅 기간 필터", value=(min_d, max_d))
    if len(date_range) == 2:
        df = df[(df[col["date"]] >= pd.Timestamp(date_range[0])) &
                (df[col["date"]] <= pd.Timestamp(date_range[1]))]

# 브랜드 필터
if col.get("brand"):
    brands_all = sorted(df[col["brand"]].dropna().unique().tolist())
    with st.sidebar:
        sel_brands = st.multiselect("🏷 브랜드 필터", brands_all, default=brands_all)
    df = df[df[col["brand"]].isin(sel_brands)]


# ────────────────────────────────────────────────
# 탭 구성
# ────────────────────────────────────────────────
st.title("🚚 온라인 배송 데이터 AI 분석 툴")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 KPI 요약",
    "📈 추이 분석",
    "🔍 이상 탐지",
    "🔵 클러스터링",
    "⚠️ 위험 브랜드",
])


# ──────────── TAB 1: KPI 요약 ────────────
with tab1:
    st.subheader("핵심 KPI 요약")

    c1, c2, c3, c4 = st.columns(4)

    total_sales = df[col["sales"]].sum() if col.get("sales") else None
    total_del   = df[col["delivery_cost"]].sum() if col.get("delivery_cost") else None
    total_ord   = df[col["order_count"]].sum() if col.get("order_count") else None
    del_ratio   = (total_del / total_sales * 100) if (total_sales and total_del) else None

    with c1:
        st.markdown(f"""<div class="metric-card">
            <h2>{fmt_won(total_sales)}</h2><p>총 매출</p></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="metric-card">
            <h2>{fmt_won(total_del)}</h2><p>총 배송비</p></div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="metric-card">
            <h2>{f'{del_ratio:.1f}%' if del_ratio else '-'}</h2><p>배송비율</p></div>""", unsafe_allow_html=True)
    with c4:
        avg_del_per_order = (total_del / total_ord) if (total_del and total_ord) else None
        st.markdown(f"""<div class="metric-card">
            <h2>{fmt_won(avg_del_per_order)}</h2><p>주문당 배송비</p></div>""", unsafe_allow_html=True)

    st.markdown("---")

    # 브랜드별 요약 테이블
    if col.get("brand"):
        st.subheader("브랜드별 KPI")
        agg = {c: "sum" for c in [col.get("sales"), col.get("delivery_cost"), col.get("order_count")] if c}
        brand_df = df.groupby(col["brand"]).agg(agg).reset_index()
        brand_df = compute_kpi(brand_df, col)

        show_cols = [col["brand"]]
        if col.get("sales"):          show_cols.append(col["sales"])
        if col.get("delivery_cost"):  show_cols.append(col["delivery_cost"])
        if col.get("order_count"):    show_cols.append(col["order_count"])
        if "배송비율(%)" in brand_df.columns: show_cols.append("배송비율(%)")
        if "객단가" in brand_df.columns:      show_cols.append("객단가")

        brand_df_show = brand_df[show_cols].sort_values(
            "배송비율(%)" if "배송비율(%)" in brand_df.columns else show_cols[1],
            ascending=False
        )
        st.dataframe(brand_df_show.style.format({
            col.get("sales", "_"): lambda x: f"{x:,.0f}" if pd.notna(x) else "-",
            col.get("delivery_cost", "_"): lambda x: f"{x:,.0f}" if pd.notna(x) else "-",
            "배송비율(%)": lambda x: f"{x:.1f}%" if pd.notna(x) else "-",
            "객단가": lambda x: f"{x:,.0f}" if pd.notna(x) else "-",
        }), use_container_width=True)
    else:
        st.info("브랜드/카테고리 컬럼을 지정하면 브랜드별 KPI 테이블이 표시됩니다.")

    # 원본 데이터
    with st.expander("📄 원본 데이터 보기"):
        st.dataframe(df, use_container_width=True)


# ──────────── TAB 2: 추이 분석 ────────────
with tab2:
    st.subheader("기간별 추이 분석")

    if not col.get("date"):
        st.warning("날짜/기간 컬럼을 지정해야 추이 분석이 가능합니다.")
    elif not (col.get("sales") or col.get("delivery_cost")):
        st.warning("매출 또는 배송비 컬럼을 지정해야 합니다.")
    else:
        date_c = col["date"]
        trend_df = df.copy()
        trend_df["_period"] = trend_df[date_c].dt.to_period("M").astype(str)

        agg_dict = {}
        if col.get("sales"):          agg_dict[col["sales"]]          = "sum"
        if col.get("delivery_cost"):  agg_dict[col["delivery_cost"]]  = "sum"
        if col.get("order_count"):    agg_dict[col["order_count"]]    = "sum"

        period_df = trend_df.groupby("_period").agg(agg_dict).reset_index()
        period_df = compute_kpi(period_df, col)
        period_df = period_df.sort_values("_period")

        # 매출 vs 배송비 듀얼 축
        if col.get("sales") and col.get("delivery_cost"):
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Bar(x=period_df["_period"], y=period_df[col["sales"]],
                                 name="매출", marker_color="#667eea", opacity=0.8), secondary_y=False)
            fig.add_trace(go.Scatter(x=period_df["_period"], y=period_df[col["delivery_cost"]],
                                     name="배송비", mode="lines+markers",
                                     line=dict(color="#e53e3e", width=2)), secondary_y=True)
            fig.update_layout(title="매출 vs 배송비 추이", height=420,
                              legend=dict(orientation="h", y=1.1))
            fig.update_yaxes(title_text="매출", secondary_y=False)
            fig.update_yaxes(title_text="배송비", secondary_y=True)
            st.plotly_chart(fig, use_container_width=True)

        # 배송비율 추이
        if "배송비율(%)" in period_df.columns:
            fig2 = px.area(period_df, x="_period", y="배송비율(%)",
                           title="배송비율(%) 추이", color_discrete_sequence=["#764ba2"])
            fig2.add_hline(y=period_df["배송비율(%)"].mean(),
                           line_dash="dash", line_color="red",
                           annotation_text=f"평균 {period_df['배송비율(%)'].mean():.1f}%")
            st.plotly_chart(fig2, use_container_width=True)

        # 객단가 추이
        if "객단가" in period_df.columns:
            fig3 = px.line(period_df, x="_period", y="객단가",
                           title="객단가 추이", markers=True,
                           color_discrete_sequence=["#38a169"])
            st.plotly_chart(fig3, use_container_width=True)

        # 브랜드별 기간 추이
        if col.get("brand") and col.get("delivery_cost"):
            st.subheader("브랜드별 배송비 추이")
            brand_trend = trend_df.groupby(["_period", col["brand"]])[col["delivery_cost"]].sum().reset_index()
            fig4 = px.line(brand_trend, x="_period", y=col["delivery_cost"],
                           color=col["brand"], markers=True,
                           title="브랜드별 배송비 추이")
            st.plotly_chart(fig4, use_container_width=True)


# ──────────── TAB 3: 이상 탐지 ────────────
with tab3:
    st.subheader("🔍 AI 이상 탐지 (Isolation Forest)")
    st.markdown("배송비율이나 주문당 배송비가 비정상적으로 높은 데이터를 자동으로 탐지합니다.")

    feat_cols = [c for c in ["배송비율(%)", "주문당배송비", "객단가"]
                 if c in df.columns and df[c].notna().sum() > 5]

    if not feat_cols:
        st.warning("이상 탐지에 사용할 KPI 컬럼이 부족합니다. (매출+배송비+주문건수 컬럼 지정 필요)")
    else:
        contamination = st.slider("이상치 비율 설정", 0.01, 0.3, 0.1, 0.01,
                                  help="전체 데이터 중 이상치로 간주할 비율")

        df_feat = df[feat_cols].dropna()
        if len(df_feat) < 10:
            st.warning("데이터가 너무 적습니다. (최소 10행 필요)")
        else:
            scaler = StandardScaler()
            X = scaler.fit_transform(df_feat)
            iso = IsolationForest(contamination=contamination, random_state=42)
            labels = iso.fit_predict(X)
            df_feat = df_feat.copy()
            df_feat["이상여부"] = ["🔴 이상" if l == -1 else "🟢 정상" for l in labels]

            # 원본 df에 결과 병합
            df_result = df.loc[df_feat.index].copy()
            df_result["이상여부"] = df_feat["이상여부"].values

            n_anomaly = (labels == -1).sum()
            st.markdown(f"""
            <div class="danger-box">
            ⚠️ 총 <b>{len(labels)}</b>건 중 <b>{n_anomaly}건</b>의 이상 데이터가 탐지되었습니다.
            </div>""", unsafe_allow_html=True)

            # 산점도 (첫 2개 피처)
            x_feat, y_feat = feat_cols[0], feat_cols[1] if len(feat_cols) > 1 else feat_cols[0]
            fig = px.scatter(df_result, x=x_feat, y=y_feat,
                             color="이상여부",
                             color_discrete_map={"🔴 이상": "#e53e3e", "🟢 정상": "#38a169"},
                             hover_data=[col.get("brand")] if col.get("brand") else None,
                             title=f"이상 탐지 결과 — {x_feat} vs {y_feat}")
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("이상 데이터 목록")
            anomaly_rows = df_result[df_result["이상여부"] == "🔴 이상"]
            show = [c for c in [col.get("date"), col.get("brand"), col.get("sales"),
                                 col.get("delivery_cost"), "배송비율(%)", "주문당배송비", "이상여부"]
                    if c and c in anomaly_rows.columns]
            st.dataframe(anomaly_rows[show], use_container_width=True)


# ──────────── TAB 4: 클러스터링 ────────────
with tab4:
    st.subheader("🔵 브랜드 클러스터링 (K-Means)")
    st.markdown("배송비율·객단가·주문당 배송비 기준으로 브랜드/상품군을 군집화합니다.")

    if not col.get("brand"):
        st.warning("브랜드/카테고리 컬럼을 지정해야 클러스터링이 가능합니다.")
    else:
        agg2 = {c: "sum" for c in [col.get("sales"), col.get("delivery_cost"), col.get("order_count")] if c}
        cl_df = df.groupby(col["brand"]).agg(agg2).reset_index()
        cl_df = compute_kpi(cl_df, col)

        cl_feat = [c for c in ["배송비율(%)", "주문당배송비", "객단가"] if c in cl_df.columns]

        if len(cl_df) < 3:
            st.warning("클러스터링을 위해 최소 3개 이상의 브랜드가 필요합니다.")
        elif not cl_feat:
            st.warning("KPI 컬럼이 부족합니다.")
        else:
            k = st.slider("클러스터 수 (K)", 2, min(8, len(cl_df)), min(3, len(cl_df)))
            cl_data = cl_df[cl_feat].fillna(0)
            sc = StandardScaler()
            X_cl = sc.fit_transform(cl_data)
            km = KMeans(n_clusters=k, random_state=42, n_init=10)
            cl_df["클러스터"] = km.fit_predict(X_cl).astype(str)

            x_c = cl_feat[0]
            y_c = cl_feat[1] if len(cl_feat) > 1 else cl_feat[0]
            sz_c = cl_feat[2] if len(cl_feat) > 2 else None

            fig = px.scatter(cl_df, x=x_c, y=y_c,
                             size=sz_c if sz_c else None,
                             color="클러스터",
                             text=col["brand"],
                             title=f"브랜드 클러스터링 — {x_c} vs {y_c}",
                             height=520)
            fig.update_traces(textposition="top center")
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("클러스터별 평균 KPI")
            cl_summary = cl_df.groupby("클러스터")[cl_feat].mean().round(2)
            st.dataframe(cl_summary, use_container_width=True)

            # 클러스터 인사이트
            st.subheader("클러스터 인사이트")
            for cid, row in cl_summary.iterrows():
                if "배송비율(%)" in row:
                    ratio = row["배송비율(%)"]
                    box_cls = "danger-box" if ratio > 20 else ("success-box" if ratio < 10 else "insight-box")
                    emoji = "⚠️" if ratio > 20 else ("✅" if ratio < 10 else "ℹ️")
                    st.markdown(
                        f'<div class="{box_cls}">{emoji} <b>클러스터 {cid}</b>: '
                        f'배송비율 <b>{ratio:.1f}%</b>'
                        + (f', 객단가 <b>{row["객단가"]:,.0f}원</b>' if "객단가" in row else "")
                        + "</div>",
                        unsafe_allow_html=True,
                    )


# ──────────── TAB 5: 위험 브랜드 ────────────
with tab5:
    st.subheader("⚠️ 위험 브랜드 / Action Items")

    if not col.get("brand"):
        st.warning("브랜드/카테고리 컬럼을 지정해야 위험 브랜드 분석이 가능합니다.")
    else:
        agg3 = {c: "sum" for c in [col.get("sales"), col.get("delivery_cost"), col.get("order_count")] if c}
        risk_df = df.groupby(col["brand"]).agg(agg3).reset_index()
        risk_df = compute_kpi(risk_df, col)

        threshold = st.slider("배송비율 위험 임계값 (%)", 5, 50, 20, 1)

        if "배송비율(%)" in risk_df.columns:
            danger = risk_df[risk_df["배송비율(%)"] >= threshold].sort_values("배송비율(%)", ascending=False)
            safe   = risk_df[risk_df["배송비율(%)"] <  threshold].sort_values("배송비율(%)", ascending=False)

            # 파이차트
            c1, c2 = st.columns(2)
            with c1:
                fig_pie = px.pie(
                    values=[len(danger), len(safe)],
                    names=["⚠️ 위험 브랜드", "✅ 정상 브랜드"],
                    color_discrete_sequence=["#e53e3e", "#38a169"],
                    title=f"브랜드 위험도 분포 (임계값 {threshold}%)",
                )
                st.plotly_chart(fig_pie, use_container_width=True)

            with c2:
                fig_bar = px.bar(
                    risk_df.sort_values("배송비율(%)", ascending=True).tail(15),
                    x="배송비율(%)", y=col["brand"], orientation="h",
                    color="배송비율(%)", color_continuous_scale="RdYlGn_r",
                    title="브랜드별 배송비율",
                )
                fig_bar.add_vline(x=threshold, line_dash="dash",
                                  line_color="red", annotation_text=f"임계값 {threshold}%")
                st.plotly_chart(fig_bar, use_container_width=True)

            # 위험 브랜드 테이블
            st.subheader(f"🔴 위험 브랜드 ({len(danger)}개)")
            if not danger.empty:
                show_cols = [col["brand"]] + [c for c in [col.get("sales"), col.get("delivery_cost"),
                             "배송비율(%)", "객단가", "주문당배송비"] if c and c in danger.columns]
                st.dataframe(danger[show_cols], use_container_width=True)

                # Action Items
                st.subheader("💡 AI 추천 Action Items")
                for _, row in danger.iterrows():
                    brand_name = row[col["brand"]]
                    ratio = row.get("배송비율(%)", 0)
                    avg_price = row.get("객단가", 0)

                    if avg_price and avg_price < 30000:
                        action = "최소주문금액 설정 — 건당 물류비 부담 완화"
                        priority = "🔴 즉시"
                    elif ratio > 30:
                        action = "묶음배송 프로모션 도입 — 배송 건수 감소 유도"
                        priority = "🟠 긴급"
                    else:
                        action = "프로모션 비용 효율화 및 배송 정책 재검토"
                        priority = "🟡 검토"

                    st.markdown(
                        f'<div class="danger-box">{priority} <b>{brand_name}</b> '
                        f'(배송비율 {ratio:.1f}%) → {action}</div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown('<div class="success-box">✅ 임계값 초과 브랜드가 없습니다.</div>',
                            unsafe_allow_html=True)

        else:
            st.warning("배송비율 계산을 위해 매출과 배송비 컬럼을 지정해주세요.")

    # 전략 요약
    st.markdown("---")
    st.subheader("📋 전략 로드맵")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown("""
        <div class="danger-box">
        <b>🔴 단기 (즉시)</b><br>
        • 저단가 브랜드 최소주문금액 설정<br>
        • 배송비 과다 브랜드 긴급 모니터링
        </div>""", unsafe_allow_html=True)
    with col_b:
        st.markdown("""
        <div class="insight-box">
        <b>🟡 중기 (1~3개월)</b><br>
        • 묶음배송 프로모션 운영<br>
        • KPI 대시보드 정례 리뷰 체계 구축
        </div>""", unsafe_allow_html=True)
    with col_c:
        st.markdown("""
        <div class="success-box">
        <b>🟢 장기 (3개월+)</b><br>
        • 고단가 브랜드 집중 육성<br>
        • 배송비 예측 모델 고도화
        </div>""", unsafe_allow_html=True)
