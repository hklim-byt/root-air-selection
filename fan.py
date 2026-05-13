import streamlit as st
import pandas as pd
import os
import matplotlib.pyplot as plt
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from io import BytesIO
import numpy as np  # 데이터 처리용 추가

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
    st.write("Root Air Fan Selection System V2.2")

# 2. 데이터 로드 함수
def load_my_data():
    file_name = 'fan_data.csv'
    if not os.path.exists(file_name): return None
    try:
        df = pd.read_csv(file_name, encoding='utf-8-sig')
    except:
        df = pd.read_csv(file_name, encoding='cp949')
    return df

# 3. 그래프 생성 함수 (성능 곡선)
def create_performance_chart(all_df, user_cmh, user_pa):
    fig, ax = plt.subplots(figsize=(8, 5))
    unique_models = all_df.iloc[:, 0].unique()
    for model in unique_models:
        model_data = all_df[all_df.iloc[:, 0] == model].sort_values(by=all_df.columns[3])
        ax.plot(model_data.iloc[:, 3], model_data.iloc[:, 5], marker='o', markersize=3, label=model, alpha=0.7)
    
    ax.scatter(user_cmh, user_pa, color='red', s=100, label='Design Point', zorder=10)
    ax.axhline(user_pa, color='red', linestyle='--', linewidth=1, alpha=0.5)
    ax.axvline(user_cmh, color='red', linestyle='--', linewidth=1, alpha=0.5)
    ax.set_xlabel('Air Flow (CMH)')
    ax.set_ylabel('Static Pressure (Pa)')
    ax.set_title('Performance Curve')
    ax.legend(fontsize='small')
    
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=150)
    buf.seek(0)
    plt.close(fig)
    return buf

# 4. 그래프 생성 함수 (소음 옥타브 밴드)
def create_noise_chart(noise_row):
    bands = ['63Hz', '125Hz', '250Hz', '500Hz', '1kHz', '2kHz', '4kHz', '8kHz']
    available_bands = [b for b in bands if b in noise_row.index]
    if not available_bands: return None
    
    # 데이터를 숫자로 안전하게 변환
    raw_values = [noise_row[b] for b in available_bands]
    values = pd.to_numeric(raw_values, errors='coerce')
    values = np.nan_to_num(values) # NaN(빈칸)을 0으로 변환
    
    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.bar(available_bands, values, color='skyblue', edgecolor='navy')
    
    max_val = max(values) if len(values) > 0 else 0
    ax.set_ylim(0, max_val + 20 if max_val > 0 else 100)
    ax.set_ylabel('Sound Pressure Level (dB)')
    ax.set_title('Octave Band Noise Spectrum')
    ax.grid(axis='y', linestyle=':', alpha=0.7)
    
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 1, f'{int(height)}', ha='center', va='bottom', fontweight='bold')
    
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=150)
    buf.seek(0)
    plt.close(fig)
    return buf

# 5. PDF 생성 함수
def create_pdf(model_info, user_cmh, user_pa, perf_buf, noise_buf, project_info):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    
    p.setFont("Helvetica-Bold", 18)
    p.drawString(50, h - 50, "Technical Selection Report")
    p.line(50, h - 65, 550, h - 65)
    
    p.setFont("Helvetica", 10)
    p.drawString(50, h - 85, f"Project: {project_info['project']}")
    p.drawString(50, h - 100, f"Customer: {project_info['customer']}")
    p.drawString(50, h - 115, f"Engineer: {project_info['manager']}")
    
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, h - 145, "[1] Technical Specifications")
    p.setFont("Helvetica", 10)
    p.drawString(60, h - 165, f"- Model: {model_info.iloc[0]}")
    p.drawString(60, h - 180, f"- Duty: {user_cmh} CMH @ {user_pa} Pa")
    p.drawString(60, h - 195, f"- Power: {model_info.iloc[6]} kW")
    
    p.drawImage(ImageReader(perf_buf), 50, h - 450, width=240, height=180)
    if noise_buf:
        p.drawImage(ImageReader(noise_buf), 300, h - 450, width=240, height=180)
    
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

# --- 메인 실행부 ---
df = load_my_data()

if df is not None:
    st.divider()
    st.subheader("📋 Project Information (English Only)")
    st.info("⚠️ Please enter all project details in English for the PDF report.")
    c1, c2, c3 = st.columns(3)
    p_name = c1.text_input("Project Name", placeholder="e.g. P4 Extension")
    c_name = c2.text_input("Customer", placeholder="e.g. K-ENSOL")
    m_name = c3.text_input("Manager", placeholder="e.g. J.H. KIM")
    
    st.subheader("🔍 Selection Conditions")
    c1, c2 = st.columns(2)
    u_cmh = c1.number_input("Flow (CMH)", value=120000, step=1000)
    u_pa = c2.number_input("Static Pressure (Pa)", value=2400, step=10)

    # 필터링
    matched = df[(df.iloc[:, 3] >= u_cmh) & (df.iloc[:, 5] >= u_pa)].copy()

    if not matched.empty:
        best = matched.sort_values(by=[df.columns[3], df.columns[5]]).iloc[0]
        st.success(f"Best Match: **{best.iloc[0]}**")
        
        perf_img = create_performance_chart(df, u_cmh, u_pa)
        
        # 소음 처리
        noise_bands = ['63Hz', '125Hz', '250Hz', '500Hz', '1kHz', '2kHz', '4kHz', '8kHz']
        has_noise = all(b in df.columns for b in noise_bands)
        
        noise_img = None
        col1, col2 = st.columns(2)
        with col1:
            st.image(perf_img, caption="Performance Selection Curve")
        with col2:
            if has_noise:
                noise_img = create_noise_chart(best)
                if noise_img:
                    st.image(noise_img, caption="Octave Band Noise Spectrum")
            else:
                st.warning("⚠️ Noise data columns not found in CSV.")

        # PDF 다운로드
        proj_info = {"project": p_name if p_name else "N/A", "customer": c_name if c_name else "N/A", "manager": m_name if m_name else "N/A"}
        pdf_data = create_pdf(best, u_cmh, u_pa, perf_img, noise_img, proj_info)
        st.download_button("📥 Download Technical Report (PDF)", pdf_data, f"Report_{p_name}.pdf", "application/pdf")
        
        st.dataframe(matched, use_container_width=True)
    else:
        st.warning("No matching fan models found.")
else:
    st.error("Missing 'fan_data.csv' file in the repository.")