import streamlit as st
import pandas as pd
import os
import matplotlib.pyplot as plt
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from io import BytesIO

# 페이지 설정
st.set_page_config(page_title="루트에어 송풍기 선정", layout="wide")

# 1. 상단 레이아웃 (로고 및 타이틀)
col_logo, col_title = st.columns([1, 4])
with col_logo:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=250)
    else:
        st.title("🏢")

with col_title:
    st.markdown("###")
    st.title("루트에어 송풍기 선정 프로그램")
    st.write("Root Air Fan Selection System V1.6")

# 2. 데이터 불러오기 함수
def load_my_data():
    file_name = 'fan_data.csv'
    if not os.path.exists(file_name): return None
    try:
        df = pd.read_csv(file_name, encoding='utf-8-sig')
    except:
        df = pd.read_csv(file_name, encoding='cp949')
    return df

df = load_my_data()

# 3. 그래프 생성 함수 (선으로 연결 + 십자선)
def create_fan_chart(all_df, user_cmh, user_pa):
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # 모델별로 그룹화하여 선을 그립니다.
    # 현재 데이터는 모델명이 모두 같으므로 하나의 이쁜 선이 그려집니다.
    unique_models = all_df.iloc[:, 0].unique()
    
    for model in unique_models:
        model_data = all_df[all_df.iloc[:, 0] == model]
        # 풍량(3번 열) 기준으로 정렬해야 선이 꼬이지 않고 예쁘게 나옵/니다.
        model_data = model_data.sort_values(by=all_df.columns[3])
        
        # 실선(plot)과 데이터 점(scatter)을 함께 표시
        ax.plot(model_data.iloc[:, 3], model_data.iloc[:, 5], marker='o', markersize=4, label=f"Curve: {model}", linewidth=2)
    
    # 설계점(입력값)에 붉은색 큰 점과 십자선 표시
    ax.scatter(user_cmh, user_pa, color='red', s=150, label='Design Point', zorder=10)
    ax.axhline(user_pa, color='red', linestyle='--', linewidth=1.5, alpha=0.7)
    ax.axvline(user_cmh, color='red', linestyle='--', linewidth=1.5, alpha=0.7)
    
    ax.set_xlabel('Air Flow (CMH)')
    ax.set_ylabel('Static Pressure (Pa)')
    ax.set_title('Fan Performance Selection Chart (Line Mode)')
    ax.grid(True, linestyle=':', alpha=0.6)
    ax.legend()

    img_buf = BytesIO()
    plt.savefig(img_buf, format='png', dpi=200)
    img_buf.seek(0)
    plt.close(fig)
    return img_buf

# 4. PDF 생성 함수
def create_pdf(model_info, user_cmh, user_pa, chart_buf):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    p.setFont("Helvetica-Bold", 20)
    p.drawString(50, height - 50, "Fan Selection Report")
    p.setFont("Helvetica", 12)
    p.line(50, height - 65, 550, height - 65)
    p.drawString(50, height - 100, f"Design Point: {user_cmh} CMH / {user_pa} Pa")
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, height - 140, "[ Selected Model Information ]")
    p.setFont("Helvetica", 12)
    p.drawString(50, height - 170, f"Model Name: {model_info.iloc[0]}")
    p.drawString(50, height - 190, f"Selected Operation: {model_info.iloc[3]} CMH / {model_info.iloc[5]} Pa")
    p.drawString(50, height - 210, f"Motor Power: {model_info.iloc[6]} kW")
    img = ImageReader(chart_buf)
    p.drawImage(img, 50, height - 580, width=500, height=330)
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

# 5. 메인 로직
if df is not None:
    st.divider()
    st.subheader("🔍 설계 조건 입력")
    c1, c2 = st.columns(2)
    with c1:
        user_cmh = st.number_input("필요 풍량 (CMH)", value=120000, step=1000)
    with c2:
        user_pa = st.number_input("필요 정압 (Pa)", value=2400, step=10)

    # 선정 로직
    matched_fans = df[(df.iloc[:, 3] >= user_cmh) & (df.iloc[:, 5] >= user_pa)].copy()

    if not matched_fans.empty:
        best_ones = matched_fans.sort_values(by=[df.columns[3], df.columns[5]])
        st.success(f"조건에 맞는 운전점을 {len(best_ones)}개 찾았습니다!")
        st.dataframe(best_ones, use_container_width=True)
        
        top_model = best_ones.iloc[0]
        chart_img = create_fan_chart(df, user_cmh, user_pa)
        
        st.divider()
        st.subheader("📈 성능 곡선 (Fan Curve)")
        st.image(chart_img, use_container_width=True)

        pdf_buf = create_pdf(top_model, user_cmh, user_pa, chart_img)
        st.download_button(label="📥 그래프 포함 PDF 보고서 다운로드", data=pdf_buf, file_name=f"Report_{top_model.iloc[0]}.pdf", mime="application/pdf")
    else:
        st.warning("⚠️ 조건에 맞는 모델이 없습니다.")

    with st.expander("📂 전체 데이터베이스 확인"):
        st.write(df)