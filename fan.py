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
    st.title("루트에어 송풍기 선정 시스템 V4.5")
    st.write("Professional Report + Comprehensive Performance Map")

# 2. 데이터 로드 (연습용 샘플 파일)
def load_my_data():
    file_name = 'fan_performance_map_sample.csv' # 연습용 데이터
    if not os.path.exists(file_name):
        return None
    try:
        df = pd.read_csv(file_name, encoding='utf-8-sig')
    except:
        df = pd.read_csv(file_name, encoding='cp949')
    return df

# 3. 종합 성능 맵 생성 함수 (V4.2 스타일)
def create_combined_chart(all_df, selected_model, user_cmh, user_pa):
    model_df = all_df[all_df['model_name'] == selected_model].sort_values(by=['rpm', 'CMH'])
    rpms = sorted(model_df['rpm'].unique())
    
    fig, ax1 = plt.subplots(figsize=(12, 8))
    ax2 = ax1.twinx()
    
    # 가시성 좋은 차별화된 색상 리스트
    distinct_colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
    
    surge_x, surge_y = [], []

    # 1. RPM별 정압 곡선 그리기
    for i, rpm in enumerate(rpms):
        data = model_df[model_df['rpm'] == rpm]
        color = distinct_colors[i % len(distinct_colors)]
        ax1.plot(data['CMH'], data['Pa'], color=color, label=f'{rpm} rpm', linewidth=2)
        
        # 서징 포인트 수집
        surge_x.append(data['CMH'].iloc[0])
        surge_y.append(data['Pa'].iloc[0])
        
        # 곡선 끝 RPM 표시
        ax1.text(data['CMH'].iloc[-1], data['Pa'].iloc[-1], f' {rpm}', color=color, fontsize=9, va='center', fontweight='bold')

    # 2. 서징 라인 (Surge Line)
    ax1.plot(surge_x, surge_y, 'r--', linewidth=2.5, label='Surge Line')
    ax1.fill_betweenx(surge_y, 0, surge_x, color='red', alpha=0.05)
    ax1.text(surge_x[0], surge_y[0], '  SURGE LINE', color='red', fontweight='bold', va='bottom')

    # 3. 효율 및 동력 (최고 RPM 기준 샘플 표시)
    max_rpm_data = model_df[model_df['rpm'] == max(rpms)]
    ax2.plot(max_rpm_data['CMH'], max_rpm_data['total efficiency (%)'], 'g:', label='Efficiency (%)', alpha=0.6)
    ax2.plot(max_rpm_data['CMH'], max_rpm_data['power (kW)'], 'm-.', label='Power (kW)', alpha=0.6)

    # 4. 설계점(Design Point)
    ax1.scatter(user_cmh, user_pa, color='red', s=250, marker='*', zorder=30, label='Design Point')
    ax1.axhline(user_pa, color='red', linestyle=':', alpha=0.3)
    ax1.axvline(user_cmh, color='red', linestyle=':', alpha=0.3)

    ax1.set_xlabel('Air Flow (CMH)', fontsize=12)
    ax1.set_ylabel('Static Pressure (Pa)', fontsize=12)
    ax2.set_ylabel('Efficiency (%) / Power (kW)', fontsize=12, color='darkgreen')
    ax1.set_title(f'Comprehensive Performance Map: {selected_model}', fontsize=16, fontweight='bold')
    
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

# 4. 소음 그래프 (V3.2 형식 유지)
def create_noise_chart(noise_row, bands):
    plot_values = []
    for b in bands:
        val = str(noise_row[b])
        first_val = val.split('/')[0].strip()
        try: plot_values.append(float(first_val))
        except: plot_values.append(0.0)
    display_labels = ['63', '125', '250', '500', '1k', '2k', '4k', '8k']
    fig, ax = plt.subplots(figsize=(12, 6))
    bars = ax.bar(display_labels, plot_values, color='skyblue', edgecolor='navy', alpha=0.8)
    ax.set_ylim(0, max(plot_values) + 25 if plot_values else 100)
    ax.set_title('Octave Band Noise Spectrum', fontsize=15, fontweight='bold')
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 1, f'{int(height)}', ha='center', va='bottom', fontweight='bold')
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=200)
    buf.seek(0)
    plt.close(fig)
    return buf

# 5. PDF 생성 함수 (V3.2 레이아웃 + V4.2 그래프)
def draw_table(p, x, y, headers, data):
    cell_width = 54
    cell_height = 25
    p.setFont("Helvetica-Bold", 8)
    for i, header in enumerate(headers):
        p.rect(x + (i * cell_width), y, cell_width, cell_height, stroke=1, fill=0)
        p.drawCentredString(x + (i * cell_width) + cell_width/2, y + 8, header)
    p.setFont("Helvetica", 8)
    for i, val in enumerate(data):
        p.rect(x + (i * cell_width), y - cell_height, cell_width, cell_height, stroke=1, fill=0)
        p.drawCentredString(x + (i * cell_width) + cell_width/2, y - cell_height + 8, str(val))

def create_pdf(model_info, user_cmh, user_pa, combined_buf, noise_buf, project_info, noise_bands, total_col):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    if os.path.exists("logo.png"):
        p.drawImage(ImageReader("logo.png"), w - 160, h - 60, width=110, height=35, preserveAspectRatio=True, mask='auto')
    
    p.setFont("Helvetica-Bold", 22)
    p.drawString(50, h - 50, "Technical Selection Report")
    p.line(50, h - 65, 550, h - 65)
    
    p.setFont("Helvetica", 11)
    p.drawString(50, h - 90, f"Project: {project_info['project']}")
    p.drawString(50, h - 110, f"Customer: {project_info['customer']}")
    p.drawString(50, h - 130, f"Prepared by: {project_info['manager']}")
    p.drawString(50, h - 150, f"Date: {project_info['date']}")
    
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, h - 190, "[1] Technical Specifications")
    p.setFont("Helvetica", 12)
    p.drawString(60, h - 215, f"- Model: {model_info['model_name']}")
    p.drawString(60, h - 235, f"- Duty: {user_cmh} CMH @ {user_pa} Pa")
    
    # 종합 그래프 삽입 (크게)
    p.drawImage(ImageReader(combined_buf), 50, h - 700, width=500, height=380)
    p.showPage()
    
    if noise_buf:
        if os.path.exists("logo.png"):
            p.drawImage(ImageReader("logo.png"), w - 160, h - 60, width=110, height=35, preserveAspectRatio=True, mask='auto')
        p.setFont("Helvetica-Bold", 22)
        p.drawString(50, h - 50, "Acoustic Analysis Report")
        p.line(50, h - 65, 550, h - 65)
        headers = ['63Hz', '125Hz', '250Hz', '500Hz', '1kHz', '2kHz', '4kHz', '8kHz', 'Total']
        data_vals = [model_info[b] for b in noise_bands]
        data_vals.append(model_info[total_col])
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
    st.subheader("📋 Project Information")
    c1, c2, c3, c4 = st.columns(4)
    p_name = c1.text_input("Project Name", "P4 Project")
    c_name = c2.text_input("Customer", "K-ENSOL")
    m_name = c3.text_input("Manager", "J.H. KIM")
    p_date = c4.date_input("Date", datetime.now())

    st.subheader("🔍 Selection Conditions")
    c1, c2 = st.columns(2)
    u_cmh = c1.number_input("Flow (CMH)", value=115000)
    u_pa = c2.number_input("Pressure (Pa)", value=2100)

    # 샘플 데이터 내 모델 선택
    models = df['model_name'].unique()
    selected_model = st.selectbox("Model Select", models)
    
    # 종합 성능 맵 생성
    combined_img = create_combined_chart(df, selected_model, u_cmh, u_pa)
    st.image(combined_img, caption="Professional Performance Map (V4.5)")
    
    # 소음 데이터 (첫 번째 행 샘플 사용)
    best = df.iloc[0] 
    noise_bands = [f'{hz}(dB / dB(A))' for hz in ['63Hz', '125Hz', '250Hz', '500Hz', '1kHz', '2kHz', '4kHz', '8kHz']]
    total_col = 'Total_dB / dB(A)'
    noise_img = create_noise_chart(best, noise_bands)
    st.image(noise_img, caption="Noise Analysis")

    proj_info = {"project": p_name, "customer": c_name, "manager": m_name, "date": p_date.strftime("%Y-%m-%d")}
    pdf_data = create_pdf(best, u_cmh, u_pa, combined_img, noise_img, proj_info, noise_bands, total_col)
    st.download_button("📥 Download Final Report (V4.5)", pdf_data, f"Report_{p_name}.pdf")
else:
    st.error("연습용 데이터 파일(`fan_performance_map_sample.csv`)을 찾을 수 없습니다.")