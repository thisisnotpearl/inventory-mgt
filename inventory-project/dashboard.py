import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import sys
import os

# ---
# Page config  
# ---
st.set_page_config(
    page_title="Inventory Dashboard",
    page_icon=":v:",
    layout="wide", # centered or wide
    initial_sidebar_state="auto", # auto, expanded, collapsed
)

# ---
# Bootstrap Django so we can import models directly
# ---


# Assumes this dashboard.py is inside the main Django project folder (same level as manage.py)
DJANGO_PROJECT_PATH = os.path.join(os.path.dirname(__file__))
sys.path.insert(0, os.path.abspath(DJANGO_PROJECT_PATH))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

MODELS_LOADED = False
_MODEL_ERR = ""
try:
    import django
    django.setup()
    from products.models.models import Product        # noqa: E402
    from categories.models.models import Category     # noqa: E402
    MODELS_LOADED = True
except Exception as _e:
    _MODEL_ERR = str(_e)

# ---
# Helpers
# ---
LOW_STOCK_DEFAULT = 10


def utc_now():
    return datetime.now(pytz.utc)


def qs_to_df(qs) -> pd.DataFrame:
    """Convert a MongoEngine QuerySet of Products to a display DataFrame."""
    rows = []
    for p in qs:
        rows.append({
            "_id":        str(p.id),
            "SKU":        p.sku or "—",
            "Name":       p.name,
            "Brand":      getattr(p, "brand", "—") or "—",
            "Category":   p.category.title if p.category else "—",
            "Quantity":   p.quantity,
            "Price (₹)": round(p.price, 2),
            "Created":    p.created_at.strftime("%Y-%m-%d") if p.created_at else "—",
            "Updated":    p.updated_at.strftime("%Y-%m-%d %H:%M") if p.updated_at else "—",
        })
    return pd.DataFrame(rows) # converting list of dicts to DataFrame


def fetch_live(category_id=None):
    # doctring
    """Non-deleted products, optionally filtered by category ObjectId string."""
    qs = Product.objects(is_deleted=False)
    if category_id:
        qs = qs.filter(category=category_id)
    return qs


def all_categories():
    return list(Category.objects.all())


# ---
# Sidebar
# ---
with st.sidebar:
    st.title("📦 Inventory")
    st.markdown("---")

    # Low-stock threshold
    threshold = st.slider(
        ":bell: Low-Stock Threshold (units)",
        min_value=1, max_value=200,
        value=LOW_STOCK_DEFAULT,
        help="Products below this quantity are flagged red.",
    )
    st.markdown("---")

    # Category filter — populated from MongoDB
    cat_map = {"All": None}
    if MODELS_LOADED:
        try:
            for c in all_categories():
                cat_map[c.title] = str(c.id)
        except Exception:
            pass

    selected_cat_label = st.selectbox("🗂️ Filter by Category", list(cat_map.keys()))
    selected_cat_id    = cat_map[selected_cat_label]

    st.markdown("---")
    st.subheader("💰 Price Range (₹)")
    price_min = st.number_input("Min", min_value=0.0, value=0.0, step=50.0)
    price_max = st.number_input("Max", min_value=0.0, value=1_000_000.0, step=50.0)

    st.markdown("---")
    search_text = st.text_input("Search Name / Brand / SKU", placeholder="e.g. Nike")

    st.markdown("---")
    st.caption("interneers-invmgt · Streamlit Dashboard")


# ---
# Main title + connection guard
# ---
st.title("📦 Inventory Dashboard")

if not MODELS_LOADED:
    st.error(
        "⚠️ **Django models could not be loaded.** "
        "Check that `DJANGO_PROJECT_PATH` in `dashboard.py` points to your "
        "`inventory-project/` folder and that MongoDB is running.\n\n"
        f"`{_MODEL_ERR}`"
    )
    st.stop()

# ---
# Fetch data
# ---
try:
    df_all      = qs_to_df(fetch_live())                    # full unfiltered set
    df_filtered = qs_to_df(fetch_live(category_id=selected_cat_id))
except Exception as e:
    st.error(f"Database error: {e}")
    st.stop()

# Apply price range + text search client-side (fast for typical inventory sizes)
if not df_filtered.empty:
    df_filtered = df_filtered[
        (df_filtered["Price (₹)"] >= price_min) &
        (df_filtered["Price (₹)"] <= price_max)
    ]
    if search_text.strip():
        q = search_text.strip()
        mask = (
            df_filtered["Name"].str.contains(q, case=False, na=False)
            | df_filtered["Brand"].str.contains(q, case=False, na=False)
            | df_filtered["SKU"].str.contains(q, case=False, na=False)
        )
        df_filtered = df_filtered[mask]

# ---
# KPI Row - key performance indicators
# ---
if not df_all.empty:
    total_skus  = len(df_all)
    total_units = int(df_all["Quantity"].sum())
    low_ct      = int((df_all["Quantity"] < threshold).sum())
    total_val   = (df_all["Quantity"] * df_all["Price (₹)"]).sum()
    num_cats    = df_all["Category"].nunique()

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total SKUs",     total_skus)
    c2.metric("Total Units",     f"{total_units:,}")
    c3.metric("Categories",      num_cats)
    c4.metric("Low-Stock",       low_ct,
              delta=f"−{low_ct}" if low_ct else None,
              delta_color="inverse")
    c5.metric("💰 Inventory Value", f"₹{total_val:,.2f}")
    st.markdown("---")

# ---
# 🚨 Stock-Alert Banner
# ---
if not df_all.empty:
    low_df = df_all[df_all["Quantity"] < threshold].copy().sort_values("Quantity")
    if not low_df.empty:
        st.error(f"🚨 **{len(low_df)} item(s) below threshold ({threshold} units)**")

        def _alert_qty(val):
            if val == 0:
                return "background-color:#c0392b;color:white;font-weight:bold"
            return "background-color:#f1948a;color:white"

        styled_alert = low_df[["SKU", "Name", "Brand", "Category", "Quantity"]].style \
            .map(_alert_qty, subset=["Quantity"])
        st.dataframe(styled_alert, use_container_width=True, hide_index=True)
        st.markdown("---")

# ---
# Main Inventory Table
# ---
heading = "📋 Inventory"
if selected_cat_label != "All":
    heading += f" — {selected_cat_label}"
if search_text.strip():
    heading += f"  (search: '{search_text}')"
st.subheader(heading)

if df_filtered.empty:
    st.info("No products match the current filters.")
else:
    def _row_qty(val):
        if val == 0:         return "background-color:#fadbd8;color:#c0392b;font-weight:bold"
        if val < threshold:  return "background-color:#fef9e7;color:#c0392b"
        return ""

    DISPLAY_COLS = ["SKU", "Name", "Brand", "Category", "Quantity", "Price (₹)", "Updated"]
    styled_main = (
        df_filtered[DISPLAY_COLS]
        .style
        .map(_row_qty, subset=["Quantity"])
        .format({"Price (₹)": "₹{:,.2f}"})
    )
    st.dataframe(styled_main, use_container_width=True, hide_index=True)

    csv_bytes = df_filtered.drop(columns=["_id"]).to_csv(index=False).encode()
    st.download_button(
        "⬇️  Export as CSV",
        data=csv_bytes,
        file_name=f"inventory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
    )

st.markdown("---")

# ---
# Add Product
# ---
with st.expander("➕  Add New Product", expanded=False):
    st.subheader("New Product")
    cats = all_categories()
    if not cats:
        st.warning("⚠️ No categories found. Create one via the API first.")
    else:
        cat_options = {c.title: c for c in cats}
        with st.form("add_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                f_name  = st.text_input("Product Name *", placeholder="e.g. Running Shoes")
                f_brand = st.text_input("Brand *",        placeholder="e.g. Nike")
                f_cat   = st.selectbox("Category *", list(cat_options.keys()))
                f_desc  = st.text_area("Description", height=80)
            with col2:
                f_qty   = st.number_input("Quantity *", min_value=0, step=1, value=0)
                f_price = st.number_input("Price (₹) *", min_value=0.0, step=0.5, value=0.0)

            if st.form_submit_button("💾  Save Product", type="primary"):
                errors = []
                if not f_name.strip():  errors.append("Name is required.")
                if not f_brand.strip(): errors.append("Brand is required.")
                if f_price <= 0:        errors.append("Price must be greater than 0.")
                if errors:
                    for e in errors:
                        st.warning(e)
                else:
                    try:
                        p = Product(
                            name=f_name.strip(),
                            brand=f_brand.strip(),
                            category=cat_options[f_cat],
                            description=f_desc.strip(),
                            quantity=f_qty,
                            price=f_price,
                        )
                        p.save()   # SKU is auto-generated inside Product.save()
                        st.success(f"✅  '{p.name}' added — SKU: `{p.sku}`")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Failed to save product: {exc}")

# ---
# 🗑️ Soft-Delete Product
# ---
with st.expander("🗑️  Remove a Product (soft-delete)", expanded=False):
    st.subheader("Remove Product")
    if df_all.empty:
        st.info("No products available.")
    else:
        label_to_id = {f"{r['SKU']} — {r['Name']}": r["_id"] for _, r in df_all.iterrows()}
        chosen = st.selectbox("Select product", list(label_to_id.keys()))
        confirm = st.checkbox(f"I confirm I want to soft-delete **{chosen}**")
        if st.button("🗑️  Delete", type="secondary", disabled=not confirm):
            try:
                p = Product.objects.get(id=label_to_id[chosen])
                p.is_deleted = True
                p.deleted_at = utc_now()
                p.save()
                st.success(f"✅  '{chosen}' soft-deleted.")
                st.rerun()
            except Exception as exc:
                st.error(f"Could not delete: {exc}")

# ---
# 🔧 Adjust Stock Quantity
# ---
with st.expander("🔧  Adjust Stock Quantity", expanded=False):
    st.subheader("Quick Stock Update")
    if df_all.empty:
        st.info("No products available.")
    else:
        label_to_id2 = {f"{r['SKU']} — {r['Name']}": r["_id"] for _, r in df_all.iterrows()}
        adj_sel = st.selectbox("Product", list(label_to_id2.keys()), key="adj_sel")
        adj_pid = label_to_id2[adj_sel]
        cur_qty = int(df_all.loc[df_all["_id"] == adj_pid, "Quantity"].values[0])

        st.markdown(f"**Current stock:** `{cur_qty}` units")

        b1, b2, b3 = st.columns([1, 1, 2])
        with b1:
            if st.button("➕  Add 10"):
                p = Product.objects.get(id=adj_pid)
                p.quantity = max(0, p.quantity + 10)
                p.save()
                st.success("Updated ✓")
                st.rerun()
        with b2:
            if st.button(" - Remove 10"):
                p = Product.objects.get(id=adj_pid)
                p.quantity = max(0, p.quantity - 10)
                p.save()
                st.success("Updated ✓")
                st.rerun()
        with b3:
            custom_delta = st.number_input("Custom change (+ or −)", step=1, value=0, key="custom_delta")
            if st.button("Apply Custom"):
                p = Product.objects.get(id=adj_pid)
                p.quantity = max(0, p.quantity + int(custom_delta))
                p.save()
                st.success(f"Stock updated to {p.quantity}")
                st.rerun()