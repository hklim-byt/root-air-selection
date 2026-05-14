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
st.set_page_config(page_title="루트에어 종합 선정 시스템 V5.5", layout="wide")

# 1. 상단 레이아웃
col_logo, col_title = st.columns([1, 4])
with col_logo:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=250)
    else:
        st.title("🏢")
with col_title:
    st.markdown("###")
    st.title("루트에어 송풍기 선정 시스템 V5.5")
    st.write("Dual Chart Layout (Pressure-Flow & Power-Efficiency)")

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

# 3. 이단 분리 그래프 생성 (상단: 정압-풍량 / 하단: 동력/효율-풍량)
def create_dual_charts(all_df, selected_model, best_rpm, user_cmh, user_pa):
    model_df = all_df[all_df['model_name'] == selected_model].sort_values(by=['rpm', 'CMH'])
    rpms = sorted(model_df['rpm'].unique())
    
    # 두 개의 서브플롯 생성 (상하 배치)
    fig, (ax_p, ax_e) = plt.subplots(2, 1, figsize=(12, 14), gridspec_kw={'height_ratios': [1.2, 1]})
    
    distinct_colors = ['#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5', '#c49c94', '#f7b6d2', '#c7c7c7', '#dbdb8d', '#9edae5']
    surge_x, surge_y = [], []

    # --- 상단 그래프: 정압 곡선 (P-Q Curve) ---
    for i, rpm in enumerate(rpms):
        data = model_df[model_df['rpm'] == rpm]
        if int(rpm) == int(best_rpm):
            color, linewidth, alpha = '#1f77b4', 4.0, 1.0
            label_txt = f'Selection: {rpm} rpm'
        else:
            color, linewidth, alpha = distinct_colors[i % len(distinct_colors)], 1.5, 0.4
            label_txt = f'{rpm} rpm'
            
        ax_p.plot(data['CMH'], data['Pa'], color=color, label=label_txt, linewidth=linewidth, alpha=alpha)
        surge_x.append(data['CMH'].iloc[0])
        surge_y.append(data['Pa'].iloc[0])
        ax_p.text(data['CMH'].iloc[-1], data['Pa'].iloc[-1], f' {rpm}', color=color, fontsize=9, va='center', fontweight='bold', alpha=alpha)

    ax_p.plot(surge_x, surge_y, 'r--', linewidth=2, label='Surge Line')
    ax_p.fill_betweenx(surge_y, 0, surge_x, color='red', alpha=0.05)
    
    # 상단 축 범위 및 가이드라인
    x_limit = max(user_cmh * 1.6, model_df['CMH'].max() * 1.1)
    ax_p.set_xlim(0, x_limit)
    ax_p.set_ylim(0, max(user_pa * 1.6, model_df['Pa'].max() * 1.1))
    ax_p.axhline(user_pa, color='red', linestyle='-', linewidth=1.2, alpha=0.5)
    ax_p.axvline(user_cmh, color='red', linestyle='-', linewidth=1.2, alpha=0.5)
    ax_p.scatter(user_cmh, user_pa, color='red', s=150, edgecolors='white', marker='o', zorder=30)
    ax_p.set_ylabel('Static Pressure (Pa)', fontsize=12)
    ax_p.set_title(f"Performance Map: {selected_model}", fontsize=15, fontweight='bold')
    ax_p.legend(loc='upper right', fontsize='small')
    ax_p.grid(True, linestyle=':', alpha=0.6)

    # --- 하단 그래프: 동력/효율 곡선 (Power & Efficiency) ---
    best_rpm_data = model_df[model_df['rpm'] == best_rpm]
    ax_e2 = ax_e.twinx()
    
    line_eff = ax_e.plot(best_rpm_data['CMH'], best_rpm_data['total efficiency (%)'], color='green', marker='s', markersize=4, label='Efficiency (%)', linewidth=2.5)
    line_pow = ax_e2.plot(best_rpm_data['CMH'], best_rpm_data['power (kW)'], color='purple', marker='^', markersize=4, label='Power (kW)', linewidth=2.5)
    
    ax_e.axvline(user_cmh, color='red', linestyle='-', linewidth=1.2, alpha=0.5)
    ax_e.set_xlim(0, x_limit)
    ax_e.set_ylim(0, 100)
    ax_e.set_xlabel('Air Flow (CMH)', fontsize=12)
    ax_e.set_ylabel('Efficiency (%)', fontsize=12, color='green')
    ax_e2.set_ylabel('Power (kW)', fontsize=12, color='purple')
    ax_e.set_title(f"Power & Efficiency at {best_rpm} rpm", fontsize=14, fontweight='bold')
    ax_e.grid(True, linestyle=':', alpha=0.6)

    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=200)
    buf.seek(0)
    plt.close(fig)
    return buf

# 4. 소음 그래프 (V5.1 유지)
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
    ax.set_title('Octave Band Noise Analysis (dB)', fontsize=15, fontweight='bold')
    for bar in bars:
        ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 1, f'{int(bar.get_height())}', ha='center', va='bottom', fontweight='bold')
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=200)
    buf.seek(0)
    plt.close(fig)
    return buf

# 5. PDF 생성 (이단 그래프 배치 조정)
def create_pdf(model_info, user_cmh, user_pa, dual_buf, noise_buf, project_info):
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
    
    # 텍스트 요약
    p.setFont("Helvetica-Bold", 13)
    p.drawString(50, h - 140, f"[1] Spec: {model_info['model_name']} ({model_info['rpm']} rpm)")
    p.setFont("Helvetica", 11)
    p.drawString(60, h - 160, f"- Flow: {user_cmh} CMH / Pressure: {user_pa} Pa / Power: {model_info['power (kW)']} kW")

    # 이단 그래프 삽입 (높이를 충분히 확보)
    p.drawImage(ImageReader(dual_buf), 40, h - 810, width=520, height=630)
    p.showPage()
    
    if noise_buf:
        if os.path.exists("logo.png"):
            p.drawImage(ImageReader("logo.png"), w - 160, h - 60, width=110, height=35, preserveAspectRatio=True, mask='auto')
        p.setFont("Helvetica-Bold", 22)
        p.drawString(50, h - 50, "Acoustic Analysis Report")
        p.drawImage(ImageReader(noise_buf), 50, h - 450, width=500, height=280)
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
        # 이단 그래프 생성
        dual_img = create_dual_charts(df, best_row['model_name'], best_row['rpm'], u_cmh, u_pa)
        st.image(dual_img)
        
        noise_img = create_noise_chart(best_row)
        if noise_img: st.image(noise_img)

        proj_info = {"project": p_name if p_name else "N/A", "customer": c_name if c_name else "N/A", "manager": m_name if m_name else "N/A", "date": p_date.strftime("%Y-%m-%d")}
        pdf_data = create_pdf(best_row, u_cmh, u_pa, dual_img, noise_img, proj_info)
        st.download_button("📥 Download Final Selection Report (V5.5)", pdf_data, f"Report_{p_name}.pdf")
    else:
        st.warning("No matching model found.")