import pandas as pd
from io import BytesIO
from datetime import datetime
from db_connection import fetch_all, fetch_one
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT


def generate_monthly_report(couple_id, month, year):
    """Generate a comprehensive monthly report for a couple"""
    try:
        # Get all transactions for the month
        query = """
        SELECT t.id, t.transaction_date, t.category_id, t.description, t.amount, t.transaction_type, c.category_name
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        WHERE t.couple_id = ? 
        AND strftime('%m', t.transaction_date) = ? 
        AND strftime('%Y', t.transaction_date) = ?
        ORDER BY t.transaction_date DESC
        """
        transactions = fetch_all(query, (couple_id, f"{month:02d}", str(year)))
        
        # Get budget data for the month
        query2 = """
        SELECT b.id, b.category_id, b.planned_amount, c.category_name
        FROM budgets b
        LEFT JOIN categories c ON b.category_id = c.id
        WHERE b.couple_id = ?
        ORDER BY c.category_name
        """
        budgets = fetch_all(query2, (couple_id,))
        
        # Get subscriptions
        query3 = """
        SELECT id, category_name, amount, frequency, next_date, status FROM recurring_transactions
        WHERE couple_id = ? AND status = 'Active'
        ORDER BY next_date ASC
        """
        subscriptions = fetch_all(query3, (couple_id,))
        
        return {
            'transactions': transactions if transactions else [],
            'budgets': budgets if budgets else [],
            'subscriptions': subscriptions if subscriptions else []
        }
    except Exception as e:
        print(f"Error generating report: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def export_to_excel(couple_id, month, year):
    """Export monthly report to Excel file"""
    try:
        report_data = generate_monthly_report(couple_id, month, year)
        
        if not report_data:
            return None
        
        # Create Excel file in memory
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Sheet 1: Summary
            summary_data = {
                'Report Period': [f"{datetime(year, month, 1).strftime('%B %Y')}"],
                'Generated Date': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
                'Total Transactions': [len(report_data['transactions'])],
                'Total Subscriptions': [len(report_data['subscriptions'])]
            }
            df_summary = pd.DataFrame(summary_data)
            df_summary.to_excel(writer, sheet_name='Summary', index=False)
            
            # Sheet 2: Transactions
            if report_data['transactions']:
                trans_list = []
                for t in report_data['transactions']:
                    t_dict = dict(t) if not isinstance(t, dict) else t
                    
                    trans_list.append({
                        'Date': t_dict.get('transaction_date', ''),
                        'Category': t_dict.get('category_name', ''),
                        'Description': t_dict.get('description', '') or '',
                        'Amount (R)': f"{float(t_dict.get('amount', 0)):.2f}",
                        'Type': t_dict.get('transaction_type', '')
                    })
                
                df_trans = pd.DataFrame(trans_list)
                df_trans.to_excel(writer, sheet_name='Transactions', index=False)
                
                # Add summary stats
                income = sum(float(t['Amount (R)']) for t in trans_list if t['Type'] == 'Income')
                expenses = sum(float(t['Amount (R)']) for t in trans_list if t['Type'] == 'Expense')
                net = income - expenses
                
                stats_data = {
                    'Metric': ['Total Income', 'Total Expenses', 'Net'],
                    'Amount (R)': [f"{income:.2f}", f"{expenses:.2f}", f"{net:.2f}"]
                }
                df_stats = pd.DataFrame(stats_data)
                df_stats.to_excel(writer, sheet_name='Transactions', startrow=len(trans_list) + 3, index=False)
            
            # Sheet 3: Budget vs Actual
            if report_data['budgets']:
                budget_rows = []
                for budget in report_data['budgets']:
                    b_dict = dict(budget) if not isinstance(budget, dict) else budget
                    
                    actual_query = """
                    SELECT SUM(amount) as total
                    FROM transactions
                    WHERE couple_id = ? AND category_id = ?
                    AND strftime('%m', transaction_date) = ?
                    AND strftime('%Y', transaction_date) = ?
                    AND transaction_type = 'Expense'
                    """
                    result = fetch_one(actual_query, (couple_id, b_dict['category_id'], f"{month:02d}", str(year)))
                    result_dict = dict(result) if result else {}
                    actual = float(result_dict.get('total', 0)) if result_dict.get('total') else 0.0
                    budgeted = float(b_dict['planned_amount'])
                    
                    budget_rows.append({
                        'Category': b_dict['category_name'],
                        'Budgeted (R)': f"{budgeted:.2f}",
                        'Actual (R)': f"{actual:.2f}",
                        'Remaining (R)': f"{budgeted - actual:.2f}",
                        'Status': '✅ On Track' if actual <= budgeted else '⚠️ Over Budget'
                    })
                
                if budget_rows:
                    df_budget = pd.DataFrame(budget_rows)
                    df_budget.to_excel(writer, sheet_name='Budget vs Actual', index=False)
            
            # Sheet 4: Subscriptions
            if report_data['subscriptions']:
                subs_list = []
                for sub in report_data['subscriptions']:
                    s_dict = dict(sub) if not isinstance(sub, dict) else sub
                    
                    subs_list.append({
                        'Subscription': s_dict.get('category_name', ''),
                        'Amount (R)': f"{float(s_dict.get('amount', 0)):.2f}",
                        'Frequency': s_dict.get('frequency', ''),
                        'Next Due': s_dict.get('next_date', ''),
                        'Status': s_dict.get('status', '')
                    })
                
                df_subs = pd.DataFrame(subs_list)
                df_subs.to_excel(writer, sheet_name='Subscriptions', index=False)
        
        output.seek(0)
        return output
    
    except Exception as e:
        print(f"Error exporting to Excel: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def export_to_pdf(couple_id, month, year):
    """Export monthly report to PDF file"""
    try:
        report_data = generate_monthly_report(couple_id, month, year)
        
        if not report_data:
            return None
        
        output = BytesIO()
        doc = SimpleDocTemplate(output, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#2E5090'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        month_name = datetime(year, month, 1).strftime('%B %Y')
        elements.append(Paragraph(f"💰 Budget Report - {month_name}", title_style))
        elements.append(Spacer(1, 0.3*inch))
        
        # Summary Section
        summary_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#2E5090'),
            spaceAfter=12,
            spaceBefore=12
        )
        elements.append(Paragraph("Summary", summary_style))
        
        # Transaction Stats
        if report_data['transactions']:
            trans_list = []
            total_income = 0
            total_expenses = 0
            
            for t in report_data['transactions']:
                t_dict = dict(t) if not isinstance(t, dict) else t
                amount = float(t_dict.get('amount', 0))
                trans_type = t_dict.get('transaction_type', '')
                
                if trans_type == 'Income':
                    total_income += amount
                else:
                    total_expenses += amount
            
            net = total_income - total_expenses
            
            summary_data = [
                ['Metric', 'Amount (R)'],
                ['Total Income', f"R{total_income:.2f}"],
                ['Total Expenses', f"R{total_expenses:.2f}"],
                ['Net', f"R{net:.2f}"]
            ]
            
            summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E5090')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(summary_table)
            elements.append(Spacer(1, 0.3*inch))
        
        # Transactions Section
        if report_data['transactions']:
            elements.append(Paragraph("Transactions", summary_style))
            
            trans_rows = [['Date', 'Category', 'Description', 'Amount (R)', 'Type']]
            for t in report_data['transactions']:
                t_dict = dict(t) if not isinstance(t, dict) else t
                trans_rows.append([
                    t_dict.get('transaction_date', ''),
                    t_dict.get('category_name', ''),
                    (t_dict.get('description', '') or '')[:20],  # Truncate long descriptions
                    f"R{float(t_dict.get('amount', 0)):.2f}",
                    t_dict.get('transaction_type', '')
                ])
            
            trans_table = Table(trans_rows, colWidths=[1.2*inch, 1.2*inch, 1.2*inch, 1*inch, 0.8*inch])
            trans_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E5090')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 8)
            ]))
            elements.append(trans_table)
            elements.append(Spacer(1, 0.3*inch))
        
        # Budget vs Actual Section
        if report_data['budgets']:
            elements.append(PageBreak())
            elements.append(Paragraph("Budget vs Actual", summary_style))
            
            budget_rows = [['Category', 'Budgeted (R)', 'Actual (R)', 'Remaining (R)', 'Status']]
            for budget in report_data['budgets']:
                b_dict = dict(budget) if not isinstance(budget, dict) else budget
                
                actual_query = """
                SELECT SUM(amount) as total
                FROM transactions
                WHERE couple_id = ? AND category_id = ?
                AND strftime('%m', transaction_date) = ?
                AND strftime('%Y', transaction_date) = ?
                AND transaction_type = 'Expense'
                """
                result = fetch_one(actual_query, (couple_id, b_dict['category_id'], f"{month:02d}", str(year)))
                result_dict = dict(result) if result else {}
                actual = float(result_dict.get('total', 0)) if result_dict.get('total') else 0.0
                budgeted = float(b_dict['planned_amount'])
                
                budget_rows.append([
                    b_dict['category_name'],
                    f"R{budgeted:.2f}",
                    f"R{actual:.2f}",
                    f"R{budgeted - actual:.2f}",
                    '✅ On Track' if actual <= budgeted else '⚠️ Over'
                ])
            
            budget_table = Table(budget_rows, colWidths=[1.5*inch, 1.2*inch, 1.2*inch, 1.2*inch, 1*inch])
            budget_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E5090')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 9)
            ]))
            elements.append(budget_table)
            elements.append(Spacer(1, 0.3*inch))
        
        # Subscriptions Section
        if report_data['subscriptions']:
            elements.append(PageBreak())
            elements.append(Paragraph("Active Subscriptions", summary_style))
            
            sub_rows = [['Subscription', 'Amount (R)', 'Frequency', 'Next Due', 'Status']]
            for sub in report_data['subscriptions']:
                s_dict = dict(sub) if not isinstance(sub, dict) else sub
                sub_rows.append([
                    s_dict.get('category_name', ''),
                    f"R{float(s_dict.get('amount', 0)):.2f}",
                    s_dict.get('frequency', ''),
                    s_dict.get('next_date', ''),
                    s_dict.get('status', '')
                ])
            
            sub_table = Table(sub_rows, colWidths=[1.5*inch, 1.2*inch, 1.2*inch, 1.2*inch, 0.8*inch])
            sub_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E5090')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 9)
            ]))
            elements.append(sub_table)
        
        # Build PDF
        doc.build(elements)
        output.seek(0)
        return output
    
    except Exception as e:
        print(f"Error exporting to PDF: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
