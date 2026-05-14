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
st.set_page_config(page_title="루트에어 종합 선정 시스템 V5.4", layout="wide")

# 1. 상단 레이아웃
col_logo, col_title = st.columns([1, 4])
with col_logo:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=250)
    else:
        st.title("🏢")
with col_title:
    st.markdown("###")
    st.title("루트에어 송풍기 선정 시스템 V5.4")
    st.write("Highlighted Selection Curve & Professional Map")

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

# 3. 종합 성능 맵 생성 (선정된 풍량 곡선 강조 로직)
def create_combined_chart(all_df, selected_model, best_rpm, user_cmh, user_pa):
    model_df = all_df[all_df['model_name'] == selected_model].sort_values(by=['rpm', 'CMH'])
    rpms = sorted(model_df['rpm'].unique())
    
    fig, ax1 = plt.subplots(figsize=(12, 8))
    
    distinct_colors = ['#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5', '#c49c94', '#f7b6d2', '#c7c7c7', '#dbdb8d', '#9edae5']
    surge_x, surge_y = [], []

    # 1. 모든 RPM 곡선 그리기 (연하게)
    for i, rpm in enumerate(rpms):
        data = model_df[model_df['rpm'] == rpm]
        
        # [핵심] 선정된 RPM 곡선은 특별히 강조 (V3.2 느낌 복원)
        if int(rpm) == int(best_rpm):
            color = '#1f77b4' # 진한 파란색
            linewidth = 4.0
            alpha = 1.0
            label_txt = f'Selection: {rpm} rpm'
        else:
            color = distinct_colors[i % len(distinct_colors)]
            linewidth = 1.5
            alpha = 0.4 # 나머지 선들은 연하게 처리
            label_txt = f'{rpm} rpm'
            
        ax1.plot(data['CMH'], data['Pa'], color=color, label=label_txt, linewidth=linewidth, alpha=alpha)
        surge_x.append(data['CMH'].iloc[0])
        surge_y.append(data['Pa'].iloc[0])
        
        # RPM 텍스트 표시
        ax1.text(data['CMH'].iloc[-1], data['Pa'].iloc[-1], f' {rpm}', color=color, fontsize=9, va='center', fontweight='bold', alpha=alpha)

    # 2. 서징 라인
    ax1.plot(surge_x, surge_y, 'r--', linewidth=2, label='Surge Line')
    ax1.fill_betweenx(surge_y, 0, surge_x, color='red', alpha=0.05)
    
    # 3. 축 범위 설정 (V5.3 중앙 정렬 유지)
    x_limit = max(user_cmh * 1.6, model_df['CMH'].max() * 1.1)
    y_limit = max(user_pa * 1.6, model_df['Pa'].max() * 1.1)
    ax1.set_xlim(0, x_limit)
    ax1.set_ylim(0, y_limit)

    # 4. 선정 지점 가이드라인 및 마킹 (붉은 십자선 + 동그라미)
    ax1.axhline(user_pa, color='red', linestyle='-', linewidth=1.5, alpha=0.6, zorder=25)
    ax1.axvline(user_cmh, color='red', linestyle='-', linewidth=1.5, alpha=0.6, zorder=25)
    ax1.scatter(user_cmh, user_pa, color='red', s=180, edgecolors='white', marker='o', linewidths=2, zorder=30, label='Design Point')

    ax1.set_xlabel('Air Flow (CMH)', fontsize=12)
    ax1.set_ylabel('Static Pressure (Pa)', fontsize=12)
    ax1.set_title(f"Highlighted Performance Map: {selected_model}", fontsize=16, fontweight='bold', pad=20)
    
    ax1.legend(loc='upper right', fontsize='small', frameon=True)
    ax1.grid(True, linestyle=':', alpha=0.6)
    
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=200)
    buf.seek(0)
    plt.close(fig)
    return buf

# 4. 소음 그래프
def create_noise_chart(noise_row):
    bands_labels = ['63', '125', '250', '500', '1k', '2k', '4k', '8k']
    plot_values = []
    found_labels = []
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

# 5. PDF 생성 (스펙 요약 포함)
def draw_table(p, x, y, headers, data):
    cell_width = 54
    cell_height = 25
    p.setFont("Helvetica-Bold", 8)
    for i, h in enumerate(headers):
        p.rect(x + (i * cell_width), y, cell_width, cell_height)
        p.drawCentredString(x + (i * cell_width) + cell_width/2, y + 8, h)
    p.setFont("Helvetica", 8)
    for i, v in enumerate(data):
        p.rect(x + (i * cell_width), y - cell_height, cell_width, cell_height)
        p.drawCentredString(x + (i * cell_width) + cell_width/2, y - cell_height + 8, str(v))

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
    p.drawString(50, h - 90, f"Project: {project_info['project']}")
    p.drawString(50, h - 105, f"Customer: {project_info['customer']}")
    p.drawString(50, h - 120, f"Engineer: {project_info['manager']}")
    p.drawString(50, h - 135, f"Date: {project_info['date']}")
    
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, h - 170, "[1] Technical Specifications")
    p.setFont("Helvetica", 12)
    p.drawString(60, h - 195, f"- Model Name: {model_info['model_name']}")
    p.drawString(60, h - 215, f"- Operation RPM: {model_info['rpm']} rpm")
    p.drawString(60, h - 235, f"- Design Duty: {user_cmh} CMH @ {user_pa} Pa")
    
    eff_total = model_info['total efficiency (%)'] if 'total efficiency (%)' in model_info else "-"
    p.drawString(60, h - 255, f"- Total Efficiency: {eff_total} %")
    p.drawString(60, h - 275, f"- Shaft Power: {model_info['power (kW)']} kW")
    
    p.drawImage(ImageReader(combined_buf), 40, h - 710, width=520, height=420)
    p.showPage()
    
    if noise_buf:
        if os.path.exists("logo.png"):
            p.drawImage(ImageReader("logo.png"), w - 160, h - 60, width=110, height=35, preserveAspectRatio=True, mask='auto')
        p.setFont("Helvetica-Bold", 22)
        p.drawString(50, h - 50, "Acoustic Analysis Report")
        p.line(50, h - 65, 550, h - 65)
        p.setFont("Helvetica-Bold", 14)
        p.drawString(50, h - 100, "[2] Noise Data Summary (dB / dB(A))")
        
        bands_labels = ['63Hz', '125Hz', '250Hz', '500Hz', '1kHz', '2kHz', '4kHz', '8kHz']
        headers = bands_labels + ['Total']
        data_vals = []
        for lbl in bands_labels:
            col = [c for c in model_info.index if lbl in c]
            data_vals.append(model_info[col[0]] if col else "-")
        total_col = [c for c in model_info.index if 'Total' in c]
        data_vals.append(model_info[total_col[0]] if total_col else "-")
        
        draw_table(p, 50, h - 150, headers, data_vals)
        p.drawImage(ImageReader(noise_buf), 50, h - 500, width=500, height=300)
        
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

    # 선정 로직 (V3.2 방식 복원: 가장 근접한 RPM 찾기)
    matched = df[(df['CMH'] >= u_cmh) & (df['Pa'] >= u_pa)].copy()
    if not matched.empty:
        best_row = matched.sort_values(by=['CMH', 'Pa']).iloc[0]
        selected_model = best_row['model_name']
        best_rpm = best_row['rpm']
        
        st.success(f"Best Match: **{selected_model}** (Selection RPM: **{best_rpm}**)")
        
        # 맵 생성 (선정된 RPM 곡선 강조 로직 적용)
        combined_img = create_combined_chart(df, selected_model, best_rpm, u_cmh, u_pa)
        st.image(combined_img)
        
        noise_img = create_noise_chart(best_row)
        if noise_img:
            st.subheader("📊 [2] Noise Data Summary (dB / dB(A))")
            st.image(noise_img)

        proj_info = {"project": p_name, "customer": c_name, "manager": m_name, "date": p_date.strftime("%Y-%m-%d")}
        pdf_data = create_pdf(best_row, u_cmh, u_pa, combined_img, noise_img, proj_info)
        st.download_button("📥 Download Final Technical Selection Report (V5.4)", pdf_data, f"Report_{p_name}.pdf")
    else:
        st.warning("No matching model found in the extended database.")
else:
    st.error("데이터 파일을 로드할 수 없습니다.")