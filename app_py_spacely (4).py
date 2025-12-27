import streamlit as st
import pandas as pd
import re

ICON_MAP = {
    "table": "🪵",
    "chair": "💺",
    "sofa": "🛋️",
    "desk": "🗄️",
    "bed": "🛏️"
}

# 1. Load DataFrame from CSV file
github_csv_url = 'https://raw.githubusercontent.com/Ertyuuu55/Spacely2/main/Furniture%20(1).csv'
df = pd.read_csv(github_csv_url) # Pass the variable, not a string literal
def format_rupiah(angka):
    return f"Rp{int(angka):,}".replace(",", ".")

# 2. Consolidated Prioritized Greedy Selection Function (copied from notebook)
def consolidated_prioritized_greedy_selection_with_quantities(df, budget, desired_categories_with_quantities):
    selected_items = []
    total_cost = 0.0
    selection_messages = []

    # Create a copy of the DataFrame to manage available items
    remaining_df = df.copy()

    # 1. Prioritized selection based on desired categories and quantities
    for item_request in desired_categories_with_quantities:
        category = item_request['category']
        quantity_desired = item_request['quantity']
        selected_count_for_category = 0

        if category not in df['category'].unique(): # Check if category exists in original df
            selection_messages.append(f"Warning: Desired category '{category}' is not available in our inventory.")
            continue

        category_items_initial = remaining_df[remaining_df['category'] == category].sort_values(by='price', ascending=True)

        if category_items_initial.empty:
            selection_messages.append(f"Warning: No items found for desired category '{category}' currently in stock.")
            continue

        for _ in range(quantity_desired):
            # Re-filter category items from the current remaining_df to get the cheapest available
            current_category_items = remaining_df[remaining_df['category'] == category].sort_values(by='price', ascending=True)

            if not current_category_items.empty:
                cheapest_item = current_category_items.iloc[0]
                if total_cost + cheapest_item['price'] <= budget:
                    selected_items.append(cheapest_item.to_dict())
                    total_cost += cheapest_item['price']
                    # Remove the selected item from remaining_df by its index
                    remaining_df = remaining_df.drop(cheapest_item.name)
                    selected_count_for_category += 1
                else:
                    selection_messages.append(f"Could not afford remaining {quantity_desired - selected_count_for_category} item(s) from category '{category}' (cheapest available: Rp{cheapest_item['price']:,.2f}) within budget. Budget remaining: Rp{budget - total_cost:,.2f}")
                    break # Break from the inner loop for this category
            else:
                selection_messages.append(f"Ran out of available items for category '{category}' before fulfilling {quantity_desired} items. Selected {selected_count_for_category}.")
                break

        if selected_count_for_category == quantity_desired:
            selection_messages.append(f"Successfully selected {quantity_desired} items for category '{category}'.")
        elif selected_count_for_category > 0:
            selection_messages.append(f"Selected {selected_count_for_category} out of {quantity_desired} desired items for category '{category}'.")

    # 2. Greedily select other cheapest items from the remaining budget and DataFrame
    selection_messages.append("Attempting to fill remaining budget with other cheapest items.")
    sorted_remaining_df = remaining_df.sort_values(by='price', ascending=True)

    for index, row in sorted_remaining_df.iterrows():
        item_price = row['price']
        if total_cost + item_price <= budget:
            selected_items.append(row.to_dict())
            total_cost += item_price
        else:
            # If adding the current item exceeds the budget, stop.
            selection_messages.append(f"Stopped greedy selection as next item (price: Rp{item_price:,.2f}) exceeds remaining budget (Rp{budget - total_cost:,.2f}).")
            break

    if not selected_items:
        selection_messages.append("No items were selected within the budget criteria.")

    return selected_items, total_cost, selection_messages

# 3. Parsing Function
def parse_user_prompt(prompt, df):
    prompt = prompt.lower()
    categories = df['category'].str.lower().unique()

    # Ambil semua angka beserta posisinya
    number_matches = [
        {
            "value": int(m.group().replace('.', '')),
            "start": m.start(),
            "end": m.end()
        }
        for m in re.finditer(r'\d{1,3}(?:\.\d{3})+|\d+', prompt)
    ]

    if not number_matches:
        return None, None, "Budget tidak ditemukan."

    # Budget = angka TERBESAR
    budget_item = max(number_matches, key=lambda x: x['value'])
    budget = budget_item['value']

    # Hapus budget dari kandidat quantity
    quantity_numbers = [
        n for n in number_matches if n != budget_item
    ]

    desired = []

    for cat in categories:
        for cat_match in re.finditer(rf'\b{cat}\b', prompt):
            cat_pos = cat_match.start()

            nearest = None
            min_distance = float('inf')

            for num in quantity_numbers:
                distance = min(
                    abs(num['start'] - cat_pos),
                    abs(num['end'] - cat_pos)
                )

                if distance < min_distance:
                    min_distance = distance
                    nearest = num

            if nearest:
                qty = nearest['value']
                quantity_numbers.remove(nearest)  
            else:
                qty = 1

            desired.append({
                "category": cat,
                "quantity": qty
            })

    return budget, desired, None

# 4. Pemanggilan Output
def select_furniture_based_on_request(df, budget, requested_items):
    selected_items = []
    total_cost = 0
    messages = []

    # MODE 1: Tidak ada furniture spesifik
    if not requested_items:
        default_categories = ['table', 'sofa', 'chair', 'desk', 'bed']

        for cat in default_categories:
            cat_items = df[df['category'].str.lower() == cat].sort_values('price')
            if not cat_items.empty:
                item = cat_items.iloc[0]
                if total_cost + item['price'] <= budget:
                    selected_items.append(item.to_dict())
                    total_cost += item['price']
                    
        if not selected_items:
            messages.append("Budget tidak mencukupi untuk membeli furniture apa pun.")

        return selected_items, total_cost, messages

    # MODE 2: Ada furniture spesifik
    for req in requested_items:
        category = req['category']
        qty = req['quantity']

        cat_items = df[df['category'].str.lower() == category.lower()].sort_values('price')

        if cat_items.empty:
            messages.append(f"Tidak ada item untuk kategori {category}")
            continue

        selected_qty = 0
        for _, row in cat_items.iterrows():
            if selected_qty >= qty:
                break
            if total_cost + row['price'] <= budget:
                selected_items.append(row.to_dict())
                total_cost += row['price']
                selected_qty += 1

        if selected_qty > 0:
            messages.append(
                f"Menampilkan {selected_qty} item untuk kategori '{category}'."
            )

    return selected_items, total_cost, messages

# 5. Streamlit Application UI
st.set_page_config(layout="centered", page_title="Furniture Recommender")
st.title("Furniture Recommendation System")
st.write("Masukkan budget Anda (dalam Rupiah) dan kategori furniture yang diinginkan beserta jumlahnya untuk mendapatkan rekomendasi.")

st.header("Chat Input")

user_prompt = st.text_input(
    "Masukkan kebutuhan furniture Anda (budget WAJIB)",
    placeholder="Contoh: Budget Rp 5000000, bed 2, chair (min 811.268)"
)

# Button to trigger recommendations
if st.button("Generate Recommendations"):
    if not user_prompt.strip():
        st.error("Input tidak boleh kosong atau budget tidak ditemukan. Pastikan Anda menyertakan 'Budget [jumlah]' atau 'Rp [jumlah]'.")
    else:
        user_budget, user_desired_categories, error = parse_user_prompt(user_prompt, df)
        
        if error:
            st.error(error)
        else:
            USD_TO_IDR = 16000
            user_budget_idr = user_budget
            user_budget_usd = user_budget_idr / USD_TO_IDR
            st.markdown("""
            <style>
            .furniture-card {
                background-color: #ffffff;
                padding: 18px;
                border-radius: 14px;
                margin-bottom: 16px;
                box-shadow: 0 6px 14px rgba(0,0,0,0.08);
            }
            .furniture-title {
                font-size: 22px;
                font-weight: 600;
                margin-bottom: 8px;
            }
            .furniture-item {
                font-size: 15px;
                margin: 4px 0;
            }
            </style>
            """, unsafe_allow_html=True)

            st.subheader("Recommendation Results")

            results, total_cost_usd, messages = select_furniture_based_on_request(
              df, user_budget_usd, user_desired_categories
            )

            total_cost_idr = total_cost_usd * USD_TO_IDR
            remaining_budget_idr = user_budget_idr - total_cost_idr

            for msg in messages:
                st.info(msg)

            if results:
                result_df = pd.DataFrame(results)

                for item in results:
                    icon = ICON_MAP.get(item['category'].lower(), "🛒")

                    st.markdown(f"""
                    <div class="furniture-card">
                        <div class="furniture-title">{icon} {item['category'].capitalize()}</div>
                        <div class="furniture-item"><b>Harga:</b> Rp{format_rupiah(item['price'] * USD_TO_IDR)}</div>
                        <div class="furniture-item"><b>Material:</b> {item['material']}</div>
                        <div class="furniture-item"><b>Warna:</b> {item['color']}</div>
                    </div>
                    """.replace(",", "."), unsafe_allow_html=True)

                st.success(f"Total Biaya: {format_rupiah(total_cost_idr)}")

                if remaining_budget_idr > 0:
                    st.info(f"Sisa Budget Anda: {format_rupiah(remaining_budget_idr)}")
                    # Suggestion tambahan (tidak otomatis)
                    suggestions = df[
                        (df['price'] * USD_TO_IDR <= remaining_budget_idr)
                    ].sort_values('price').head(3)
                    
                    if not suggestions.empty:
                        st.markdown("💡 *Dengan sisa budget ini, Anda masih bisa membeli:*")
                        for _, row in suggestions.iterrows():
                            icon = ICON_MAP.get(row['category'].lower(), "🛒")
                            st.write(f"- {icon} {row['category'].capitalize()} — {format_rupiah(row['price'] * USD_TO_IDR)}")

                elif remaining_budget_idr == 0:
                    st.info("Budget Anda pas.")
                else:
                    st.warning("Budget tidak mencukupi")
            else:
                st.warning("Tidak ada furniture yang bisa direkomendasikan.")
