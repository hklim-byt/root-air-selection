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

# 1. 메인 그래프 생성 (V6.5 마스터 로직 유지)
def create_master_chart(all_df, selected_model, user_cmh, user_pa):
    model_df = all_df[all_df['model_name'] == selected_model].sort_values(by=['rpm', 'CMH'])
    rpms = sorted(model_df['rpm'].unique())
    fig, ax = plt.subplots(figsize=(10, 6.5))
    for rpm in rpms:
        data = model_df[model_df['rpm'] == rpm]
        ax.plot(data['CMH'], data['Pa'], color='steelblue', linewidth=1.0, alpha=0.4)
        ax.text(data['CMH'].iloc[-1], data['Pa'].iloc[-1], f' {int(rpm)} RPM', color='steelblue', fontsize=8, alpha=0.6)
    x_path = np.linspace(0, user_cmh * 1.1, 100)
    k = user_pa / (user_cmh**2) if user_cmh != 0 else 0
    y_path = k * (x_path**2)
    ax.plot(x_path, y_path, color='#1f77b4', linewidth=3.5, label='System Curve')
    ax.axvline(user_cmh, color='red', linestyle='--', linewidth=0.8, alpha=0.4)
    ax.axhline(user_pa, color='red', linestyle='--', linewidth=0.8, alpha=0.4)
    ax.scatter(user_cmh, user_pa, color='red', s=120, edgecolors='white', zorder=20)
    ax.set_title(f"Performance Map: {selected_model}", fontsize=14, fontweight='bold')
    ax.grid(True, linestyle=':', alpha=0.4)
    buf = BytesIO(); plt.savefig(buf, format='png', dpi=200); buf.seek(0); plt.close(fig)
    return buf

# 2. 소음 그래프 생성
def create_noise_chart(noise_row):
    bands = ['63', '125', '250', '500', '1k', '2k', '4k', '8k']
    vals = [float(str(noise_row[[c for c in noise_row.index if b in c][0]]).split('/')[0]) for b in bands]
    fig, ax = plt.subplots(figsize=(10, 3.5))
    ax.bar(bands, vals, color='skyblue', edgecolor='navy', alpha=0.7)
    ax.set_title('Octave Band Spectrum (dB)', fontsize=12)
    buf = BytesIO(); plt.savefig(buf, format='png', dpi=150); buf.seek(0); plt.close(fig)
    return buf

# 3. PDF 생성 (요청하신 3가지 수정사항 반영)
def create_final_report(project_info, model_data, chart_buf, noise_buf, design_point):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    
    # 타이틀
    p.setFont("Helvetica-Bold", 22); p.drawString(50, h-50, "Technical Selection Report")
    p.line(50, h-60, 545, h-60)

    # [수정 1 & 2] 데이터 분리 및 수직 배치
    # 1. Project Information (좌측)
    p.setFont("Helvetica-Bold", 12); p.drawString(50, h-85, "[1] Project Information")
    p.setFont("Helvetica", 10)
    p.drawString(60, h-105, f"Project Name: {project_info['project']}")
    p.drawString(60, h-120, f"Customer: {project_info['customer']}")
    p.drawString(60, h-135, f"Engineer: {project_info['manager']}")
    p.drawString(60, h-150, f"Date: {project_info['date']}")

    # 2. Design & Performance Data (우측 수직 배치)
    p.setFont("Helvetica-Bold", 12); p.drawString(300, h-85, "[2] Design & Performance")
    p.setFont("Helvetica", 10)
    p.drawString(310, h-105, f"Selected Model: {model_data['model_name']}")
    p.drawString(310, h-120, f"Design Flow: {design_point['cmh']:,} CMH")
    p.drawString(310, h-135, f"Design Pressure: {design_point['pa']:,} Pa")
    p.drawString(310, h-150, f"Operating Speed: {model_data['rpm']} RPM")
    p.drawString(310, h-165, f"Absorbed Power: {model_data['power (kW)']} kW")
    p.drawString(310, h-180, f"Total Efficiency: {model_data['total efficiency (%)']}%")

    # 성능 그래프 삽입
    p.drawImage(ImageReader(chart_buf), 45, h-510, width=500, height=320)

    # [수정 3] 소음 그래프 및 하단 표 형식 데이터
    p.setFont("Helvetica-Bold", 12); p.drawString(50, h-535, "[3] Acoustic Analysis")
    p.drawImage(ImageReader(noise_buf), 50, h-700, width=490, height=160)
    
    # 소음 데이터 표 (Table) 그리기
    table_y = h-740
    p.setLineWidth(1); p.setStrokeColor(colors.black)
    # 표 헤더 배경
    p.setFillColor(colors.lightgrey); p.rect(50, table_y, 495, 20, fill=1)
    p.setFillColor(colors.black); p.setFont("Helvetica-Bold", 9)
    
    bands = ['63Hz', '125Hz', '250Hz', '500Hz', '1kHz', '2kHz', '4kHz', '8kHz', 'Total']
    for i, b in enumerate(bands):
        p.drawString(55 + (i*55), table_y + 7, b)
    
    # 표 수치 데이터
    p.setFont("Helvetica", 9); table_y -= 20
    p.rect(50, table_y, 495, 20, fill=0)
    noise_vals = [model_data['63Hz(dB / dB(A))'], model_data['125Hz(dB / dB(A))'], 
                  model_data['250Hz(dB / dB(A))'], model_data['500Hz(dB / dB(A))'],
                  model_data['1kHz(dB / dB(A))'], model_data['2kHz(dB / dB(A))'],
                  model_data['4kHz(dB / dB(A))'], model_data['8kHz(dB / dB(A))'],
                  model_data['Total_dB / dB(A)']]
    
    for i, v in enumerate(noise_vals):
        val_display = str(v).split('/')[0].strip() + " dB"
        p.drawString(55 + (i*55), table_y + 7, val_display)

    p.showPage(); p.save(); buffer.seek(0)
    return buffer

# --- 메인 로직 (Streamlit) ---
# (이전 데이터 로드 및 UI 부분 동일)