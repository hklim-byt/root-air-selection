# 4. 그래프 생성 함수 (소음 옥타브 밴드) - 더 안전한 버전
def create_noise_chart(noise_data):
    # 주파수 대역 이름 (CSV 컬럼명과 일치해야 함)
    bands = ['63Hz', '125Hz', '250Hz', '500Hz', '1kHz', '2kHz', '4kHz', '8kHz']
    
    # 실제 데이터에서 해당 컬럼만 추출 (에러 방지를 위해 존재하는 것만 필터링)
    available_bands = [b for b in bands if b in noise_data.columns]
    
    if not available_bands:
        return None
        
    values = noise_data[available_bands].values[0]
    
    fig, ax = plt.subplots(figsize=(8, 4))
    # 그래프 그리기
    bars = ax.bar(available_bands, values, color='skyblue', edgecolor='navy')
    
    # 스타일 설정
    ax.set_ylim(0, max(values) + 20 if len(values)>0 else 100)
    ax.set_ylabel('Sound Pressure Level (dB)')
    ax.set_title('Octave Band Noise Spectrum')
    ax.grid(axis='y', linestyle=':', alpha=0.7)
    
    # 막대 위에 숫자 표시
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 1, f'{int(height)}', ha='center', va='bottom', fontweight='bold')
    
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=150)
    buf.seek(0)
    plt.close(fig)
    return buf

# --- 메인 로직 내 그래프 출력 부분 수정 ---
# (if not matched.empty: 블록 내부를 아래처럼 수정하세요)
        # 소음 컬럼이 있는지 확인
        noise_bands = ['63Hz', '125Hz', '250Hz', '500Hz', '1kHz', '2kHz', '4kHz', '8kHz']
        has_noise = all(b in df.columns for b in noise_bands)
        
        col1, col2 = st.columns(2)
        with col1:
            st.image(perf_img, caption="Performance Curve")
        with col2:
            if has_noise:
                noise_img = create_noise_chart(pd.DataFrame([best]))
                if noise_img:
                    st.image(noise_img, caption="Noise Spectrum")
            else:
                st.warning("⚠️ CSV 파일에서 소음 컬럼(63Hz~8kHz)을 찾을 수 없습니다. 컬럼명을 확인해 주세요.")