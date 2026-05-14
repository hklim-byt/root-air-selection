import streamlit as st
import pandas as pd
import os
import matplotlib.pyplot as plt
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
from io import BytesIO
import numpy as np
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="루트에어 선정 시스템 V7.0", layout="wide")

# 1. 데이터 로드 함수
def load_my_data():
    target_file = 'fan_performance_map_full_sample.csv'
    if os.path.exists(target_file):
        try: return pd.read_csv(target_file, encoding='utf-8-sig')
        except: return pd.read_csv(target_file, encoding='cp949')
    return None

# 2. 메인 성능 맵 생성
def create_master_chart(all_df, selected_model, user_cmh, user_pa):
    model_df = all_df[all_df['model_name'] == selected_model].sort_values(by=['rpm', 'CMH'])
    rpms = sorted(model_df['rpm'].unique())
    fig, ax = plt.subplots(figsize=(10, 6.5))
    
    for rpm in rpms:
        data = model_df[model_df['rpm'] == rpm]
        ax.plot(data['CMH'], data['Pa'], color='steelblue', linewidth=1.2, alpha=0.5)
        ax.text(data['CMH'].iloc[-1], data['Pa'].iloc[-1], f' {int(rpm)} RPM', 
                color='steelblue', fontsize=8, fontweight='bold', alpha=0.7)

    x_path = np.linspace(0, user_cmh * 1.1, 100)
    k = user_pa / (user_cmh**2) if user_cmh != 0 else 0
    y_path = k * (x_path**2)
    ax.plot(x_path, y_path, color='#1f77b4', linewidth=4, label='System Resistance')

    ax.axvline(user_cmh, color='red', linestyle='--', linewidth=1, alpha=0.4)
    ax.axhline(user_pa, color='red', linestyle='--', linewidth=1, alpha=0.4)
    ax.scatter(user_cmh, user_pa, color='red', s=150, edgecolors='white', zorder=30, label='Design Point')

    ax.set_xlabel('Flow (CMH)', fontweight='bold')
    ax.set_ylabel('Pressure (Pa)', fontweight='bold')
    ax.set_title(f"Performance Map: {selected_model}", fontsize=15, fontweight='bold')
    ax.grid(True, linestyle=':', alpha=0.5); ax.legend(loc='upper right')
    buf = BytesIO(); plt.savefig(buf, format='png', dpi=200); buf.seek(0); plt.close(fig)
    return buf

# 3. 소음 차트 생성
def create_noise_chart(noise_row):
    bands = ['63', '125', '250', '500', '1k', '2k', '4k', '8k']
    vals = [float(str(noise_row[[c for c in noise_row.index if b in c][0]]).split('/')[0]) for b in bands]
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.bar(bands, vals, color='skyblue', edgecolor='navy', alpha=0.7)
    ax.set_title('Octave Band Noise Analysis (dB)', fontweight='bold')
    for i, v in enumerate(vals): ax.text(i, v + 0.5, f'{int(v)}', ha='center', fontweight='bold')
    buf = BytesIO(); plt.savefig(buf, format='png', dpi=150); buf.seek(0); plt.close(fig)
    return buf

# 4. PDF 리포트 생성 (로고 추가 버전)
def create_final_pdf(p_info, model_data, chart_buf, noise_buf, d_point):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    
    # [추가] 회사 로고 배치 (좌측 상단)
    logo_path = "logo.png"
    if os.path.exists(logo_path):
        p.drawImage(logo_path, 50, h-75, width=120, preserveAspectRatio=True, mask='auto')
    
    # 타이틀 (로고 옆으로 이동)
    p.setFont("Helvetica-Bold", 20)
    p.drawRightString(545, h-60, "Technical Selection Report")
    p.line(50, h-85, 545, h-85)

    # 섹션 1: Project Information (수직 배치)
    p.setFont("Helvetica-Bold", 12); p.drawString(50, h-110, "[1] Project Information")
    p.setFont("Helvetica", 10)
    p.drawString(60, h-130, f"Project Name: {p_info['project']}")
    p.drawString(60, h-145, f"Customer: {p_info['customer']}")
    p.drawString(60, h-160, f"Engineer: {p_info['manager']}")
    p.drawString(60, h-175, f"Date: {p_info['date']}")

    # 섹션 2: Design & Performance (수직 배치)
    p.setFont("Helvetica-Bold", 12); p.drawString(50, h-210, "[2] Design & Performance")
    p.setFont("Helvetica", 10)
    p.drawString(60, h-230, f"Selected Model: {model_data['model_name']}")
    p.drawString(60, h-245, f"Operating Speed: {model_data['rpm']} RPM")
    p.drawString(60, h-260, f"Design Flow: {d_point['cmh']:,} CMH / Design Pressure: {d_point['pa']:,} Pa")
    p.drawString(60, h-275, f"Absorbed Power: {model_data['power (kW)']} kW / Total Efficiency: {model_data['total efficiency (%)']}%")

    # 성능 그래프
    p.drawImage(ImageReader(chart_buf), 45, h-630, width=500, height=350)

    # 섹션 3: 소음 데이터 및 격자 표
    p.setFont("Helvetica-Bold", 12); p.drawString(50, h-655, "[3] Acoustic Analysis")
    p.drawImage(ImageReader(noise_buf), 50, h-790, width=490, height=130)
    
    # 격자 표(Grid Table) 그리기
    table_y = h-815
    p.setLineWidth(0.5); p.setStrokeColor(colors.black)
    p.setFillColor(colors.lightgrey); p.rect(50, table_y, 495, 18, fill=1)
    p.setFillColor(colors.black); p.setFont("Helvetica-Bold", 9)
    
    labels = ['63Hz', '125Hz', '250Hz', '500Hz', '1kHz', '2kHz', '4kHz', '8kHz', 'Total']
    for i, b in enumerate(labels):
        p.drawString(55 + (i*55), table_y + 5, b)
        p.line(50 + (i*55), table_y, 50 + (i*55), table_y + 18)
    p.line(545, table_y, 545, table_y + 18)
    
    p.setFont("Helvetica", 9); table_y -= 18
    p.rect(50, table_y, 495, 18, fill=0)
    noise_cols = ['63Hz(dB / dB(A))', '125Hz(dB / dB(A))', '250Hz(dB / dB(A))', '500Hz(dB / dB(A))',
                  '1kHz(dB / dB(A))', '2kHz(dB / dB(A))', '4kHz(dB / dB(A))', '8kHz(dB / dB(A))', 'Total_dB / dB(A)']
    for i, col in enumerate(noise_cols):
        val = str(model_data[col]).split('/')[0].strip() + " dB"
        p.drawString(55 + (i*55), table_y + 5, val)
        p.line(50 + (i*55), table_y, 50 + (i*55), table_y + 18)
    p.line(545, table_y, 545, table_y + 18)

    p.showPage(); p.save(); buffer.seek(0)
    return buffer

# --- 메인 실행부 (Streamlit) ---
df = load_my_data()
if df is not None:
    st.title("🏢 루트에어 송풍기 선정 시스템 V7.0")
    
    # 화면 로고 표시
    if os.path.exists("logo.png"):
        st.image("logo.png", width=200)
    
    st.divider()
    
    # 프로젝트 정보 입력 (Placeholder 적용)
    st.subheader("📋 Project Information")
    c1, c2, c3, c4 = st.columns(4)
    p_name = c1.text_input("Project Name", placeholder="English Only")
    c_name = c2.text_input("Customer", placeholder="English Only")
    m_name = c3.text_input("Manager", placeholder="English Only")
    p_date = c4.date_input("Date", datetime.now())

    # 설계 조건 및 모델 선택
    st.subheader("🎯 Design Duty")
    col1, col2, col3 = st.columns(3)
    u_cmh = col1.number_input("Design Flow (CMH)", value=115000)
    u_pa = col2.number_input("Design Pressure (Pa)", value=2100)
    selected_model = col3.selectbox("Select Model", df['model_name'].unique())
    
    model_data = df[df['model_name'] == selected_model].iloc[0]
    
    # 화면 그래프 출력
    chart_img = create_master_chart(df, selected_model, u_cmh, u_pa)
    st.image(chart_img)
    
    noise_img = create_noise_chart(model_data)
    st.subheader("🔊 Noise Data Analysis")
    st.image(noise_img)
    
    # PDF 생성 및 다운로드 (N/A 로직 포함)
    p_info = {
        "project": p_name if p_name else "N/A",
        "customer": c_name if c_name else "N/A",
        "manager": m_name if m_name else "N/A",
        "date": p_date.strftime("%Y-%m-%d")
    }
    d_point = {"cmh": u_cmh, "pa": u_pa}
    pdf_file = create_final_pdf(p_info, model_data, chart_img, noise_img, d_point)
    
    st.download_button(
        label="📥 Download Final Technical Report (PDF)",
        data=pdf_file,
        file_name=f"Report_{p_info['project']}.pdf",
        mime="application/pdf"
    )
else:
    st.error("데이터 파일을 찾을 수 없습니다.")