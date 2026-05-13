import streamlit as st
import pandas as pd
import os
import matplotlib.pyplot as plt
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
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
    st.write("Root Air Fan Selection System V2.3")

# 2. 데이터 로드 함수
def load_my_data():
    file_name = 'fan_data.csv'
    if not os.path.exists(file_name): return None
    try:
        df = pd.read_csv(file_name, encoding='utf-8-sig')
    except:
        df = pd.read_csv(file_name, encoding='cp949')
    return df

# 3. 성능 곡선 그래프 (크기 확대 버전)
def create_performance_chart(all_df, user_cmh, user_pa):
    fig, ax = plt.subplots(figsize=(12, 8)) # 크기 확대
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

# 4. 소음 스펙트럼 그래프 (합계 소음 포함)
def create_noise_chart(noise_row):
    bands = ['63Hz', '125Hz', '250Hz', '500Hz', '1kHz', '2kHz', '4kHz', '8kHz']
    available_bands = [b for b in bands if b in noise_row.index]
    if not available_bands: return None
    
    values = pd.to_numeric([noise_row[b] for b in available_bands], errors='coerce')
    values = np.nan_to_num(values)
    total_db = noise_row['Total_dB'] if 'Total_dB' in noise_row.index else "N/A"
    
    fig, ax = plt.subplots(figsize=(12, 6)) # 크기 확대
    bars = ax.bar(available_bands, values, color='skyblue', edgecolor='navy', alpha=0.8)
    
    max_val = max(values) if len(values) > 0 else 0
    ax.set_ylim(0, max_val + 25)
    ax.set_ylabel('Sound Pressure Level (dB)', fontsize=12)
    ax.set_title(f'Octave Band Noise Spectrum (Total: {total_db} dB)', fontsize=15, fontweight='bold')
    ax.grid(axis='y', linestyle=':', alpha=0.7)
    
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 1, f'{int(height)}', ha='center', va='bottom', fontweight='bold')
    
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=200)
    buf.seek(0)
    plt.close(fig)
    return buf

# 5. PDF 생성 함수 (2페이지 구성)
def create_pdf(model_info, user_cmh, user_pa, perf_buf, noise_buf, project_info):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    
    # --- PAGE 1: Technical Spec & Performance Curve ---
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
    p.drawString(60, h - 215, f"- RPM: {model_info.iloc[1]}") # RPM 추가
    p.drawString(60, h - 235, f"- Design Duty: {user_cmh} CMH @ {user_pa} Pa")
    p.drawString(60, h - 255, f"- Motor Power: {model_info.iloc[6]} kW")
    
    # 성능 곡선 삽입 (크게)
    p.drawImage(ImageReader(perf_buf), 50, h - 680, width=500, height=380)
    
    p.showPage() # 다음 페이지로 이동
    
    # --- PAGE 2: Noise Analysis ---
    if noise_buf:
        p.setFont("Helvetica-Bold", 22)
        p.drawString(50, h - 50, "Acoustic Analysis Report")
        p.line(50, h - 65, 550, h - 65)
        
        p.setFont("Helvetica-Bold", 14)
        p.drawString(50, h - 100, "[2] Noise Data Summary")
        p.setFont("Helvetica", 12)
        total_db = model_info['Total_dB'] if 'Total_dB' in model_info.index else "N/A"
        p.drawString(60, h - 130, f"- Total Sound Pressure Level: {total_db} dB(A)")
        
        # 소음 테이블 (간략)
        p.setFont("Helvetica-Bold", 10)
        bands = ['63', '125', '250', '500', '1k', '2k', '4k', '8k']
        for i, b in enumerate(bands):
            p.drawString(60 + (i*60), h - 170, f"{b}Hz")
        
        p.setFont("Helvetica", 10)
        for i, b in enumerate(['63Hz', '125Hz', '250Hz', '500Hz', '1kHz', '2kHz', '4kHz', '8kHz']):
            val = model_info[b] if b in model_info.index else "-"
            p.drawString(60 + (i*60), h - 190, str(val))
            
        # 소음 그래프 삽입 (크게)
        p.drawImage(ImageReader(noise_buf), 50, h - 550, width=500, height=280)
        
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
    
    st.subheader("🔍 Design Conditions")
    c1, c2 = st.columns(2)
    u_cmh = c1.number_input("Flow (CMH)", value=120000, step=1000)
    u_pa = c2.number_input("Pressure (Pa)", value=2400, step=10)

    matched = df[(df.iloc[:, 3] >= u_cmh) & (df.iloc[:, 5] >= u_pa)].copy()

    if not matched.empty:
        best = matched.sort_values(by=[df.columns[3], df.columns[5]]).iloc[0]
        st.success(f"Best Match: **{best.iloc[0]}** (RPM: {best.iloc[1]})")
        
        perf_img = create_performance_chart(df, u_cmh, u_pa)
        
        noise_bands = ['63Hz', '125Hz', '250Hz', '500Hz', '1kHz', '2kHz', '4kHz', '8kHz']
        has_noise = all(b in df.columns for b in noise_bands)
        
        noise_img = None
        st.subheader("📊 Performance & Noise Analysis")
        st.image(perf_img, caption="Performance Selection Curve")
        
        if has_noise:
            noise_img = create_noise_chart(best)
            if noise_img:
                st.image(noise_img, caption="Acoustic Spectrum")
                total_val = best['Total_dB'] if 'Total_dB' in best.index else 'N/A'
                st.info(f"🔊 **Total Noise Level: {total_val} dB(A)**")

        proj_info = {"project": p_name, "customer": c_name, "manager": m_name}
        pdf_data = create_pdf(best, u_cmh, u_pa, perf_img, noise_img, proj_info)
        st.download_button("📥 Download Detailed Report (2 Pages PDF)", pdf_data, f"Report_{p_name}.pdf", "application/pdf")
        
        with st.expander("📂 Matching Models Data"):
            st.dataframe(matched, use_container_width=True)
    else:
        st.warning("No matching model found.")