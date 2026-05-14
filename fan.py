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
st.set_page_config(page_title="루트에어 선정 시스템 V6.1", layout="wide")

# 1. 상단 레이아웃
col_logo, col_title = st.columns([1, 4])
with col_logo:
    if os.path.exists("logo.png"): st.image("logo.png", width=250)
    else: st.title("🏢")
with col_title:
    st.title("루트에어 송풍기 선정 시스템 V6.1")
    st.write("Final Integrated Selection Map & Noise Analysis")

# 2. 데이터 로드
def load_my_data():
    file_name = 'fan_performance_map_extended.csv'
    if not os.path.exists(file_name):
        file_name = 'fan_performance_map_full_sample.csv'
        if not os.path.exists(file_name): return None
    try: df = pd.read_csv(file_name, encoding='utf-8-sig')
    except: df = pd.read_csv(file_name, encoding='cp949')
    return df

# 3. V6.1 그래프 생성: 강조선 + RPM 라벨(단위포함) + 서징/포인트 유지
def create_v6_1_chart(all_df, selected_model, best_rpm, user_cmh, user_pa):
    model_df = all_df[all_df['model_name'] == selected_model].sort_values(by=['rpm', 'CMH'])
    rpms = sorted(model_df['rpm'].unique())
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # 색상 테마
    colors = plt.cm.Blues(np.linspace(0.4, 0.8, len(rpms)))
    surge_x, surge_y = [], []

    # 1. RPM 곡선 그리기
    for i, rpm in enumerate(rpms):
        data = model_df[model_df['rpm'] == rpm]
        
        # [요청 1] 선정된 RPM 곡선은 V3.2처럼 굵은 파란색 선으로 유지
        if int(rpm) == int(best_rpm):
            color, linewidth, alpha, zorder = '#1f77b4', 4.5, 1.0, 10
        else:
            color, linewidth, alpha, zorder = colors[i], 1.2, 0.4, 1
            
        ax.plot(data['CMH'], data['Pa'], color=color, linewidth=linewidth, alpha=alpha, zorder=zorder)
        
        # [요청 3] RPM 숫자 뒤에 'RPM' 단위 추가
        ax.text(data['CMH'].iloc[-1], data['Pa'].iloc[-1], f' {int(rpm)} RPM', 
                color=color, fontsize=9, va='center', fontweight='bold', alpha=alpha+0.2 if alpha < 1 else 1)
        
        surge_x.append(data['CMH'].iloc[0])
        surge_y.append(data['Pa'].iloc[0])

    # 2. [요청 2] 서징 영역 및 선전포인트 붉은선/점 유지
    ax.plot(surge_x, surge_y, 'r--', linewidth=2.5, label='Surge Line', zorder=15)
    ax.fill_betweenx(surge_y, 0, surge_x, color='red', alpha=0.07, zorder=0)

    # 설계 지점 강조 (붉은 십자선 + 포인트)
    ax.axvline(user_cmh, color='red', linestyle='-', linewidth=1.5, alpha=0.6, zorder=20)
    ax.axhline(user_pa, color='red', linestyle='-', linewidth=1.5, alpha=0.6, zorder=20)
    ax.scatter(user_cmh, user_pa, color='red', s=180, edgecolors='white', marker='o', linewidths=2, zorder=30, label='Design Point')

    # 축 범위 및 설정
    x_limit = max(user_cmh * 1.6, model_df['CMH'].max() * 1.1)
    y_limit = max(user_pa * 1.6, model_df['Pa'].max() * 1.1)
    ax.set_xlim(0, x_limit)
    ax.set_ylim(0, y_limit)
    ax.set_xlabel('Air Flow (CMH)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Static Pressure (Pa)', fontsize=12, fontweight='bold')
    ax.set_title(f"Technical Selection: {selected_model}", fontsize=16, fontweight='bold', pad=20)
    ax.grid(True, linestyle=':', alpha=0.5)
    ax.legend(loc='upper right')
    
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=200)
    buf.seek(0)
    plt.close(fig)
    return buf

# 4. [요청 4] 소음 자료 차트 재생성
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
    bars = ax.bar(found_labels, plot_values, color='skyblue', edgecolor='navy', alpha=0.8)
    ax.set_ylim(0, max(plot_values) + 20)
    ax.set_title('Octave Band Noise Analysis (dB)', fontsize=14, fontweight='bold')
    for bar in bars:
        ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 1, f'{int(bar.get_height())}', ha='center', va='bottom', fontweight='bold')
    
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=150)
    buf.seek(0)
    plt.close(fig)
    return buf

# [PDF 생성 로직 생략 - 이전 V6.0과 동일하게 유지]

# --- 메인 실행부 ---
df = load_my_data()
if df is not None:
    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    p_name = c1.text_input("Project Name")
    c_name = c2.text_input("Customer")
    m_name = c3.text_input("Manager")
    p_date = c4.date_input("Date", datetime.now())

    c1, c2 = st.columns(2)
    u_cmh = c1.number_input("Design Flow (CMH)", value=115000)
    u_pa = c2.number_input("Design Pressure (Pa)", value=2100)

    matched = df[(df['CMH'] >= u_cmh) & (df['Pa'] >= u_pa)].copy()
    if not matched.empty:
        best_row = matched.sort_values(by=['CMH', 'Pa']).iloc[0]
        
        # V6.1 그래프 및 소음 차트 출력
        chart_img = create_v6_1_chart(df, best_row['model_name'], best_row['rpm'], u_cmh, u_pa)
        st.image(chart_img, caption="Integrated Technical Selection Map V6.1")
        
        st.subheader("🔊 [2] Noise Data Summary")
        noise_img = create_noise_chart(best_row)
        if noise_img:
            st.image(noise_img)
        
        # PDF 다운로드 버튼 등 나머지 로직...
    else:
        st.warning("No matching model found.")