"""
PSS Analytics — дашборд анализа рынка Kaspi.
Фильтры: период, мультивыбор категорий и брендов. Кнопка "сводка для Клода".
"""
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="PSS Analytics", page_icon="📊", layout="wide")


# ─────────────────────────────────────────────
#  ФОРМАТИРОВАНИЕ ЧИСЕЛ
# ─────────────────────────────────────────────
def fmt_money(v):
    # Всегда в миллионах для единообразия (с пробелами-разделителями)
    if v >= 1e6:
        mln = v / 1e6
        # целая часть с пробелами + 1 знак после запятой
        whole = int(mln)
        frac = int(round((mln - whole) * 10))
        return f"{whole:,}".replace(",", " ") + f",{frac} млн ₸"
    if v >= 1e3:
        return f"{v/1e3:.0f} тыс ₸"
    return f"{v:.0f} ₸"


def fmt_num(v):
    return f"{int(round(v)):,}".replace(",", " ")


def fmt_qty(v):
    if v >= 1e6:
        return f"{v/1e6:.2f} млн шт".replace(".", ",")
    if v >= 1e3:
        return f"{v/1e3:.1f} тыс шт".replace(".", ",")
    return f"{int(v)} шт"


# ─────────────────────────────────────────────
#  ЗАГРУЗКА ДАННЫХ
# ─────────────────────────────────────────────
@st.cache_data
def load_data():
    df = pd.read_csv("kaspi_all_data.csv")
    df["period"] = df["period"].astype(str)
    return df

df = load_data()

# ─────────────────────────────────────────────
#  ПРОВЕРКА ПАРОЛЯ
# ─────────────────────────────────────────────
def check_password():
    """Показывает окно ввода пароля. Пускает дальше только при верном."""
    def password_entered():
        if st.session_state.get("password_input") == st.secrets.get("app_password"):
            st.session_state["auth_ok"] = True
            del st.session_state["password_input"]
        else:
            st.session_state["auth_ok"] = False

    if st.session_state.get("auth_ok"):
        return True

    st.markdown("### 🔒 Вход в PSS Analytics")
    st.text_input("Пароль", type="password", key="password_input",
                  on_change=password_entered)
    if st.session_state.get("auth_ok") is False:
        st.error("Неверный пароль. Попробуй ещё раз.")
    st.stop()

check_password()

# ─────────────────────────────────────────────
#  ЗАГОЛОВОК
# ─────────────────────────────────────────────
st.title("📊 PSS Analytics — рынок Kaspi")
st.caption(f"Данные: {df['period'].min()} — {df['period'].max()} · "
           f"{fmt_num(len(df))} строк · {df['category'].nunique()} категорий")

# ─────────────────────────────────────────────
#  ФИЛЬТРЫ
# ─────────────────────────────────────────────
st.sidebar.header("Фильтры")

periods = sorted(df["period"].unique())

# --- Период: ручной выбор начала и конца ---
st.sidebar.subheader("Период")
col_p1, col_p2 = st.sidebar.columns(2)
sel_start = col_p1.selectbox("С", periods, index=0)
sel_end = col_p2.selectbox("По", periods, index=len(periods) - 1)
# защита от перепутанного порядка
if sel_start > sel_end:
    sel_start, sel_end = sel_end, sel_start

# --- Категории: мультивыбор ---
all_cats = sorted(df["category"].unique())
sel_cats = st.sidebar.multiselect(
    "Категории (пусто = все)", all_cats, default=[]
)

# --- Бренды: мультивыбор, все бренды ---
# если выбраны категории — показываем бренды только из них
if sel_cats:
    brand_pool = sorted(df[df["category"].isin(sel_cats)]["brand"].unique())
else:
    brand_pool = sorted(df["brand"].unique())
sel_brands = st.sidebar.multiselect(
    f"Бренды (пусто = все, всего {len(brand_pool)})", brand_pool, default=[]
)

# ─────────────────────────────────────────────
#  ПРИМЕНЯЕМ ФИЛЬТРЫ
# ─────────────────────────────────────────────
mask = (df["period"] >= sel_start) & (df["period"] <= sel_end)
if sel_cats:
    mask &= df["category"].isin(sel_cats)
if sel_brands:
    mask &= df["brand"].isin(sel_brands)
d = df[mask]

# Показываем активный выбор
sel_info = []
if sel_cats:
    sel_info.append(f"категории: {', '.join(sel_cats)}")
if sel_brands:
    sel_info.append(f"бренды: {', '.join(sel_brands)}")
if sel_info:
    st.info(f"📍 Выбрано — {' · '.join(sel_info)} · период {sel_start}–{sel_end}")

if len(d) == 0:
    st.warning("Нет данных по выбранным фильтрам. Измени выбор.")
    st.stop()

# ─────────────────────────────────────────────
#  КЛЮЧЕВЫЕ ЦИФРЫ
# ─────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("Оборот", fmt_money(d["revenue"].sum()))
c2.metric("Продажи", fmt_qty(d["sales_qty"].sum()))
c3.metric("Товаров", fmt_num(d["product_code"].nunique()))
c4.metric("Ср. цена", fmt_num(d["price"].mean()) + " ₸")

st.divider()

# ─────────────────────────────────────────────
#  ГРАФИК 1 — ДИНАМИКА ПО МЕСЯЦАМ
# ─────────────────────────────────────────────
st.subheader("Динамика по месяцам")
monthly = d.groupby("period").agg(
    Выручка=("revenue", "sum"),
    Продажи=("sales_qty", "sum"),
).reset_index()
monthly["показ"] = (monthly["Выручка"] / 1e6).round(2)
unit = "млн ₸"

fig1 = px.line(monthly, x="period", y="показ", markers=True,
               labels={"period": "Месяц", "показ": f"Выручка, {unit}"})
fig1.update_traces(line_color="#2a78d6")
st.plotly_chart(fig1, use_container_width=True)

# ─────────────────────────────────────────────
#  ГРАФИК 2 — ТОП КАТЕГОРИЙ И БРЕНДОВ
# ─────────────────────────────────────────────
col_a, col_b = st.columns(2)

with col_a:
    st.subheader("Топ-10 категорий")
    tc = d.groupby("category")["revenue"].sum().sort_values(ascending=False).head(10)
    fig2 = px.bar(x=(tc/1e6).round(1).values, y=tc.index, orientation="h",
                  labels={"x": "Выручка, млн ₸", "y": ""})
    fig2.update_traces(marker_color="#2a78d6")
    fig2.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig2, use_container_width=True)

with col_b:
    st.subheader("Топ-10 брендов")
    tb = d.groupby("brand")["revenue"].sum().sort_values(ascending=False).head(10)
    fig3 = px.bar(x=(tb/1e6).round(1).values, y=tb.index, orientation="h",
                  labels={"x": "Выручка, млн ₸", "y": ""})
    fig3.update_traces(marker_color="#1baf7a")
    fig3.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig3, use_container_width=True)

# ─────────────────────────────────────────────
#  ТАБЛИЦА ТОП ТОВАРОВ
# ─────────────────────────────────────────────
st.subheader("Топ-20 товаров")
top_prod = (d.groupby(["name", "brand", "category"])
            .agg(Выручка=("revenue", "sum"),
                 Продажи=("sales_qty", "sum"),
                 Ср_цена=("price", "mean"))
            .sort_values("Выручка", ascending=False).head(20).reset_index())
top_prod_show = top_prod.copy()
top_prod_show["Выручка"] = top_prod["Выручка"].apply(lambda x: fmt_num(x) + " ₸")
top_prod_show["Продажи"] = top_prod["Продажи"].apply(fmt_num)
top_prod_show["Ср_цена"] = top_prod["Ср_цена"].apply(lambda x: fmt_num(x) + " ₸")
top_prod_show.columns = ["Название", "Бренд", "Категория", "Выручка", "Продажи, шт", "Ср. цена"]
st.dataframe(top_prod_show, use_container_width=True, hide_index=True)

# ─────────────────────────────────────────────
#  СВОДКА ДЛЯ КЛОДА
# ─────────────────────────────────────────────
st.divider()
st.subheader("🤖 Сводка для Клода")
st.caption("Жми кнопку — получишь компактный текст. Скопируй и вставь Клоду в чат для анализа.")

if st.button("Сгенерировать сводку"):
    brief = [f"СВОДКА PSS Analytics ({sel_start}–{sel_end})"]
    if sel_cats:
        brief.append(f"Категории: {', '.join(sel_cats)}")
    if sel_brands:
        brief.append(f"Бренды: {', '.join(sel_brands)}")
    brief.append(f"Оборот: {fmt_money(d['revenue'].sum())}, продажи {fmt_qty(d['sales_qty'].sum())}")
    brief.append(f"Товаров: {fmt_num(d['product_code'].nunique())}, ср.цена {fmt_num(d['price'].mean())} ₸")
    brief.append("\nТОП-8 категорий:")
    for cat, v in d.groupby("category")["revenue"].sum().sort_values(ascending=False).head(8).items():
        brief.append(f"  {cat}: {fmt_money(v)}")
    brief.append("\nТОП-8 брендов:")
    for br, v in d.groupby("brand")["revenue"].sum().sort_values(ascending=False).head(8).items():
        brief.append(f"  {br}: {fmt_money(v)}")
    st.code("\n".join(brief), language="text")
