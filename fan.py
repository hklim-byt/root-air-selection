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
st.set_page_config(page_title="루트에어 선정 시스템 V6.8", layout="wide")

# 1. 데이터 로드 함수 (강화됨)
def load_my_data():
    # 사용자가 업로드한 파일명에 맞춰 확인
    target_files = ['fan_performance_map_full_sample.csv', 'fan_data.csv']
    df = None
    for f_name in target_files:
        if os.path.exists(f_name):
            try:
                df = pd.read_csv(f_name, encoding='utf-8-sig')
                break
            except:
                df = pd.read_csv(f_name, encoding='cp949')
                break
    return df

# 2. 메인 성능 맵 생성 (0,0 시작 저항곡선 + 선명한 RPM 맵)
def create_master_chart(all_df, selected_model, user_cmh, user_pa):
    model_df = all_df[all_df['model_name'] == selected_model].sort_values(by=['rpm', 'CMH'])
    rpms = sorted(model_df['rpm'].unique())
    
    fig, ax = plt.subplots(figsize=(10, 6.5))
    
    # RPM 곡선들 (선명도 보정)
    for rpm in rpms:
        data = model_df[model_df['rpm'] == rpm]
        ax.plot(data['CMH'], data['Pa'], color='steelblue', linewidth=1.2, alpha=0.5, zorder=1)
        ax.text(data['CMH'].iloc[-1], data['Pa'].iloc[-1], f' {int(rpm)} RPM', 
                color='steelblue', fontsize=8, va='center', fontweight='bold', alpha=0.7)

    # 시스템 저항 곡선: (0,0)에서 설계점까지 포물선
    x_path = np.linspace(0, user_cmh * 1.1, 100) 
    k = user_pa / (user_cmh**2) if user_cmh != 0 else 0
    y_path = k * (x_path**2)
    ax.plot(x_path, y_path, color='#1f77b4', linewidth=4, alpha=1.0, zorder=20, label='System Resistance')

    # 설계 지점 마킹 (붉은 십자선 + 포인트)
    ax.axvline(user_cmh, color='red', linestyle='--', linewidth=1, alpha=0.4, zorder=15)
    ax.axhline(user_pa, color='red', linestyle='--', linewidth=1, alpha=0.4, zorder=15)
    ax.scatter(user_cmh, user_pa, color='red', s=150, edgecolors='white', marker='o', linewidths=1.5, zorder=30, label='Design Point')

    ax.set_xlim(0, max(user_cmh * 1.5, model_df['CMH'].max() * 1.1))
    ax.set_ylim(0, max(user_pa * 1.5, model_df['Pa'].max() * 1.1))
    ax.set_xlabel('Flow (CMH)', fontweight='bold')
    ax.set_ylabel('Pressure (Pa)', fontweight='bold')
    ax.set_title(f"Performance Map: {selected_model}", fontsize=15, fontweight='bold')
    ax.grid(True, linestyle=':', alpha=0.5)
    ax.legend(loc='upper right')
    
    plt.tight_layout()
    buf = BytesIO(); plt.savefig(buf, format='png', dpi=200); buf.seek(0); plt.close(fig)
    return buf

# 3. 소음 분석 차트 생성
def create_noise_chart(noise_row):
    bands = ['63', '125', '250', '500', '1k', '2k', '4k', '8k']
    vals = []
    for b in bands:
        col = [c for c in noise_row.index if b in c][0]
        val = str(noise_row[col]).split('/')[0].strip().replace('dB', '')
        vals.append(float(val))
    
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.bar(bands, vals, color='skyblue', edgecolor='navy', alpha=0.7)
    ax.set_title('Octave Band Noise Analysis (dB)', fontweight='bold')
    for i, v in enumerate(vals):
        ax.text(i, v + 0.5, f'{int(v)}', ha='center', fontweight='bold')
    
    buf = BytesIO(); plt.savefig(buf, format='png', dpi=150); buf.seek(0); plt.close(fig)
    return buf

# 4. PDF 리포트 생성 (데이터 분리, 수직 배치, 표 형식 적용)
def create_final_pdf(project_info, model_data, chart_buf, noise_buf, design_point):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    
    # 헤더 및 타이틀
    p.setFont("Helvetica-Bold", 22); p.drawString(50, h-50, "Technical Selection Report")
    p.line(50, h-60, 545, h-60)

    # [수정 1 & 2] 데이터 분리 및 수직 배치
    # 좌측: Project Information
    p.setFont("Helvetica-Bold", 12); p.drawString(50, h-85, "[1] Project Information")
    p.setFont("Helvetica", 10)
    p.drawString(60, h-105, f"Project Name: {project_info['project']}")
    p.drawString(60, h-120, f"Customer: {project_info['customer']}")
    p.drawString(60, h-135, f"Engineer: {project_info['manager']}")
    p.drawString(60, h-150, f"Date: {project_info['date']}")

    # 우측: Design & Performance (수직 배치)
    p.setFont("Helvetica-Bold", 12); p.drawString(320, h-85, "[2] Design & Performance")
    p.setFont("Helvetica", 10)
    p.drawString(330, h-105, f"Selected Model: {model_data['model_name']}")
    p.drawString(330, h-120, f"Operating Speed: {model_data['rpm']} RPM")
    p.drawString(330, h-135, f"Design Flow: {design_point['cmh']:,} CMH")
    p.drawString(330, h-150, f"Design Pressure: {design_point['pa']:,} Pa")
    p.drawString(330, h-165, f"Absorbed Power: {model_data['power (kW)']} kW")
    p.drawString(330, h-180, f"Total Efficiency: {model_data['total efficiency (%)']}%")

    # 성능 그래프
    p.drawImage(ImageReader(chart_buf), 45, h-520, width=500, height=330)

    # [수정 3] 소음 데이터 및 표 형식
    p.setFont("Helvetica-Bold", 12); p.drawString(50, h-545, "[3] Acoustic Analysis")
    p.drawImage(ImageReader(noise_buf), 50, h-710, width=490, height=160)
    
    # 표(Table) 그리기
    table_y = h-745
    p.setLineWidth(1); p.setStrokeColor(colors.black)
    p.setFillColor(colors.lightgrey); p.rect(50, table_y, 495, 20, fill=1) # 헤더 배경
    p.setFillColor(colors.black); p.setFont("Helvetica-Bold", 9)
    
    bands_lbl = ['63Hz', '125Hz', '250Hz', '500Hz', '1kHz', '2kHz', '4kHz', '8kHz', 'Total']
    for i, b in enumerate(bands_lbl):
        p.drawString(55 + (i*55), table_y + 7, b)
    
    p.setFont("Helvetica", 9); table_y -= 20
    p.rect(50, table_y, 495, 20, fill=0) # 데이터 칸
    noise_cols = ['63Hz(dB / dB(A))', '125Hz(dB / dB(A))', '250Hz(dB / dB(A))', '500Hz(dB / dB(A))',
                  '1kHz(dB / dB(A))', '2kHz(dB / dB(A))', '4kHz(dB / dB(A))', '8kHz(dB / dB(A))', 'Total_dB / dB(A)']
    for i, col in enumerate(noise_cols):
        val = str(model_data[col]).split('/')[0].strip() + " dB"
        p.drawString(55 + (i*55), table_y + 7, val)

    p.showPage(); p.save(); buffer.seek(0)
    return buffer

# --- 메인 실행부 ---
df = load_my_data()

if df is not None:
    st.title("🏢 루트에어 송풍기 선정 시스템 V6.8")
    st.divider()
    
    # 프로젝트 정보 입력
    st.subheader("📋 Project Information")
    c1, c2, c3, c4 = st.columns(4)
    p_name = c1.text_input("Project Name", value="RouteAir-2024")
    c_name = c2.text_input("Customer", value="Global Tech")
    m_name = c3.text_input("Manager", value="Engineer Lee")
    p_date = c4.date_input("Date", datetime.now())

    # 설계 조건 입력
    st.subheader("🎯 Design Duty")
    col1, col2, col3 = st.columns(3)
    u_cmh = col1.number_input("Design Flow (CMH)", value=115000)
    u_pa = col2.number_input("Design Pressure (Pa)", value=2100)
    selected_model = col3.selectbox("Select Model", df['model_name'].unique())
    
    # 데이터 처리
    model_data = df[df['model_name'] == selected_model].iloc[0]
    
    # 결과 화면 출력
    st.divider()
    chart_img = create_master_chart(df, selected_model, u_cmh, u_pa)
    st.image(chart_img)
    
    noise_img = create_noise_chart(model_data)
    st.subheader("🔊 Noise Data Analysis")
    st.image(noise_img)
    
    # PDF 다운로드
    p_info = {"project": p_name, "customer": c_name, "manager": m_name, "date": p_date.strftime("%Y-%m-%d")}
    d_point = {"cmh": u_cmh, "pa": u_pa}
    pdf_file = create_final_pdf(p_info, model_data, chart_img, noise_img, d_point)
    
    st.download_button(
        label="📥 Download Technical Selection Report (PDF)",
        data=pdf_file,
        file_name=f"Technical_Report_{p_name}.pdf",
        mime="application/pdf"
    )
else:
    st.error("데이터 파일(fan_performance_map_full_sample.csv)을 찾을 수 없습니다. 파일을 확인해 주세요.")