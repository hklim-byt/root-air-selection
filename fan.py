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
st.set_page_config(page_title="루트에어 선정 시스템 V6.4", layout="wide")

# 1. 상단 레이아웃
col_logo, col_title = st.columns([1, 4])
with col_logo:
    if os.path.exists("logo.png"): st.image("logo.png", width=250)
    else: st.title("🏢")
with col_title:
    st.title("루트에어 송풍기 선정 시스템 V6.4")
    st.write("Performance Map + System Resistance Curve Visualization")

# 2. 데이터 로드
def load_my_data():
    file_name = 'fan_performance_map_extended.csv'
    if not os.path.exists(file_name):
        file_name = 'fan_performance_map_full_sample.csv'
        if not os.path.exists(file_name): return None
    try: df = pd.read_csv(file_name, encoding='utf-8-sig')
    except: df = pd.read_csv(file_name, encoding='cp949')
    return df

# 3. V6.4 그래프 생성: RPM 맵 + 시스템 경로 곡선
def create_v6_4_chart(all_df, selected_model, user_cmh, user_pa, start_cmh, start_pa):
    model_df = all_df[all_df['model_name'] == selected_model].sort_values(by=['rpm', 'CMH'])
    rpms = sorted(model_df['rpm'].unique())
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # 1. 배경 RPM 곡선 (연하게)
    for rpm in rpms:
        data = model_df[model_df['rpm'] == rpm]
        ax.plot(data['CMH'], data['Pa'], color='steelblue', linewidth=0.8, alpha=0.25, zorder=1)
        ax.text(data['CMH'].iloc[-1], data['Pa'].iloc[-1], f' {int(rpm)} RPM', 
                color='steelblue', fontsize=8, va='center', alpha=0.3)

    # 2. [핵심 요청] 시스템 저항 곡선 (System Curve) 추가
    # 시작점과 끝점을 부드럽게 잇는 포물선(저항곡선 특성) 계산
    # P = k * Q^2 의 원리를 이용하여 경로 생성
    x_path = np.linspace(start_cmh, user_cmh, 50)
    # 단순 직선이 아닌 송풍기 특성에 맞는 곡선으로 시뮬레이션
    y_path = start_pa + (user_pa - start_pa) * ((x_path - start_cmh) / (user_cmh - start_cmh))**2
    
    # [강조] 풍량-정압 경로 곡선을 굵은 파란색 선으로 표시
    ax.plot(x_path, y_path, color='#1f77b4', linewidth=4, alpha=1.0, zorder=20, label='System Resistance Curve')

    # 3. 선정 지점 및 가이드라인 (붉은 십자선 + 포인트)
    ax.axvline(user_cmh, color='red', linestyle='-', linewidth=1.2, alpha=0.5, zorder=15)
    ax.axhline(user_pa, color='red', linestyle='-', linewidth=1.2, alpha=0.5, zorder=15)
    ax.scatter(user_cmh, user_pa, color='red', s=180, edgecolors='white', marker='o', linewidths=2, zorder=30, label='Design Point')
    
    # 시작점 표시
    ax.scatter(start_cmh, start_pa, color='navy', s=80, marker='x', zorder=25, label='Start Point')

    # 4. 축 범위 및 설정
    x_limit = max(user_cmh * 1.5, model_df['CMH'].max() * 1.1)
    y_limit = max(user_pa * 1.5, model_df['Pa'].max() * 1.1)
    ax.set_xlim(0, x_limit); ax.set_ylim(0, y_limit)
    
    ax.set_xlabel('Air Flow (CMH)', fontweight='bold')
    ax.set_ylabel('Static Pressure (Pa)', fontweight='bold')
    ax.set_title(f"System Operation Analysis: {selected_model}", fontsize=16, fontweight='bold', pad=20)
    ax.grid(True, linestyle=':', alpha=0.4)
    ax.legend(loc='upper right')
    
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=200)
    buf.seek(0)
    plt.close(fig)
    return buf

# --- 메인 실행부 ---
df = load_my_data()
if df is not None:
    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    p_name = c1.text_input("Project Name")
    c_name = c2.text_input("Customer")
    m_name = c3.text_input("Manager")
    p_date = c4.date_input("Date")

    st.subheader("📍 곡선 설정 (저항 곡선 시작점)")
    col_s1, col_s2 = st.columns(2)
    s_cmh = col_s1.number_input("시작 풍량 (CMH)", value=20000)
    s_pa = col_s2.number_input("시작 정압 (Pa)", value=500)

    st.subheader("🎯 최종 선정 조건 (목표 지점)")
    c1, c2 = st.columns(2)
    u_cmh = c1.number_input("목표 풍량 (CMH)", value=160000)
    u_pa = c2.number_input("목표 정압 (Pa)", value=3000)

    selected_model = st.selectbox("Model Select", df['model_name'].unique())
    
    # V6.4 저항 곡선 포함 그래프 생성
    chart_img = create_v6_4_chart(df, selected_model, u_cmh, u_pa, s_cmh, s_pa)
    st.image(chart_img, caption="Performance Map with Highlighted System Curve")
    
    # 소음 등 데이터는 기존 방식 유지...