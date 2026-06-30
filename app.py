"""
PSS Analytics — дашборд анализа рынка Kaspi.
Открывается как сайт. Фильтры, графики, кнопка "сводка для Клода".
"""
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="PSS Analytics", page_icon="📊", layout="wide")

# ─────────────────────────────────────────────
#  ЗАГРУЗКА ДАННЫХ (кэшируется — грузится один раз)
# ─────────────────────────────────────────────
@st.cache_data
def load_data():
    df = pd.read_csv("kaspi_all_data.csv")
    df["period"] = df["period"].astype(str)
    return df

df = load_data()

# ─────────────────────────────────────────────
#  ЗАГОЛОВОК
# ─────────────────────────────────────────────
st.title("📊 PSS Analytics — рынок Kaspi")
st.caption(f"Данные: {df['period'].min()} — {df['period'].max()} · "
           f"{len(df):,} строк · {df['category'].nunique()} категорий")

# ─────────────────────────────────────────────
#  ФИЛЬТРЫ (боковая панель)
# ─────────────────────────────────────────────
st.sidebar.header("Фильтры")

periods = sorted(df["period"].unique())
sel_periods = st.sidebar.select_slider(
    "Период", options=periods, value=(periods[0], periods[-1])
)

cats = ["Все"] + sorted(df["category"].unique())
sel_cat = st.sidebar.selectbox("Категория", cats)

brands = ["Все"] + (
    sorted(df[df["category"] == sel_cat]["brand"].unique())
    if sel_cat != "Все" else sorted(df["brand"].value_counts().head(50).index)
)
sel_brand = st.sidebar.selectbox("Бренд (топ-50)", brands)

# Применяем фильтры
mask = (df["period"] >= sel_periods[0]) & (df["period"] <= sel_periods[1])
if sel_cat != "Все":
    mask &= df["category"] == sel_cat
if sel_brand != "Все":
    mask &= df["brand"] == sel_brand
d = df[mask]

# ─────────────────────────────────────────────
#  КЛЮЧЕВЫЕ ЦИФРЫ
# ─────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("Оборот", f"{d['revenue'].sum()/1e9:.1f} млрд ₸")
c2.metric("Продажи", f"{d['sales_qty'].sum()/1e6:.2f} млн шт")
c3.metric("Категорий", d["category"].nunique())
c4.metric("Ср. цена", f"{d['price'].mean():,.0f} ₸")

st.divider()

# ─────────────────────────────────────────────
#  ГРАФИК 1 — ДИНАМИКА ПО МЕСЯЦАМ
# ─────────────────────────────────────────────
st.subheader("Динамика по месяцам")
monthly = d.groupby("period").agg(
    Выручка=("revenue", lambda x: round(x.sum()/1e9, 2)),
    Продажи=("sales_qty", "sum"),
).reset_index()
fig1 = px.line(monthly, x="period", y="Выручка", markers=True,
               labels={"period": "Месяц", "Выручка": "Выручка, млрд ₸"})
fig1.update_traces(line_color="#2a78d6")
st.plotly_chart(fig1, use_container_width=True)

# ─────────────────────────────────────────────
#  ГРАФИК 2 — ТОП КАТЕГОРИЙ И БРЕНДОВ
# ─────────────────────────────────────────────
col_a, col_b = st.columns(2)

with col_a:
    st.subheader("Топ-10 категорий")
    top_cat = (d.groupby("category")["revenue"].sum()/1e9).sort_values(ascending=False).head(10)
    fig2 = px.bar(x=top_cat.values, y=top_cat.index, orientation="h",
                  labels={"x": "Выручка, млрд ₸", "y": ""})
    fig2.update_traces(marker_color="#2a78d6")
    fig2.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig2, use_container_width=True)

with col_b:
    st.subheader("Топ-10 брендов")
    top_brand = (d.groupby("brand")["revenue"].sum()/1e9).sort_values(ascending=False).head(10)
    fig3 = px.bar(x=top_brand.values, y=top_brand.index, orientation="h",
                  labels={"x": "Выручка, млрд ₸", "y": ""})
    fig3.update_traces(marker_color="#1baf7a")
    fig3.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig3, use_container_width=True)

# ─────────────────────────────────────────────
#  ТАБЛИЦА ТОП ТОВАРОВ
# ─────────────────────────────────────────────
st.subheader("Топ-20 товаров")
top_prod = (d.groupby(["name", "brand", "category"])
            .agg(Выручка_млн=("revenue", lambda x: round(x.sum()/1e6, 1)),
                 Продажи=("sales_qty", "sum"),
                 Ср_цена=("price", lambda x: round(x.mean())))
            .sort_values("Выручка_млн", ascending=False).head(20).reset_index())
st.dataframe(top_prod, use_container_width=True)

# ─────────────────────────────────────────────
#  СВОДКА ДЛЯ КЛОДА
# ─────────────────────────────────────────────
st.divider()
st.subheader("🤖 Сводка для Клода")
st.caption("Жми кнопку — получишь компактный текст. Скопируй и вставь Клоду в чат для анализа.")

if st.button("Сгенерировать сводку"):
    total = d["revenue"].sum()/1e9
    brief = [f"СВОДКА PSS Analytics ({sel_periods[0]}–{sel_periods[1]})"]
    if sel_cat != "Все":
        brief.append(f"Категория: {sel_cat}")
    if sel_brand != "Все":
        brief.append(f"Бренд: {sel_brand}")
    brief.append(f"Оборот: {total:.1f} млрд ₸, продажи {d['sales_qty'].sum()/1e6:.2f} млн шт")
    brief.append("\nТОП-8 категорий (млрд ₸):")
    for cat, v in (d.groupby("category")["revenue"].sum()/1e9).sort_values(ascending=False).head(8).items():
        brief.append(f"  {cat}: {v:.1f}")
    brief.append("\nТОП-8 брендов (млрд ₸):")
    for br, v in (d.groupby("brand")["revenue"].sum()/1e9).sort_values(ascending=False).head(8).items():
        brief.append(f"  {br}: {v:.1f}")
    st.code("\n".join(brief), language="text")
