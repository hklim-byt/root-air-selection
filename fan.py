# 4. 그래프 생성 함수 (소음 옥타브 밴드)
def create_noise_chart(noise_data):
    # 이 아래 줄들은 모두 같은 깊이로 들여쓰기가 되어야 합니다.
    noise_bands = ['63Hz', '125Hz', '250Hz', '500Hz', '1kHz', '2kHz', '4kHz', '8kHz']
    
    # 실제 데이터에서 해당 컬럼만 추출
    available_bands = [b for b in noise_bands if b in noise_data.columns]
    
    if not available_bands:
        return None
        
    values = noise_data[available_bands].values[0]
    
    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.bar(available_bands, values, color='skyblue', edgecolor='navy')
    
    ax.set_ylim(0, max(values) + 20 if len(values)>0 else 100)
    ax.set_ylabel('Sound Pressure Level (dB)')
    ax.set_title('Octave Band Noise Spectrum')
    ax.grid(axis='y', linestyle=':', alpha=0.7)
    
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 1, f'{int(height)}', ha='center', va='bottom', fontweight='bold')
    
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=150)
    buf.seek(0)
    plt.close(fig)
    return buf