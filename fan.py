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

# 1. 페이지 설정 및 데이터 로드 (이전과 동일)
st.set_page_config(page_title="루트에어 선정 시스템 V7.9.7", layout="wide")

def load_my_data():
    target_file = 'fan_performance_map_full_sample.csv' 
    if os.path.exists(target_file):
        try: return pd.read_csv(target_file, encoding='utf-8-sig')
        except: return pd.read_csv(target_file, encoding='cp949')
    return None

def get_noise_pair_safe(model_data, keyword):
    for col in model_data.index:
        if keyword.lower() in col.lower():
            val = str(model_data[col]).strip()
            val = val.replace('dB(A)', '').replace('dB', '').strip()
            if '/' in val:
                parts = val.split('/')
                return parts[0].strip(), parts[1].strip()
            return val, val
    return "0", "0"

# 2. 메인 성능 맵 생성 (V7.9 로직 유지)
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
    ax.plot(x_path, k*(x_path**2), color='#1f77b4', linewidth=4, label='System Resistance')
    ax.scatter(user_cmh, user_pa, color='red', s=150, edgecolors='white', zorder=30)
    ax.set_xlim(0, x_max); ax.set_ylim(0, max(user_pa * 1.5, model_df['Pa'].max()))
    ax.set_xlabel('Flow (CMH)'); ax.set_ylabel('Pressure (Pa)')
    ax.set_title(f"Performance Map: {selected_model}", fontsize=15, fontweight='bold')
    ax.grid(True, linestyle=':', alpha=0.5); ax.legend(loc='upper right')
    buf = BytesIO(); plt.savefig(buf, format='png', dpi=200, bbox_inches='tight'); plt.close(fig)
    return buf

# 3. 소음 그래프 생성 (Total 포함)
def create_noise_chart(model_data):
    bands = ['63', '125', '250', '500', '1k', '2k', '4k', '8k', 'Total']
    db_vals, dba_vals = [], []
    for b in bands:
        db, dba = get_noise_pair_safe(model_data, b)
        try: db_vals.append(float(db)); dba_vals.append(float(dba))
        except: db_vals.append(0.0); dba_vals.append(0.0)
    fig, ax1 = plt.subplots(figsize=(10, 5))
    ax1.bar(bands, db_vals, color='skyblue', alpha=0.6, label='Noise Level (dB)')
    ax1.plot(bands, dba_vals, color='red', marker='o', linewidth=2, label='Weighting (dB(A))')
    for i, (v1, v2) in enumerate(zip(db_vals, dba_vals)):
        ax1.text(i, v1 + 1, f'{int(v1)}', ha='center', color='blue', fontsize=9, fontweight='bold')
        ax1.text(i, v2 - 4, f'{int(v2)}', ha='center', color='red', fontsize=9, fontweight='bold')
    ax1.legend(loc='upper right'); plt.tight_layout()
    buf = BytesIO(); plt.savefig(buf, format='png', dpi=150, bbox_inches='tight'); plt.close(fig)
    return buf

# 4. PDF 리포트 생성 (누락 데이터 수정 및 표 머리글 추가)
def create_final_pdf(p_info, model_data, chart_buf, noise_buf, d_point):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4); w, h = A4
    logo_path = "logo.png"

    def draw_header(c):
        c.setFont("Helvetica-Bold", 22); c.drawString(50, h-60, "Technical Selection Report")
        if os.path.exists(logo_path): c.drawImage(logo_path, w-180, h-82, width=130, preserveAspectRatio=True, mask='auto')
        c.setLineWidth(1.5); c.line(50, h-90, w-50, h-90)

    # 1페이지
    draw_header(p)
    p.setFont("Helvetica", 10.5)
    p.drawString(65, h-130, f"Date : {p_info['date']}")
    p.drawString(65, h-150, f"Project Name : {p_info['project']}")
    p.drawString(65, h-170, f"Customer : {p_info['customer']}")
    p.drawString(65, h-190, f"Engineer : {p_info['manager']}")

    # [수정] 누락되었던 성능 데이터 출력부 보강
    p.setFont("Helvetica-Bold", 12); p.drawString(50, h-225, "[2] Design & Performance")
    p.setFont("Helvetica", 10.5)
    p.drawString(65, h-250, f"Selected Model : {model_data['model_name']}")
    p.drawString(65, h-270, f"Operating Speed : {int(model_data['rpm'])} RPM")
    p.drawString(65, h-290, f"Design Flow : {d_point['cmh']:,} CMH / Design Pressure : {d_point['pa']:,} Pa")
    
    # 동력 및 효율 데이터 (데이터프레임 컬럼명에 맞춰 수정)
    p_fan = model_data.get('power (kW)', 'N/A')
    eff = model_data.get('total efficiency (%)', 'N/A')
    p.drawString(65, h-310, f"Absorbed Power (P fan) : {p_fan} kW / Total Efficiency : {eff}%")

    chart_buf.seek(0); p.drawImage(ImageReader(chart_buf), 50, h-750, width=500, height=380)
    p.drawCentredString(w/2, 40, "- Page 1 -")
    
    # 2페이지
    p.showPage(); draw_header(p)
    noise_buf.seek(0); p.drawImage(ImageReader(noise_buf), 50, h-450, width=500, height=280)
    
    # [수정] 소음 표 첫 칸에 '(dB / dB(A))' 추가 및 격자 레이아웃
    table_y = h-520
    p.setLineWidth(0.5); p.setFillColor(colors.lightgrey); p.rect(50, table_y, 495, 22, fill=1)
    p.setFillColor(colors.black); p.setFont("Helvetica-Bold", 8)
    
    # 헤더 구성
    labels = ['(dB / dB(A))', '63Hz', '125Hz', '250Hz', '500Hz', '1kHz', '2kHz', '4kHz', '8kHz', 'Total']
    col_widths = [75] + [46.6]*9 # 첫 칸을 좀 더 넓게 배분
    
    curr_x = 50
    for i, label in enumerate(labels):
        p.drawCentredString(curr_x + col_widths[i]/2, table_y + 7, label)
        p.line(curr_x, table_y, curr_x, table_y + 22)
        curr_x += col_widths[i]
    p.line(545, table_y, 545, table_y + 22)
    
    # 데이터 행
    p.setFont("Helvetica", 7.5); table_y -= 22; p.rect(50, table_y, 495, 22, fill=0)
    curr_x = 50
    p.drawCentredString(curr_x + col_widths[0]/2, table_y + 7, "Sound Level") # 첫 칸 내용
    curr_x += col_widths[0]
    
    for i, kw in enumerate(['63', '125', '250', '500', '1k', '2k', '4k', '8k', 'Total']):
        db, dba = get_noise_pair_safe(model_data, kw)
        p.drawCentredString(curr_x + col_widths[i+1]/2, table_y + 7, f"{db} / {dba}")
        p.line(curr_x, table_y, curr_x, table_y + 22)
        curr_x += col_widths[i+1]
    
    p.line(50, table_y, 50, table_y + 22) # 맨 왼쪽 선
    p.line(545, table_y, 545, table_y + 22) # 맨 오른쪽 선

    p.drawCentredString(w/2, 40, "- Page 2 -")
    p.showPage(); p.save(); buffer.seek(0)
    return buffer

# --- 메인 실행부 (Streamlit) ---
df = load_my_data()
if df is not None:
    c1, c2 = st.columns([1, 4])
    with c1:
        if os.path.exists("logo.png"): st.image("logo.png", width=150)
    with c2: st.title("루트에어 송풍기 선정 시스템 V7.9.7")
    
    st.divider()
    col_a, col_b, col_c, col_d = st.columns(4)
    p_date = col_a.date_input("Date", datetime.now())
    p_name = col_b.text_input("Project Name", value="P4 PH.2 OAC Fan")
    cust_name = col_c.text_input("Customer", value="K-ENSOL")
    mgr_name = col_d.text_input("Manager", value="HK.Lim")

    col_1, col_2, col_3 = st.columns(3)
    u_cmh = col_1.number_input("Design Flow (CMH)", value=115000)
    u_pa = col_2.number_input("Design Pressure (Pa)", value=2100)
    selected_model = col_3.selectbox("Select Model", df['model_name'].unique())
    
    model_data = df[df['model_name'] == selected_model].iloc[0]
    
    chart_buf = create_master_chart(df, selected_model, u_cmh, u_pa)
    noise_buf = create_noise_chart(model_data)
    
    st.image(chart_buf)
    st.image(noise_buf)
    
    p_info = {"project": p_name, "customer": cust_name, "manager": mgr_name, "date": p_date.strftime("%Y-%m-%d")}
    pdf_file = create_final_pdf(p_info, model_data, chart_buf, noise_buf, {"cmh": u_cmh, "pa": u_pa})
    st.download_button("📥 Download Final Technical Report", pdf_file, f"Report_{p_name}.pdf")
else:
    st.error("데이터 파일을 로드할 수 없습니다.")