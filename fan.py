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
st.set_page_config(page_title="루트에어 선정 시스템 V7.9", layout="wide")

# 1. 데이터 로드 함수
def load_my_data():
    target_file = 'fan_performance_map_full_sample.csv' 
    if os.path.exists(target_file):
        try: return pd.read_csv(target_file, encoding='utf-8-sig')
        except: return pd.read_csv(target_file, encoding='cp949')
    return None

# 2. 메인 성능 맵 생성 (서징 영역 복구)
def create_master_chart(all_df, selected_model, user_cmh, user_pa):
    model_df = all_df[all_df['model_name'] == selected_model].sort_values(by=['rpm', 'CMH'])
    rpms = sorted(model_df['rpm'].unique())
    fig, ax = plt.subplots(figsize=(10, 7))
    
    surge_x, surge_y = [], []
    
    for rpm in rpms:
        data = model_df[model_df['rpm'] == rpm]
        ax.plot(data['CMH'], data['Pa'], color='steelblue', linewidth=1.2, alpha=0.5)
        ax.text(data['CMH'].iloc[-1], data['Pa'].iloc[-1], f' {int(rpm)} RPM', 
                color='steelblue', fontsize=9, fontweight='bold', va='center')
        
        # 서징 포인트 수집 (각 RPM 곡선의 첫 번째 데이터 포인트)
        surge_x.append(data['CMH'].iloc[0])
        surge_y.append(data['Pa'].iloc[0])

    # [수정] 서징 라인 및 영역 표시
    ax.plot(surge_x, surge_y, 'r--', linewidth=2.5, label='Surge Line', zorder=5)
    ax.fill_betweenx(surge_y, 0, surge_x, color='red', alpha=0.07, zorder=0)

    # 시스템 저항 곡선
    x_max = max(user_cmh * 1.3, model_df['CMH'].max())
    x_path = np.linspace(0, x_max, 100)
    k = user_pa / (user_cmh**2) if user_cmh != 0 else 0
    y_path = k * (x_path**2)
    ax.plot(x_path, y_path, color='#1f77b4', linewidth=4, label='System Resistance')

    # 설계점 마킹
    ax.axvline(user_cmh, color='red', linestyle='--', linewidth=1, alpha=0.4)
    ax.axhline(user_pa, color='red', linestyle='--', linewidth=1, alpha=0.4)
    ax.scatter(user_cmh, user_pa, color='red', s=150, edgecolors='white', zorder=30, label='Design Point')

    ax.set_xlim(0, x_max)
    ax.set_ylim(0, max(user_pa * 1.5, model_df['Pa'].max()))
    ax.set_xlabel('Flow (CMH)', fontweight='bold'); ax.set_ylabel('Pressure (Pa)', fontweight='bold')
    ax.set_title(f"Performance Map: {selected_model}", fontsize=16, fontweight='bold', pad=20)
    ax.grid(True, linestyle=':', alpha=0.5); ax.legend(loc='upper right', fontsize=10)
    plt.tight_layout()
    buf = BytesIO(); plt.savefig(buf, format='png', dpi=200); buf.seek(0); plt.close(fig)
    return buf

# [create_noise_chart 함수 및 PDF 생성 로직은 V7.8과 동일하게 유지하되 Date 위치 유지]
def create_final_pdf(p_info, model_data, chart_buf, noise_buf, d_point):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    logo_path = "logo.png"
    p.setFont("Helvetica-Bold", 22); p.drawString(50, h-60, "Technical Selection Report")
    if os.path.exists(logo_path):
        p.drawImage(logo_path, w-180, h-82, width=130, preserveAspectRatio=True, mask='auto')
    p.setLineWidth(1.5); p.line(50, h-90, w-50, h-90)

    # Date 위치 유지 (V7.8 반영분)
    p.setFont("Helvetica-Bold", 12); p.drawString(50, h-120, "[1] Project Information")
    p.setFont("Helvetica", 10.5)
    p.drawString(65, h-145, f"Date : {p_info['date']}")
    p.drawString(65, h-165, f"Project Name : {p_info['project']}")
    p.drawString(65, h-185, f"Customer : {p_info['customer']}")
    p.drawString(65, h-205, f"Engineer : {p_info['manager']}")

    p.setFont("Helvetica-Bold", 12); p.drawString(50, h-245, "[2] Design & Performance")
    p.setFont("Helvetica", 10.5)
    p.drawString(65, h-270, f"Selected Model : {model_data['model_name']}")
    p.drawString(65, h-290, f"Operating Speed : {model_data['rpm']} RPM")
    p.drawString(65, h-310, f"Design Flow : {d_point['cmh']:,} CMH / Design Pressure : {d_point['pa']:,} Pa")
    p.drawString(65, h-330, f"Absorbed Power : {model_data['power (kW)']} kW / Total Efficiency : {model_data['total efficiency (%)']}%")

    p.drawImage(ImageReader(chart_buf), 50, h-760, width=495, height=410)
    p.setFont("Helvetica-Oblique", 9); p.drawCentredString(w/2, 40, "- Page 1 -")
    
    p.showPage()
    # 2페이지 소음 분석 및 격자 표 (V7.8과 동일)
    p.setFont("Helvetica-Bold", 22); p.drawString(50, h-60, "Technical Selection Report")
    if os.path.exists(logo_path):
        p.drawImage(logo_path, w-180, h-82, width=130, preserveAspectRatio=True, mask='auto')
    p.setLineWidth(1.5); p.line(50, h-90, w-50, h-90)
    p.setFont("Helvetica-Bold", 12); p.drawString(50, h-120, "[3] Acoustic Analysis")
    p.drawImage(ImageReader(noise_buf), 50, h-450, width=495, height=280)
    # [표 생성 로직 중략]
    p.setFont("Helvetica-Oblique", 9); p.drawCentredString(w/2, 40, "- Page 2 -")
    p.showPage(); p.save(); buffer.seek(0)
    return buffer

# --- 메인 실행부 (Streamlit) ---
df = load_my_data()
if df is not None:
    # 헤더 구성 (V7.8 동일)
    header_col1, header_col2 = st.columns([1.2, 4])
    with header_col1:
        if os.path.exists("logo.png"):
            st.write("##"); st.image("logo.png", width=180)
    with header_col2:
        st.markdown("<h1 style='margin-top: 25px;'>루트에어 송풍기 선정 시스템 V7.9</h1>", unsafe_allow_html=True)
    
    st.divider()
    
    # [입력 및 실행 로직]
    # ... (V7.8의 입력을 따르되 서징 영역 포함된 차트 호출)