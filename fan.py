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
st.set_page_config(page_title="루트에어 선정 시스템 V5.8", layout="wide")

# 1. 상단 레이아웃
col_logo, col_title = st.columns([1, 4])
with col_logo:
    if os.path.exists("logo.png"): st.image("logo.png", width=250)
    else: st.title("🏢")
with col_title:
    st.title("루트에어 송풍기 선정 시스템 V5.8")
    st.write("Single Integrated Map: All RPMs + Highlighted Curve")

# 2. 데이터 로드
def load_my_data():
    file_name = 'fan_performance_map_extended.csv'
    if not os.path.exists(file_name):
        file_name = 'fan_performance_map_full_sample.csv'
        if not os.path.exists(file_name): return None
    try: df = pd.read_csv(file_name, encoding='utf-8-sig')
    except: df = pd.read_csv(file_name, encoding='cp949')
    return df

# 3. 통합 그래프 생성 (하나의 차트에 모든 요소 삽입)
def create_unified_chart(all_df, selected_model, best_rpm, user_cmh, user_pa):
    model_df = all_df[all_df['model_name'] == selected_model].sort_values(by=['rpm', 'CMH'])
    rpms = sorted(model_df['rpm'].unique())
    
    fig, ax1 = plt.subplots(figsize=(12, 8))
    
    # 색상 설정
    distinct_colors = ['#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5', '#c49c94', '#f7b6d2', '#c7c7c7', '#dbdb8d', '#9edae5']
    surge_x, surge_y = [], []

    # 1. 모든 RPM 곡선 그리기
    for i, rpm in enumerate(rpms):
        data = model_df[model_df['rpm'] == rpm]
        
        if int(rpm) == int(best_rpm):
            # [강조] V3.2처럼 현재 선정된 RPM 곡선은 매우 굵고 진하게 (점 없이)
            ax1.plot(data['CMH'], data['Pa'], color='#1f77b4', linewidth=5, zorder=15, label=f'Selected: {rpm} rpm')
        else:
            # 배경 RPM 곡선들은 연하게 표시
            ax1.plot(data['CMH'], data['Pa'], color=distinct_colors[i % len(distinct_colors)], linewidth=1.5, alpha=0.35, zorder=5)
        
        # 서징 포인트 수집 및 RPM 텍스트
        surge_x.append(data['CMH'].iloc[0])
        surge_y.append(data['Pa'].iloc[0])
        ax1.text(data['CMH'].iloc[-1], data['Pa'].iloc[-1], f' {rpm}', color='gray', fontsize=9, fontweight='bold', alpha=0.5)

    # 2. 서징 라인 표시
    ax1.plot(surge_x, surge_y, 'r--', linewidth=2.5, label='Surge Line', zorder=20)
    ax1.fill_betweenx(surge_y, 0, surge_x, color='red', alpha=0.07, zorder=1)

    # 3. 선정 지점 가이드라인 (붉은 십자선 + 포인트)
    ax1.axhline(user_pa, color='red', linestyle='-', linewidth=1.5, alpha=0.8, zorder=25)
    ax1.axvline(user_cmh, color='red', linestyle='-', linewidth=1.5, alpha=0.8, zorder=25)
    ax1.scatter(user_cmh, user_pa, color='red', s=200, edgecolors='white', marker='o', linewidths=2, zorder=30, label='Design Point')

    # 4. 축 범위 및 라벨 (중앙 정렬)
    x_limit = max(user_cmh * 1.6, model_df['CMH'].max() * 1.1)
    y_limit = max(user_pa * 1.6, model_df['Pa'].max() * 1.1)
    ax1.set_xlim(0, x_limit)
    ax1.set_ylim(0, y_limit)
    
    ax1.set_xlabel('Air Flow (CMH)', fontsize=12)
    ax1.set_ylabel('Static Pressure (Pa)', fontsize=12)
    ax1.set_title(f"Selection Map: {selected_model}", fontsize=16, fontweight='bold', pad=20)
    
    ax1.legend(loc='upper right', fontsize='small', frameon=True)
    ax1.grid(True, linestyle=':', alpha=0.5)
    
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=200)
    buf.seek(0)
    plt.close(fig)
    return buf

# [소음 차트 및 PDF 생성 로직 유지]
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
    fig, ax = plt.subplots(figsize=(10, 5))
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
    p.setFont("Helvetica", 11)
    p.drawString(50, h-90, f"Project: {project_info['project']} | Customer: {project_info['customer']}")
    # 통합 그래프 삽입
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
        # 단일 통합 그래프 생성
        unified_img = create_unified_chart(df, best_row['model_name'], best_row['rpm'], u_cmh, u_pa)
        st.image(unified_img, caption="Integrated Performance Selection Map")
        
        noise_img = create_noise_chart(best_row)
        if noise_img: st.image(noise_img)

        proj_info = {"project": p_name, "customer": c_name, "manager": m_name, "date": p_date.strftime("%Y-%m-%d")}
        pdf_data = create_pdf(best_row, u_cmh, u_pa, unified_img, noise_img, proj_info)
        st.download_button("📥 Download Final Report (V5.8)", pdf_data, f"Report_{p_name}.pdf")