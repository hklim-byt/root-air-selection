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
    st.write("Root Air Fan Selection System V4.0 (Full Performance Map)")

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

# 3. 종합 성능 곡선 생성 함수 (V4.0 핵심)
def create_combined_chart(all_df, selected_model_name, user_cmh, user_pa):
    model_df = all_df[all_df['model_name'] == selected_model_name].sort_values(by=['rpm', 'CMH'])
    rpms = sorted(model_df['rpm'].unique())
    
    fig, ax1 = plt.subplots(figsize=(12, 8))
    ax2 = ax1.twinx() # 효율 및 동력을 위한 보조축
    
    # 컬러맵 설정 (다채로운 색상)
    colors_list = plt.cm.jet(np.linspace(0, 1, len(rpms)))
    
    surging_x = []
    surging_y = []

    # 1. RPM별 성능 곡선 (Pa) 및 서징 라인 데이터 수집
    for i, rpm in enumerate(rpms):
        rpm_data = model_df[model_df['rpm'] == rpm]
        line, = ax1.plot(rpm_data['CMH'], rpm_data['Pa'], color=colors_list[i], label=f'{rpm} rpm', linewidth=1.5)
        
        # 곡선 끝에 RPM 텍스트 추가 (가시성 향상)
        ax1.text(rpm_data['CMH'].iloc[-1], rpm_data['Pa'].iloc[-1], f' {rpm}', fontsize=8, color=colors_list[i], va='center')
        
        # 서징 포인트 (각 RPM의 최소 풍량 지점)
        surging_x.append(rpm_data['CMH'].iloc[0])
        surging_y.append(rpm_data['Pa'].iloc[0])

    # 2. 서징 라인 (Surging Line) 그리기
    ax1.plot(surging_x, surging_y, 'r--', linewidth=2.5, label='Surging Line')
    ax1.fill_betweenx(surging_y, 0, surging_x, color='red', alpha=0.05) # 운전 금지 영역 색칠
    ax1.text(surging_x[0], surging_y[0], '  SURGE LINE', color='red', fontsize=10, fontweight='bold', va='bottom')

    # 3. 동력(kW) 및 효율(%) 곡선 (가독성을 위해 파선/점선 사용)
    # 전체 데이터를 다 그리면 복잡하므로 대표 RPM(최대) 하나만 그리거나 스케일링하여 표시
    max_rpm_data = model_df[model_df['rpm'] == max(rpms)]
    ax2.plot(max_rpm_data['CMH'], max_rpm_data['total efficiency (%)'], 'g-.', label='Efficiency (%)', alpha=0.6)
    ax2.plot(max_rpm_data['CMH'], max_rpm_data['power (kW)'], 'm:', label='Power (kW)', alpha=0.6)

    # 4. 설계점(Design Point) 표시
    ax1.scatter(user_cmh, user_pa, color='black', s=200, marker='*', label='Design Point', zorder=20)
    ax1.annotate(f'Selected Point\n({user_cmh}CMH / {user_pa}Pa)', xy=(user_cmh, user_pa), xytext=(user_cmh+5000, user_pa+200),
                 arrowprops=dict(facecolor='black', shrink=0.05, width=1, headwidth=5))

    # 레이블 설정
    ax1.set_xlabel('Air Flow (CMH)', fontsize=12)
    ax1.set_ylabel('Static Pressure (Pa)', fontsize=12)
    ax2.set_ylabel('Efficiency (%) / Power (kW)', fontsize=12)
    ax1.set_title(f'Comprehensive Performance Map: {selected_model_name}', fontsize=16, fontweight='bold')
    
    # 범례 정리
    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines + lines2, labels + labels2, loc='upper left', bbox_to_anchor=(1.1, 1), fontsize='small')
    
    ax1.grid(True, linestyle=':', alpha=0.6)
    
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=200)
    buf.seek(0)
    plt.close(fig)
    return buf

# 4. 소음 그래프 (기존 유지)
def create_noise_chart(noise_row, bands):
    plot_values = []
    for b in bands:
        val = str(noise_row[b])
        first_val = val.split('/')[0].strip()
        try: plot_values.append(float(first_val))
        except: plot_values.append(0.0)
    display_labels = ['63', '125', '250', '500', '1k', '2k', '4k', '8k']
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(display_labels, plot_values, color='skyblue', edgecolor='navy')
    ax.set_title('Acoustic Spectrum')
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=150)
    buf.seek(0)
    plt.close(fig)
    return buf

# 5. PDF 생성 (V4.0)
def create_pdf(model_info, user_cmh, user_pa, combined_buf, noise_buf, project_info, noise_bands, total_col):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    
    # 1페이지
    if os.path.exists("logo.png"):
        p.drawImage(ImageReader("logo.png"), w - 160, h - 60, width=110, height=35, preserveAspectRatio=True, mask='auto')
    p.setFont("Helvetica-Bold", 20)
    p.drawString(50, h - 50, "Fan Selection Technical Report")
    p.line(50, h - 65, 550, h - 65)
    
    p.setFont("Helvetica", 10)
    p.drawString(50, h - 85, f"Project: {project_info['project']}  |  Customer: {project_info['customer']}")
    p.drawString(50, h - 100, f"Engineer: {project_info['manager']}  |  Date: {project_info['date']}")
    
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, h - 130, "[1] Performance Specification")
    p.setFont("Helvetica", 11)
    p.drawString(60, h - 150, f"- Model: {model_info['model_name']} / RPM: {model_info['rpm']}")
    p.drawString(60, h - 165, f"- Flow: {user_cmh} CMH / Pressure: {user_pa} Pa")
    p.drawString(60, h - 180, f"- P fan: {model_info['power (kW)']} kW / Total Eff: {model_info['total efficiency (%)']}%")

    p.drawImage(ImageReader(combined_buf), 40, h - 630, width=520, height=430)
    p.showPage()
    
    # 2페이지 (소음)
    if noise_buf:
        p.drawImage(ImageReader(combined_buf), w-100, h-40, width=80, height=30) # 로고 대신 작게 표시하거나 로고 재사용
        p.setFont("Helvetica-Bold", 20)
        p.drawString(50, h - 50, "Acoustic Analysis")
        p.drawImage(ImageReader(noise_buf), 50, h - 450, width=500, height=250)
    
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

# --- 메인 실행 ---
df = load_my_data()
if df is not None:
    st.divider()
    st.subheader("📋 Project Details")
    c1, c2, c3, c4 = st.columns(4)
    p_name = c1.text_input("Project", "P4 Project")
    c_name = c2.text_input("Customer", "K-ENSOL")
    m_name = c3.text_input("Manager", "J.H. KIM")
    p_date = c4.date_input("Date", datetime.now())

    st.subheader("🔍 Selection Conditions")
    c1, c2 = st.columns(2)
    u_cmh = c1.number_input("Air Flow (CMH)", value=120000)
    u_pa = c2.number_input("Static Pressure (Pa)", value=2400)

    matched = df[(df['CMH'] >= u_cmh) & (df['Pa'] >= u_pa)].copy()

    if not matched.empty:
        best = matched.sort_values(by=['CMH', 'Pa']).iloc[0]
        st.success(f"Selected: **{best['model_name']}**")
        
        # 종합 차트 생성
        combined_img = create_combined_chart(df, best['model_name'], u_cmh, u_pa)
        st.image(combined_img, caption="Total Performance Map (V4.0)")
        
        # 소음 처리
        noise_bands = [f'{hz}(dB / dB(A))' for hz in ['63Hz', '125Hz', '250Hz', '500Hz', '1kHz', '2kHz', '4kHz', '8kHz']]
        total_col = 'Total_dB / dB(A)'
        noise_img = create_noise_chart(best, noise_bands) if total_col in best.index else None

        proj_info = {"project": p_name, "customer": c_name, "manager": m_name, "date": p_date.strftime("%Y-%m-%d")}
        pdf_data = create_pdf(best, u_cmh, u_pa, combined_img, noise_img, proj_info, noise_bands, total_col)
        st.download_button("📥 Download Full Performance Report", pdf_data, f"Report_{p_name}.pdf")
    else:
        st.warning("No matching models found.")