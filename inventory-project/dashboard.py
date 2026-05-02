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
    st.caption("invmgt · Streamlit Dashboard")


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

st.markdown("---")

import requests

DJANGO_API = "http://localhost:8000/api/v1/products"

with st.expander("🤖 AI Scenario Generator", expanded=False):
    st.subheader("Populate Database with AI-Generated Products")
    
    scenario = st.selectbox("Choose Scenario", [
        "standard", "holiday_rush", "summer_sale", "back_to_school", "clearance"
    ])
    count = st.slider("Number of products", 5, 100, 20, step=5)
    
    if st.button("🚀 Generate & Populate DB"):
        with st.spinner(f"Calling OpenAI to generate {count} products..."):
            try:
                response = requests.post(f"{DJANGO_API}/generate/", json={"count": count, "scenario": scenario})
                if response.status_code == 201:
                    data = response.json()
                    st.success(f"✅ {data['saved']} products added! AI Errors: {len(data['ai_errors'])}, DB Errors: {len(data['save_errors'])}")
                    st.rerun()
                else:
                    st.error(f"Error: {response.text}")
            except Exception as e:
                st.error(f"Failed to reach API: {e}")

st.markdown("---")

with st.expander("📋 Audit Trail — Future Stock Events", expanded=False):
    st.subheader("Stock Event Audit Trail")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        if st.button("⚡ Generate 10 AI Events"):
            with st.spinner("Generating..."):
                try:
                    response = requests.post(f"{DJANGO_API}/generate-events/")
                    if response.status_code == 201:
                        data = response.json()
                        st.success(f"✅ {data['saved']} events added!")
                    else:
                        st.error(f"Error: {response.text}")
                except Exception as e:
                    st.error(f"Failed to reach API: {e}")
                    
    with col2:
        status_filter = st.selectbox("Filter by Status", ["All", "PENDING", "COMPLETED", "CANCELLED"])
        
    try:
        params = {} if status_filter == "All" else {"status": status_filter}
        response = requests.get(f"{DJANGO_API}/stock-events/", params=params)
        if response.status_code == 200:
            events = response.json()
            if events:
                df_events = pd.DataFrame(events)[["expected_date", "event_type", "product_sku", "product_name", "quantity_delta", "unit_price", "supplier", "status", "notes"]]
                st.dataframe(df_events, use_container_width=True, hide_index=True)
            else:
                st.info("No events found.")
    except Exception as e:
        st.warning("Failed to load events")

st.markdown("---")

# ---
# 🧠 Semantic Search (Week 7)
# This section lets users search products by MEANING, not just keywords.
# For example, searching "construction toys" will find "Lego Castle" even
# though the word "construction" doesn't appear in the product name.
# ---
with st.expander("🧠 Semantic Search", expanded=False):
    st.subheader("Search by Meaning")
    st.caption(
        "Unlike keyword search, semantic search understands what you *mean*. "
        "Try queries like 'construction toys', 'gifts for toddlers', or "
        "'outdoor fun for summer'."
    )

    # Step 1: Make sure embeddings are computed
    # Embeddings need to be pre-computed before search can work.
    # This button triggers a one-time computation for all products.
    col_embed, col_eval = st.columns(2)
    with col_embed:
        if st.button("⚙️ Compute Embeddings", help="Pre-compute vectors for all products. Run this after adding new products."):
            with st.spinner("Computing embeddings for all products... (first run downloads the model ~90MB)"):
                try:
                    response = requests.post(f"{DJANGO_API}/compute-embeddings/")
                    if response.status_code == 200:
                        data = response.json()
                        st.success(f"✅ Computed embeddings for {data.get('computed', 0)} / {data.get('total', 0)} products")
                    else:
                        st.error(f"Error: {response.text}")
                except Exception as e:
                    st.error(f"Failed to reach API: {e}")

    with col_eval:
        if st.button("📊 Evaluate Search Quality", help="Run the evalset to measure precision, recall, and F1 score."):
            with st.spinner("Running 8 test queries against the search engine..."):
                try:
                    response = requests.get(f"{DJANGO_API}/evaluate-search/")
                    if response.status_code == 200:
                        eval_data = response.json()
                        st.markdown("### Search Quality Metrics")

                        m1, m2, m3 = st.columns(3)
                        m1.metric("Avg Precision", f"{eval_data.get('avg_precision', 0):.1%}")
                        m2.metric("Avg Recall", f"{eval_data.get('avg_recall', 0):.1%}")
                        m3.metric("F1 Score", f"{eval_data.get('f1_score', 0):.1%}")

                        st.caption(f"Model: {eval_data.get('model_used', 'unknown')} · {eval_data.get('queries_evaluated', 0)} queries evaluated")

                        # Show per-query breakdown
                        per_q = eval_data.get("per_query", [])
                        if per_q:
                            st.markdown("#### Per-Query Breakdown")
                            for pq in per_q:
                                with st.container():
                                    st.markdown(
                                        f"**\"{pq['query']}\"** — "
                                        f"P: {pq.get('precision', 0):.0%} · "
                                        f"R: {pq.get('recall', 0):.0%} · "
                                        f"Hits: {pq.get('hits', 0)}/{pq.get('results_count', 0)}"
                                    )
                    else:
                        st.error(f"Error: {response.text}")
                except Exception as e:
                    st.error(f"Failed to reach API: {e}")

    st.markdown("---")

    # Step 2: The actual search bar
    semantic_query = st.text_input(
        "🔍 Semantic Search",
        placeholder="e.g. construction toys, gifts for toddlers, outdoor fun...",
        key="semantic_search_input",
    )

    if semantic_query.strip():
        with st.spinner("Searching by meaning..."):
            try:
                response = requests.get(
                    f"{DJANGO_API}/semantic-search/",
                    params={"q": semantic_query, "top_k": 10}
                )
                if response.status_code == 200:
                    search_results = response.json()
                    if search_results:
                        st.markdown(f"### Found {len(search_results)} semantically similar products")
                        for idx, result in enumerate(search_results):
                            with st.container():
                                col_info, col_score, col_action = st.columns([4, 1, 1])
                                with col_info:
                                    st.markdown(
                                        f"**{result['name']}** ({result.get('brand', '—')}) "
                                        f"— ₹{result.get('price', 0):,.2f} · "
                                        f"Stock: {result.get('quantity', 0)}"
                                    )
                                    if result.get("description"):
                                        st.caption(result["description"][:120])
                                with col_score:
                                    # Show similarity as a percentage for readability
                                    sim_pct = result.get("similarity", 0) * 100
                                    st.metric("Match", f"{sim_pct:.1f}%")
                                with col_action:
                                    # "Find Similar" button for each result
                                    if st.button("🔗 Similar", key=f"sim_{idx}_{result['id']}"):
                                        st.session_state["find_similar_id"] = result["id"]
                                        st.session_state["find_similar_name"] = result["name"]

                            st.markdown("---")
                    else:
                        st.info("No products matched your query. Try a different search or lower the similarity threshold.")
                else:
                    st.error(f"Search error: {response.text}")
            except Exception as e:
                st.error(f"Failed to reach API: {e}")

    # Step 3: Show "Find Similar" results if a button was clicked
    if st.session_state.get("find_similar_id"):
        sim_id = st.session_state["find_similar_id"]
        sim_name = st.session_state.get("find_similar_name", "")
        st.markdown(f"### 🔗 Products similar to *{sim_name}*")

        try:
            response = requests.get(
                f"{DJANGO_API}/{sim_id}/similar/",
                params={"top_k": 5}
            )
            if response.status_code == 200:
                similar = response.json()
                if similar:
                    sim_df = pd.DataFrame(similar)[["name", "brand", "category", "price", "quantity", "similarity"]]
                    sim_df["similarity"] = sim_df["similarity"].apply(lambda x: f"{x*100:.1f}%")
                    sim_df.columns = ["Name", "Brand", "Category", "Price (₹)", "Stock", "Similarity"]
                    st.dataframe(sim_df, use_container_width=True, hide_index=True)
                else:
                    st.info("No similar products found. Make sure embeddings are computed.")
        except Exception as e:
            st.error(f"Failed to load similar products: {e}")

        # Clear the state so the section doesn't persist on rerun
        if st.button("✕ Close similar products"):
            del st.session_state["find_similar_id"]
            del st.session_state["find_similar_name"]
            st.rerun()

st.markdown("---")

# ---
# 💬 RAG Chatbot (Week 8)
# Ask the Expert: Uses LangChain, ChromaDB, and Groq to answer questions
# strictly based on uploaded store policies and product manuals.
# ---
with st.expander("💬 Ask the Expert (RAG Bot)", expanded=False):
    st.subheader("Store Assistant")
    st.caption(
        "This AI is 'grounded' — it can only answer based on the store's "
        "actual Return Policy, Vendor FAQ, and Product Manuals. "
        "It will not hallucinate answers."
    )

    # Sidebar / Controls for RAG
    col_rag_1, col_rag_2 = st.columns(2)
    with col_rag_1:
        if st.button("📚 Load Documents into VectorDB", help="Chunks text files and saves them to ChromaDB"):
            with st.spinner("Ingesting manuals and policies..."):
                try:
                    response = requests.post(f"{DJANGO_API}/rag/ingest/")
                    if response.status_code == 200:
                        data = response.json()
                        st.success(f"✅ Successfully ingested {data.get('chunks_ingested')} chunks into ChromaDB!")
                    else:
                        st.error(f"Error: {response.text}")
                except Exception as e:
                    st.error(f"API Error: {e}")

    with col_rag_2:
        if st.button("📋 Run RAG Evaluation", help="Tests if Retrieval and Generation are accurate"):
            with st.spinner("Running Retrieval & Generation Suites..."):
                try:
                    response = requests.get(f"{DJANGO_API}/rag/evaluate/")
                    if response.status_code == 200:
                        data = response.json()
                        st.markdown("#### Evaluation Results")
                        ret_eval = data.get("retrieval_eval", {})
                        gen_eval = data.get("generation_eval", {})
                        
                        st.metric("Retrieval Accuracy", f"{ret_eval.get('retrieval_score_pct', 0):.0f}%")
                        st.metric("Generation Accuracy", f"{gen_eval.get('generation_score_pct', 0):.0f}%")
                        
                        st.caption("Check API logs for detailed breakdown.")
                    else:
                        st.error(f"Error: {response.text}")
                except Exception as e:
                    st.error(f"API Error: {e}")

    st.markdown("---")
    
    # Advanced Toggle: Combine RAG with Database
    use_advanced = st.checkbox(
        "🔥 Advanced Mode (Combine RAG with Live Database Stock)", 
        help="If checked, the AI will retrieve BOTH the product manual (RAG) AND the live stock levels (MongoDB) to answer your question."
    )

    # Chat Interface
    # We use session state to keep the chat history visible
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat messages from history on app rerun
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if "sources" in message:
                with st.expander("View Retrieved Context"):
                    for idx, source in enumerate(message["sources"]):
                        st.caption(f"**Chunk {idx+1}**: {source['content'][:200]}...")
            if "db_hits" in message and message["db_hits"]:
                st.caption(f"*(Database checked for: {', '.join(message['db_hits'])})*")

    # React to user input
    if prompt := st.chat_input("Ask about returns, warranties, or specific products..."):
        # Display user message in chat message container
        st.chat_message("user").markdown(prompt)
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Ask the RAG API
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            with st.spinner("Thinking..."):
                try:
                    response = requests.post(
                        f"{DJANGO_API}/rag/ask/",
                        json={"q": prompt, "use_advanced": use_advanced}
                    )
                    if response.status_code == 200:
                        data = response.json()
                        answer = data.get("answer", "No answer provided.")
                        sources = data.get("sources", [])
                        db_hits = data.get("db_hits", [])
                        
                        message_placeholder.markdown(answer)
                        
                        if sources:
                            with st.expander("View Retrieved Context"):
                                for idx, source in enumerate(sources):
                                    st.caption(f"**Chunk {idx+1}**: {source['content'][:200]}...")
                        
                        if db_hits:
                            st.caption(f"*(Database checked for: {', '.join(db_hits)})*")

                        # Add assistant response to chat history
                        st.session_state.messages.append({
                            "role": "assistant", 
                            "content": answer,
                            "sources": sources,
                            "db_hits": db_hits
                        })
                    else:
                        st.error(f"Error: {response.text}")
                except Exception as e:
                    st.error(f"Failed to reach API: {e}")

st.markdown("---")

# ---
# 🤖 AI Sales Agent (Week 9 & 10)
# A multi-step ReAct agent that can lookup products, check inventory,
# and calculate quotes while strictly enforcing discount policies.
# ---
with st.expander("🤖 AI Sales Agent (Quotes & Discounts)", expanded=False):
    st.subheader("Store Quote Generator")
    st.caption(
        "This is an Autonomous Agent. It has access to tools like `get_product_info`, "
        "`check_inventory`, and `calculate_quote`. Ask it for a quote, and watch its reasoning process!"
    )

    if "agent_messages" not in st.session_state:
        st.session_state.agent_messages = []

    # Display chat history
    for message in st.session_state.agent_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            # Display the intermediate tools called
            if message.get("steps"):
                with st.expander("View Agent Reasoning (Tool Calls)", expanded=False):
                    for step in message["steps"]:
                        st.code(
                            f"Tool: {step.get('tool')}\n"
                            f"Input: {step.get('tool_input')}\n"
                            f"Result: {step.get('result')}",
                            language="json"
                        )

    # Chat Input
    if prompt := st.chat_input("Ask for a quote (e.g. 'I need 60 building blocks, can I get a 30% discount?')...", key="agent_input"):
        st.chat_message("user").markdown(prompt)
        st.session_state.agent_messages.append({"role": "user", "content": prompt})

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            with st.spinner("Agent is reasoning and calling tools..."):
                try:
                    response = requests.post(
                        f"{DJANGO_API}/agent/quote/",
                        json={"q": prompt, "history": st.session_state.agent_messages[:-1]}
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        answer = data.get("answer", "Error getting answer.")
                        steps = data.get("steps", [])
                        
                        message_placeholder.markdown(answer)
                        
                        if steps:
                            with st.expander("View Agent Reasoning (Tool Calls)", expanded=False):
                                for step in steps:
                                    st.code(
                                        f"Tool: {step.get('tool')}\n"
                                        f"Input: {step.get('tool_input')}\n"
                                        f"Result: {step.get('result')}",
                                        language="json"
                                    )
                                    
                        st.session_state.agent_messages.append({
                            "role": "assistant",
                            "content": answer,
                            "steps": steps
                        })
                    else:
                        st.error(f"Error: {response.text}")
                except Exception as e:
                    st.error(f"API Error: {e}")