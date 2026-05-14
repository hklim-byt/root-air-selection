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
st.set_page_config(page_title="루트에어 선정 시스템 V6.3", layout="wide")

# 1. 상단 로고 및 타이틀
col_logo, col_title = st.columns([1, 4])
with col_logo:
    if os.path.exists("logo.png"): st.image("logo.png", width=250)
    else: st.title("🏢")
with col_title:
    st.title("루트에어 송풍기 선정 시스템 V6.3")
    st.write("Performance Map with Static Pressure & Flow Guide")

# 2. 데이터 로드
def load_my_data():
    file_name = 'fan_performance_map_extended.csv'
    if not os.path.exists(file_name):
        file_name = 'fan_performance_map_full_sample.csv'
        if not os.path.exists(file_name): return None
    try: df = pd.read_csv(file_name, encoding='utf-8-sig')
    except: df = pd.read_csv(file_name, encoding='cp949')
    return df

# 3. V6.3 그래프 생성: RPM 맵(배경) + 정압/풍량 가이드선 강조
def create_v6_3_chart(all_df, selected_model, best_rpm, user_cmh, user_pa):
    model_df = all_df[all_df['model_name'] == selected_model].sort_values(by=['rpm', 'CMH'])
    rpms = sorted(model_df['rpm'].unique())
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # 1. 배경 RPM 곡선 (강조 없이 연하게 표시)
    for rpm in rpms:
        data = model_df[model_df['rpm'] == rpm]
        # 모든 RPM 선을 동일한 굵기와 연한 색상으로 처리
        ax.plot(data['CMH'], data['Pa'], color='steelblue', linewidth=1.0, alpha=0.3, zorder=1)
        # RPM 라벨 표시 (단위 포함)
        ax.text(data['CMH'].iloc[-1], data['Pa'].iloc[-1], f' {int(rpm)} RPM', 
                color='steelblue', fontsize=9, va='center', alpha=0.4)

    # 2. 서징 라인 및 영역
    surge_x = [model_df[model_df['rpm'] == r]['CMH'].iloc[0] for r in rpms]
    surge_y = [model_df[model_df['rpm'] == r]['Pa'].iloc[0] for r in rpms]
    ax.plot(surge_x, surge_y, 'r--', linewidth=2.0, label='Surge Line', zorder=5)
    ax.fill_betweenx(surge_y, 0, surge_x, color='red', alpha=0.05, zorder=0)

    # 3. [핵심 요청] 정압별 풍량 그래프 가이드 (V3.2 스타일 강조)
    # 선정 정압(Pa) 수평선 - 바닥부터 해당 지점까지의 위치 확인용
    ax.axhline(user_pa, color='blue', linestyle='--', linewidth=2.0, alpha=0.7, zorder=15, label=f'Design Pressure: {user_pa} Pa')
    # 선정 풍량(CMH) 수직선 - 바닥(0)부터 위쪽 끝까지 풍량 위치 표시
    ax.axvline(user_cmh, color='darkgreen', linestyle='-', linewidth=2.5, alpha=0.8, zorder=20, label=f'Design Flow: {user_cmh} CMH')
    
    # 4. 선정 지점 포인트 (붉은 동그라미)
    ax.scatter(user_cmh, user_pa, color='red', s=180, edgecolors='white', marker='o', linewidths=2, zorder=30, label='Selection Point')

    # 축 설정 및 중앙 정렬
    x_limit = max(user_cmh * 1.6, model_df['CMH'].max() * 1.1)
    y_limit = max(user_pa * 1.6, model_df['Pa'].max() * 1.1)
    ax.set_xlim(0, x_limit); ax.set_ylim(0, y_limit)
    
    ax.set_xlabel('Air Flow (CMH)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Static Pressure (Pa)', fontsize=12, fontweight='bold')
    ax.set_title(f"Technical Performance Map: {selected_model}", fontsize=16, fontweight='bold', pad=20)
    ax.grid(True, linestyle=':', alpha=0.5)
    ax.legend(loc='upper right', fontsize='small')
    
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=200)
    buf.seek(0)
    plt.close(fig)
    return buf

# 4. 소음 분석 차트 (V3.2 스타일 복구)
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
    ax.bar(found_labels, plot_values, color='skyblue', edgecolor='navy', alpha=0.8)
    ax.set_ylim(0, max(plot_values) + 20)
    ax.set_title('Octave Band Noise Analysis (dB)', fontsize=14, fontweight='bold')
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

    # 선정 로직
    matched = df[(df['CMH'] >= u_cmh) & (df['Pa'] >= u_pa)].copy()
    if not matched.empty:
        best_row = matched.sort_values(by=['CMH', 'Pa']).iloc[0]
        
        # V6.3 그래프 출력
        chart_img = create_v6_3_chart(df, best_row['model_name'], best_row['rpm'], u_cmh, u_pa)
        st.image(chart_img, caption="V6.3 Final Performance Selection Map")
        
        # 소음 분석 출력
        st.subheader("🔊 [2] Noise Data Summary")
        noise_img = create_noise_chart(best_row)
        if noise_img: st.image(noise_img)
    else:
        st.warning("No matching model found.")