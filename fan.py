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
st.set_page_config(page_title="루트에어 종합 선정 시스템 V5.0", layout="wide")

# 1. 상단 레이아웃
col_logo, col_title = st.columns([1, 4])
with col_logo:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=250)
    else:
        st.title("🏢")
with col_title:
    st.markdown("###")
    st.title("루트에어 송풍기 선정 시스템 V5.0")
    st.write("Professional Hybrid Version (V3.2 Layout + V4.7 Map)")

# 2. 데이터 로드
def load_my_data():
    file_name = 'fan_performance_map_full_sample.csv'
    if not os.path.exists(file_name):
        file_name = 'fan_data_filled.csv' # 백업 파일명
        if not os.path.exists(file_name): return None
    try:
        df = pd.read_csv(file_name, encoding='utf-8-sig')
    except:
        df = pd.read_csv(file_name, encoding='cp949')
    return df

# 3. 종합 성능 맵 생성 (V4.7 기반)
def create_combined_chart(all_df, selected_model, user_cmh, user_pa):
    model_df = all_df[all_df['model_name'] == selected_model].sort_values(by=['rpm', 'CMH'])
    rpms = sorted(model_df['rpm'].unique())
    
    fig, ax1 = plt.subplots(figsize=(12, 8))
    ax2 = ax1.twinx()
    
    distinct_colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
    surge_x, surge_y = [], []

    for i, rpm in enumerate(rpms):
        data = model_df[model_df['rpm'] == rpm]
        color = distinct_colors[i % len(distinct_colors)]
        ax1.plot(data['CMH'], data['Pa'], color=color, label=f'{rpm} rpm', linewidth=2)
        surge_x.append(data['CMH'].iloc[0])
        surge_y.append(data['Pa'].iloc[0])
        ax1.text(data['CMH'].iloc[-1], data['Pa'].iloc[-1], f' {rpm}', color=color, fontsize=9, va='center', fontweight='bold')

    ax1.plot(surge_x, surge_y, 'r--', linewidth=2.5, label='Surge Line')
    ax1.fill_betweenx(surge_y, 0, surge_x, color='red', alpha=0.05)
    
    max_rpm_data = model_df[model_df['rpm'] == max(rpms)]
    ax2.plot(max_rpm_data['CMH'], max_rpm_data['total efficiency (%)'], 'g:', label='Eff (%)', alpha=0.5)
    ax2.plot(max_rpm_data['CMH'], max_rpm_data['power (kW)'], 'm-.', label='kW', alpha=0.5)

    ax1.scatter(user_cmh, user_pa, color='red', s=250, marker='*', zorder=30, label='Design Point')
    ax1.set_xlabel('Air Flow (CMH)', fontsize=12)
    ax1.set_ylabel('Static Pressure (Pa)', fontsize=12)
    
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc='upper right', fontsize='small')
    ax1.grid(True, linestyle=':', alpha=0.6)
    
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=200)
    buf.seek(0)
    plt.close(fig)
    return buf

# 4. 소음 그래프
def create_noise_chart(noise_row):
    bands_labels = ['63', '125', '250', '500', '1k', '2k', '4k', '8k']
    plot_values = []
    found_labels = []
    
    for lbl in bands_labels:
        target_col = [c for c in noise_row.index if lbl in c]
        if target_col:
            val = str(noise_row[target_col[0]])
            first_val = val.split('/')[0].strip().replace('dB', '').strip()
            try:
                plot_values.append(float(first_val))
                found_labels.append(lbl)
            except: pass

    if not plot_values: return None
    
    fig, ax = plt.subplots(figsize=(12, 6))
    bars = ax.bar(found_labels, plot_values, color='skyblue', edgecolor='navy', alpha=0.8)
    ax.set_ylim(0, max(plot_values) + 25)
    ax.set_title('Octave Band Noise Analysis', fontsize=15, fontweight='bold')
    for bar in bars:
        ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 1, f'{int(bar.get_height())}', ha='center', va='bottom', fontweight='bold')
    
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=200)
    buf.seek(0)
    plt.close(fig)
    return buf

# 5. PDF 생성 함수 (V3.2 레이아웃 스타일 복구)
def draw_table(p, x, y, headers, data):
    cell_width = 54
    cell_height = 25
    p.setFont("Helvetica-Bold", 8)
    for i, h in enumerate(headers):
        p.rect(x + (i * cell_width), y, cell_width, cell_height)
        p.drawCentredString(x + (i * cell_width) + cell_width/2, y + 8, h)
    p.setFont("Helvetica", 8)
    for i, v in enumerate(data):
        p.rect(x + (i * cell_width), y - cell_height, cell_width, cell_height)
        p.drawCentredString(x + (i * cell_width) + cell_width/2, y - cell_height + 8, str(v))

def create_pdf(model_info, user_cmh, user_pa, combined_buf, noise_buf, project_info):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    if os.path.exists("logo.png"):
        p.drawImage(ImageReader("logo.png"), w - 160, h - 60, width=110, height=35, preserveAspectRatio=True, mask='auto')
    
    p.setFont("Helvetica-Bold", 22)
    p.drawString(50, h - 50, "Technical Selection Report")
    p.line(50, h - 65, 550, h - 65)
    
    # 상단 프로젝트 정보
    p.setFont("Helvetica", 11)
    p.drawString(50, h - 90, f"Project: {project_info['project']}")
    p.drawString(50, h - 105, f"Customer: {project_info['customer']}")
    p.drawString(50, h - 120, f"Engineer: {project_info['manager']}")
    p.drawString(50, h - 135, f"Date: {project_info['date']}")
    
    # [복구] V3.2 스타일 기술 사양 섹션
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, h - 170, "[1] Technical Specifications")
    p.setFont("Helvetica", 12)
    p.drawString(60, h - 195, f"- Model Name: {model_info['model_name']}")
    p.drawString(60, h - 215, f"- Operation RPM: {model_info['rpm']} rpm")
    p.drawString(60, h - 235, f"- Design Duty: {user_cmh} CMH @ {user_pa} Pa")
    
    eff_total = model_info['total efficiency (%)'] if 'total efficiency (%)' in model_info else "-"
    eff_static = model_info['static pressure efficiency (%)'] if 'static pressure efficiency (%)' in model_info else "-"
    p.drawString(60, h - 255, f"- Total Efficiency: {eff_total} % / Static Efficiency: {eff_static} %")
    p.drawString(60, h - 275, f"- P fan: {model_info['power (kW)']} kW")
    
    # 종합 그래프 삽입 (위치 조정하여 상단 텍스트와 겹치지 않게 함)
    p.drawImage(ImageReader(combined_buf), 40, h - 710, width=520, height=420)
    p.showPage()
    
    # 2페이지 (소음 분석)
    if noise_buf:
        if os.path.exists("logo.png"):
            p.drawImage(ImageReader("logo.png"), w - 160, h - 60, width=110, height=35, preserveAspectRatio=True, mask='auto')
        p.setFont("Helvetica-Bold", 22)
        p.drawString(50, h - 50, "Acoustic Analysis Report")
        p.line(50, h - 65, 550, h - 65)
        
        p.setFont("Helvetica-Bold", 14)
        p.drawString(50, h - 100, "[2] Noise Data Summary")
        
        # 소음 테이블 헤더 및 데이터
        bands_labels = ['63Hz', '125Hz', '250Hz', '500Hz', '1kHz', '2kHz', '4kHz', '8kHz']
        headers = bands_labels + ['Total']
        data_vals = []
        for lbl in bands_labels:
            col = [c for c in model_info.index if lbl in c]
            data_vals.append(model_info[col[0]] if col else "-")
        total_col = [c for c in model_info.index if 'Total' in c]
        data_vals.append(model_info[total_col[0]] if total_col else "-")
        
        draw_table(p, 50, h - 150, headers, data_vals)
        p.drawImage(ImageReader(noise_buf), 50, h - 500, width=500, height=300)
        
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

# --- 메인 실행부 ---
df = load_my_data()
if df is not None:
    st.divider()
    st.subheader("📋 Project Information")
    c1, c2, c3, c4 = st.columns(4)
    # [수정] Placeholder 문구 추가 (회색 안내 텍스트)
    p_name = c1.text_input("Project Name", placeholder="English Only")
    c_name = c2.text_input("Customer", placeholder="English Only")
    m_name = c3.text_input("Manager", placeholder="English Only")
    p_date = c4.date_input("Date", datetime.now())

    st.subheader("🔍 Selection Conditions")
    c1, c2 = st.columns(2)
    u_cmh = c1.number_input("Design Flow (CMH)", value=115000)
    u_pa = c2.number_input("Design Pressure (Pa)", value=2100)

    selected_model = st.selectbox("Model Select", df['model_name'].unique())
    
    # 맵 생성 및 화면 표시
    combined_img = create_combined_chart(df, selected_model, u_cmh, u_pa)
    st.image(combined_img, caption="Comprehensive Performance Map")
    
    # 소음 분석 화면 표시
    best_row = df[df['model_name'] == selected_model].iloc[0]
    noise_img = create_noise_chart(best_row)
    if noise_img:
        st.image(noise_img, caption="Noise Spectrum Analysis")

    # PDF 생성용 정보 구성
    proj_info = {
        "project": p_name if p_name else "N/A",
        "customer": c_name if c_name else "N/A",
        "manager": m_name if m_name else "N/A",
        "date": p_date.strftime("%Y-%m-%d")
    }
    
    # [복구된 레이아웃] PDF 다운로드 버튼
    pdf_data = create_pdf(best_row, u_cmh, u_pa, combined_img, noise_img, proj_info)
    st.download_button("📥 Download Final Technical Report (V5.0)", pdf_data, f"Report_{p_name}.pdf")
else:
    st.error("데이터 파일을 찾을 수 없습니다.")