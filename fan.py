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
st.set_page_config(page_title="루트에어 선정 시스템 V6.5", layout="wide")

# 1. 상단 레이아웃
col_logo, col_title = st.columns([1, 4])
with col_logo:
    if os.path.exists("logo.png"): st.image("logo.png", width=250)
    else: st.title("🏢")
with col_title:
    st.title("루트에어 송풍기 선정 시스템 V6.5")
    st.write("Final Master: System Curve (from 0,0) & Enhanced RPM Map")

# 2. 데이터 로드
def load_my_data():
    file_name = 'fan_performance_map_extended.csv'
    if not os.path.exists(file_name):
        file_name = 'fan_performance_map_full_sample.csv'
        if not os.path.exists(file_name): return None
    try: df = pd.read_csv(file_name, encoding='utf-8-sig')
    except: df = pd.read_csv(file_name, encoding='cp949')
    return df

# 3. V6.5 그래프 생성: (0,0) 시작 저항 곡선 + 선명한 RPM 맵
def create_v6_5_chart(all_df, selected_model, user_cmh, user_pa):
    model_df = all_df[all_df['model_name'] == selected_model].sort_values(by=['rpm', 'CMH'])
    rpms = sorted(model_df['rpm'].unique())
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # [수정 3] RPM 곡선 선명도 강화 (Alpha 상향 및 색상 진하게)
    for rpm in rpms:
        data = model_df[model_df['rpm'] == rpm]
        ax.plot(data['CMH'], data['Pa'], color='steelblue', linewidth=1.2, alpha=0.5, zorder=1)
        ax.text(data['CMH'].iloc[-1], data['Pa'].iloc[-1], f' {int(rpm)} RPM', 
                color='steelblue', fontsize=9, va='center', fontweight='bold', alpha=0.7)

    # 1. 서징 라인
    surge_x = [model_df[model_df['rpm'] == r]['CMH'].iloc[0] for r in rpms]
    surge_y = [model_df[model_df['rpm'] == r]['Pa'].iloc[0] for r in rpms]
    ax.plot(surge_x, surge_y, 'r--', linewidth=2.5, label='Surge Line', zorder=5)
    ax.fill_betweenx(surge_y, 0, surge_x, color='red', alpha=0.07, zorder=0)

    # [수정 1, 2] 저항 곡선 최적화: (0,0)에서 고정 시작, 마커 제거
    # 포물선 방정식: P = k * Q^2 (k = user_pa / user_cmh^2)
    x_path = np.linspace(0, user_cmh, 100) 
    k = user_pa / (user_cmh**2) if user_cmh != 0 else 0
    y_path = k * (x_path**2)
    
    # 시스템 저항 곡선 (굵은 파란색)
    ax.plot(x_path, y_path, color='#1f77b4', linewidth=4.5, alpha=1.0, zorder=20, label='System Resistance Curve')

    # 2. 선정 지점 가이드 (붉은 십자선 + 포인트)
    ax.axvline(user_cmh, color='red', linestyle='-', linewidth=1.5, alpha=0.6, zorder=15)
    ax.axhline(user_pa, color='red', linestyle='-', linewidth=1.5, alpha=0.6, zorder=15)
    ax.scatter(user_cmh, user_pa, color='red', s=200, edgecolors='white', marker='o', linewidths=2, zorder=30, label='Design Point')

    # 3. 축 범위 및 설정 (0부터 시작)
    x_limit = max(user_cmh * 1.5, model_df['CMH'].max() * 1.1)
    y_limit = max(user_pa * 1.5, model_df['Pa'].max() * 1.1)
    ax.set_xlim(0, x_limit); ax.set_ylim(0, y_limit)
    
    ax.set_xlabel('Air Flow (CMH)', fontweight='bold', fontsize=12)
    ax1 = ax.set_ylabel('Static Pressure (Pa)', fontweight='bold', fontsize=12)
    ax.set_title(f"Final Selection Analysis: {selected_model}", fontsize=18, fontweight='bold', pad=25)
    ax.grid(True, linestyle=':', alpha=0.5)
    ax.legend(loc='upper right', frameon=True, shadow=True)
    
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=200)
    buf.seek(0)
    plt.close(fig)
    return buf

# [소음 그래프 및 PDF 로직은 V6.1 유지]

# --- 메인 실행부 ---
df = load_my_data()
if df is not None:
    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    p_name = c1.text_input("Project Name", placeholder="English Only")
    c_name = c2.text_input("Customer", placeholder="English Only")
    m_name = c3.text_input("Manager", placeholder="English Only")
    p_date = c4.date_input("Date", datetime.now())

    st.subheader("🎯 Selection Duty")
    c1, c2 = st.columns(2)
    u_cmh = c1.number_input("Design Flow (CMH)", value=115000)
    u_pa = c2.number_input("Design Pressure (Pa)", value=2100)

    selected_model = st.selectbox("Model Select", df['model_name'].unique())
    
    # V6.5 그래프 생성
    chart_img = create_v6_5_chart(df, selected_model, u_cmh, u_pa)
    st.image(chart_img, caption="V6.5 Optimized System Resistance Map")
    
    # 소음 등 추가 정보 표시...
    best_row = df[df['model_name'] == selected_model].iloc[0]
    st.success(f"Confirmed: {selected_model} for {u_cmh} CMH at {u_pa} Pa")