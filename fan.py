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

# 1. 페이지 설정 및 데이터 로드 (1 RPM 마스터 데이터 연동)
st.set_page_config(page_title="루트에어 선정 시스템 V8.4.1", layout="wide")

def load_my_data():
    target_file = 'fan_performance_map_full_sample_1rpm_steps.csv' 
    if os.path.exists(target_file):
        try: return pd.read_csv(target_file, encoding='utf-8-sig')
        except: return pd.read_csv(target_file, encoding='cp949')
    return None

# 주파수별 고유 소음 데이터(dB / dB(A)) 1:1 정밀 매칭 함수
def get_exact_noise_pair(model_data, keyword):
    column_mapping = {
        '63': '63Hz(dB / dB(A))', '125': '125Hz(dB / dB(A))', '250': '250Hz(dB / dB(A))',
        '500': '500Hz(dB / dB(A))', '1k': '1kHz(dB / dB(A))', '2k': '2kHz(dB / dB(A))',
        '4k': '4kHz(dB / dB(A))', '8k': '8kHz(dB / dB(A))', 'total': 'Total_dB / dB(A)'
    }
    target_col = column_mapping.get(keyword.strip().lower())
    
    if target_col and target_col in model_data.index:
        val = str(model_data[target_col]).strip()
        val = val.replace('dB(A)', '').replace('dB', '').strip()
        if '/' in val:
            parts = val.split('/')
            return parts[0].strip(), parts[1].strip()
        return val, val
    return "0", "0"

# 2. 메인 성능 맵 생성
def create_master_chart(all_df, selected_model, user_cmh, user_pa):
    active_df = all_df[(all_df['model_name'] == selected_model) & (all_df['rpm'] > 0)]
    
    fig, ax1 = plt.subplots(figsize=(10, 7))
    ax2 = ax1.twinx()
    
    all_rpms = sorted(active_df['rpm'].unique())
    visual_rpms = [rpm for rpm in all_rpms if rpm % 50 == 0 or rpm == max(all_rpms)]
    
    for rpm in visual_rpms:
        data = active_df[active_df['rpm'] == rpm].sort_values('CMH')
        if len(data) > 0:
            ax1.plot(data['CMH'], data['Pa'], color='steelblue', linewidth=1.2, alpha=0.5)
            ax1.text(data['CMH'].iloc[-1], data['Pa'].iloc[-1], f' {int(rpm)} RPM', color='steelblue', fontsize=9, va='center')
            
            ax2.plot(data['CMH'], data['power (kW)'], color='darkgreen', linewidth=1.2, linestyle='--', alpha=0.7)
            ax2.text(data['CMH'].iloc[0], data['power (kW)'].iloc[0], f'{data["power (kW)"].iloc[0]:.1f} kW ', color='darkgreen', fontsize=8, ha='right', va='center', alpha=0.8)

    x_max = max(user_cmh * 1.3, active_df['CMH'].max() if not active_df.empty else 1000)
    y_max = max(user_pa * 1.5, active_df['Pa'].max() if not active_df.empty else 1000)

    k1 = 2100 / (97500 ** 2) 
    k2 = 400 / (75000 ** 2)  

    x_contour = np.linspace(0, x_max, 300)
    y_area1 = k1 * (x_contour ** 2)
    y_area2 = k2 * (x_contour ** 2)
    
    ax1.plot(x_contour, y_area1, color='purple', linestyle='-.', linewidth=2.0, label='Area 1 Boundary')
    ax1.plot(x_contour, y_area2, color='darkorange', linestyle='-.', linewidth=2.0, label='Area 2 Boundary')

    ax1.fill_between(x_contour, 0, y_area2, color='pink', alpha=0.12, zorder=0, label='Out of Bounds (Pink)')
    ax1.fill_between(x_contour, y_area1, y_max * 2, color='pink', alpha=0.12, zorder=0)

    x_path = np.linspace(0, x_max, 100)
    k = user_pa / (user_cmh**2) if user_cmh != 0 else 0
    ax1.plot(x_path, k*(x_path**2), color='#1f77b4', linewidth=4, label='System Resistance')
    
    ax1.axvline(user_cmh, color='red', linestyle='--', linewidth=1, alpha=0.4)
    ax1.axhline(user_pa, color='red', linestyle='--', linewidth=1, alpha=0.4)
    ax1.scatter(user_cmh, user_pa, color='red', s=150, edgecolors='white', zorder=30)

    ax1.set_xlim(0, x_max)
    ax1.set_ylim(0, y_max)
    ax2.set_ylim(0, active_df['power (kW)'].max() * 1.3 if not active_df.empty else 100)
    
    ax1.set_xlabel('Air Flow (CMH)', fontweight='bold')
    ax1.set_ylabel('Static Pressure (Pa)', color='steelblue', fontweight='bold')
    ax2.set_ylabel('Shaft Power (kW)', color='darkgreen', fontweight='bold')
    
    ax1.tick_params(axis='y', labelcolor='steelblue')
    ax2.tick_params(axis='y', labelcolor='darkgreen')
    ax1.set_title(f"Performance Map: {selected_model}", fontsize=15, fontweight='bold')
    ax1.grid(True, linestyle=':', alpha=0.5)
    ax1.legend(loc='upper left')
    
    plt.tight_layout()
    buf = BytesIO(); plt.savefig(buf, format='png', dpi=200, bbox_inches='tight'); plt.close(fig)
    return buf

# 3. 소음 통합 그래프 생성
def create_noise_chart(model_data):
    bands = ['63', '125', '250', '500', '1k', '2k', '4k', '8k', 'Total']
    db_vals, dba_vals = [], []
    for b in bands:
        db, dba = get_exact_noise_pair(model_data, b)
        try: 
            db_vals.append(float(db))
            dba_vals.append(float(dba))
        except: 
            db_vals.append(0.0)
            dba_vals.append(0.0)
        
    fig, ax1 = plt.subplots(figsize=(10, 5))
    ax1.bar(bands, db_vals, color='skyblue', alpha=0.6, label='Noise Level (dB)')
    ax1.plot(bands, dba_vals, color='red', marker='o', linewidth=2, label='Weighting (dB(A))')
    
    max_val = max(max(db_vals), max(dba_vals)) if db_vals else 100
    ax1.set_ylim(0, max_val * 1.2)
    
    for i, (v1, v2) in enumerate(zip(db_vals, dba_vals)):
        ax1.text(i, v1 + 1.5, f'{int(v1)}', ha='center', color='blue', fontsize=9, fontweight='bold')
        ax1.text(i, v2 - 4.5, f'{int(v2)}', ha='center', color='red', fontsize=9, fontweight='bold')
        
    ax1.set_ylabel('Sound Level (dB / dB(A))', fontweight='bold')
    ax1.set_title('Octave Band Analysis (including Total)', fontsize=14, fontweight='bold')
    ax1.legend(loc='upper right'); plt.tight_layout()
    buf = BytesIO(); plt.savefig(buf, format='png', dpi=150, bbox_inches='tight'); plt.close(fig)
    return buf

# 4. PDF 리포트 생성 (첨부사진 속 우측 사각 박스 페이지 넘버링 규격 적용)
def create_final_pdf(p_info, model_data, chart_buf, noise_buf, d_point):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4); w, h = A4
    logo_path = "logo.png"

    # [사진 동기화] 하단 데코레이션 및 사각 박스 넘버링 드로잉 함수
    def draw_page_decorations(c, page_num):
        # 상단 헤더 라인
        c.setFont("Helvetica-Bold", 22); c.drawString(50, h-60, "Technical Selection Report")
        if os.path.exists(logo_path): c.drawImage(logo_path, w-180, h-82, width=130, preserveAspectRatio=True, mask='auto')
        c.setLineWidth(1.5); c.setStrokeColor(colors.black); c.line(50, h-90, w-50, h-90)
        
        # 하단 상단 경계 미세 가이드선
        c.setLineWidth(0.5); c.setStrokeColor(colors.lightgrey); c.line(50, 55, w-50, 55)
        
        # 1. 왼쪽 저작권 및 컨택 문구 출력
        c.setFillColor(colors.gray); c.setFont("Helvetica", 8)
        footer_text = "Copyright © ROOT AIR Co., Ltd. All Rights Reserved.  |  Tel: +82-2-1234-5678  |  Email: contact@root-air.com"
        c.drawString(50, 38, footer_text)
        
        # 2. [사진 완벽 동기화] 우측 하단 선으로 둘러싸인 정교한 페이지 사각 박스 구현
        box_w, box_h = 45, 20
        box_x = w - 50 - box_w
        box_y = 28
        
        # 테두리 사각형 그리기
        c.setLineWidth(0.8); c.setStrokeColor(colors.gray)
        c.rect(box_x, box_y, box_w, box_h, fill=0)
        
        # 사각 박스 정중앙에 'Page X' 텍스트 인치 매칭
        c.setFillColor(colors.black); c.setFont("Helvetica", 8.5)
        c.drawCentredString(box_x + (box_w / 2), box_y + 6.5, f"Page {page_num}")

    # 1페이지 드로잉
    draw_page_decorations(p, 1)
    p.setFont("Helvetica", 10.5); p.setFillColor(colors.black)
    p.drawString(65, h-130, f"Date : {p_info['date']}")
    p.drawString(65, h-165, f"Project Name : {p_info['project']}")
    p.drawString(65, h-185, f"Customer : {p_info['customer']}")
    p.drawString(65, h-205, f"Engineer : {p_info['manager']}")

    p.setFont("Helvetica-Bold", 12); p.drawString(50, h-245, "Design & Performance")
    p.setFont("Helvetica", 10.5)
    p.drawString(65, h-270, f"Selected Model : {model_data['model_name']}")
    p.drawString(65, h-290, f"Operating Speed : {int(model_data['rpm'])} RPM")
    p.drawString(65, h-310, f"Design Flow : {d_point['cmh']:,} CMH / Design Pressure : {d_point['pa']:,} Pa")
    
    p_fan = model_data.get('power (kW)', 'N/A')
    eff = model_data.get('total efficiency (%)', 'N/A')
    p.drawString(65, h-330, f"Absorbed Power (P fan) : {p_fan} kW / Total Efficiency : {eff}%")

    chart_buf.seek(0); p.drawImage(ImageReader(chart_buf), 50, h-740, width=500, height=380)
    
    # 2페이지 드로잉
    p.showPage()
    draw_page_decorations(p, 2)
    p.setFont("Helvetica-Bold", 12); p.setFillColor(colors.black); p.drawString(50, h-120, "Acoustic Analysis")
    
    noise_buf.seek(0); p.drawImage(ImageReader(noise_buf), 50, h-430, width=500, height=280)
    
    table_y = h-490
    p.setLineWidth(0.5); p.setFillColor(colors.lightgrey); p.rect(50, table_y, 495, 22, fill=1)
    p.setFillColor(colors.black); p.setFont("Helvetica-Bold", 8)
    
    labels = ['(dB / dB(A))', '63Hz', '125Hz', '250Hz', '500Hz', '1kHz', '2kHz', '4kHz', '8kHz', 'Total']
    col_widths = [75] + [46.6]*9
    
    curr_x = 50
    for i, label in enumerate(labels):
        p.drawCentredString(curr_x + col_widths[i]/2, table_y + 7, label)
        curr_x += col_widths[i]
    
    p.setFont("Helvetica", 7.5); table_y -= 22; p.rect(50, table_y, 495, 22, fill=0)
    curr_x = 50
    p.drawCentredString(curr_x + col_widths[0]/2, table_y + 7, "Sound Level")
    curr_x += col_widths[0]
    
    for i, kw in enumerate(['63', '125', '250', '500', '1k', '2k', '4k', '8k', 'Total']):
        db, dba = get_exact_noise_pair(model_data, kw)
        p.drawCentredString(curr_x + col_widths[i+1]/2, table_y + 7, f"{db} / {dba}")
        curr_x += col_widths[i+1]
    
    curr_x = 50
    for w_val in col_widths:
        p.line(curr_x, table_y, curr_x, table_y + 44)
        curr_x += w_val
    p.line(545, table_y, 545, table_y + 44)

    p.showPage(); p.save(); buffer.seek(0)
    return buffer

# --- 메인 실행부 (Streamlit UI) ---
df = load_my_data()
if df is not None:
    c1, c2 = st.columns([1, 4])
    with c1:
        if os.path.exists("logo.png"): st.image("logo.png", width=150)
    with c2: st.title("루트에어 송풍기 선정 시스템 V8.4.1")
    
    st.divider()
    
    col_a, col_b, col_c, col_d = st.columns(4)
    p_date = col_a.date_input("Date", datetime.now())
    p_name_raw = col_b.text_input("Project Name", placeholder="English Only")
    cust_name_raw = col_c.text_input("Customer", placeholder="English Only")
    mgr_name_raw = col_d.text_input("Manager", placeholder="English Only")
    
    p_name = p_name_raw if p_name_raw.strip() != "" else "N/A"
    cust_name = cust_name_raw if cust_name_raw.strip() != "" else "N/A"
    mgr_name = mgr_name_raw if mgr_name_raw.strip() != "" else "N/A"

    col_1, col_2, col_3 = st.columns(3)
    u_cmh = col_1.number_input("Design Flow (CMH)", value=115000)
    u_pa = col_2.number_input("Design Pressure (Pa)", value=2100)
    selected_model = col_3.selectbox("Select Model", df['model_name'].unique())
    
    # 1 RPM 정밀 고속 연동 파서 구동
    valid_df = df[(df['model_name'] == selected_model) & (df['rpm'] > 0)].copy()
    if not valid_df.empty:
        valid_df['distance'] = ((valid_df['CMH'] - u_cmh) ** 2) + ((valid_df['Pa'] - u_pa) ** 2) * 50
        best_row_index = valid_df['distance'].idxmin()
        model_data = valid_df.loc[best_row_index]
    else:
        model_data = df[df['model_name'] == selected_model].iloc[0]
        
    p_fan = model_data.get('power (kW)', 'N/A')
    eff = model_data.get('total efficiency (%)', 'N/A')
    calculated_rpm = int(model_data['rpm'])

    # 실시간 계산 데이터 대시보드 스코어카드 표기 (Tip Speed 제외, 원본 3열 구조 보존)
    st.write("") 
    res_col1, res_col2, res_col3 = st.columns(3)
    with res_col1:
        st.metric(label="⚙️ Calculated Operating Speed", value=f"{calculated_rpm} RPM")
    with res_col2:
        st.metric(label="⚡ Absorbed Power (P fan)", value=f"{p_fan} kW")
    with res_col3:
        st.metric(label="📊 Total Efficiency", value=f"{eff} %")
    
    st.divider()
    
    chart_buf = create_master_chart(df, selected_model, u_cmh, u_pa)
    noise_buf = create_noise_chart(model_data)
    
    st.image(chart_buf)
    st.image(noise_buf)
    
    p_info = {"project": p_name, "customer": cust_name, "manager": mgr_name, "date": p_date.strftime("%Y-%m-%d")}
    pdf_file = create_final_pdf(p_info, model_data, chart_buf, noise_buf, {"cmh": u_cmh, "pa": u_pa})
    st.download_button("📥 Download Final Technical Report", pdf_file, f"Report_{p_info['project']}.pdf")
else:
    st.error("⚠️ 데이터 파일('fan_performance_map_full_sample_1rpm_steps.csv')을 찾을 수 없습니다.")