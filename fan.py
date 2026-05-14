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
st.set_page_config(page_title="루트에어 선정 시스템 V5.9", layout="wide")

# 1. 상단 레이아웃
col_logo, col_title = st.columns([1, 4])
with col_logo:
    if os.path.exists("logo.png"): st.image("logo.png", width=250)
    else: st.title("🏢")
with col_title:
    st.title("루트에어 송풍기 선정 시스템 V5.9")
    st.write("All-in-One Integrated Map (Pressure, Power, Efficiency)")

# 2. 데이터 로드
def load_my_data():
    file_name = 'fan_performance_map_extended.csv'
    if not os.path.exists(file_name):
        file_name = 'fan_performance_map_full_sample.csv'
        if not os.path.exists(file_name): return None
    try: df = pd.read_csv(file_name, encoding='utf-8-sig')
    except: df = pd.read_csv(file_name, encoding='cp949')
    return df

# 3. 사진 요청사항 반영: 모든 지표 통합 그래프 생성
def create_all_in_one_chart(all_df, selected_model, best_rpm, user_cmh, user_pa):
    model_df = all_df[all_df['model_name'] == selected_model].sort_values(by=['rpm', 'CMH'])
    rpms = sorted(model_df['rpm'].unique())
    
    fig, ax1 = plt.subplots(figsize=(12, 8))
    ax2 = ax1.twinx() # 효율/동력을 위한 보조 Y축
    
    distinct_colors = ['#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5', '#c49c94', '#f7b6d2', '#c7c7c7', '#dbdb8d', '#9edae5']
    surge_x, surge_y = [], []

    # 1. 배경: 모든 RPM 정압 곡선
    for i, rpm in enumerate(rpms):
        data = model_df[model_df['rpm'] == rpm]
        if int(rpm) == int(best_rpm):
            # 선정된 정압 곡선 (굵게)
            ax1.plot(data['CMH'], data['Pa'], color='#1f77b4', linewidth=4, zorder=10, label=f'P-Q Curve ({rpm} rpm)')
            
            # [복구 및 추가] 사진 속 초록색 선처럼 효율과 동력을 겹쳐 그리기
            ax2.plot(data['CMH'], data['total efficiency (%)'], color='green', linestyle='--', linewidth=2, alpha=0.8, label='Efficiency (%)')
            ax2.plot(data['CMH'], data['power (kW)'], color='purple', linestyle=':', linewidth=2, alpha=0.8, label='Power (kW)')
        else:
            # 배경 곡선 (연하게)
            ax1.plot(data['CMH'], data['Pa'], color=distinct_colors[i % len(distinct_colors)], linewidth=1, alpha=0.3)
        
        surge_x.append(data['CMH'].iloc[0])
        surge_y.append(data['Pa'].iloc[0])

    # 2. 서징 라인
    ax1.plot(surge_x, surge_y, 'r--', linewidth=2, label='Surge Line', zorder=5)
    ax1.fill_betweenx(surge_y, 0, surge_x, color='red', alpha=0.05)

    # 3. 선정 지점 마킹 (붉은 십자선 + 포인트)
    ax1.axhline(user_pa, color='red', linestyle='-', linewidth=1.5, alpha=0.6, zorder=20)
    ax1.axvline(user_cmh, color='red', linestyle='-', linewidth=1.5, alpha=0.6, zorder=20)
    ax1.scatter(user_cmh, user_pa, color='red', s=150, edgecolors='white', marker='o', zorder=30, label='Design Point')

    # 4. 축 설정
    x_limit = max(user_cmh * 1.6, model_df['CMH'].max() * 1.1)
    ax1.set_xlim(0, x_limit)
    ax1.set_ylim(0, max(user_pa * 1.6, model_df['Pa'].max() * 1.1))
    ax2.set_ylim(0, 100) # 효율/동력축 범위

    ax1.set_xlabel('Air Flow (CMH)', fontsize=12)
    ax1.set_ylabel('Static Pressure (Pa)', fontsize=12)
    ax2.set_ylabel('Efficiency (%) / Power (kW)', fontsize=12, color='darkgreen')
    ax1.set_title(f"Comprehensive Selection Map: {selected_model}", fontsize=16, fontweight='bold', pad=20)
    
    # 범례 통합 표시
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right', fontsize='small')
    
    ax1.grid(True, linestyle=':', alpha=0.5)
    plt.tight_layout()
    
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=200)
    buf.seek(0)
    plt.close(fig)
    return buf

# [이하 소음 및 PDF 로직은 V5.8과 동일]
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
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.bar(found_labels, plot_values, color='skyblue', edgecolor='navy')
    ax.set_title('Noise Data (dB)')
    buf = BytesIO(); plt.savefig(buf, format='png', dpi=150); buf.seek(0); plt.close(fig)
    return buf

def create_pdf(model_info, user_cmh, user_pa, chart_buf, noise_buf, project_info):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    if os.path.exists("logo.png"): p.drawImage(ImageReader("logo.png"), w-160, h-60, width=110, height=35, mask='auto')
    p.setFont("Helvetica-Bold", 20); p.drawString(50, h-50, "Technical Selection Report")
    p.drawImage(ImageReader(chart_buf), 40, h-600, width=520, height=380)
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
        # 통합 차트 생성
        unified_img = create_all_in_one_chart(df, best_row['model_name'], best_row['rpm'], u_cmh, u_pa)
        st.image(unified_img)
        
        noise_img = create_noise_chart(best_row)
        if noise_img: st.image(noise_img)

        proj_info = {"project": p_name, "customer": c_name, "manager": m_name, "date": p_date.strftime("%Y-%m-%d")}
        pdf_data = create_pdf(best_row, u_cmh, u_pa, unified_img, noise_img, proj_info)
        st.download_button("📥 Download Final Report (V5.9)", pdf_data, f"Report_{p_name}.pdf")