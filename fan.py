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
st.set_page_config(page_title="루트에어 송풍기 선정", layout="wide")

# 1. 상단 레이아웃
col_logo, col_title = st.columns([1, 4])
with col_logo:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=250)
    else:
        st.title("🏢")
with col_title:
    st.markdown("###")
    st.title("루트에어 송풍기 선정 프로그램")
    st.write("Root Air Fan Selection System V3.3")

# 2. 데이터 로드
def load_my_data():
    file_name = 'fan_data_filled.csv'
    if not os.path.exists(file_name):
        file_name = 'fan_data.csv'
        if not os.path.exists(file_name): return None
    try:
        df = pd.read_csv(file_name, encoding='utf-8-sig')
    except:
        df = pd.read_csv(file_name, encoding='cp949')
    return df

# 3. 성능 곡선 그래프 (서징 라인 포함)
def create_performance_chart(all_df, selected_model_name, user_cmh, user_pa):
    model_df = all_df[all_df['model_name'] == selected_model_name].sort_values(by=['rpm', 'CMH'])
    rpms = sorted(model_df['rpm'].unique())
    
    # 가시성이 좋은 뚜렷한 색상들
    distinct_colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    surging_x = []
    surging_y = []

    # 1. RPM별 정압 곡선 그리기
    for i, rpm in enumerate(rpms):
        rpm_data = model_df[model_df['rpm'] == rpm]
        color = distinct_colors[i % len(distinct_colors)]
        
        ax.plot(rpm_data['CMH'], rpm_data['Pa'], color=color, label=f'{rpm} rpm', linewidth=2)
        # 곡선 끝에 RPM 표시
        ax.text(rpm_data['CMH'].iloc[-1], rpm_data['Pa'].iloc[-1], f' {rpm}rpm', fontsize=9, color=color, va='center', fontweight='bold')
        
        # 서징 포인트 수집 (각 RPM 곡선의 가장 왼쪽 점)
        surging_x.append(rpm_data['CMH'].iloc[0])
        surging_y.append(rpm_data['Pa'].iloc[0])

    # 2. 서징 라인 (Surge Line) 추가
    ax.plot(surging_x, surging_y, color='red', linestyle='--', linewidth=2.5, label='Surge Line')
    ax.fill_betweenx(surging_y, 0, surging_x, color='red', alpha=0.1) # 서징 영역 색칠
    ax.text(surging_x[0], surging_y[0], '  SURGING ZONE', color='red', fontsize=10, fontweight='bold', va='bottom')

    # 3. 설계점(Design Point) 강조
    ax.scatter(user_cmh, user_pa, color='red', s=250, marker='*', label='Design Point', zorder=20)
    ax.axhline(user_pa, color='red', linestyle=':', linewidth=1, alpha=0.4)
    ax.axvline(user_cmh, color='red', linestyle=':', linewidth=1, alpha=0.4)

    ax.set_xlabel('Air Flow (CMH)', fontsize=12)
    ax.set_ylabel('Static Pressure (Pa)', fontsize=12)
    ax.set_title(f'Performance Curve with Surge Line: {selected_model_name}', fontsize=15, fontweight='bold')
    ax.legend(loc='upper right', fontsize='small')
    ax.grid(True, linestyle=':', alpha=0.6)
    
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=200)
    buf.seek(0)
    plt.close(fig)
    return buf

# 4. 소음 그래프 (V3.2 유지)
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
    
    max_val = max(plot_values) if plot_values else 0
    ax.set_ylim(0, max_val + 25)
    ax.set_ylabel('Sound Pressure Level (dB)', fontsize=12)
    ax.set_title('Octave Band Noise Spectrum', fontsize=15, fontweight='bold')
    ax.grid(axis='y', linestyle=':', alpha=0.7)
    
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 1, f'{int(height)}', ha='center', va='bottom', fontweight='bold')
    
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=200)
    buf.seek(0)
    plt.close(fig)
    return buf

# 5. PDF 생성 함수 (V3.2 레이아웃 유지)
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

def create_pdf(model_info, user_cmh, user_pa, perf_buf, noise_buf, project_info, noise_bands, total_col):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    
    # PAGE 1
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
    p.drawString(60, h - 215, f"- Model Name: {model_info['model_name']}")
    p.drawString(60, h - 235, f"- Operation RPM: {model_info['rpm']} rpm")
    p.drawString(60, h - 255, f"- Design Duty: {user_cmh} CMH @ {user_pa} Pa")
    p.drawString(60, h - 275, f"- Total Eff: {model_info['total efficiency (%)']}% / Static Eff: {model_info['static pressure efficiency (%)']}%")
    p.drawString(60, h - 295, f"- P fan: {model_info['power (kW)']} kW")
    
    p.drawImage(ImageReader(perf_buf), 50, h - 710, width=500, height=380)
    p.showPage()
    
    # PAGE 2
    if noise_buf:
        if os.path.exists("logo.png"):
            p.drawImage(ImageReader("logo.png"), w - 160, h - 60, width=110, height=35, preserveAspectRatio=True, mask='auto')
        p.setFont("Helvetica-Bold", 22)
        p.drawString(50, h - 50, "Acoustic Analysis Report")
        p.line(50, h - 65, 550, h - 65)
        
        p.setFont("Helvetica-Bold", 14)
        p.drawString(50, h - 100, "[2] Noise Data Table")
        headers = ['63Hz', '125Hz', '250Hz', '500Hz', '1kHz', '2kHz', '4kHz', '8kHz', 'Total']
        data_vals = [model_info[b] for b in noise_bands]
        data_vals.append(model_info[total_col])
        draw_table(p, 50, h - 150, headers, data_vals)
        p.drawImage(ImageReader(noise_buf), 50, h - 520, width=500, height=300)
        
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

# --- 메인 실행 ---
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
    u_cmh = c1.number_input("Flow (CMH)", value=120000)
    u_pa = c2.number_input("Pressure (Pa)", value=2400)

    matched = df[(df['CMH'] >= u_cmh) & (df['Pa'] >= u_pa)].copy()

    if not matched.empty:
        best = matched.sort_values(by=['CMH', 'Pa']).iloc[0]
        st.success(f"Best Match: **{best['model_name']}** (RPM: {best['rpm']})")
        
        st.info(f"✨ Total Eff: **{best['total efficiency (%)']}%** | Static Eff: **{best['static pressure efficiency (%)']}%**")
        
        # V3.3: 서징 라인이 포함된 성능 곡선
        perf_img = create_performance_chart(df, best['model_name'], u_cmh, u_pa)
        st.image(perf_img, caption="Performance Curve with Surge Line")
        
        # 소음 처리 (V3.2 형식 유지)
        noise_bands = [f'{hz}(dB / dB(A))' for hz in ['63Hz', '125Hz', '250Hz', '500Hz', '1kHz', '2kHz', '4kHz', '8kHz']]
        total_col = 'Total_dB / dB(A)'
        noise_img = create_noise_chart(best, noise_bands)
        
        st.image(noise_img, caption="Noise Analysis")

        proj_info = {"project": p_name, "customer": c_name, "manager": m_name, "date": p_date.strftime("%Y-%m-%d")}
        pdf_data = create_pdf(best, u_cmh, u_pa, perf_img, noise_img, proj_info, noise_bands, total_col)
        st.download_button("📥 Download Technical Report (V3.3 PDF)", pdf_data, f"Report_{p_name}.pdf")
    else:
        st.warning("No matching model found.")