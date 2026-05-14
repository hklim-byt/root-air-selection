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
st.set_page_config(page_title="루트에어 선정 시스템 V5.7", layout="wide")

# 1. 상단 로고 및 타이틀
col_logo, col_title = st.columns([1, 4])
with col_logo:
    if os.path.exists("logo.png"): st.image("logo.png", width=250)
    else: st.title("🏢")
with col_title:
    st.title("루트에어 송풍기 선정 시스템 V5.7")
    st.write("Professional Catalog Style: Stacked Performance Map")

# 2. 데이터 로드 (확장 데이터 사용)
def load_my_data():
    file_name = 'fan_performance_map_extended.csv'
    if not os.path.exists(file_name):
        file_name = 'fan_performance_map_full_sample.csv'
        if not os.path.exists(file_name): return None
    try: df = pd.read_csv(file_name, encoding='utf-8-sig')
    except: df = pd.read_csv(file_name, encoding='cp949')
    return df

# 3. 사진과 동일한 이단 적층형 그래프 생성
def create_stacked_chart(all_df, selected_model, best_rpm, user_cmh, user_pa):
    model_df = all_df[all_df['model_name'] == selected_model].sort_values(by=['rpm', 'CMH'])
    rpms = sorted(model_df['rpm'].unique())
    
    # 상단(정압), 하단(효율/동력) 이단 구성 (X축 공유)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 15), sharex=True, gridspec_kw={'height_ratios': [1.5, 1]})
    plt.subplots_adjust(hspace=0.05) # 두 그래프 사이 간격 최소화
    
    distinct_colors = ['#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5', '#c49c94', '#f7b6d2', '#c7c7c7', '#dbdb8d', '#9edae5']
    surge_x, surge_y = [], []

    # --- 상단 그래프 (Pressure Map) ---
    for i, rpm in enumerate(rpms):
        data = model_df[model_df['rpm'] == rpm]
        if int(rpm) == int(best_rpm):
            # 선정된 RPM 곡선: 점 없이 굵고 진하게
            ax1.plot(data['CMH'], data['Pa'], color='#1f77b4', linewidth=4.5, zorder=10, label=f'Selection: {rpm} rpm')
        else:
            # 배경 RPM 곡선: 연하게
            ax1.plot(data['CMH'], data['Pa'], color=distinct_colors[i % len(distinct_colors)], linewidth=1.2, alpha=0.4)
        
        surge_x.append(data['CMH'].iloc[0])
        surge_y.append(data['Pa'].iloc[0])
        ax1.text(data['CMH'].iloc[-1], data['Pa'].iloc[-1], f' {rpm}', color='gray', fontsize=9, fontweight='bold', alpha=0.6)

    ax1.plot(surge_x, surge_y, 'r--', linewidth=2.5, label='Surge Line')
    ax1.fill_betweenx(surge_y, 0, surge_x, color='red', alpha=0.07)
    
    # 상단 마킹 (선정 지점)
    ax1.axhline(user_pa, color='red', linestyle='-', linewidth=1.5, alpha=0.7)
    ax1.axvline(user_cmh, color='red', linestyle='-', linewidth=1.5, alpha=0.7)
    ax1.scatter(user_cmh, user_pa, color='red', s=150, edgecolors='white', marker='o', zorder=30)
    
    ax1.set_ylabel('Static Pressure (Pa)', fontsize=12)
    ax1.legend(loc='upper right', fontsize='small')
    ax1.grid(True, linestyle=':', alpha=0.5)

    # --- 하단 그래프 (Efficiency & Power) ---
    best_data = model_df[model_df['rpm'] == best_rpm]
    ax3 = ax2.twinx()
    
    # 효율 선 (초록색, 점 없음)
    ax2.plot(best_data['CMH'], best_data['total efficiency (%)'], color='green', linewidth=3, label='Efficiency (%)')
    # 동력 선 (보라색, 점 없음)
    ax3.plot(best_data['CMH'], best_data['power (kW)'], color='purple', linewidth=3, label='Power (kW)')
    
    # 하단 마킹 (선정 풍량 위치 세로선)
    ax2.axvline(user_cmh, color='red', linestyle='-', linewidth=1.5, alpha=0.7)
    
    ax2.set_xlabel('Air Flow (CMH)', fontsize=12)
    ax2.set_ylabel('Efficiency (%)', color='green', fontsize=12)
    ax3.set_ylabel('Power (kW)', color='purple', fontsize=12)
    
    # 축 범위 설정 (V5.3 중앙 정렬 로직 유지)
    x_limit = max(user_cmh * 1.6, model_df['CMH'].max() * 1.1)
    ax1.set_xlim(0, x_limit)
    ax1.set_ylim(0, max(user_pa * 1.6, model_df['Pa'].max() * 1.1))
    ax2.set_ylim(0, 100)
    
    ax2.grid(True, linestyle=':', alpha=0.5)
    
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=200)
    buf.seek(0)
    plt.close(fig)
    return buf

# [소음 그래프 및 PDF 생성 로직은 V5.6과 동일]
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
    fig, ax = plt.subplots(figsize=(12, 5))
    bars = ax.bar(found_labels, plot_values, color='skyblue', edgecolor='navy', alpha=0.8)
    ax.set_ylim(0, max(plot_values) + 25)
    ax.set_title('Noise Analysis (dB)', fontsize=15, fontweight='bold')
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=150)
    buf.seek(0)
    plt.close(fig)
    return buf

def create_pdf(model_info, user_cmh, user_pa, combined_buf, noise_buf, project_info):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    if os.path.exists("logo.png"): p.drawImage(ImageReader("logo.png"), w-160, h-60, width=110, height=35, preserveAspectRatio=True, mask='auto')
    p.setFont("Helvetica-Bold", 20); p.drawString(50, h-50, "Technical Selection Report")
    p.setFont("Helvetica", 10); p.drawString(50, h-80, f"Project: {project_info['project']} | Customer: {project_info['customer']}")
    # 이단 그래프 삽입 (사진처럼 길게 배치)
    p.drawImage(ImageReader(combined_buf), 40, h-750, width=520, height=650)
    p.showPage(); p.save(); buffer.seek(0)
    return buffer

# --- 메인 실행부 ---
df = load_my_data()
if df is not None:
    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    p_name = c1.text_input("Project", placeholder="English Only")
    c_name = c2.text_input("Customer", placeholder="English Only")
    m_name = c3.text_input("Manager", placeholder="English Only")
    p_date = c4.date_input("Date", datetime.now())

    c1, c2 = st.columns(2)
    u_cmh = c1.number_input("Flow (CMH)", value=115000)
    u_pa = c2.number_input("Pressure (Pa)", value=2100)

    matched = df[(df['CMH'] >= u_cmh) & (df['Pa'] >= u_pa)].copy()
    if not matched.empty:
        best_row = matched.sort_values(by=['CMH', 'Pa']).iloc[0]
        # V5.7 적층형 그래프 생성
        stacked_img = create_stacked_chart(df, best_row['model_name'], best_row['rpm'], u_cmh, u_pa)
        st.image(stacked_img, caption="Professional Catalog Map (Stacked)")
        
        noise_img = create_noise_chart(best_row)
        if noise_img: st.image(noise_img)

        proj_info = {"project": p_name, "customer": c_name, "manager": m_name, "date": p_date.strftime("%Y-%m-%d")}
        pdf_data = create_pdf(best_row, u_cmh, u_pa, stacked_img, noise_img, proj_info)
        st.download_button("📥 Download Final Report (V5.7)", pdf_data, f"Report_{p_name}.pdf")