import streamlit as st
import pandas as pd
import os
import matplotlib.pyplot as plt
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from io import BytesIO
import numpy as np
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="루트에어 선정 시스템 V6.6", layout="wide")

# 1. 상단 레이아웃
col_logo, col_title = st.columns([1, 4])
with col_logo:
    if os.path.exists("logo.png"): st.image("logo.png", width=250)
    else: st.title("🏢")
with col_title:
    st.title("루트에어 송풍기 선정 시스템 V6.6")
    st.write("Final Integrated Solution: Performance Map, System Curve & Noise Analysis")

# 2. 데이터 로드
def load_my_data():
    file_name = 'fan_performance_map_full_sample.csv' # 또는 사용자님의 파일명
    if not os.path.exists(file_name): return None
    try: df = pd.read_csv(file_name, encoding='utf-8-sig')
    except: df = pd.read_csv(file_name, encoding='cp949')
    return df

# 3. 메인 그래프 생성: (0,0) 시작 저항 곡선 + 선명한 RPM 맵
def create_master_chart(all_df, selected_model, user_cmh, user_pa):
    model_df = all_df[all_df['model_name'] == selected_model].sort_values(by=['rpm', 'CMH'])
    rpms = sorted(model_df['rpm'].unique())
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # RPM 곡선 선명도 (V6.5 기준 유지)
    for rpm in rpms:
        data = model_df[model_df['rpm'] == rpm]
        ax.plot(data['CMH'], data['Pa'], color='steelblue', linewidth=1.2, alpha=0.5, zorder=1)
        ax.text(data['CMH'].iloc[-1], data['Pa'].iloc[-1], f' {int(rpm)} RPM', 
                color='steelblue', fontsize=9, va='center', fontweight='bold', alpha=0.7)

    # 서징 라인
    surge_x = [model_df[model_df['rpm'] == r]['CMH'].iloc[0] for r in rpms]
    surge_y = [model_df[model_df['rpm'] == r]['Pa'].iloc[0] for r in rpms]
    ax.plot(surge_x, surge_y, 'r--', linewidth=2.5, label='Surge Line', zorder=5)
    ax.fill_betweenx(surge_y, 0, surge_x, color='red', alpha=0.07, zorder=0)

    # 시스템 저항 곡선: (0,0)에서 설계점까지 포물선
    x_path = np.linspace(0, user_cmh, 100) 
    k = user_pa / (user_cmh**2) if user_cmh != 0 else 0
    y_path = k * (x_path**2)
    ax.plot(x_path, y_path, color='#1f77b4', linewidth=4.5, alpha=1.0, zorder=20, label='System Resistance Curve')

    # 설계 지점 가이드 (붉은 십자선 + 포인트)
    ax.axvline(user_cmh, color='red', linestyle='-', linewidth=1.5, alpha=0.6, zorder=15)
    ax.axhline(user_pa, color='red', linestyle='-', linewidth=1.5, alpha=0.6, zorder=15)
    ax.scatter(user_cmh, user_pa, color='red', s=200, edgecolors='white', marker='o', linewidths=2, zorder=30, label='Design Point')

    # 축 범위 및 설정
    x_limit = max(user_cmh * 1.5, model_df['CMH'].max() * 1.1)
    y_limit = max(user_pa * 1.5, model_df['Pa'].max() * 1.1)
    ax.set_xlim(0, x_limit); ax.set_ylim(0, y_limit)
    ax.set_xlabel('Air Flow (CMH)', fontweight='bold', fontsize=12)
    ax.set_ylabel('Static Pressure (Pa)', fontweight='bold', fontsize=12)
    ax.set_title(f"Performance Map: {selected_model}", fontsize=18, fontweight='bold', pad=25)
    ax.grid(True, linestyle=':', alpha=0.5)
    ax.legend(loc='upper right', frameon=True, shadow=True)
    
    plt.tight_layout()
    buf = BytesIO(); plt.savefig(buf, format='png', dpi=200); buf.seek(0); plt.close(fig)
    return buf

# 4. 소음 분석 차트 생성
def create_noise_chart(noise_row):
    bands = ['63', '125', '250', '500', '1k', '2k', '4k', '8k']
    plot_values = []
    for b in bands:
        col = [c for c in noise_row.index if b in c][0]
        val = str(noise_row[col]).split('/')[0].strip().replace('dB', '')
        plot_values.append(float(val))
    
    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(bands, plot_values, color='skyblue', edgecolor='navy', alpha=0.8)
    ax.set_ylim(0, max(plot_values) + 20)
    ax.set_title('Octave Band Noise Analysis (dB)', fontsize=14, fontweight='bold')
    for bar in bars:
        ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 1, f'{int(bar.get_height())}', ha='center', va='bottom', fontweight='bold')
    
    buf = BytesIO(); plt.savefig(buf, format='png', dpi=150); buf.seek(0); plt.close(fig)
    return buf

# 5. PDF 리포트 생성 (통합 그래프 + 소음 그래프 포함)
def create_pdf(project_info, chart_buf, noise_buf, model_data):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    
    # 헤더
    p.setFont("Helvetica-Bold", 22); p.drawString(50, h-60, "Technical Selection Report")
    p.setFont("Helvetica", 12)
    p.drawString(50, h-90, f"Project: {project_info['project']} | Customer: {project_info['customer']}")
    p.drawString(50, h-105, f"Model: {model_data['model_name']} | Date: {project_info['date']}")
    
    # 메인 그래프 삽입
    p.drawImage(ImageReader(chart_buf), 40, h-500, width=520, height=380)
    
    # 소음 그래프 삽입 (하단)
    if noise_buf:
        p.drawImage(ImageReader(noise_buf), 50, h-780, width=500, height=250)
        
    p.showPage(); p.save(); buffer.seek(0)
    return buffer

# --- 메인 실행부 ---
df = load_my_data()
if df is not None:
    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    p_name = c1.text_input("Project Name", value="RouteAir_Project_01")
    c_name = c2.text_input("Customer", value="General_Client")
    m_name = c3.text_input("Manager", value="Manager_Lee")
    p_date = c4.date_input("Date", datetime.now())

    st.subheader("🎯 Design Duty & Model Selection")
    col1, col2, col3 = st.columns(3)
    u_cmh = col1.number_input("Design Flow (CMH)", value=115000)
    u_pa = col2.number_input("Design Pressure (Pa)", value=2100)
    selected_model = col3.selectbox("Select Fan Model", df['model_name'].unique())
    
    # 매칭 데이터 찾기
    model_rows = df[df['model_name'] == selected_model]
    best_row = model_rows.iloc[0] # 선정 로직에 따른 대표 행
    
    # 그래프 생성
    master_chart = create_master_chart(df, selected_model, u_cmh, u_pa)
    st.image(master_chart)
    
    noise_chart = create_noise_chart(best_row)
    st.image(noise_chart)
    
    # PDF 준비 및 다운로드
    p_info = {"project": p_name, "customer": c_name, "manager": m_name, "date": p_date.strftime("%Y-%m-%d")}
    pdf_file = create_pdf(p_info, master_chart, noise_chart, best_row)
    
    st.download_button(
        label="📥 Download Technical Report (PDF)",
        data=pdf_file,
        file_name=f"Report_{p_name}.pdf",
        mime="application/pdf"
    )