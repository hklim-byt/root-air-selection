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
    st.write("Root Air Fan Selection System V2.5")

# 2. 데이터 로드
def load_my_data():
    file_name = 'fan_data.csv'
    if not os.path.exists(file_name): return None
    try:
        df = pd.read_csv(file_name, encoding='utf-8-sig')
    except:
        df = pd.read_csv(file_name, encoding='cp949')
    return df

# 3. 성능 곡선 그래프
def create_performance_chart(all_df, user_cmh, user_pa):
    fig, ax = plt.subplots(figsize=(12, 8))
    unique_models = all_df.iloc[:, 0].unique()
    for model in unique_models:
        model_data = all_df[all_df.iloc[:, 0] == model].sort_values(by=all_df.columns[3])
        ax.plot(model_data.iloc[:, 3], model_data.iloc[:, 5], marker='o', markersize=4, label=model, linewidth=2)
    
    ax.scatter(user_cmh, user_pa, color='red', s=200, label='Design Point', zorder=10)
    ax.axhline(user_pa, color='red', linestyle='--', linewidth=1.5, alpha=0.6)
    ax.axvline(user_cmh, color='red', linestyle='--', linewidth=1.5, alpha=0.6)
    ax.set_xlabel('Air Flow (CMH)', fontsize=12)
    ax.set_ylabel('Static Pressure (Pa)', fontsize=12)
    ax.set_title('Fan Performance Curve', fontsize=15, fontweight='bold')
    ax.grid(True, linestyle=':', alpha=0.7)
    ax.legend(fontsize='medium')
    
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=200)
    buf.seek(0)
    plt.close(fig)
    return buf

# 4. 소음 스펙트럼 그래프 (복합 텍스트 처리)
def create_noise_chart(noise_row, bands):
    plot_values = []
    for b in bands:
        val = str(noise_row[b])
        # "85 / 82" 같은 형식이면 앞의 숫자(85)만 가져와서 그래프를 그립니다.
        first_val = val.split('/')[0].strip().replace('dB(A)', '').replace('dB', '').strip()
        try:
            plot_values.append(float(first_val))
        except:
            plot_values.append(0.0)
    
    display_labels = ['63', '125', '250', '500', '1k', '2k', '4k', '8k']
    
    fig, ax = plt.subplots(figsize=(12, 6))
    bars = ax.bar(display_labels, plot_values, color='skyblue', edgecolor='navy', alpha=0.8)
    
    max_val = max(plot_values) if plot_values else 0
    ax.set_ylim(0, max_val + 25)
    ax.set_ylabel('Sound Pressure Level (dB)', fontsize=12)
    ax.set_title(f'Noise Spectrum Analysis', fontsize=15, fontweight='bold')
    ax.grid(axis='y', linestyle=':', alpha=0.7)
    
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 1, f'{int(height)}', ha='center', va='bottom', fontweight='bold')
    
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=200)
    buf.seek(0)
    plt.close(fig)
    return buf

# 5. PDF 생성 함수 (표 형식 개선)
def draw_table(p, x, y, headers, data):
    cell_width = 54
    cell_height = 25 # 높이 약간 확대
    
    p.setFont("Helvetica-Bold", 8) # 글자 크기 조정
    for i, header in enumerate(headers):
        p.rect(x + (i * cell_width), y, cell_width, cell_height, stroke=1, fill=0)
        p.drawCentredString(x + (i * cell_width) + cell_width/2, y + 8, header)
    
    p.setFont("Helvetica", 9)
    for i, val in enumerate(data):
        p.rect(x + (i * cell_width), y - cell_height, cell_width, cell_height, stroke=1, fill=0)
        p.drawCentredString(x + (i * cell_width) + cell_width/2, y - cell_height + 8, str(val))

def create_pdf(model_info, user_cmh, user_pa, perf_buf, noise_buf, project_info, noise_bands, total_col):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    
    # PAGE 1
    p.setFont("Helvetica-Bold", 22)
    p.drawString(50, h - 50, "Technical Selection Report")
    p.line(50, h - 65, 550, h - 65)
    
    p.setFont("Helvetica", 11)
    p.drawString(50, h - 90, f"Project: {project_info['project']}")
    p.drawString(50, h - 110, f"Customer: {project_info['customer']}")
    p.drawString(50, h - 130, f"Prepared by: {project_info['manager']}")
    
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, h - 170, "[1] Technical Specifications")
    p.setFont("Helvetica", 12)
    p.drawString(60, h - 195, f"- Model Name: {model_info.iloc[0]}")
    p.drawString(60, h - 215, f"- Operation RPM: {model_info.iloc[1]} rpm")
    p.drawString(60, h - 235, f"- Design Point: {user_cmh} CMH @ {user_pa} Pa")
    p.drawString(60, h - 255, f"- Motor Power: {model_info.iloc[6]} kW")
    
    p.drawImage(ImageReader(perf_buf), 50, h - 680, width=500, height=380)
    p.showPage()
    
    # PAGE 2
    if noise_buf:
        p.setFont("Helvetica-Bold", 22)
        p.drawString(50, h - 50, "Acoustic Analysis Report")
        p.line(50, h - 65, 550, h - 65)
        
        p.setFont("Helvetica-Bold", 14)
        p.drawString(50, h - 100, "[2] Noise Data Table (dB / dB(A))")
        
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
    c1, c2, c3 = st.columns(3)
    p_name = c1.text_input("Project Name", placeholder="English Only")
    c_name = c2.text_input("Customer", placeholder="English Only")
    m_name = c3.text_input("Manager", placeholder="English Only")
    
    u_cmh = st.number_input("Flow (CMH)", value=120000, step=1000)
    u_pa = st.number_input("Pressure (Pa)", value=2400, step=10)

    matched = df[(df.iloc[:, 3] >= u_cmh) & (df.iloc[:, 5] >= u_pa)].copy()

    if not matched.empty:
        best = matched.sort_values(by=[df.columns[3], df.columns[5]]).iloc[0]
        st.success(f"Best Match: **{best.iloc[0]}** (RPM: {best.iloc[1]})")
        
        perf_img = create_performance_chart(df, u_cmh, u_pa)
        
        # 바뀐 컬럼 이름 설정
        noise_bands = [f'{hz}(dB / dB(A))' for hz in ['63Hz', '125Hz', '250Hz', '500Hz', '1kHz', '2kHz', '4kHz', '8kHz']]
        total_col = 'Total_dB / dB(A)'
        has_noise = all(b in df.columns for b in noise_bands) and total_col in df.columns
        
        st.image(perf_img, caption="Performance Curve")
        
        noise_img = None
        if has_noise:
            noise_img = create_noise_chart(best, noise_bands)
            st.image(noise_img, caption="Noise Spectrum")
            st.info(f"🔊 **Total Noise Level: {best[total_col]}**")

        proj_info = {"project": p_name, "customer": c_name, "manager": m_name}
        pdf_data = create_pdf(best, u_cmh, u_pa, perf_img, noise_img, proj_info, noise_bands, total_col)
        st.download_button("📥 Download Technical Report (V2.5)", pdf_data, f"Report_{p_name}.pdf")