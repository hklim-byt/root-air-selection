import streamlit as st
import pandas as pd
import os
import matplotlib.pyplot as plt
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics        # 폰트 등록 엔진
from reportlab.pdfbase.ttfonts import TTFont    # TrueType 폰트 파서
from io import BytesIO
import numpy as np
from datetime import datetime

# =========================================================================
# [핵심 수정을 통한 한글 깨짐 원천 차단 프로세스]
# =========================================================================
font_path = "malgun.ttf"
if os.path.exists(font_path):
    # 1. ReportLab PDF 문서 본문용 한글 폰트 등록
    pdfmetrics.registerFont(TTFont('Malgun', font_path))
    FONT_NAME = 'Malgun'
    
    # 2. [차트 깨짐 해결] Matplotlib 이미지 엔진에도 '맑은 고딕' 폰트를 강제 매칭
    from matplotlib import font_manager, rc
    font_name = font_manager.FontProperties(fname=font_path).get_name()
    rc('font', family=font_name)
    # 마이너스 부호(-) 깨짐 방지 설정
    plt.rcParams['axes.unicode_minus'] = False
else:
    FONT_NAME = 'Helvetica'

# 페이지 설정 및 데이터 로드 (1 RPM 마스터 데이터 연동)
st.set_page_config(page_title="루트에어 선정 시스템 V8.4.7", layout="wide")

def load_my_data():
    target_file = 'fan_performance_map_full_sample_1rpm_steps.csv' 
    if os.path.exists(target_file):
        try: return pd.read_csv(target_file, encoding='utf-8-sig')
        except: return pd.read_csv(target_file, encoding='cp949')
    return None

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

# 2. 메인 성능 맵 생성 (차트 내부 폰트 최적화)
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
            data_first = data["power (kW)"].iloc[0]
            ax2.text(data['CMH'].iloc[0], data_first, f'{data_first:.1f} kW ', color='darkgreen', fontsize=8, ha='right', va='center', alpha=0.8)

    x_max = max(user_cmh * 1.3, active_df['CMH'].max() if not active_df.empty else 1000)
    y_max = max(user_pa * 1.5, active_df['Pa'].max() if not active_df.empty else 1000)

    k1 = 2100 / (97500 ** 2) 
    k2 = 400 / (75000 ** 2)  

    x_contour = np.linspace(0, x_max, 300)
    y_area1 = k1 * (x_contour ** 2)
    y_area2 = k2 * (x_contour ** 2)
    
    ax1.plot(x_contour, y_area1, color='purple', linestyle='-.', linewidth=2.0, label='Area 1 경계')
    ax1.plot(x_contour, y_area2, color='darkorange', linestyle='-.', linewidth=2.0, label='Area 2 경계')

    ax1.fill_between(x_contour, 0, y_area2, color='pink', alpha=0.12, zorder=0, label='운전 제한 구역 (Pink)')
    ax1.fill_between(x_contour, y_area1, y_max * 2, color='pink', alpha=0.12, zorder=0)

    x_path = np.linspace(0, x_max, 100)
    k = user_pa / (user_cmh**2) if user_cmh != 0 else 0
    ax1.plot(x_path, k*(x_path**2), color='#1f77b4', linewidth=4, label='계통 저항 곡선')
    
    ax1.axvline(user_cmh, color='red', linestyle='--', linewidth=1, alpha=0.4)
    ax1.axhline(user_pa, color='red', linestyle='--', linewidth=1, alpha=0.4)
    ax1.scatter(user_cmh, user_pa, color='red', s=150, edgecolors='white', zorder=30)

    ax1.set_xlim(0, x_max)
    ax1.set_ylim(0, y_max)
    ax2.set_ylim(0, active_df['power (kW)'].max() * 1.3 if not active_df.empty else 100)
    
    # 그래프 축 라벨 한글화 및 가독성 패치
    ax1.set_xlabel('풍량 Air Flow (CMH)', fontweight='bold')
    ax1.set_ylabel('정압 Static Pressure (Pa)', color='steelblue', fontweight='bold')
    ax2.set_ylabel('축동력 Shaft Power (kW)', color='darkgreen', fontweight='bold')
    
    ax1.tick_params(axis='y', labelcolor='steelblue')
    ax2.tick_params(axis='y', labelcolor='darkgreen')
    ax1.set_title(f"성능 곡선 맵 (Performance Map): {selected_model}", fontsize=14, fontweight='bold')
    ax1.grid(True, linestyle=':', alpha=0.5)
    ax1.legend(loc='upper left')
    
    plt.tight_layout()
    buf = BytesIO(); plt.savefig(buf, format='png', dpi=200, bbox_inches='tight'); plt.close(fig)
    return buf

# 3. 소음 통합 그래프 생성
def create_noise_chart(model_data):
    bands = ['63', '125', '250', '500', '1k', '2k', '4k', '8k', '총소음']
    db_vals, dba_vals = [], []
    for b in ['63', '125', '250', '500', '1k', '2k', '4k', '8k', 'Total']:
        db, dba = get_exact_noise_pair(model_data, b)
        try: 
            db_vals.append(float(db))
            dba_vals.append(float(dba))
        except: 
            db_vals.append(0.0)
            dba_vals.append(0.0)
        
    fig, ax1 = plt.subplots(figsize=(10, 5))
    ax1.bar(bands, db_vals, color='skyblue', alpha=0.6, label='소음 레벨 Noise Level (dB)')
    ax1.plot(bands, dba_vals, color='red', marker='o', linewidth=2, label='보정값 Weighting (dB(A))')
    
    max_val = max(max(db_vals), max(dba_vals)) if db_vals else 100
    ax1.set_ylim(0, max_val * 1.2)
    
    for i, (v1, v2) in enumerate(zip(db_vals, dba_vals)):
        ax1.text(i, v1 + 1.5, f'{int(v1)}', ha='center', color='blue', fontsize=9, fontweight='bold')
        ax1.text(i, v2 - 4.5, f'{int(v2)}', ha='center', color='red', fontsize=9, fontweight='bold')
        
    ax1.set_ylabel('음압 레벨 Sound Level (dB / dB(A))', fontweight='bold')
    ax1.set_title('주파수대역별 소음 분석 (Octave Band Analysis)', fontsize=13, fontweight='bold')
    ax1.legend(loc='upper right'); plt.tight_layout()
    buf = BytesIO(); plt.savefig(buf, format='png', dpi=150, bbox_inches='tight'); plt.close(fig)
    return buf

# 4. PDF 리포트 생성 (한글 폰트 전면 유효 래핑 및 타이틀 서식 수정)
def create_final_pdf(p_info, model_data, chart_buf, noise_buf, d_point):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4); w, h = A4
    logo_path = "logo.png"

    def draw_page_decorations(c, page_num):
        # 상단 헤더 라인 (순수 한글 크기 서식 지정으로 충돌 방지)
        c.setFont(f"{FONT_NAME}", 18); c.drawString(50, h-60, "송풍기 기술 선정 보고서")
        if os.path.exists(logo_path): c.drawImage(logo_path, w-180, h-82, width=130, preserveAspectRatio=True, mask='auto')
        c.setLineWidth(1.5); c.setStrokeColor(colors.black); c.line(50, h-90, w-50, h-90)
        
        # 하단 상단 경계 회색 가이드 미세선
        c.setLineWidth(0.5); c.setStrokeColor(colors.lightgrey); c.line(50, 55, w-50, 55)
        
        # 1. 하단 저작권 및 사용자 입력 오피셜 회사 정보
        c.setFillColor(colors.gray); c.setFont(f"{FONT_NAME}", 8)
        footer_text = "Copyright © RootAir ALL RIGHTS RESERVED. | Tel: +82-02-2082-7654 | Email: rootair@rootair.co.kr"
        c.drawString(50, 38, footer_text)
        
        # 2. 우측 하단 선으로 둘러싸인 완벽한 크기의 사각 박스 넘버링 구현
        box_w, box_h = 45, 20
        box_x = w - 50 - box_w
        box_y = 28
        
        # 테두리 사각형 렌더링
        c.setLineWidth(0.8); c.setStrokeColor(colors.gray)
        c.rect(box_x, box_y, box_w, box_h, fill=0)
        
        # 사각 박스 한가운데에 'Page X' 텍스트 안착
        c.setFillColor(colors.black); c.setFont(f"{FONT_NAME}", 8.5)
        c.drawCentredString(box_x + (box_w / 2), box_y + 6.5, f"Page {page_num}")

    # 1페이지 드로잉 (맑은 고딕 가변 배정)
    draw_page_decorations(p, 1)
    p.setFont(f"{FONT_NAME}", 10.5); p.setFillColor(colors.black)
    p.drawString(65, h-130, f"발행 일자 (Date) : {p_info['date']}")
    p.drawString(65, h-165, f"프로젝트명 (Project) : {p_info['project']}")
    p.drawString(65, h-185, f"고객사명 (Customer) : {p_info['customer']}")
    p.drawString(65, h-205, f"담당 엔지니어 (Engineer) : {p_info['manager']}")

    p.setFont(f"{FONT_NAME}", 12); p.drawString(50, h-245, "■ 설계 및 성능 사양 (Design & Performance)")
    p.setFont(f"{FONT_NAME}", 10.5)
    p.drawString(65, h-270, f"선정 모델 (Selected Model) : {model_data['model_name']}")
    p.drawString(65, h-290, f"계산 운전 회전수 (Operating Speed) : {int(model_data['rpm'])} RPM")
    p.drawString(65, h-310, f"설계 풍량 (Design Flow) : {d_point['cmh']:,} CMH / 설계 정압 (Static Pressure) : {d_point['pa']:,} Pa")
    
    p_fan = model_data.get('power (kW)', 'N/A')
    eff = model_data.get('total efficiency (%)', 'N/A')
    p.drawString(65, h-330, f"송풍기 소요동력 (Absorbed Power) : {p_fan} kW / 전효율 (Total Efficiency) : {eff}%")

    chart_buf.seek(0); p.drawImage(ImageReader(chart_buf), 50, h-740, width=500, height=380)
    
    # 2페이지 드로잉
    p.showPage()
    draw_page_decorations(p, 2)
    p.setFont(f"{FONT_NAME}", 12); p.setFillColor(colors.black); p.drawString(50, h-120, "■ 옥타브 밴드 소음 분석 (Acoustic Analysis)")
    
    noise_buf.seek(0); p.drawImage(ImageReader(noise_buf), 50, h-430, width=500, height=280)
    
    table_y = h-490
    p.setLineWidth(0.5); p.setFillColor(colors.lightgrey); p.rect(50, table_y, 495, 22, fill=1)
    p.setFillColor(colors.black); p.setFont(f"{FONT_NAME}", 8)
    
    labels = ['구분 (dB/dB(A))', '63Hz', '125Hz', '250Hz', '500Hz', '1kHz', '2kHz', '4kHz', '8kHz', '총 소음']
    col_widths = [75] + [46.6]*9
    
    curr_x = 50
    for i, label in enumerate(labels):
        p.drawCentredString(curr_x + col_widths[i]/2, table_y + 7, label)
        curr_x += col_widths[i]
    
    p.setFont(f"{FONT_NAME}", 7.5); table_y -= 22; p.rect(50, table_y, 495, 22, fill=0)
    curr_x = 50
    p.drawCentredString(curr_x + col_widths[0]/2, table_y + 7, "소음 측정값")
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
    with c2: st.title("루트에어 송풍기 선정 시스템 V8.4.7")
    
    st.divider()
    
    col_a, col_b, col_c, col_d = st.columns(4)
    p_date = col_a.date_input("Date", datetime.now())
    p_name_raw = col_b.text_input("Project Name", placeholder="English / 한글 모두 지원")
    cust_name_raw = col_c.text_input("Customer", placeholder="English / 한글 모두 지원")
    mgr_name_raw = col_d.text_input("Manager", placeholder="English / 한글 모두 지원")
    
    p_name = p_name_raw if p_name_raw.strip() != "" else "N/A"
    cust_name = cust_name_raw if cust_name_raw.strip() != "" else "N/A"
    mgr_name = mgr_name_raw if mgr_name_raw.strip() != "" else "N/A"

    col_1, col_2, col_3 = st.columns(3)
    u_cmh = col_1.number_input("Design Flow (CMH)", value=115000)
    u_pa = col_2.number_input("Design Pressure (Pa)", value=2100)
    selected_model = col_3.selectbox("Select Model", df['model_name'].unique())
    
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

    st.write("") 
    res_col1, res_col2, res_col3 = st.columns(3)
    with res_col1:
        st.metric(label="⚙️ Calculated Operating Speed", value=f"{calculated_rpm} RPM")
    with res_col2:
        st.metric(label="⚡ Absorbed Power (P fan)", value=f"{p_fan} kW")
    with res_col3:
        st.metric(label="📊 Total Efficiency", value=f"{eff} %")
    
    st.divider()
    
    # 폰트가 동기화된 상태에서 버퍼 생성
    chart_buf = create_master_chart(df, selected_model, u_cmh, u_pa)
    noise_buf = create_noise_chart(model_data)
    
    st.image(chart_buf)
    st.image(noise_buf)
    
    p_info = {"project": p_name, "customer": cust_name, "manager": mgr_name, "date": p_date.strftime("%Y-%m-%d")}
    pdf_file = create_final_pdf(p_info, model_data, chart_buf, noise_buf, {"cmh": u_cmh, "pa": u_pa})
    st.download_button("📥 Download Final Technical Report", pdf_file, f"Report_{p_info['project']}.pdf")
else:
    st.error("⚠️ 데이터 파일('fan_performance_map_full_sample_1rpm_steps.csv')을 찾을 수 없습니다.")