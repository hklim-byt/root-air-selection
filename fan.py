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
    st.write("Root Air Fan Selection System V1.7")

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

# 4. PDF 생성 함수 (입력 정보 추가)
def create_pdf(model_info, user_cmh, user_pa, chart_buf, project_info):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # 보고서 제목
    p.setFont("Helvetica-Bold", 20)
    p.drawString(50, height - 50, "Fan Selection Report")
    p.line(50, height - 65, 550, height - 65)
    
    # 프로젝트 및 고객 정보 (추가된 부분)
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, height - 90, "[ Project Information ]")
    p.setFont("Helvetica", 11)
    p.drawString(60, height - 110, f"- Project Name: {project_info['project']}")
    p.drawString(60, height - 130, f"- Customer: {project_info['customer']}")
    p.drawString(60, height - 150, f"- Prepared by: {project_info['manager']}")
    
    # 설계 조건 및 모델 정보
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, height - 180, "[ Technical Specifications ]")
    p.setFont("Helvetica", 11)
    p.drawString(60, height - 200, f"- Design Point: {user_cmh} CMH / {user_pa} Pa")
    p.drawString(60, height - 220, f"- Selected Model: {model_info.iloc[0]}")
    p.drawString(60, height - 240, f"- Motor Power: {model_info.iloc[6]} kW")
    
    # 그래프 삽입
    img = ImageReader(chart_buf)
    p.drawImage(img, 50, height - 600, width=500, height=330)
    
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

# 5. 메인 로직
if df is not None:
    st.divider()
    
    # 신규 추가: 프로젝트 정보 입력 섹션
    st.subheader("📋 프로젝트 정보 입력")
    row1_col1, row1_col2, row1_col3 = st.columns(3)
    with row1_col1:
        project_name = st.text_input("공사명 (Project Name)", placeholder="예: 00공장 증설 공사")
    with row1_col2:
        customer_name = st.text_input("고객사 (Customer)", placeholder="예: (주)루트에어")
    with row1_col3:
        manager_name = st.text_input("송풍기 선정 담당자", placeholder="예: 홍길동 과장")

    st.subheader("🔍 설계 조건 입력")
    c1, c2 = st.columns(2)
    with c1:
        user_cmh = st.number_input("필요 풍량 (CMH)", value=1