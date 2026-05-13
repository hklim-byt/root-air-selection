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
st.set_page_config(page_title="루트에어 종합 선정 시스템", layout="wide")

# 1. 상단 레이아웃
col_logo, col_title = st.columns([1, 4])
with col_logo:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=250)
    else:
        st.title("🏢")
with col_title:
    st.markdown("###")
    st.title("루트에어 종합 선정 시스템 V4.7")
    st.write("Full Performance Map + Octave Noise Analysis")

# 2. 데이터 로드 (소음 포함 새 샘플 파일)
def load_my_data():
    file_name = 'fan_performance_map_full_sample.csv'
    if not os.path.exists(file_name):
        return None
    try:
        df = pd.read_csv(file_name, encoding='utf-8-sig')
    except:
        df = pd.read_csv(file_name, encoding='cp949')
    return df

# 3. 종합 성능 맵 생성
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
    ax1.set_xlabel('Air Flow (CMH)')
    ax1.set_ylabel('Static Pressure (Pa)')
    
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

# 4. 소음 그래프 (V4.6 방식 계승)
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

# 5. PDF 생성 (표 및 로고 포함)
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
    
    p.setFont("Helvetica-Bold", 20)
    p.drawString(50, h - 50, "Technical Selection Report")
    p.line(50, h - 65, 550, h - 65)
    p.setFont("Helvetica", 10)
    p.drawString(50, h - 85, f"Project: {project_info['project']} | Customer: {project_info['customer']}")
    p.drawString(50, h - 100, f"Engineer: {project_info['manager']} | Date: {project_info['date']}")
    
    p.drawImage(ImageReader(combined_buf), 50, h - 650, width=500, height=400)
    p.showPage()
    
    if noise_buf:
        if os.path.exists("logo.png"):
            p.drawImage(ImageReader("logo.png"), w - 160, h - 60, width=110, height=35, preserveAspectRatio=True, mask='auto')
        p.setFont("Helvetica-Bold", 20)
        p.drawString(50, h - 50, "Acoustic Analysis Report")
        p.line(50, h - 65, 550, h - 65)
        
        # 소음 테이블 데이터 준비
        bands_labels = ['63Hz', '125Hz', '250Hz', '500Hz', '1kHz', '2kHz', '4kHz', '8kHz']
        headers = bands_labels + ['Total']
        data_vals = []
        for lbl in bands_labels:
            col = [c for c in model_info.index if lbl in c]
            data_vals.append(model_info[col[0]] if col else "-")
        total_col = [c for c in model_info.index if 'Total' in c]
        data_vals.append(model_info[total_col[0]] if total_col else "-")
        
        draw_table(p, 50, h - 150, headers, data_vals)
        p.drawImage(ImageReader(noise_buf), 50, h - 520, width=500, height=300)
        
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

# --- 메인 실행부 ---
df = load_my_data()
if df is not None:
    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    p_name = c1.text_input("Project Name", "Full Sample Project")
    c_name = c2.text_input("Customer", "K-ENSOL")
    m_name = c3.text_input("Manager", "J.H. KIM")
    p_date = c4.date_input("Date", datetime.now())

    c1, c2 = st.columns(2)
    u_cmh = c1.number_input("Design Flow (CMH)", value=115000)
    u_pa = c2.number_input("Design Pressure (Pa)", value=2100)

    selected_model = st.selectbox("Model Select", df['model_name'].unique())
    
    combined_img = create_combined_chart(df, selected_model, u_cmh, u_pa)
    st.image(combined_img, caption="V4.7 Comprehensive Performance Map")
    
    # 선택된 모델의 첫 행(RPM) 소음 데이터로 분석
    best_row = df[df['model_name'] == selected_model].iloc[0]
    noise_img = create_noise_chart(best_row)
    if noise_img:
        st.image(noise_img, caption="Acoustic Spectrum")

    proj_info = {"project": p_name, "customer": c_name, "manager": m_name, "date": p_date.strftime("%Y-%m-%d")}
    pdf_data = create_pdf(best_row, u_cmh, u_pa, combined_img, noise_img, proj_info)
    st.download_button("📥 Download Technical Report (V4.7)", pdf_data, f"Report_{p_name}.pdf")
else:
    st.error("새 샘플 파일(`fan_performance_map_full_sample.csv`)을 찾을 수 없습니다.")