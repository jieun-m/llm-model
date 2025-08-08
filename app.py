import streamlit as st
import os
import pandas as pd
from services.azure_clients import get_container_client, setup_openai_client
from services.document_intelligence import list_blobs_by_prefix, extract_job_posting_text, analyze_resume_with_ai
from services.llm_service import evaluate_candidate_fit, extract_score_from_evaluation
from components.chatbot import chat_with_llm
from utils.data_parser import process_certificate_field, process_award_field, process_education_field, process_experience_field

def main():
    st.set_page_config(
        page_title="이력서 분석 시스템",
        page_icon="📄",
        layout="wide"
    )
    
    # 스크롤바 너비 조절
    st.markdown("""
    <style>
        ::-webkit-scrollbar {
            width: 12px;
        }
    </style>
    """, unsafe_allow_html=True)
    
    st.title("📄 이력서 분석 시스템")
    
    # API 키 디버그 정보 표시
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    # 환경 변수 상태 확인
    env_vars = {
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        "AZURE_ENDPOINT": os.getenv("AZURE_ENDPOINT"),
        "OPENAI_API_VERSION": os.getenv("OPENAI_API_VERSION"),
        "OPENAI_API_TYPE": os.getenv("OPENAI_API_TYPE"),
        "AZURE_STORAGE_CONNECTION_STRING": os.getenv("AZURE_STORAGE_CONNECTION_STRING"),
        "DOCUMENT_INTELLIGENCE_ENDPOINT": os.getenv("DOCUMENT_INTELLIGENCE_ENDPOINT"),
        "DOCUMENT_INTELLIGENCE_KEY": os.getenv("DOCUMENT_INTELLIGENCE_KEY")
    }
    
    # 디버그 정보 표시 (개발용)
    with st.expander("🔍 API 키 디버그 정보", expanded=False):
        st.write("**환경 변수 상태:**")
        for key, value in env_vars.items():
            if value:
                # API 키는 보안을 위해 일부만 표시
                if "KEY" in key or "CONNECTION_STRING" in key:
                    masked_value = value[:10] + "..." + value[-10:] if len(value) > 20 else "***"
                    st.write(f"- {key}: {masked_value}")
                else:
                    st.write(f"- {key}: {value}")
            else:
                st.write(f"- {key}: ❌ 설정되지 않음")
        
        # 누락된 필수 API 키 확인
        missing_apis = []
        if not env_vars["OPENAI_API_KEY"]:
            missing_apis.append("Azure OpenAI API 키")
        if not env_vars["AZURE_ENDPOINT"]:
            missing_apis.append("Azure OpenAI 엔드포인트")
        if not env_vars["AZURE_STORAGE_CONNECTION_STRING"]:
            missing_apis.append("Azure Storage 연결 문자열")
        if not env_vars["DOCUMENT_INTELLIGENCE_ENDPOINT"]:
            missing_apis.append("Document Intelligence 엔드포인트")
        if not env_vars["DOCUMENT_INTELLIGENCE_KEY"]:
            missing_apis.append("Document Intelligence 키")
        
        if missing_apis:
            st.error(f"❌ 다음 API 키가 설정되지 않았습니다: {', '.join(missing_apis)}")
        else:
            st.success("✅ 모든 필수 API 키가 설정되었습니다.")
    
    st.markdown("---")
    
    # 컨테이너 클라이언트 가져오기
    container_client = get_container_client()
    
    if not container_client:
        st.error("컨테이너에 연결할 수 없습니다.")
        return
    
    # 채용공고 파일들 가져오기
    job_files = list_blobs_by_prefix(container_client, "job-posting/")
    
    # 채용공고 선택 및 표시
    if job_files:
        st.subheader("📢 채용공고")
        selected_job = st.selectbox(
            "채용공고 파일 선택", 
            job_files, 
            format_func=lambda x: os.path.basename(x),
            help="분석할 채용공고를 선택하세요"
        )
        
        if selected_job:
            # 채용공고 텍스트 추출
            job_text = extract_job_posting_text(selected_job, container_client)
            
            if job_text:
                with st.expander(f"📋 {os.path.basename(selected_job)} - 채용공고 내용", expanded=True):
                    st.text_area("채용공고 내용", job_text, height=800, disabled=True)
                    
                    # 채용공고 다운로드 버튼
                    blob_client = container_client.get_blob_client(selected_job)
                    st.download_button(
                        label="📥 채용공고 파일 다운로드",
                        data=blob_client.download_blob().readall(),
                        file_name=os.path.basename(selected_job),
                        mime="application/octet-stream"
                    )
            else:
                st.warning("선택한 채용공고에서 텍스트를 추출할 수 없습니다.")
    else:
        st.info("📢 채용공고가 업로드되어 있지 않습니다.")
    
    st.markdown("---")
    
    # 세션 상태 초기화
    if 'analysis_in_progress' not in st.session_state:
        st.session_state.analysis_in_progress = False
    if 'analysis_results' not in st.session_state:
        st.session_state.analysis_results = None
    if 'analysis_completed' not in st.session_state:
        st.session_state.analysis_completed = False
    
    # Resume 폴더의 파일들 가져오기
    try:
        if not container_client:
            st.error("컨테이너 클라이언트가 None입니다.")
            return
        
        blobs = container_client.list_blobs()
        if blobs is None:
            st.warning("Blob 목록을 가져올 수 없습니다.")
            return
        
        blob_list = list(blobs)
        resume_files = [blob for blob in blob_list if 'resume' in blob.name.lower()]
        
        st.info(f"총 {len(blob_list)}개의 파일을 찾았고, 그 중 {len(resume_files)}개의 이력서 파일이 있습니다.")
        
        if not resume_files:
            st.warning("📁 Resume 폴더에 파일이 없습니다.")
            return
        
        # 분석 중이 아닐 때와 분석 중일 때를 완전히 분리
        if not st.session_state.analysis_in_progress:
            # 분석 중이 아닐 때만 표시할 컨테이너
            with st.container():
                st.subheader(f"📋 Resume 폴더 파일 목록 ({len(resume_files)}개)")
                
                # 분석 버튼
                if st.button("🚀 모든 이력서 분석 시작", type="primary"):
                    st.session_state.analysis_in_progress = True
                    st.session_state.analysis_completed = False
                    st.session_state.analysis_results = None
                    st.rerun()
                
                # 파일 목록 표시
                st.write("**📁 분석할 파일 목록:**")
                for blob in resume_files:
                    st.write(f"- {blob.name}")
        
        # 분석 중일 때 - 완전히 다른 컨테이너
        if st.session_state.analysis_in_progress:
            # 기존 컨텐츠를 지우고 분석 진행 상태만 표시
            analysis_container = st.empty()
            with analysis_container.container():
                st.info("분석을 시작합니다. 잠시만 기다려주세요...")
            
            # 진행률 표시
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            all_results = []
            
            for i, blob in enumerate(resume_files):
                status_text.text(f"분석 중: {blob.name} ({i+1}/{len(resume_files)})")
                
                # Document Intelligence로 분석
                analysis_result = analyze_resume_with_ai(blob.name)
                
                if analysis_result:
                    # 적합성 평가 결과도 함께 저장
                    fitness_evaluation = None
                    fitness_score = None
                    
                    if job_files and selected_job:
                        job_text = extract_job_posting_text(selected_job, container_client)
                        if job_text and analysis_result["documents"] and analysis_result["documents"][0]["fields"]:
                            fields_data = analysis_result["documents"][0]["fields"]
                            target_fields = ["학력사항", "경력사항", "자격증", "수상경력"]
                            resume_fields = {}
                            
                            for field_name in target_fields:
                                if field_name in fields_data:
                                    if field_name == "학력사항":
                                        # 학력사항 데이터를 구조화된 형태로 변환
                                        from services.llm_service import process_education_field
                                        education_data = process_education_field(fields_data[field_name]['content'])
                                        resume_fields[field_name] = education_data
                                    elif field_name == "경력사항":
                                        # 경력사항 데이터를 구조화된 형태로 변환
                                        from services.llm_service import process_experience_field
                                        experience_data = process_experience_field(fields_data[field_name]['content'])
                                        resume_fields[field_name] = experience_data
                                    elif field_name == "자격증":
                                        # 자격증 데이터를 구조화된 형태로 변환
                                        from services.llm_service import process_certificate_field
                                        certificate_data = process_certificate_field(fields_data[field_name]['content'])
                                        resume_fields[field_name] = certificate_data
                                    elif field_name == "수상경력":
                                        # 수상경력 데이터를 구조화된 형태로 변환
                                        from services.llm_service import process_award_field
                                        award_data = process_award_field(fields_data[field_name]['content'])
                                        resume_fields[field_name] = award_data
                                    else:
                                        resume_fields[field_name] = fields_data[field_name]['content']
                            
                            if resume_fields:
                                # API 키 상태 확인
                                import os
                                from dotenv import load_dotenv
                                load_dotenv()
                                
                                openai_key = os.getenv("OPENAI_API_KEY")
                                azure_endpoint = os.getenv("AZURE_ENDPOINT")
                                
                                # API 키 디버그 정보 추가
                                debug_info = f"""
🔍 디버그 정보:
- OpenAI API 키: {'설정됨' if openai_key else '설정되지 않음'}
- Azure 엔드포인트: {'설정됨' if azure_endpoint else '설정되지 않음'}
- 이력서 필드 수: {len(resume_fields)}
- 채용공고 길이: {len(job_text) if job_text else 0}자
"""
                                
                                success, evaluation_result = evaluate_candidate_fit(job_text, resume_fields)
                                if success:
                                    fitness_evaluation = evaluation_result
                                    fitness_score = extract_score_from_evaluation(evaluation_result)
                                else:
                                    # 실패 시 디버그 정보 포함
                                    fitness_evaluation = f"❌ 평가 실패\n{debug_info}\n\n오류: {evaluation_result}"
                                    fitness_score = None
                    
                    all_results.append({
                        "file_name": blob.name,
                        "analysis": analysis_result,
                        "fitness_evaluation": fitness_evaluation,
                        "fitness_score": fitness_score
                    })
                
                # 진행률 업데이트
                progress_bar.progress((i + 1) / len(resume_files))
            
            # 분석 완료
            st.session_state.analysis_results = all_results
            st.session_state.analysis_in_progress = False
            st.session_state.analysis_completed = True
            st.rerun()
        
        # 분석 완료 후 결과 표시
        if st.session_state.analysis_completed and st.session_state.analysis_results:
            all_results = st.session_state.analysis_results
            
            st.success(f"✅ {len(all_results)}개 파일 분석 완료!")
            
            # 결과 요약
            st.subheader("📊 분석 결과 요약")
            
            summary_data = []
            for result in all_results:
                file_name = result["file_name"]
                analysis = result["analysis"]
                
                # 문서 정보
                doc_count = len(analysis["documents"])
                page_count = len(analysis["pages"])
                table_count = len(analysis["tables"])
                kv_count = len(analysis["key_value_pairs"])
                
                # 필드 정보 (첫 번째 문서 기준)
                fields = []
                if analysis["documents"]:
                    fields = list(analysis["documents"][0]["fields"].keys())
                
                # 저장된 적합성 점수 사용
                fitness_score = result.get("fitness_score")
                
                summary_data.append({
                    "파일명": file_name,
                    "문서 수": doc_count,
                    "페이지 수": page_count,
                    "테이블 수": table_count,
                    "키-값 쌍 수": kv_count,
                    "추출된 필드": ", ".join(fields[:5]) + ("..." if len(fields) > 5 else ""),
                    "적합성 점수": fitness_score if fitness_score is not None else "평가 불가"
                })
            
            # 점수 순으로 정렬 (점수가 높은 순)
            df_summary = pd.DataFrame(summary_data)
            # 적합성 점수가 숫자인 경우만 정렬 가능하도록 처리
            df_summary['정렬용_점수'] = pd.to_numeric(df_summary['적합성 점수'].replace('평가 불가', -1), errors='coerce')
            df_summary = df_summary.sort_values('정렬용_점수', ascending=False)
            df_summary = df_summary.drop('정렬용_점수', axis=1)
            
            # 요약 테이블 표시
            st.dataframe(df_summary, use_container_width=True)
            
            # 상세 결과 표시
            st.subheader("🔍 상세 분석 결과")
            
            for result in all_results:
                file_name = result["file_name"]
                analysis = result["analysis"]
                
                with st.expander(f"📄 {file_name}", expanded=False):
                    # 필드 정보 표시
                    if analysis["documents"] and analysis["documents"][0]["fields"]:
                        st.write("**🏷️ 추출된 필드:**")
                        fields = analysis["documents"][0]["fields"]
                        
                        # 필드 데이터를 테이블 형태로 준비
                        field_data = []
                        for field_name, field_info in fields.items():
                            # 학력사항 필드인 경우 구조화된 형태로 표시
                            if field_name == "학력사항":
                                from services.llm_service import process_education_field
                                education_data = process_education_field(field_info['content'])
                                if education_data:
                                    # 학력사항 데이터를 JSON 형태로 표시
                                    import json
                                    education_json = json.dumps(education_data, ensure_ascii=False, indent=2)
                                    field_data.append({
                                        "필드명": field_name,
                                        "타입": field_info['type'],
                                        "값": education_json,
                                        "신뢰도": f"{field_info['confidence']:.2f}"
                                    })
                                else:
                                    field_data.append({
                                        "필드명": field_name,
                                        "타입": field_info['type'],
                                        "값": "학력사항 정보 없음",
                                        "신뢰도": f"{field_info['confidence']:.2f}"
                                    })
                            elif field_name == "경력사항":
                                # 경력사항 필드인 경우 구조화된 형태로 표시
                                from services.llm_service import process_experience_field
                                experience_data = process_experience_field(field_info['content'])
                                if experience_data:
                                    # 경력사항 데이터를 JSON 형태로 표시
                                    import json
                                    experience_json = json.dumps(experience_data, ensure_ascii=False, indent=2)
                                    field_data.append({
                                        "필드명": field_name,
                                        "타입": field_info['type'],
                                        "값": experience_json,
                                        "신뢰도": f"{field_info['confidence']:.2f}"
                                    })
                                else:
                                    field_data.append({
                                        "필드명": field_name,
                                        "타입": field_info['type'],
                                        "값": "경력사항 정보 없음",
                                        "신뢰도": f"{field_info['confidence']:.2f}"
                                    })
                            elif field_name == "자격증":
                                from services.llm_service import process_certificate_field
                                certificate_data = process_certificate_field(field_info['content'])
                                if certificate_data:
                                    # 자격증 데이터를 JSON 형태로 표시
                                    import json
                                    certificate_json = json.dumps(certificate_data, ensure_ascii=False, indent=2)
                                    field_data.append({
                                        "필드명": field_name,
                                        "타입": field_info['type'],
                                        "값": certificate_json,
                                        "신뢰도": f"{field_info['confidence']:.2f}"
                                    })
                                else:
                                    field_data.append({
                                        "필드명": field_name,
                                        "타입": field_info['type'],
                                        "값": "자격증 정보 없음",
                                        "신뢰도": f"{field_info['confidence']:.2f}"
                                    })
                            elif field_name == "수상경력":
                                # 수상경력 필드인 경우 구조화된 형태로 표시
                                from services.llm_service import process_award_field
                                award_data = process_award_field(field_info['content'])
                                if award_data:
                                    # 수상경력 데이터를 JSON 형태로 표시
                                    import json
                                    award_json = json.dumps(award_data, ensure_ascii=False, indent=2)
                                    field_data.append({
                                        "필드명": field_name,
                                        "타입": field_info['type'],
                                        "값": award_json,
                                        "신뢰도": f"{field_info['confidence']:.2f}"
                                    })
                                else:
                                    field_data.append({
                                        "필드명": field_name,
                                        "타입": field_info['type'],
                                        "값": "수상경력 정보 없음",
                                        "신뢰도": f"{field_info['confidence']:.2f}"
                                    })
                            else:
                                field_data.append({
                                    "필드명": field_name,
                                    "타입": field_info['type'],
                                    "값": field_info['content'],
                                    "신뢰도": f"{field_info['confidence']:.2f}"
                                })
                        
                        # 필드 데이터를 테이블로 표시
                        if field_data:
                            df_fields = pd.DataFrame(field_data)
                            st.dataframe(df_fields, use_container_width=True)
                    
                    # 채용 적합성 평가
                    if job_files and selected_job:
                        job_text = extract_job_posting_text(selected_job, container_client)
                        if job_text:
                            st.markdown("---")
                            st.write("**🎯 채용 적합성 평가:**")
                            
                            # 이력서 필드 데이터 준비 (요약 테이블과 동일한 필드만 사용)
                            target_fields = ["학력사항", "경력사항", "자격증", "수상경력"]
                            resume_fields = {}
                            
                            for field_name in target_fields:
                                if field_name in fields:
                                    if field_name == "학력사항":
                                        # 학력사항 데이터를 구조화된 형태로 변환
                                        from services.llm_service import process_education_field
                                        education_data = process_education_field(fields[field_name]['content'])
                                        resume_fields[field_name] = education_data
                                    elif field_name == "경력사항":
                                        # 경력사항 데이터를 구조화된 형태로 변환
                                        from services.llm_service import process_experience_field
                                        experience_data = process_experience_field(fields[field_name]['content'])
                                        resume_fields[field_name] = experience_data
                                    elif field_name == "자격증":
                                        # 자격증 데이터를 구조화된 형태로 변환
                                        from services.llm_service import process_certificate_field
                                        certificate_data = process_certificate_field(fields[field_name]['content'])
                                        resume_fields[field_name] = certificate_data
                                    elif field_name == "수상경력":
                                        # 수상경력 데이터를 구조화된 형태로 변환
                                        from services.llm_service import process_award_field
                                        award_data = process_award_field(fields[field_name]['content'])
                                        resume_fields[field_name] = award_data
                                    else:
                                        resume_fields[field_name] = fields[field_name]['content']
                            
                            # 평가 기준 데이터 JSON 형식으로 표시
                            st.write("**📋 평가 기준 데이터:**")
                            import json
                            
                            # 추출할 주요 필드들
                            target_fields = ["학력사항", "경력사항", "자격증", "수상경력"]
                            extracted_info = {}
                            
                            for field_name in target_fields:
                                if field_name in fields:
                                    field_info = fields[field_name]
                                    
                                    # 학력사항 필드인 경우 구조화된 형태로 변환
                                    if field_name == "학력사항":
                                        from services.llm_service import process_education_field
                                        education_data = process_education_field(field_info['content'])
                                        extracted_info[field_name] = education_data
                                    elif field_name == "경력사항":
                                        # 경력사항 필드인 경우 구조화된 형태로 변환
                                        from services.llm_service import process_experience_field
                                        experience_data = process_experience_field(field_info['content'])
                                        extracted_info[field_name] = experience_data
                                    elif field_name == "자격증":
                                        from services.llm_service import process_certificate_field
                                        certificate_data = process_certificate_field(field_info['content'])
                                        extracted_info[field_name] = certificate_data
                                    elif field_name == "수상경력":
                                        # 수상경력 필드인 경우 구조화된 형태로 변환
                                        from services.llm_service import process_award_field
                                        award_data = process_award_field(field_info['content'])
                                        extracted_info[field_name] = award_data
                                    else:
                                        extracted_info[field_name] = {
                                            "content": field_info['content'],
                                            "confidence": field_info['confidence'],
                                            "type": field_info['type']
                                        }
                            
                            # JSON 형태로 표시
                            if extracted_info:
                                formatted_json = json.dumps(extracted_info, ensure_ascii=False, indent=2)
                                st.code(formatted_json, language="json")
                            else:
                                st.warning("평가 기준 데이터를 추출할 수 없습니다.")
                            
                            # 저장된 적합성 평가 결과 사용
                            fitness_evaluation = result.get("fitness_evaluation")
                            
                            if fitness_evaluation:
                                st.success("✅ 적합성 평가 결과")
                                st.markdown("**📊 평가 결과:**")
                                st.text_area(
                                    "평가 결과",
                                    value=fitness_evaluation,
                                    height=200,
                                    disabled=True,
                                    key=f"eval_result_{file_name}"
                                )
                            else:
                                st.warning("⚠️ 적합성 평가 결과가 없습니다.")
    
    except Exception as e:
        st.error(f"파일 목록 가져오기 실패: {str(e)}")
    
    # 챗봇 기능 호출 (항상 화면 하단에 표시)
    chat_with_llm()

if __name__ == "__main__":
    main() 