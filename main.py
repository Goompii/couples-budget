import streamlit as st
import pandas as pd
from authentication import login_user, register_user
from transactions import save_transaction, get_user_transactions, get_category_summary, get_monthly_total, save_budget, get_budgets, get_budget_vs_actual, edit_transaction, delete_transaction_user
from couple_pairing import send_pairing_request, get_couple_id, get_partner_info, unpair_couple
from db_connection import execute_query, fetch_all, fetch_one
from config import APP_NAME, DEFAULT_CATEGORIES
from security import check_session_timeout
from admin import is_admin, get_all_users, delete_user, get_user_details, get_system_stats, get_all_transactions, delete_transaction, reset_user_password
import time
import datetime
from reports import export_to_excel




# Page config
st.set_page_config(
    page_title=APP_NAME,
    page_icon="💰",
    layout="wide"
)



# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.couple_id = None
    st.session_state.is_admin = False
    st.session_state.last_activity = None



# Try to restore session from browser storage
try:
    from streamlit.runtime.scriptrunner import get_script_run_ctx
    ctx = get_script_run_ctx()
    if ctx:
        # Session will be maintained across refreshes automatically
        pass
except:
    pass




# Title and sidebar
st.title(f"💰 {APP_NAME}")



if not st.session_state.logged_in:
    # Login/Register Page
    st.write("Welcome to the Couples Budget App!")
    
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        st.subheader("Login")
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        
        if st.button("Login"):
            if username and password:
                success, user, message = login_user(username, password)
                if success:
                    st.session_state.logged_in = True
                    st.session_state.user_id = user['id']
                    st.session_state.username = user['username']



                    # Check if admin
                    from security import sanitize_input
                    is_user_admin = (user['username'] == 'admin')
                    st.session_state.is_admin = is_user_admin



                    # Auto-link couple if paired
                    couple_id = get_couple_id(user['id'])
                    if couple_id:
                        st.session_state.couple_id = couple_id
                    else:
                        st.session_state.couple_id = user['id']
                    
                    st.success(message)
                    st.rerun()



                    # Mark successful login
                    st.session_state.last_activity = datetime.datetime.now()



                else:
                    st.error(message)
            else:
                st.warning("Please enter username and password")
    
    with tab2:
        st.subheader("Create Account")
        new_username = st.text_input("Choose Username", key="reg_username")
        new_email = st.text_input("Email Address", key="reg_email")
        new_password = st.text_input("Password", type="password", key="reg_password")
        new_full_name = st.text_input("Full Name", key="reg_fullname")
        
        if st.button("Register"):
            if new_username and new_email and new_password and new_full_name:
                success, message = register_user(new_username, new_email, new_password, new_full_name)
                if success:
                    st.success(message)
                    st.info("Now go to the Login tab to login!")
                else:
                    st.error(message)
            else:
                st.warning("Please fill in all fields")



else:
    # Main App (After Login)
    
    # Check session timeout
    if check_session_timeout():
        st.rerun()
    
    st.sidebar.write(f"Welcome, {st.session_state.username}! 👋")
    
    if st.session_state.is_admin:
        menu_items = [
            "Dashboard",
            "Add Transaction",
            "View Transactions",
            "Subscriptions",
            "Budgets",
            "📊 Reports",
            "Settings",
            "👨‍💼 Admin Panel"
        ]
    else:
        menu_items = [
            "Dashboard",
            "Add Transaction",
            "View Transactions",
            "Subscriptions",
            "Budgets",
            "📊 Reports",
            "Settings"
        ]



    menu = st.sidebar.radio("Navigation", menu_items)



    
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.user_id = None
        st.session_state.username = None
        st.session_state.is_admin = False
        st.rerun()



    
    if menu == "Dashboard":
        st.subheader("📊 Dashboard")
        
        # Get monthly totals
        monthly_data = get_monthly_total(st.session_state.couple_id)
        category_data = get_category_summary(st.session_state.couple_id)
        
        # Calculate totals
        total_income = 0
        total_expenses = 0
        
        for item in monthly_data:
            if item['transaction_type'] == 'Income':
                total_income = item['total']
            else:
                total_expenses = item['total']
        
        net = total_income - total_expenses
        
        # Display summary cards
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("💚 Income", f"R{total_income:.2f}")
        
        with col2:
            st.metric("❤️ Expenses", f"R{total_expenses:.2f}")
        
        with col3:
            if net >= 0:
                st.metric("💰 Balance", f"R{net:.2f}", delta="Positive")
            else:
                st.metric("💰 Balance", f"R{net:.2f}", delta="Negative")
        
        st.divider()
        
        # Spending by Category
        if category_data:
            st.subheader("📈 Spending by Category")
            
            expense_categories = {}
            for item in category_data:
                if item['transaction_type'] == 'Expense':
                    expense_categories[item['category_name']] = item['total']
            
            if expense_categories:
                import plotly.graph_objects as go
                
                fig = go.Figure(data=[go.Pie(
                    labels=list(expense_categories.keys()),
                    values=list(expense_categories.values()),
                    hole=0
                )])
                
                fig.update_layout(title="Expense Breakdown")
                st.plotly_chart(fig, width='stretch')
            else:
                st.info("No expenses recorded yet!")
        else:
            st.info("Add some transactions to see your dashboard!")
        
    elif menu == "Add Transaction":
        st.subheader("Add Transaction")
        
        with st.form("add_transaction_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                trans_type = st.selectbox("Type", ["Expense", "Income"], key="add_trans_type")
            with col2:
                amount = st.number_input("Amount", min_value=0.0, step=0.01, key="add_trans_amount")
            
            category = st.selectbox("Category", list(DEFAULT_CATEGORIES.keys()), key="add_trans_category")
            description = st.text_area("Description (optional)", key="add_trans_desc")
            trans_date = st.date_input("Date", datetime.date.today(), key="add_trans_date")
            
            submitted = st.form_submit_button("Save Transaction", use_container_width=True)
            
            if submitted:
                if amount > 0 and category:
                    if not st.session_state.couple_id:
                        st.session_state.couple_id = st.session_state.user_id
                    
                    success, message = save_transaction(
                        user_id=st.session_state.user_id,
                        couple_id=st.session_state.couple_id,
                        amount=amount,
                        category=category,
                        description=description,
                        trans_date=trans_date,
                        trans_type=trans_type
                    )
                    
                    if success:
                        st.success(message)
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(message)
                else:
                    st.error("Please fill in all fields")

    
    elif menu == "View Transactions":
        st.subheader("View Transactions")
        
        transactions = get_user_transactions(st.session_state.couple_id, st.session_state.user_id)
        
        if transactions:
            st.write(f"**Total Transactions: {len(transactions)}**")
            st.divider()
            
            for trans in transactions:
                col1, col2, col3, col4, col5, col6, col7 = st.columns([1.5, 1.2, 1.2, 1.2, 1, 0.6, 0.6])
                
                with col1:
                    st.write(f"**{trans['transaction_date']}**")
                with col2:
                    st.write(trans['category_name'])
                with col3:
                    st.write(trans['description'] if trans['description'] else "—")
                with col4:
                    if trans['transaction_type'] == 'Income':
                        st.write(f"🟢 +R{trans['amount']}")
                    else:
                        st.write(f"🔴 -R{trans['amount']}")
                with col5:
                    st.write(trans['transaction_type'])
                
                # Edit Button
                with col6:
                    if st.button("✏️", key=f"edit_trans_{trans['id']}", help="Edit"):
                        st.session_state.edit_trans_id = trans['id']
                        st.session_state.edit_trans_amount = trans['amount']
                        st.session_state.edit_trans_category = trans['category_name']
                        st.session_state.edit_trans_desc = trans['description']
                        st.session_state.edit_trans_date = trans['transaction_date']
                        st.session_state.edit_trans_type = trans['transaction_type']
                        st.session_state.show_edit_form = True
                
                # Delete Button
                with col7:
                    if st.button("🗑️", key=f"del_trans_{trans['id']}", help="Delete"):
                        success, msg = delete_transaction_user(st.session_state.user_id, trans['id'])
                        if success:
                            st.success(msg)
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(msg)
                
                st.divider()
            
            # Edit Transaction Form (if edit button clicked)
            if st.session_state.get('show_edit_form', False):
                st.subheader("✏️ Edit Transaction")
                
                with st.form("edit_transaction_form"):
                    col1, col2 = st.columns(2)
                    with col1:
                        edit_type = st.selectbox(
                            "Type", 
                            ["Expense", "Income"],
                            index=0 if st.session_state.get('edit_trans_type') == 'Expense' else 1,
                            key="edit_type"
                        )
                    with col2:
                        edit_amount = st.number_input(
                            "Amount",
                            min_value=0.0,
                            step=0.01,
                            value=float(st.session_state.get('edit_trans_amount', 0)),
                            key="edit_amount"
                        )
                    
                    edit_category = st.selectbox(
                        "Category",
                        list(DEFAULT_CATEGORIES.keys()),
                        index=list(DEFAULT_CATEGORIES.keys()).index(st.session_state.get('edit_trans_category', 'Food & Groceries')) if st.session_state.get('edit_trans_category') in DEFAULT_CATEGORIES.keys() else 0,
                        key="edit_category"
                    )
                    
                    edit_description = st.text_area(
                        "Description (optional)",
                        value=st.session_state.get('edit_trans_desc', ''),
                        key="edit_description"
                    )
                    
                    edit_date = st.date_input(
                        "Date",
                        value=datetime.datetime.strptime(st.session_state.get('edit_trans_date', datetime.date.today().isoformat()), '%Y-%m-%d').date() if isinstance(st.session_state.get('edit_trans_date'), str) else datetime.date.today(),
                        key="edit_date"
                    )
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button("💾 Save Changes"):
                            if edit_amount > 0:
                                success, message = edit_transaction(
                                    user_id=st.session_state.user_id,
                                    transaction_id=st.session_state.get('edit_trans_id'),
                                    amount=edit_amount,
                                    category=edit_category,
                                    description=edit_description,
                                    trans_date=edit_date,
                                    trans_type=edit_type,
                                    couple_id=st.session_state.couple_id
                                )
                                if success:
                                    st.success(message)
                                    st.session_state.show_edit_form = False
                                    st.rerun()
                                else:
                                    st.error(message)
                            else:
                                st.error("Amount must be greater than 0")
                    
                    with col2:
                        if st.form_submit_button("❌ Cancel"):
                            st.session_state.show_edit_form = False
                            st.rerun()
        else:
            st.info("No transactions yet. Add one in the 'Add Transaction' tab!")



    elif menu == "Subscriptions":
        st.subheader("🔄 Recurring Subscriptions & Payments")
        
        from recurring import (
            get_recurring_transactions, save_recurring_transaction, 
            delete_recurring_transaction, update_recurring_status,
            get_upcoming_subscriptions, get_monthly_subscription_cost
        )
        
        tab1, tab2, tab3 = st.tabs(["📋 Active Subscriptions", "➕ Add New", "📊 Analytics"])
        
        with tab1:
            st.subheader("Active Subscriptions")
            
            recurring = get_recurring_transactions(st.session_state.couple_id)
            
            if recurring:
                # Calculate total monthly cost
                monthly_total = get_monthly_subscription_cost(st.session_state.couple_id)
                st.metric("💰 Monthly Recurring Cost", f"R{monthly_total:.2f}")
                st.divider()
                
                for item in recurring:
                    with st.container():
                        col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 0.8])
                        
                        with col1:
                            st.write(f"**{item['category_name']}**")
                            st.caption(item['description'] if item['description'] else "No description")
                        
                        with col2:
                            if item['status'] == 'Active':
                                st.write(f"🟢 {item['frequency']}")
                            else:
                                st.write(f"⚪ {item['status']}")
                        
                        with col3:
                            st.write(f"R{item['amount']:.2f}")
                        
                        with col4:
                            st.caption(f"Next: {item['next_date']}")
                        
                        with col5:
                            if st.button("⏸️" if item['status'] == 'Active' else "▶️", key=f"toggle_{item['id']}", help="Pause/Resume"):
                                new_status = 'Paused' if item['status'] == 'Active' else 'Active'
                                success, msg = update_recurring_status(item['id'], new_status)
                                if success:
                                    st.rerun()
                            
                            if st.button("🗑️", key=f"del_recurring_{item['id']}"):
                                success, msg = delete_recurring_transaction(item['id'])
                                if success:
                                    st.success("Deleted!")
                                    st.rerun()
                        
                        st.divider()
            else:
                st.info("No recurring subscriptions yet. Add one to get started!")
        
        with tab2:
            st.subheader("Add New Recurring Transaction")
            
            # Use form to better handle submissions
            with st.form("add_subscription_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    sub_name = st.text_input("Subscription/Bill Name (e.g., Netflix, Gym)")
                    sub_amount = st.number_input("Monthly Amount (R)", min_value=0.0, step=0.01, value=0.0)
                
                with col2:
                    sub_frequency = st.selectbox("Frequency", ["Weekly", "Bi-weekly", "Monthly", "Quarterly", "Yearly"])
                    sub_date = st.date_input("Next Due Date", datetime.date.today())
                
                sub_description = st.text_area("Notes (optional)", placeholder="e.g., Gym membership, auto-renews")
                
                submitted = st.form_submit_button("➕ Add Subscription", use_container_width=True)
                
                if submitted:
                    if sub_name and sub_amount > 0:
                        success, msg = save_recurring_transaction(
                            couple_id=st.session_state.couple_id,
                            category=sub_name,
                            amount=sub_amount,
                            frequency=sub_frequency,
                            next_date=sub_date.strftime('%Y-%m-%d'),
                            description=sub_description
                        )
                        
                        if success:
                            st.success("✅ Subscription added successfully!")
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error(msg)
                    else:
                        st.error("❌ Please fill in name and amount (must be greater than 0)")
        
        with tab3:
            st.subheader("📊 Subscription Analytics")
            
            monthly_cost = get_monthly_subscription_cost(st.session_state.couple_id)
            upcoming = get_upcoming_subscriptions(st.session_state.couple_id, 30)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("💰 Monthly Cost", f"R{monthly_cost:.2f}")
            
            with col2:
                st.metric("📅 Annual Cost", f"R{monthly_cost * 12:.2f}")
            
            with col3:
                st.metric("⏰ Due in 30 Days", len(upcoming))
            
            st.divider()
            
            st.subheader("Upcoming in Next 30 Days")
            if upcoming:
                for sub in upcoming:
                    st.write(f"🔔 **{sub['category_name']}** - R{sub['amount']:.2f} on {sub['next_date']}")
            else:
                st.info("No subscriptions due in next 30 days")
    
    elif menu == "Budgets":
        st.subheader("💰 Budget Management")
        
        from datetime import datetime
        now = datetime.now()
        
        col1, col2 = st.columns(2)
        with col1:
            month = st.selectbox("Month", range(1, 13), index=now.month - 1)
        with col2:
            year = st.selectbox("Year", range(2024, 2026), index=0)
        
        st.divider()
        
        # Set Budget Section
        st.subheader("📊 Set Budget")
        
        col1, col2 = st.columns(2)
        with col1:
            budget_category = st.selectbox("Category", list(DEFAULT_CATEGORIES.keys()))
        with col2:
            budget_amount = st.number_input("Budget Amount (R)", min_value=0.0, step=100.0)
        
        if st.button("Save Budget"):
            if budget_amount > 0:
                success, message = save_budget(
                    couple_id=st.session_state.couple_id,
                    category_name=budget_category,
                    planned_amount=budget_amount,
                    month=month,
                    year=year
                )
                if success:
                    st.success(message)
                else:
                    st.error(message)
            else:
                st.error("Please enter a budget amount")
        
        st.divider()
        
        # Budget vs Actual
        st.subheader("📈 Budget vs Actual Spending")
        
        budget_data = get_budget_vs_actual(st.session_state.couple_id, month, year)
        
        if budget_data:
            for item in budget_data:
                category = item['category_name']
                budgeted = item['budgeted']
                actual = item['actual']
                
                if budgeted > 0:
                    percentage = (actual / budgeted) * 100
                    
                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        st.write(f"**{category}**")
                        progress_value = min(percentage / 100, 1.0)
                        
                        if percentage > 100:
                            st.progress(1.0)
                            st.warning(f"🔴 Over budget! {percentage:.0f}%")
                        elif percentage > 80:
                            st.progress(progress_value)
                            st.warning(f"🟡 Caution {percentage:.0f}%")
                        else:
                            st.progress(progress_value)
                            st.success(f"🟢 On track {percentage:.0f}%")
                    
                    with col2:
                        st.metric("Budget", f"R{budgeted:.0f}")
                    
                    with col3:
                        st.metric("Spent", f"R{actual:.0f}")
        else:
            st.info("No expense categories with budgets set yet!")



    
    elif menu == "📊 Reports":
        st.subheader("📊 Monthly Reports & Export")
        
        from datetime import datetime
        now = datetime.now()
        
        st.write("Generate and download your monthly financial report.")
        st.divider()
        
        col1, col2 = st.columns(2)
        with col1:
            report_month = st.selectbox("📅 Select Month", range(1, 13), index=now.month - 1, key="report_month")
        with col2:
            report_year = st.selectbox("📆 Select Year", range(2024, 2026), key="report_year")
        
        st.divider()
        
        # Format choice
        export_format = st.radio("Choose export format:", ["📊 Excel", "📄 PDF"], horizontal=True)
        
        st.write("Click the button below to generate your report:")
        
        if st.button("📥 Generate & Download Report", use_container_width=True):
            with st.spinner("⏳ Generating report..."):
                if export_format == "📊 Excel":
                    from reports import export_to_excel
                    file_data = export_to_excel(st.session_state.couple_id, report_month, report_year)
                    file_ext = "xlsx"
                    mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                else:
                    from reports import export_to_pdf
                    file_data = export_to_pdf(st.session_state.couple_id, report_month, report_year)
                    file_ext = "pdf"
                    mime_type = "application/pdf"
                
                if file_data:
                    month_name = datetime(report_year, report_month, 1).strftime('%B %Y')
                    st.download_button(
                        label=f"⬇️ Download {month_name} Report ({file_ext.upper()})",
                        data=file_data,
                        file_name=f"Budget_Report_{month_name.replace(' ', '_')}.{file_ext}",
                        mime=mime_type,
                        use_container_width=True
                    )
                    st.success("✅ Report generated successfully!")
                else:
                    st.error("❌ Error generating report - please check your data")
        
        st.divider()
        
        st.info("📋 Your report will include:\n\n"
                "• **Summary** - Report period and key metrics\n"
                "• **Transactions** - All transactions with dates and amounts\n"
                "• **Budget vs Actual** - Spending compared to budgets\n"
                "• **Subscriptions** - All active subscriptions")
        
    elif menu == "Settings":
        st.subheader("⚙️ Settings")
        
        st.write(f"**Username:** {st.session_state.username}")
        st.write(f"**User ID:** {st.session_state.user_id}")
        
        st.divider()
        st.subheader("👫 Partner Link")
        
        col1, col2 = st.columns(2)
        
        with col1:
            partner_username = st.text_input("Partner Username")
        
        with col2:
            couple_name = st.text_input("Couple Name (optional)")
        
        if st.button("🔗 Link Partner"):
            if partner_username:
                success, message = send_pairing_request(
                    user1_id=st.session_state.user_id,
                    user2_username=partner_username,
                    couple_name=couple_name or f"{st.session_state.username} & {partner_username}"
                )
                
                if success:
                    st.success(message)
                    new_couple_id = get_couple_id(st.session_state.user_id)
                    if new_couple_id:
                        st.session_state.couple_id = new_couple_id
                        st.rerun()
                else:
                    st.error(message)
            else:
                st.error("Enter partner username")
        
        if st.session_state.couple_id:
            st.divider()
            partner = get_partner_info(st.session_state.couple_id, st.session_state.user_id)
            if partner:
                st.success(f"✅ Linked with {partner['full_name']}")
                
                if st.button("🔓 Unlink Partner"):
                    success, msg = unpair_couple(st.session_state.couple_id)
                    if success:
                        st.success(msg)
                        st.session_state.couple_id = None
                        st.rerun()
        
    elif menu == "👨‍💼 Admin Panel":
        st.subheader("👨‍💼 Admin Dashboard")
        
        if not st.session_state.is_admin:
            st.error("❌ Unauthorized access")
            st.stop()
        
        admin_tab1, admin_tab2, admin_tab3 = st.tabs(["📊 Stats", "👥 Users", "🔄 Subscriptions"])
        
        with admin_tab1:
            st.subheader("System Statistics")
            stats = get_system_stats()
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("👥 Total Users", stats.get('total_users', 0))
            with col2:
                st.metric("👫 Couples", stats.get('total_couples', 0))
            with col3:
                st.metric("💳 Transactions", stats.get('total_transactions', 0))
            with col4:
                st.metric("💰 Budgets", stats.get('total_budgets', 0))
        
        with admin_tab2:
            st.subheader("User Accounts & Transactions")
            
            users = get_all_users()
            st.write(f"**Total Users: {len(users)}**")
            st.divider()
            
            if users:
                # Create user selector
                user_options = {f"{user['username']} ({user['full_name']})": user['id'] for user in users}
                selected_user_display = st.selectbox(
                    "📋 Select User to View Details",
                    list(user_options.keys()),
                    key="admin_user_select"
                )
                selected_user_id = user_options[selected_user_display]
                
                st.divider()
                
                # Show user details
                user_detail = next((u for u in users if u['id'] == selected_user_id), None)
                if user_detail:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.write(f"**👤 Username:** {user_detail['username']}")
                    with col2:
                        st.write(f"**📧 Email:** {user_detail['email']}")
                    with col3:
                        st.write(f"**👤 Name:** {user_detail['full_name']}")
                    
                    st.caption(f"Created: {user_detail['created_at']}")
                    
                    st.divider()
                    
                    # Password reset section
                    st.subheader("🔑 Reset Password")
                    new_password = st.text_input("New Password", type="password", key=f"reset_pwd_{selected_user_id}")
                    confirm_password = st.text_input("Confirm Password", type="password", key=f"confirm_pwd_{selected_user_id}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("🔐 Reset Password", key=f"btn_reset_pwd_{selected_user_id}"):
                            if new_password and confirm_password:
                                if new_password == confirm_password:
                                    success, msg = reset_user_password(st.session_state.username, selected_user_id, new_password)
                                    if success:
                                        st.success(msg)
                                    else:
                                        st.error(msg)
                                else:
                                    st.error("❌ Passwords don't match")
                            else:
                                st.error("❌ Please enter both passwords")
                    
                    with col2:
                        if st.button("🗑️ Delete This User", key=f"del_user_{selected_user_id}"):
                            success, msg = delete_user(st.session_state.username, selected_user_id)
                            if success:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
                
                st.divider()
                
                # Show user's transactions
                st.subheader(f"💳 Transactions for {selected_user_display}")
                
                from admin import get_transactions_by_user_id
                user_transactions = get_transactions_by_user_id(selected_user_id)
                
                if user_transactions:
                    st.write(f"**Total: {len(user_transactions)}**")
                    
                    # Summary stats
                    total_income = 0
                    total_expenses = 0
                    
                    for trans in user_transactions:
                        if trans['transaction_type'] == 'Income':
                            total_income += trans['amount']
                        else:
                            total_expenses += trans['amount']
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("💚 Income", f"R{total_income:.2f}")
                    with col2:
                        st.metric("❤️ Expenses", f"R{total_expenses:.2f}")
                    with col3:
                        net = total_income - total_expenses
                        st.metric("💰 Net", f"R{net:.2f}")
                    
                    st.divider()
                    
                    # Display transactions
                    for trans in user_transactions:
                        with st.container():
                            col1, col2, col3, col4 = st.columns([2, 1, 1, 0.8])
                            
                            with col1:
                                st.write(f"**{trans['category_name']}**")
                                st.caption(trans['description'] if trans['description'] else "No description")
                            
                            with col2:
                                if trans['transaction_type'] == 'Income':
                                    st.write(f"🟢 +R{trans['amount']}")
                                else:
                                    st.write(f"🔴 -R{trans['amount']}")
                            
                            with col3:
                                st.caption(trans['transaction_date'])
                            
                            with col4:
                                if st.button("🗑️", key=f"del_trans_{trans['id']}"):
                                    success, msg = delete_transaction(st.session_state.username, trans['id'])
                                    if success:
                                        st.success(msg)
                                        st.rerun()
                                    else:
                                        st.error(msg)
                            
                            st.divider()
                else:
                    st.info("No transactions for this user")
            else:
                st.info("No users found")
        
        with admin_tab3:
            st.subheader("🔄 All Subscriptions by User")
            
            from recurring import get_recurring_transactions, get_monthly_subscription_cost, delete_recurring_transaction
            from couple_pairing import get_couple_id
            
            users = get_all_users()
            
            if users:
                user_options = {
                    f"{user['username']} ({user['full_name']})": user['id']
                    for user in users
                }
                selected_user_display = st.selectbox(
                    "👤 Select User to View Subscriptions",
                    list(user_options.keys()),
                    key="admin_sub_user_select"
                )
                selected_user_id = user_options[selected_user_display]
                
                # Get the couple_id for this user
                couple_id = get_couple_id(selected_user_id)
                if not couple_id:
                    couple_id = selected_user_id  # If no couple, use user_id
                
                st.divider()
                
                # Get subscriptions for this user's couple
                user_subscriptions = get_recurring_transactions(couple_id)
                
                if user_subscriptions:
                    st.write(f"**Total Subscriptions: {len(user_subscriptions)}**")
                    
                    # Calculate monthly cost for this user's couple
                    monthly_cost = get_monthly_subscription_cost(couple_id)
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("💰 Monthly Cost", f"R{monthly_cost:.2f}")
                    with col2:
                        st.metric("📅 Annual Cost", f"R{monthly_cost * 12:.2f}")
                    with col3:
                        active_count = len([s for s in user_subscriptions if s['status'] == 'Active'])
                        st.metric("🟢 Active", active_count)
                    
                    st.divider()
                    
                    # Display subscriptions
                    for sub in user_subscriptions:
                        with st.container():
                            col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 0.8])
                            
                            with col1:
                                st.write(f"**{sub['category_name']}**")
                                st.caption(sub['description'] if sub['description'] else "No description")
                            
                            with col2:
                                if sub['status'] == 'Active':
                                    st.write(f"🟢 {sub['frequency']}")
                                elif sub['status'] == 'Paused':
                                    st.write("🟡 Paused")
                                else:
                                    st.write(f"⚪ {sub['status']}")
                            
                            with col3:
                                st.write(f"R{sub['amount']:.2f}")
                            
                            with col4:
                                st.caption(f"Next: {sub['next_date']}")
                            
                            with col5:
                                if st.button("🗑️", key=f"admin_del_sub_{sub['id']}"):
                                    success, msg = delete_recurring_transaction(sub['id'])
                                    if success:
                                        st.success("Deleted!")
                                        st.rerun()
                                    else:
                                        st.error(msg)
                            
                            st.divider()
                else:
                    st.info("This user has no subscriptions")
            else:
                st.info("No users found")
