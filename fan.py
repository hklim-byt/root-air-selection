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
st.set_page_config(page_title="루트에어 종합 성능 분석", layout="wide")

# 1. 상단 레이아웃
st.title("📊 송풍기 종합 성능 분석 (연습용)")
st.write("Full Performance Map Visualization Version")

# 2. 데이터 로드 (샘플 파일 우선 로드)
def load_sample_data():
    file_name = 'fan_performance_map_sample.csv'
    if not os.path.exists(file_name):
        return None
    return pd.read_csv(file_name, encoding='utf-8-sig')

# 3. 종합 성능 곡선 생성 (V4.2 핵심)
def create_full_map(all_df, selected_model, user_cmh, user_pa):
    model_df = all_df[all_df['model_name'] == selected_model].sort_values(by=['rpm', 'CMH'])
    rpms = sorted(model_df['rpm'].unique())
    
    fig, ax1 = plt.subplots(figsize=(12, 8))
    ax2 = ax1.twinx() # 효율/동력용 보조축
    
    # 뚜렷한 색상 테마
    colors = plt.cm.viridis(np.linspace(0, 1, len(rpms)))
    
    surge_x, surge_y = [], []

    # 1. 각 RPM별 성능 곡선 그리기
    for i, rpm in enumerate(rpms):
        data = model_df[model_df['rpm'] == rpm]
        ax1.plot(data['CMH'], data['Pa'], color=colors[i], label=f'{rpm} rpm', linewidth=2)
        
        # 각 곡선의 시작점(최소 풍량)을 서징 라인 데이터로 수집
        surge_x.append(data['CMH'].iloc[0])
        surge_y.append(data['Pa'].iloc[0])
        
        # 곡선 끝에 RPM 표시
        ax1.text(data['CMH'].iloc[-1], data['Pa'].iloc[-1], f' {rpm}', color=colors[i], fontsize=9, va='center', fontweight='bold')

    # 2. 서징 라인(Surge Line) 자동 생성
    ax1.plot(surge_x, surge_y, 'r--', linewidth=3, label='Surge Line')
    ax1.fill_betweenx(surge_y, 0, surge_x, color='red', alpha=0.05) # 서징 영역
    ax1.text(surge_x[0], surge_y[0], '  SURGE LINE', color='red', fontweight='bold', va='bottom')

    # 3. 효율 및 동력 곡선 (가시성을 위해 가장 높은 RPM 기준 하나만 예시로 표시)
    max_rpm_data = model_df[model_df['rpm'] == max(rpms)]
    ax2.plot(max_rpm_data['CMH'], max_rpm_data['total efficiency (%)'], 'g:', label='Eff (%) at Max RPM', alpha=0.5)
    ax2.plot(max_rpm_data['CMH'], max_rpm_data['power (kW)'], 'm-.', label='kW at Max RPM', alpha=0.5)

    # 4. 설계점(Design Point)
    ax1.scatter(user_cmh, user_pa, color='black', s=200, marker='*', zorder=30, label='Design Point')
    ax1.axhline(user_pa, color='gray', linestyle=':', alpha=0.3)
    ax1.axvline(user_cmh, color='gray', linestyle=':', alpha=0.3)

    # 축 설정
    ax1.set_xlabel('Air Flow (CMH)', fontsize=12)
    ax1.set_ylabel('Static Pressure (Pa)', fontsize=12)
    ax2.set_ylabel('Efficiency (%) / Power (kW)', fontsize=12, color='darkgreen')
    ax1.set_title(f'Comprehensive Fan Performance Map: {selected_model}', fontsize=16, fontweight='bold')
    
    # 범례 통합
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right', fontsize='small')
    
    ax1.grid(True, which='both', linestyle='--', alpha=0.5)
    plt.tight_layout()
    
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=200)
    buf.seek(0)
    plt.close(fig)
    return buf

# --- 메인 실행부 ---
df = load_sample_data()

if df is not None:
    st.info("💡 이 화면은 연습용 샘플 데이터(`fan_performance_map_sample.csv`)를 기반으로 작동 중입니다.")
    
    col1, col2 = st.columns(2)
    u_cmh = col1.number_input("입력 풍량 (CMH)", value=115000)
    u_pa = col2.number_input("입력 정압 (Pa)", value=2100)
    
    models = df['model_name'].unique()
    selected_model = st.selectbox("모델 선택", models)
    
    # 그래프 생성
    map_img = create_full_map(df, selected_model, u_cmh, u_pa)
    st.image(map_img, use_container_width=True)
    
    st.subheader("📋 전체 데이터 확인")
    st.dataframe(df)
else:
    st.error("샘플 데이터 파일을 찾을 수 없습니다. `fan_performance_map_sample.csv`가 있는지 확인해주세요.")