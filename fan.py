# 4. 그래프 생성 함수 (데이터 누락 대응 버전)
def create_noise_chart(noise_row):
    bands = ['63Hz', '125Hz', '250Hz', '500Hz', '1kHz', '2kHz', '4kHz', '8kHz']
    available_bands = [b for b in bands if b in noise_row.index]
    if not available_bands: return None
    
    # 데이터를 숫자로 변환하고, 빈 값(NaN)은 0으로 채웁니다.
    import numpy as np
    values = pd.to_numeric([noise_row[b] for b in available_bands], errors='coerce')
    values = np.nan_to_num(values) # 숫자가 아닌 값은 0으로 변경
    
    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.bar(available_bands, values, color='skyblue', edgecolor='navy')
    
    # Y축 범위 설정 시 에러 방지
    max_val = max(values) if len(values) > 0 else 0
    ax.set_ylim(0, max_val + 20 if max_val > 0 else 100)
    
    ax.set_ylabel('Sound Pressure Level (dB)')
    ax.set_title('Octave Band Noise Spectrum')
    
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 1, f'{int(height)}', ha='center', va='bottom')
    
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=150)
    buf.seek(0)
    plt.close(fig)
    return buf