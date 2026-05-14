import streamlit as st
import pandas as pd
import os
import matplotlib.pyplot as plt
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from io import BytesIO
import numpy as np
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="루트에어 종합 선정 시스템 V5.6", layout="wide")

# 1. 상단 레이아웃
col_logo, col_title = st.columns([1, 4])
with col_logo:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=250)
    else:
        st.title("🏢")
with col_title:
    st.markdown("###")
    st.title("루트에어 송풍기 선정 시스템 V5.6")
    st.write("Integrated Performance Map with Highlighted Selection Curve")

# 2. 데이터 로드
def load_my_data():
    file_name = 'fan_performance_map_extended.csv'
    if not os.path.exists(file_name):
        file_name = 'fan_performance_map_full_sample.csv'
        if not os.path.exists(file_name): return None
    try:
        df = pd.read_csv(file_name, encoding='utf-8-sig')
    except:
        df = pd.read_csv(file_name, encoding='cp949')
    return df

# 3. 통합 강조 그래프 생성
def create_integrated_chart(all_df, selected_model, best_rpm, user_cmh, user_pa):
    model_df = all_df[all_df['model_name'] == selected_model].sort_values(by=['rpm', 'CMH'])
    rpms = sorted(model_df['rpm'].unique())
    
    fig, ax1 = plt.subplots(figsize=(12, 8))
    
    # 가시성을 위한 부드러운 색상 팔레트
    distinct_colors = ['#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5', '#c49c94', '#f7b6d2', '#c7c7c7', '#dbdb8d', '#9edae5']
    surge_x, surge_y = [], []

    # 1. 모든 RPM 배경 곡선 및 선정 곡선 강조
    for i, rpm in enumerate(rpms):
        data = model_df[model_df['rpm'] == rpm]
        
        if int(rpm) == int(best_rpm):
            # 선정된 곡선: 점(marker) 없이 아주 굵은 선으로 강조
            color, linewidth, alpha, zorder = '#1f77b4', 4.5, 1.0, 10
            label_txt = f'Selected Curve ({rpm} rpm)'
        else:
            # 나머지 곡선: 연하게 배경 처리
            color, linewidth, alpha, zorder = distinct_colors[i % len(distinct_colors)], 1.2, 0.4, 1
            label_txt = f'{rpm} rpm'
            
        ax1.plot(data['CMH'], data['Pa'], color=color, label=label_txt, linewidth=linewidth, alpha=alpha, zorder=zorder)
        
        # 서징 포인트 수집
        surge_x.append(data['CMH'].iloc[0])
        surge_y.append(data['Pa'].iloc[0])
        
        # RPM 라벨 표시
        ax1.text(data['CMH'].iloc[-1], data['Pa'].iloc[-1], f' {rpm}', color=color, fontsize=9, va='center', fontweight='bold', alpha=alpha)

    # 2. 서징 라인 및 영역 표시 (기존 스타일 유지)
    ax1.plot(surge_x, surge_y, 'r--', linewidth=2.5, label='Surge Line', zorder=15)
    ax1.fill_betweenx(surge_y, 0, surge_x, color='red', alpha=0.07, zorder=0)
    ax1.text(surge_x[0], surge_y[0], '  SURGE LINE', color='red', fontweight='bold', va='bottom')

    # 3. 선정 지점 마킹: 붉은색 십자선 + 붉은 동그라미 (강력 강조)
    ax1.axhline(user_pa, color='red', linestyle='-', linewidth=1.5, alpha=0.8, zorder=20)
    ax1.axvline(user_cmh, color='red', linestyle='-', linewidth=1.5, alpha=0.8, zorder=20)
    ax1.scatter(user_cmh, user_pa, color='red', s=180, edgecolors='white', marker='o', linewidths=2, zorder=30, label='Selected Duty')

    # 4. 축 범위 최적화 (중앙 정렬)
    x_limit = max(user_cmh * 1.6, model_df['CMH'].max() * 1.1)
    y_limit = max(user_pa * 1.6, model_df['Pa'].max() * 1.1)
    ax1.set_xlim(0, x_limit)
    ax1.set_ylim(0, y_limit)

    ax1.set_xlabel('Air Flow (CMH)', fontsize=12)
    ax1.set_ylabel('Static Pressure (Pa)', fontsize=12)
    ax1.set_title(f"Comprehensive Selection Map: {selected_model}", fontsize=16, fontweight='bold', pad=20)
    
    ax1.legend(loc='upper right', fontsize='small', frameon=True)
    ax1.grid(True, linestyle=':', alpha=0.6)
    
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=200)
    buf.seek(0)
    plt.close(fig)
    return buf

# [이하 소음 그래프 및 PDF 생성 로직은 V5.5와 동일하게 유지]
def create_noise_chart(noise_row):
    bands_labels = ['63', '125', '250', '500', '1k', '2k', '4k', '8k']
    plot_values, found_labels = [], []
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
    ax.set_title('Octave Band Noise Analysis (dB)', fontsize=15, fontweight='bold')
    for bar in bars:
        ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 1, f'{int(bar.get_height())}', ha='center', va='bottom', fontweight='bold')
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=200)
    buf.seek(0)
    plt.close(fig)
    return buf

def create_pdf(model_info, user_cmh, user_pa, combined_buf, noise_buf, project_info):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    if os.path.exists("logo.png"):
        p.drawImage(ImageReader("logo.png"), w - 160, h - 60, width=110, height=35, preserveAspectRatio=True, mask='auto')
    
    p.setFont("Helvetica-Bold", 22)
    p.drawString(50, h - 50, "Technical Selection Report")
    p.line(50, h - 65, 550, h - 65)
    
    p.setFont("Helvetica", 11)
    p.drawString(50, h - 90, f"Project: {project_info['project']}  |  Customer: {project_info['customer']}")
    p.drawString(50, h - 105, f"Engineer: {project_info['manager']}  |  Date: {project_info['date']}")
    
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, h - 170, "[1] Technical Specifications")
    p.setFont("Helvetica", 12)
    p.drawString(60, h - 195, f"- Model Name: {model_info['model_name']} / {model_info['rpm']} rpm")
    p.drawString(60, h - 215, f"- Design Duty: {user_cmh} CMH @ {user_pa} Pa")
    p.drawString(60, h - 235, f"- Power: {model_info['power (kW)']} kW / Eff: {model_info['total efficiency (%)']}%")

    p.drawImage(ImageReader(combined_buf), 40, h - 680, width=520, height=420)
    p.showPage()
    
    if noise_buf:
        if os.path.exists("logo.png"):
            p.drawImage(ImageReader("logo.png"), w - 160, h - 60, width=110, height=35, preserveAspectRatio=True, mask='auto')
        p.setFont("Helvetica-Bold", 22)
        p.drawString(50, h - 50, "Acoustic Analysis Report")
        p.drawImage(ImageReader(noise_buf), 50, h - 450, width=500, height=300)
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

# --- 메인 실행부 ---
df = load_my_data()
if df is not None:
    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    p_name = c1.text_input("Project Name", placeholder="English Only")
    c_name = c2.text_input("Customer", placeholder="English Only")
    m_name = c3.text_input("Manager", placeholder="English Only")
    p_date = c4.date_input("Date", datetime.now())

    c1, c2 = st.columns(2)
    u_cmh = c1.number_input("Design Flow (CMH)", value=115000)
    u_pa = c2.number_input("Design Pressure (Pa)", value=2100)

    matched = df[(df['CMH'] >= u_cmh) & (df['Pa'] >= u_pa)].copy()
    if not matched.empty:
        best_row = matched.sort_values(by=['CMH', 'Pa']).iloc[0]
        
        # V5.6 통합 강조 그래프 생성
        combined_img = create_integrated_chart(df, best_row['model_name'], best_row['rpm'], u_cmh, u_pa)
        st.image(combined_img)
        
        noise_img = create_noise_chart(best_row)
        if noise_img: st.image(noise_img)

        proj_info = {"project": p_name if p_name else "N/A", "customer": c_name if c_name else "N/A", "manager": m_name if m_name else "N/A", "date": p_date.strftime("%Y-%m-%d")}
        pdf_data = create_pdf(best_row, u_cmh, u_pa, combined_img, noise_img, proj_info)
        st.download_button("📥 Download Final Selection Report (V5.6)", pdf_data, f"Report_{p_name}.pdf")