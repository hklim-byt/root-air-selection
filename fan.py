# ... (앞부분 생략: 상단 레이아웃 및 데이터 로드 코드는 동일)

# 5. 메인 로직
if df is not None:
    st.divider()
    
    # 프로젝트 정보 입력 섹션 (안내 문구 강화)
    st.subheader("📋 프로젝트 정보 입력")
    st.info("⚠️ PDF 보고서 한글 깨짐 방지를 위해 **모든 항목을 영문(English)**으로 작성해 주세요.")
    
    row1_col1, row1_col2, row1_col3 = st.columns(3)
    with row1_col1:
        # placeholder에 영문 작성을 유도하는 메시지를 넣었습니다.
        project_name = st.text_input("공사명 (Project Name)", placeholder="Example: 00 Plant Project (English Only)")
    with row1_col2:
        customer_name = st.text_input("고객사 (Customer)", placeholder="Example: Root Air Co., Ltd.")
    with row1_col3:
        manager_name = st.text_input("담당자 (Manager)", placeholder="Example: Gildong Hong")

    st.subheader("🔍 설계 조건 입력")
    # ... (중략: 풍량/정압 입력 및 선정 로직 동일)

    if not matched_fans.empty:
        # ... (중략: 그래프 생성 동일)

        # PDF 다운로드 부분
        pdf_buf = create_pdf(top_model, user_cmh, user_pa, chart_img, project_info)
        st.download_button(
            label="📥 Download Selection Report (PDF)", # 버튼도 영문으로 변경
            data=pdf_buf,
            file_name=f"Report_{project_name}.pdf" if project_name else "Report.pdf",
            mime="application/pdf"
        )
        
# ... (이하 동일)