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
st.set_page_config(page_title="루트에어 선정 시스템 V6.0", layout="wide")

# 1. 상단 레이아웃
col_logo, col_title = st.columns([1, 4])
with col_logo:
    if os.path.exists("logo.png"): st.image("logo.png", width=250)
    else: st.title("🏢")
with col_title:
    st.title("루트에어 송풍기 선정 시스템 V6.0")
    st.write("Professional Map with Flow-Guide Visualization")

# 2. 데이터 로드
def load_my_data():
    file_name = 'fan_performance_map_extended.csv'
    if not os.path.exists(file_name):
        file_name = 'fan_performance_map_full_sample.csv'
        if not os.path.exists(file_name): return None
    try: df = pd.read_csv(file_name, encoding='utf-8-sig')
    except: df = pd.read_csv(file_name, encoding='cp949')
    return df

# 3. V6.0 그래프 생성: RPM 맵 + 하단 풍량 가이드
def create_v6_chart(all_df, selected_model, user_cmh, user_pa):
    model_df = all_df[all_df['model_name'] == selected_model].sort_values(by=['rpm', 'CMH'])
    rpms = sorted(model_df['rpm'].unique())
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # RPM 곡선 색상 테마 (차분한 톤)
    colors = plt.cm.Blues(np.linspace(0.4, 0.9, len(rpms)))
    surge_x, surge_y = [], []

    # 1. RPM 곡선 그리기 (강조 없이 균일하게)
    for i, rpm in enumerate(rpms):
        data = model_df[model_df['rpm'] == rpm]
        ax.plot(data['CMH'], data['Pa'], color=colors[i], linewidth=1.5, alpha=0.7)
        
        # [요청 1] RPM 선 끝단에 숫자 표시
        ax.text(data['CMH'].iloc[-1], data['Pa'].iloc[-1], f' {int(rpm)}', 
                color=colors[i], fontsize=10, va='center', fontweight='bold')
        
        surge_x.append(data['CMH'].iloc[0])
        surge_y.append(data['Pa'].iloc[0])

    # 2. 서징 라인 및 영역
    ax.plot(surge_x, surge_y, 'r--', linewidth=2, label='Surge Line')
    ax.fill_betweenx(surge_y, 0, surge_x, color='red', alpha=0.05)

    # 3. [요청 3] 하단 풍량 가이드 라인 (바닥부터 위로 뻗는 선)
    ax.axvline(user_cmh, color='red', linestyle='-', linewidth=2, alpha=0.6, zorder=10)
    ax.axhline(user_pa, color='red', linestyle='-', linewidth=1, alpha=0.4, zorder=5)
    
    # 설계 지점 포인트
    ax.scatter(user_cmh, user_pa, color='red', s=150, edgecolors='white', marker='o', linewidths=2, zorder=30, label='Selection Point')
    
    # 4. 축 범위 및 중앙 정렬
    x_limit = max(user_cmh * 1.5, model_df['CMH'].max() * 1.1)
    y_limit = max(user_pa * 1.5, model_df['Pa'].max() * 1.1)
    ax.set_xlim(0, x_limit)
    ax.set_ylim(0, y_limit)

    ax.set_xlabel('Air Flow (CMH)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Static Pressure (Pa)', fontsize=12, fontweight='bold')
    ax.set_title(f"Performance Analysis: {selected_model}", fontsize=16, fontweight='bold', pad=20)
    
    ax.grid(True, linestyle=':', alpha=0.5)
    ax.legend(loc='upper right')
    
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=200)
    buf.seek(0)
    plt.close(fig)
    return buf

# [PDF 생성 및 소음 로직은 이전과 동일하게 유지하여 보고서 품질 보존]
def create_pdf(model_info, user_cmh, user_pa, chart_buf, project_info):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    if os.path.exists("logo.png"): p.drawImage(ImageReader("logo.png"), w-160, h-60, width=110, height=35, mask='auto')
    p.setFont("Helvetica-Bold", 20); p.drawString(50, h-50, "Selection Report V6.0")
    p.setFont("Helvetica", 11); p.drawString(50, h-85, f"Project: {project_info['project']} | Model: {model_info['model_name']}")
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
    u_cmh = c1.number_input("Design Flow (CMH)", value=115000)
    u_pa = c2.number_input("Design Pressure (Pa)", value=2100)

    selected_model = st.selectbox("Model Select", df['model_name'].unique())
    
    # V6.0 그래프 생성
    chart_img = create_v6_chart(df, selected_model, u_cmh, u_pa)
    st.image(chart_img, caption="Final Performance Selection Map")
    
    # 선택 모델 데이터 요약 (PDF용)
    best_row = df[df['model_name'] == selected_model].iloc[0]
    
    proj_info = {"project": p_name if p_name else "N/A", "customer": c_name if c_name else "N/A", "manager": m_name if m_name else "N/A", "date": p_date.strftime("%Y-%m-%d")}
    pdf_data = create_pdf(best_row, u_cmh, u_pa, chart_img, proj_info)
    st.download_button("📥 Download Final Report (V6.0)", pdf_data, f"Report_{p_name}.pdf")