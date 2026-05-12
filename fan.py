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
    st.write("Root Air Fan Selection System V1.5")

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

# 3. 그래프 생성 함수 (선정점에 붉은 선 추가)
def create_fan_chart(all_df, user_cmh, user_pa):
    fig, ax = plt.subplots(figsize=(8, 5))
    
    # 전체 데이터 점 찍기
    ax.scatter(all_df.iloc[:, 3], all_df.iloc[:, 5], color='blue', label='Available Models', alpha=0.5)
    
    # 선정점(입력값) 표시
    ax.scatter(user_cmh, user_pa, color='red', s=100, label='Design Point (Input)', zorder=5)
    
    # 붉은색 가로, 세로 점선 추가
    ax.axhline(user_pa, color='red', linestyle='--', linewidth=1)
    ax.axvline(user_cmh, color='red', linestyle='--', linewidth=1)
    
    # 축 이름 및 스타일
    ax.set_xlabel('Air Flow (CMH)')
    ax.set_ylabel('Static Pressure (Pa)')
    ax.set_title('Fan Performance Selection Chart')
    ax.grid(True, linestyle=':', alpha=0.6)
    ax.legend()

    # 이미지를 메모리에 저장
    img_buf = BytesIO()
    plt.savefig(img_buf, format='png', dpi=200)
    img_buf.seek(0)
    plt.close(fig)
    return img_buf

# 4. PDF 생성 함수 (그래프 이미지 포함)
def create_pdf(model_info, user_cmh, user_pa, chart_buf):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # 상단 텍스트 정보
    p.setFont("Helvetica-Bold", 20)
    p.drawString(50, height - 50, "Fan Selection Report")
    
    p.setFont("Helvetica", 12)
    p.line(50, height - 65, 550, height - 65)
    
    p.drawString(50, height - 100, f"Design Point: {user_cmh} CMH / {user_pa} Pa")
    
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, height - 140, "[ Selected Model Information ]")
    p.setFont("Helvetica", 12)
    p.drawString(50, height - 170, f"Model Name: {model_info.iloc[0]}")
    p.drawString(50, height - 190, f"Performance: {model_info.iloc[3]} CMH / {model_info.iloc[5]} Pa")
    p.drawString(50, height - 210, f"Motor Power: {model_info.iloc[6]} kW")
    
    # --- 그래프 삽입 부분 ---
    p.drawString(50, height - 260, "[ Performance Chart ]")
    # 그래프 버퍼를 이미지로 읽어서 삽입 (x, y, width, height)
    img = ImageReader(chart_buf)
    p.drawImage(img, 50, height - 620, width=500, height=330)
    
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
        st.success(f"조건에 맞는 송풍기를 {len(best_ones)}개 찾았습니다!")
        st.dataframe(best_ones, use_container_width=True)
        
        top_model = best_ones.iloc[0]

        # 그래프 생성 (Matplotlib 사용)
        chart_img = create_fan_chart(df, user_cmh, user_pa)
        
        # 화면에 그래프 표시
        st.divider()
        st.subheader("📈 성능 분포 그래프")
        st.image(chart_img, caption="선정 위치 십자선 표시 (Red Line)", use_container_width=True)

        # PDF 생성 및 다운로드 버튼
        pdf_buf = create_pdf(top_model, user_cmh, user_pa, chart_img)
        st.download_button(
            label="📥 그래프 포함 PDF 보고서 다운로드",
            data=pdf_buf,
            file_name=f"Report_{top_model.iloc[0]}.pdf",
            mime="application/pdf"
        )
    else:
        st.warning("⚠️ 조건에 맞는 모델이 없습니다.")