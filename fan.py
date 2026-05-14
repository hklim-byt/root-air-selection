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
st.set_page_config(page_title="루트에어 선정 시스템 V7.9.1", layout="wide")

# 1. 데이터 로드 함수 (경로 및 인코딩 방어 로직)
def load_my_data():
    # 사용 중인 파일명을 정확히 입력해 주세요. (예: fan_performance_map_full_sample.csv)
    target_file = 'fan_performance_map_full_sample.csv' 
    if os.path.exists(target_file):
        try: return pd.read_csv(target_file, encoding='utf-8-sig')
        except: return pd.read_csv(target_file, encoding='cp949')
    return None

# 소음 데이터에서 dB와 dB(A)를 안전하게 추출하는 함수
def get_noise_pair(model_data, keyword):
    for col in model_data.index:
        if keyword.lower() in col.lower():
            raw_val = str(model_data[col])
            if '/' in raw_val:
                return raw_val.strip()
            return f"{raw_val.strip()} / -" # dB(A) 정보가 없을 경우 처리
    return "0 / 0"

# 2. 메인 성능 맵 생성 (V7.9 서징 로직 유지)
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
        surge_x.append(data['CMH'].iloc[0])
        surge_y.append(data['Pa'].iloc[0])

    # V7.9 서징 라인 (데이터 기반)
    ax.plot(surge_x, surge_y, 'r--', linewidth=2.5, label='Surge Line', zorder=5)
    ax.fill_betweenx(surge_y, 0, surge_x, color='red', alpha=0.07, zorder=0)

    # 시스템 저항 곡선
    x_max = max(user_cmh * 1.3, model_df['CMH'].max())
    x_path = np.linspace(0, x_max, 100)
    k = user_pa / (user_cmh**2) if user_cmh != 0 else 0
    y_path = k * (x_path**2)
    ax.plot(x_path, y_path, color='#1f77b4', linewidth=4, label='System Resistance')

    ax.scatter(user_cmh, user_pa, color='red', s=150, edgecolors='white', zorder=30, label='Design Point')
    ax.set_xlim(0, x_max); ax.set_ylim(0, max(user_pa * 1.5, model_df['Pa'].max()))
    ax.set_xlabel('Flow (CMH)', fontweight='bold'); ax.set_ylabel('Pressure (Pa)', fontweight='bold')
    ax.set_title(f"Performance Map: {selected_model}", fontsize=16, fontweight='bold', pad=20)
    ax.grid(True, linestyle=':', alpha=0.5); ax.legend(loc='upper right', fontsize=10)
    plt.tight_layout()
    buf = BytesIO(); plt.savefig(buf, format='png', dpi=200); buf.seek(0); plt.close(fig)
    return buf

# 3. 소음 차트 생성
def create_noise_chart(model_data):
    bands = ['63', '125', '250', '500', '1k', '2k', '4k', '8k']
    vals = []
    for b in bands:
        pair = get_noise_pair(model_data, b)
        vals.append(float(pair.split('/')[0])) # 그래프는 dB 값 기준
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(bands, vals, color='skyblue', edgecolor='navy', alpha=0.7)
    ax.set_title('Octave Band Noise Analysis (dB)', fontweight='bold', fontsize=14)
    for i, v in enumerate(vals): ax.text(i, v + 0.5, f'{int(v)}', ha='center', fontweight='bold', fontsize=10)
    plt.tight_layout()
    buf = BytesIO(); plt.savefig(buf, format='png', dpi=150); buf.seek(0); plt.close(fig)
    return buf

# 4. PDF 리포트 생성 (2페이지 분량 및 dB/dB(A) 병행 표기)
def create_final_pdf(p_info, model_data, chart_buf, noise_buf, d_point):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    logo_path = "logo.png"
    
    # 1페이지 헤더
    p.setFont("Helvetica-Bold", 22); p.drawString(50, h-60, "Technical Selection Report")
    if os.path.exists(logo_path):
        p.drawImage(logo_path, w-180, h-82, width=130, preserveAspectRatio=True, mask='auto')
    p.setLineWidth(1.5); p.line(50, h-90, w-50, h-90)

    # 날짜 상단 배치
    p.setFont("Helvetica-Bold", 12); p.drawString(50, h-120, "[1] Project Information")
    p.setFont("Helvetica", 10.5)
    p.drawString(65, h-145, f"Date : {p_info['date']}")
    p.drawString(65, h-165, f"Project Name : {p_info['project']}")
    p.drawString(65, h-185, f"Customer : {p_info['customer']}")
    p.drawString(65, h-205, f"Engineer : {p_info['manager']}")

    # 성능 데이터
    p.setFont("Helvetica-Bold", 12); p.drawString(50, h-245, "[2] Design & Performance")
    p.setFont("Helvetica", 10.5)
    p.drawString(65, h-270, f"Selected Model : {model_data['model_name']}")
    p.drawString(65, h-290, f"Operating Speed : {model_data['rpm']} RPM")
    p.drawString(65, h-310, f"Design Flow : {d_point['cmh']:,} CMH / Design Pressure : {d_point['pa']:,} Pa")
    p.drawString(65, h-330, f"Absorbed Power : {model_data['power (kW)']} kW / Total Efficiency : {model_data['total efficiency (%)']}%")

    p.drawImage(ImageReader(chart_buf), 50, h-760, width=495, height=410)
    p.setFont("Helvetica-Oblique", 9); p.drawCentredString(w/2, 40, "- Page 1 -")
    
    # 2페이지 소음 리포트
    p.showPage()
    p.setFont("Helvetica-Bold", 22); p.drawString(50, h-60, "Technical Selection Report")
    if os.path.exists(logo_path):
        p.drawImage(logo_path, w-180, h-82, width=130, preserveAspectRatio=True, mask='auto')
    p.setLineWidth(1.5); p.line(50, h-90, w-50, h-90)
    
    p.setFont("Helvetica-Bold", 12); p.drawString(50, h-120, "[3] Acoustic Analysis")
    p.drawImage(ImageReader(noise_buf), 50, h-450, width=495, height=280)
    
    # 표 생성 (dB / dB(A))
    table_y = h-520
    p.setLineWidth(0.5); p.setFillColor(colors.lightgrey); p.rect(50, table_y, 495, 22, fill=1)
    p.setFillColor(colors.black); p.setFont("Helvetica-Bold", 8)
    labels = ['63Hz', '125Hz', '250Hz', '500Hz', '1kHz', '2kHz', '4kHz', '8kHz', 'Total']
    for i, b in enumerate(labels):
        p.drawCentredString(77 + (i*55), table_y + 7, b)
        p.line(50 + (i*55), table_y, 50 + (i*55), table_y + 22)
    p.line(545, table_y, 545, table_y + 22)
    
    p.setFont("Helvetica", 7.5); table_y -= 22; p.rect(50, table_y, 495, 22, fill=0)
    keywords = ['63', '125', '250', '500', '1k', '2k', '4k', '8k', 'Total']
    for i, kw in enumerate(keywords):
        pair = get_noise_pair(model_data, kw)
        p.drawCentredString(77 + (i*55), table_y + 7, pair)
        p.line(50 + (i*55), table_y, 50 + (i*55), table_y + 22)
    p.line(545, table_y, 545, table_y + 22)

    p.setFont("Helvetica-Oblique", 9); p.drawCentredString(w/2, 40, "- Page 2 -")
    p.showPage(); p.save(); buffer.seek(0)
    return buffer

# --- 메인 실행부 ---
df = load_my_data()

if df is not None:
    # 프로그램 상단 로고 수평 배치
    h_col1, h_col2 = st.columns([1.2, 4])
    with h_col1:
        if os.path.exists("logo.png"):
            st.write("##"); st.image("logo.png", width=180)
    with h_col2:
        st.markdown("<h1 style='margin-top: 25px;'>루트에어 송풍기 선정 시스템 V7.9.1</h1>", unsafe_allow_html=True)
    
    st.divider()
    
    # 정보 입력
    st.subheader("📋 Project Information")
    c1, c2, c3, c4 = st.columns(4)
    p_date = c1.date_input("Date", datetime.now())
    p_name = c2.text_input("Project Name", placeholder="English Only")
    c_name = c3.text_input("Customer", placeholder="English Only")
    m_name = c4.text_input("Manager", placeholder="English Only")

    # 설계 조건
    st.subheader("🎯 Design Duty")
    col1, col2, col3 = st.columns(3)
    u_cmh = col1.number_input("Design Flow (CMH)", value=115000)
    u_pa = col2.number_input("Design Pressure (Pa)", value=2100)
    selected_model = col3.selectbox("Select Model", df['model_name'].unique())
    
    model_data = df[df['model_name'] == selected_model].iloc[0]
    
    # 차트 출력
    chart_img = create_master_chart(df, selected_model, u_cmh, u_pa)
    st.image(chart_img)
    
    noise_img = create_noise_chart(model_data)
    st.subheader("🔊 Noise Data Analysis")
    st.image(noise_img)
    
    # PDF 준비
    p_info = {"project": p_name if p_name else "N/A", "customer": c_name if c_name else "N/A", "manager": m_name if m_name else "N/A", "date": p_date.strftime("%Y-%m-%d")}
    d_point = {"cmh": u_cmh, "pa": u_pa}
    pdf_file = create_final_pdf(p_info, model_data, chart_img, noise_img, d_point)
    
    st.download_button(label="📥 Download Technical Report (PDF)", data=pdf_file, file_name=f"Report_{p_info['project']}.pdf", mime="application/pdf")
else:
    # 파일이 없을 경우 경고 메시지를 표시하여 '빈 화면' 현상 방지
    st.error("⚠️ 데이터 파일('fan_performance_map_full_sample.csv')이 로드되지 않았습니다. 파일이 프로그램과 같은 경로에 있는지 확인해 주세요.")