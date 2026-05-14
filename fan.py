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
st.set_page_config(page_title="루트에어 선정 시스템 V6.2", layout="wide")

# 1. 상단 레이아웃
col_logo, col_title = st.columns([1, 4])
with col_logo:
    if os.path.exists("logo.png"): st.image("logo.png", width=250)
    else: st.title("🏢")
with col_title:
    st.title("루트에어 송풍기 선정 시스템 V6.2")
    st.write("Final Master Version: Highlighted Selection Curve & Noise Data")

# 2. 데이터 로드
def load_my_data():
    # 확장 데이터 우선 로드
    file_name = 'fan_performance_map_extended.csv'
    if not os.path.exists(file_name):
        file_name = 'fan_performance_map_full_sample.csv'
        if not os.path.exists(file_name): return None
    try: df = pd.read_csv(file_name, encoding='utf-8-sig')
    except: df = pd.read_csv(file_name, encoding='cp949')
    return df

# 3. V6.2 그래프 생성: 파란색 강조 곡선 완벽 복구
def create_v6_2_chart(all_df, selected_model, best_rpm, user_cmh, user_pa):
    model_df = all_df[all_df['model_name'] == selected_model].sort_values(by=['rpm', 'CMH'])
    rpms = sorted(model_df['rpm'].unique())
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # 1. 배경 RPM 곡선 그리기 (연하게)
    for rpm in rpms:
        data = model_df[model_df['rpm'] == rpm]
        if int(rpm) != int(best_rpm):
            ax.plot(data['CMH'], data['Pa'], color='lightgray', linewidth=1.2, alpha=0.4, zorder=1)
            # RPM 라벨 표시
            ax.text(data['CMH'].iloc[-1], data['Pa'].iloc[-1], f' {int(rpm)} RPM', 
                    color='gray', fontsize=9, va='center', alpha=0.5)

    # 2. [핵심] 선정된 RPM 곡선만 굵은 파란색으로 덧그리기 (V3.2 스타일)
    selection_data = model_df[model_df['rpm'] == best_rpm]
    ax.plot(selection_data['CMH'], selection_data['Pa'], color='#1f77b4', linewidth=5, zorder=10, label=f'Selection: {best_rpm} RPM')
    ax.text(selection_data['CMH'].iloc[-1], selection_data['Pa'].iloc[-1], f' {int(best_rpm)} RPM', 
            color='#1f77b4', fontsize=10, va='center', fontweight='bold', zorder=11)

    # 3. 서징 라인 및 영역
    surge_x = [model_df[model_df['rpm'] == r]['CMH'].iloc[0] for r in rpms]
    surge_y = [model_df[model_df['rpm'] == r]['Pa'].iloc[0] for r in rpms]
    ax.plot(surge_x, surge_y, 'r--', linewidth=2.5, label='Surge Line', zorder=15)
    ax.fill_betweenx(surge_y, 0, surge_x, color='red', alpha=0.07, zorder=0)

    # 4. 선정 지점 마킹 (붉은 십자선 + 포인트)
    ax.axvline(user_cmh, color='red', linestyle='-', linewidth=1.5, alpha=0.6, zorder=20)
    ax.axhline(user_pa, color='red', linestyle='-', linewidth=1.5, alpha=0.6, zorder=20)
    ax.scatter(user_cmh, user_pa, color='red', s=180, edgecolors='white', marker='o', linewidths=2, zorder=30, label='Design Point')

    # 축 설정 및 중앙 정렬
    x_limit = max(user_cmh * 1.6, model_df['CMH'].max() * 1.1)
    y_limit = max(user_pa * 1.6, model_df['Pa'].max() * 1.1)
    ax.set_xlim(0, x_limit); ax.set_ylim(0, y_limit)
    ax.set_xlabel('Air Flow (CMH)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Static Pressure (Pa)', fontsize=12, fontweight='bold')
    ax.set_title(f"Technical Analysis: {selected_model}", fontsize=16, fontweight='bold', pad=20)
    ax.grid(True, linestyle=':', alpha=0.5)
    ax.legend(loc='upper right')
    
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=200)
    buf.seek(0)
    plt.close(fig)
    return buf

# 4. 소음 차트 생성 함수 (복구)
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
    
    buf = BytesIO(); plt.savefig(buf, format='png', dpi=150); buf.seek(0); plt.close(fig)
    return buf

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

    # 선정 모델 자동 매칭 (연습용: CMH/Pa 만족하는 첫 모델)
    matched = df[(df['CMH'] >= u_cmh) & (df['Pa'] >= u_pa)].copy()
    if not matched.empty:
        best_row = matched.sort_values(by=['CMH', 'Pa']).iloc[0]
        selected_model = best_row['model_name']
        best_rpm = best_row['rpm']
        
        # 그래프 출력
        chart_img = create_v6_2_chart(df, selected_model, best_rpm, u_cmh, u_pa)
        st.image(chart_img, caption="Technical Selection Map V6.2")
        
        # 소음 분석 출력
        st.subheader("🔊 [2] Noise Data Summary")
        noise_img = create_noise_chart(best_row)
        if noise_img: st.image(noise_img)
        
        # PDF 다운로드 로직 (기존과 동일)
        st.success(f"Selected: {selected_model} at {best_rpm} RPM")
    else:
        st.warning("No matching model found in the database.")
else:
    st.error("데이터 파일을 찾을 수 없습니다.")