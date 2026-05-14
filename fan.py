import streamlit as st
import pandas as pd
import os
import matplotlib.pyplot as plt
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
from io import BytesIO
import numpy as np
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="루트에어 선정 시스템 V7.9.4", layout="wide")

# 1. 데이터 로드 함수 (파일 유무 및 인코딩 방어)
def load_my_data():
    target_file = 'fan_performance_map_full_sample.csv' 
    if os.path.exists(target_file):
        try: return pd.read_csv(target_file, encoding='utf-8-sig')
        except: return pd.read_csv(target_file, encoding='cp949')
    return None

# [KeyError 방지] 소음 데이터(dB / dB(A))를 키워드로 안전하게 추출하는 함수
def get_noise_pair_safe(model_data, keyword):
    for col in model_data.index:
        if keyword.lower() in col.lower():
            val = str(model_data[col]).strip()
            val = val.replace('dB(A)', '').replace('dB', '').strip()
            if '/' in val:
                parts = val.split('/')
                return parts[0].strip(), parts[1].strip()
            return val, val # 슬래시가 없는 경우 동일 값으로 처리
    return "0", "0"

# 2. 메인 성능 맵 생성 (V7.9 오리지널 서징 로직)
def create_master_chart(all_df, selected_model, user_cmh, user_pa):
    model_df = all_df[all_df['model_name'] == selected_model].sort_values(by=['rpm', 'CMH'])
    rpms = sorted(model_df['rpm'].unique())
    fig, ax = plt.subplots(figsize=(10, 7))
    
    surge_x, surge_y = [], []
    for rpm in rpms:
        data = model_df[model_df['rpm'] == rpm]
        ax.plot(data['CMH'], data['Pa'], color='steelblue', linewidth=1.2, alpha=0.5)
        ax.text(data['CMH'].iloc[-1], data['Pa'].iloc[-1], f' {int(rpm)} RPM', color='steelblue', fontsize=9, va='center')
        surge_x.append(data['CMH'].iloc[0]); surge_y.append(data['Pa'].iloc[0])

    ax.plot(surge_x, surge_y, 'r--', linewidth=2.5, label='Surge Line')
    ax.fill_betweenx(surge_y, 0, surge_x, color='red', alpha=0.07)

    x_max = max(user_cmh * 1.3, model_df['CMH'].max())
    x_path = np.linspace(0, x_max, 100)
    k = user_pa / (user_cmh**2) if user_cmh != 0 else 0
    y_path = k * (x_path**2)
    ax.plot(x_path, y_path, color='#1f77b4', linewidth=4, label='System Resistance')
    ax.scatter(user_cmh, user_pa, color='red', s=150, edgecolors='white', zorder=30)

    ax.set_xlim(0, x_max); ax.set_ylim(0, max(user_pa * 1.5, model_df['Pa'].max()))
    ax.set_xlabel('Flow (CMH)'); ax.set_ylabel('Pressure (Pa)')
    ax.set_title(f"Performance Map: {selected_model}", fontsize=15, fontweight='bold')
    ax.grid(True, linestyle=':', alpha=0.5); ax.legend(loc='upper right')
    
    buf = BytesIO(); plt.savefig(buf, format='png', dpi=200, bbox_inches='tight'); plt.close(fig)
    return buf

# 3. 소음 통합 그래프 (dB 막대 + dB(A) 꺾은선)
def create_noise_chart(model_data):
    bands = ['63', '125', '250', '500', '1k', '2k', '4k', '8k']
    db_vals, dba_vals = [], []
    for b in bands:
        db, dba = get_noise_pair_safe(model_data, b)
        try:
            db_vals.append(float(db)); dba_vals.append(float(dba))
        except:
            db_vals.append(0.0); dba_vals.append(0.0)
        
    fig, ax1 = plt.subplots(figsize=(10, 5))
    ax1.bar(bands, db_vals, color='skyblue', alpha=0.6, label='Noise Level (dB)')
    ax1.plot(bands, dba_vals, color='red', marker='o', linewidth=2, label='Weighting (dB(A))')
    
    ax1.set_ylabel('Sound Level (dB / dB(A))', fontweight='bold')
    ax1.set_title('Octave Band Analysis: dB & dB(A)', fontsize=14, fontweight='bold')
    
    for i, (v1, v2) in enumerate(zip(db_vals, dba_vals)):
        ax1.text(i, v1 + 1, f'{int(v1)}', ha='center', color='blue', fontsize=9, fontweight='bold')
        ax1.text(i, v2 - 4, f'{int(v2)}', ha='center', color='red', fontsize=9, fontweight='bold')
        
    ax1.legend(loc='upper right'); plt.tight_layout()
    buf = BytesIO(); plt.savefig(buf, format='png', dpi=150, bbox_inches='tight'); plt.close(fig)
    return buf

# 4. PDF 리포트 생성 (그래프 누락 방지 로직 적용)
def create_final_pdf(p_info, model_data, chart_buf, noise_buf, d_point):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    logo_path = "logo.png"

    # 헤더 함수
    def draw_header(canvas_obj):
        canvas_obj.setFont("Helvetica-Bold", 22)
        canvas_obj.drawString(50, h-60, "Technical Selection Report")
        if os.path.exists(logo_path):
            canvas_obj.drawImage(logo_path, w-180, h-82, width=130, preserveAspectRatio=True, mask='auto')
        canvas_obj.setLineWidth(1.5); canvas_obj.line(50, h-90, w-50, h-90)

    # 1페이지: 프로젝트 정보 & 성능 맵
    draw_header(p)
    p.setFont("Helvetica-Bold", 12); p.drawString(50, h-120, "[1] Project Information")
    p.setFont("Helvetica", 10.5)
    p.drawString(65, h-145, f"Date : {p_info['date']}")
    p.drawString(65, h-165, f"Project Name : {p_info['project']}")
    p.drawString(65, h-185, f"Customer : {p_info['customer']}")
    p.drawString(65, h-205, f"Engineer : {p_info['manager']}")

    p.setFont("Helvetica-Bold", 12); p.drawString(50, h-245, "[2] Design & Performance")
    p.setFont("Helvetica", 10.5)
    p.drawString(65, h-270, f"Selected Model : {model_data['model_name']}")
    p.drawString(65, h-290, f"Design Flow : {d_point['cmh']:,} CMH / Design Pressure : {d_point['pa']:,} Pa")
    
    chart_buf.seek(0) # 버퍼 포인터 초기화
    p.drawImage(ImageReader(chart_buf), 50, h-750, width=500, height=380)
    p.drawCentredString(w/2, 40, "- Page 1 -")
    
    # 2페이지: 소음 분석
    p.showPage()
    draw_header(p)
    p.setFont("Helvetica-Bold", 12); p.drawString(50, h-120, "[3] Acoustic Analysis")
    
    noise_buf.seek(0)
    p.drawImage(ImageReader(noise_buf), 50, h-450, width=500, height=280)
    
    # 소음 격자 표 (dB / dB(A))
    table_y = h-520
    p.setLineWidth(0.5); p.setFillColor(colors.lightgrey); p.rect(50, table_y, 495, 22, fill=1)
    p.setFillColor(colors.black); p.setFont("Helvetica-Bold", 9)
    labels = ['63Hz', '125Hz', '250Hz', '500Hz', '1kHz', '2kHz', '4kHz', '8kHz', 'Total']
    for i, b in enumerate(labels):
        p.drawCentredString(77 + (i*55), table_y + 7, b)
        p.line(50 + (i*55), table_y, 50 + (i*55), table_y + 22)
    p.line(545, table_y, 545, table_y + 22)
    
    p.setFont("Helvetica", 7.5); table_y -= 22; p.rect(50, table_y, 495, 22, fill=0)
    keywords = ['63', '125', '250', '500', '1k', '2k', '4k', '8k', 'Total']
    for i, kw in enumerate(keywords):
        db, dba = get_noise_pair_safe(model_data, kw)
        p.drawCentredString(77 + (i*55), table_y + 7, f"{db} / {dba}")
        p.line(50 + (i*55), table_y, 50 + (i*55), table_y + 22)
    p.line(545, table_y, 545, table_y + 22)

    p.drawCentredString(w/2, 40, "- Page 2 -")
    p.showPage(); p.save(); buffer.seek(0)
    return buffer

# --- 메인 실행부 ---
df = load_my_data()
if df is not None:
    # 프로그램 상단 헤더
    c_logo, c_title = st.columns([1, 4])
    with c_logo:
        if os.path.exists("logo.png"): st.image("logo.png", width=150)
    with c_title:
        st.title("루트에어 송풍기 선정 시스템 V7.9.4")
    
    st.divider()
    
    # 정보 입력
    c1, c2, c3, c4 = st.columns(4)
    p_date = c1.date_input("Date", datetime.now())
    p_name = c2.text_input("Project Name", placeholder="English Only")
    cust_name = c3.text_input("Customer", placeholder="English Only")
    mgr_name = c4.text_input("Manager", placeholder="English Only")

    # 설계 조건
    col1, col2, col3 = st.columns(3)
    u_cmh = col1.number_input("Design Flow (CMH)", value=115000)
    u_pa = col2.number_input("Design Pressure (Pa)", value=2100)
    selected_model = col3.selectbox("Select Model", df['model_name'].unique())
    
    model_data = df[df['model_name'] == selected_model].iloc[0]
    
    # 차트 생성 (화면용 & PDF용 분리)
    chart_buf = create_master_chart(df, selected_model, u_cmh, u_pa)
    noise_buf = create_noise_chart(model_data)
    
    # 화면 출력
    st.image(chart_buf)
    st.image(noise_buf)
    
    # PDF 준비 및 다운로드
    p_info = {"project": p_name if p_name else "N/A", "customer": cust_name if cust_name else "N/A", 
              "manager": mgr_name if mgr_name else "N/A", "date": p_date.strftime("%Y-%m-%d")}
    d_point = {"cmh": u_cmh, "pa": u_pa}
    
    final_pdf = create_final_pdf(p_info, model_data, chart_buf, noise_buf, d_point)
    st.download_button(label="📥 Download Final Technical Report", data=final_pdf, 
                       file_name=f"Report_{p_info['project']}.pdf", mime="application/pdf")
else:
    st.error("데이터 파일을 찾을 수 없습니다. 파일명을 확인해 주세요.")