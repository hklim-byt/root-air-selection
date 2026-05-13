import streamlit as st
import pandas as pd
import os
import matplotlib.pyplot as plt
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from io import BytesIO

# 페이지 설정
st.set_page_config(page_title="루트에어 송풍기 선정", layout="wide")

# 1. 상단 레이아웃 (로고 및 타이틀)
col_logo, col_title = st.columns([1, 4])
with col_logo:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=250)
    else:
        st.title("🏢")

with col_title:
    st.markdown("###")
    st.title("루트에어 송풍기 선정 프로그램")
    st.write("Root Air Fan Selection System V1.9")

# 2. 데이터 불러오기 함수
def load_my_data():
    file_name = 'fan_data.csv'
    if not os.path.exists(file_name): return None
    try:
        df = pd.read_csv(file_name, encoding='utf-8-sig')
    except:
        df = pd.read_csv(file_name, encoding='cp949')
    return df

df = load_my_data()

# 3. 그래프 생성 함수
def create_fan_chart(all_df, user_cmh, user_pa):
    fig, ax = plt.subplots(figsize=(10, 6))
    unique_models = all_df.iloc[:, 0].unique()
    for model in unique_models:
        model_data = all_df[all_df.iloc[:, 0] == model]
        model_data = model_data.sort_values(by=all_df.columns[3])
        ax.plot(model_data.iloc[:, 3], model_data.iloc[:, 5], marker='o', markersize=4, label=f"Curve: {model}", linewidth=2)
    
    ax.scatter(user_cmh, user_pa, color='red', s=150, label='Design Point', zorder=10)
    ax.axhline(user_pa, color='red', linestyle='--', linewidth=1.5, alpha=0.7)
    ax.axvline(user_cmh, color='red', linestyle='--', linewidth=1.5, alpha=0.7)
    
    ax.set_xlabel('Air Flow (CMH)')
    ax.set_ylabel('Static Pressure (Pa)')
    ax.set_title('Fan Performance Selection Chart')
    ax.grid(True, linestyle=':', alpha=0.6)
    ax.legend()

    img_buf = BytesIO()
    plt.savefig(img_buf, format='png', dpi=200)
    img_buf.seek(0)
    plt.close(fig)
    return img_buf

# 4. PDF 생성 함수 (영문 리포트 전용)
def create_pdf(model_info, user_cmh, user_pa, chart_buf, project_info):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    p.setFont("Helvetica-Bold", 20)
    p.drawString(50, height - 50, "Fan Selection Report")
    p.line(50, height - 65, 550, height - 65)
    
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, height - 90, "[ Project Information ]")
    p.setFont("Helvetica", 11)
    p.drawString(60, height - 110, f"- Project Name: {project_info['project']}")
    p.drawString(60, height - 130, f"- Customer: {project_info['customer']}")
    p.drawString(60, height - 150, f"- Prepared by: {project_info['manager']}")
    
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, height - 180, "[ Technical Specifications ]")
    p.setFont("Helvetica", 11)
    p.drawString(60, height - 200, f"- Design Point: {user_cmh} CMH / {user_pa} Pa")
    p.drawString(60, height - 220, f"- Selected Model: {model_info.iloc[0]}")
    p.drawString(60, height - 240, f"- Motor Power: {model_info.iloc[6]} kW")
    
    img = ImageReader(chart_buf)
    p.drawImage(img, 50, height - 600, width=500, height=330)
    
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

# 5. 메인 로직
if df is not None:
    st.divider()
    
    # 영문 작성 안내 가이드
    st.subheader("📋 Project Information")
    st.info("⚠️ To prevent character corruption in the PDF, please enter all fields in **English**.")
    
    row1_col1, row1_col2, row1_col3 = st.columns(3)
    with row1_col1:
        project_name = st.text_input("Project Name", placeholder="e.g. 00 Plant Extension")
    with row1_col2:
        customer_name = st.text_input("Customer", placeholder="e.g. Root Air Co., Ltd.")
    with row1_col3:
        manager_name = st.text_input("Prepared by (Manager)", placeholder="e.g. Gildong Hong")

    st.subheader("🔍 Design Conditions")
    c1, c2 = st.columns(2)
    with c1:
        user_cmh = st.number_input("Required Flow (CMH)", value=120000, step=1000)
    with c2:
        user_pa = st.number_input("Required Static Pressure (Pa)", value=2400, step=10)

    # 선정 로직
    matched_fans = df[(df.iloc[:, 3] >= user_cmh) & (df.iloc[:, 5] >= user_pa)].copy()

    if not matched_fans.empty:
        best_ones = matched_fans.sort_values(by=[df.columns[3], df.columns[5]])
        st.success(f"Successfully found {len(best_ones)} operation points!")
        
        top_model = best_ones.iloc[0]
        chart_img = create_fan_chart(df, user_cmh, user_pa)
        
        project_info = {
            "project": project_name if project_name else "N/A",
            "customer": customer_name if customer_name else "N/A",
            "manager": manager_name if manager_name else "N/A"
        }

        st.divider()
        st.subheader("📈 Performance Curve")
        st.image(chart_img, use_container_width=True)

        pdf_buf = create_pdf(top_model, user_cmh, user_pa, chart_img, project_info)
        st.download_button(
            label="📥 Download Selection Report (PDF)",
            data=pdf_buf,
            file_name=f"Report_{project_name}.pdf" if project_name else "Report.pdf",
            mime="application/pdf"
        )
        
        st.dataframe(best_ones, use_container_width=True)
    else:
        st.warning("⚠️ No matching models found.")

    with st.expander("📂 View Database"):
        st.write(df)