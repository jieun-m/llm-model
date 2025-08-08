import streamlit as st
import openai
import re
# from config import *
from dotenv import load_dotenv
import os
from services.azure_clients import setup_openai_client

# .env 파일 로드
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_TYPE = os.getenv("OPENAI_API_TYPE")
OPENAI_API_VERSION = os.getenv("OPENAI_API_VERSION")
AZURE_ENDPOINT = os.getenv("AZURE_ENDPOINT")

AZURE_SEARCH_SERVICE_NAME = os.getenv("AZURE_SEARCH_SERVICE_NAME")
AZURE_SEARCH_INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX_NAME")
AZURE_SEARCH_API_KEY = os.getenv("AZURE_SEARCH_API_KEY")
AZURE_SEARCH_API_VERSION = os.getenv("AZURE_SEARCH_API_VERSION")

# 데이터 파싱 함수들 추가
def parse_certificate_data(certificate_text):
    """자격증 텍스트를 파싱하여 구조화된 형태로 변환"""
    if not certificate_text or certificate_text.strip() == "":
        return []
    
    # \n을 기준으로 분리
    lines = certificate_text.strip().split('\n')
    
    certificates = []
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        # 빈 줄 건너뛰기
        if not line:
            i += 1
            continue
        
        # 날짜 패턴 확인 (YYYY.MM.DD 또는 YYYY-MM-DD)
        date_pattern = r'^\d{4}[.-]\d{2}[.-]\d{2}$'
        
        if re.match(date_pattern, line):
            # 날짜를 찾았으면 다음 2개 라인이 자격증명과 발급기관일 가능성이 높음
            try:
                date_str = line
                # 날짜 형식 통일 (YYYY-MM-DD)
                if '.' in date_str:
                    date_str = date_str.replace('.', '-')
                
                # 다음 라인들이 있는지 확인
                if i + 1 < len(lines) and i + 2 < len(lines):
                    certificate_name = lines[i + 1].strip()
                    issuing_authority = lines[i + 2].strip()
                    
                    # 유효한 데이터인지 확인
                    if certificate_name and issuing_authority:
                        certificates.append({
                            "자격증명": certificate_name,
                            "발급기관": issuing_authority,
                            "취득일": date_str
                        })
                        i += 3  # 3개 라인을 처리했으므로 3칸 이동
                    else:
                        i += 1
                else:
                    i += 1
            except Exception as e:
                i += 1
        else:
            i += 1
    
    return certificates

def process_certificate_field(field_content):
    """자격증 필드 내용을 구조화된 형태로 변환"""
    if not field_content:
        return []
    
    return parse_certificate_data(field_content)

def parse_award_data(award_text):
    """수상경력 텍스트를 파싱하여 구조화된 형태로 변환"""
    if not award_text or award_text.strip() == "":
        return []
    
    # \n을 기준으로 분리
    lines = award_text.strip().split('\n')
    
    awards = []
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        # 빈 줄 건너뛰기
        if not line:
            i += 1
            continue
        
        # 날짜 패턴 확인 (YYYY.MM.DD 또는 YYYY-MM-DD)
        date_pattern = r'^\d{4}[.-]\d{2}[.-]\d{2}$'
        
        if re.match(date_pattern, line):
            # 날짜를 찾았으면 다음 2개 라인이 활동내용과 주관처일 가능성이 높음
            try:
                date_str = line
                # 날짜 형식 통일 (YYYY-MM-DD)
                if '.' in date_str:
                    date_str = date_str.replace('.', '-')
                
                # 다음 라인들이 있는지 확인
                if i + 1 < len(lines) and i + 2 < len(lines):
                    activity_content = lines[i + 1].strip()
                    organizing_body = lines[i + 2].strip()
                    
                    # 유효한 데이터인지 확인
                    if activity_content and organizing_body:
                        awards.append({
                            "활동내용": activity_content,
                            "주관처": organizing_body,
                            "수상일": date_str
                        })
                        i += 3  # 3개 라인을 처리했으므로 3칸 이동
                    else:
                        i += 1
                else:
                    i += 1
            except Exception as e:
                i += 1
        else:
            i += 1
    
    return awards

def process_award_field(field_content):
    """수상경력 필드 내용을 구조화된 형태로 변환"""
    if not field_content:
        return []
    
    return parse_award_data(field_content)

def parse_education_data(education_text):
    """
    학력사항 텍스트를 파싱하여 구조화된 형태로 변환
    """
    if not education_text or education_text.strip() == "":
        return []
    
    # \n을 기준으로 분리
    lines = education_text.strip().split('\n')
    
    education_records = []
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        # 빈 줄 건너뛰기
        if not line:
            i += 1
            continue
        
        # 졸업년도 패턴 확인 (YYYY)
        year_pattern = r'^\d{4}$'
        
        if re.match(year_pattern, line):
            # 졸업년도를 찾았으면 다음 라인들을 확인
            try:
                graduation_year = line
                
                # 다음 라인들이 있는지 확인
                if i + 1 < len(lines):
                    education_level = lines[i + 1].strip()  # 중학교, 고등학교, 대학교, 석사 등
                    
                    if i + 2 < len(lines):
                        school_name = lines[i + 2].strip()
                        
                        if i + 3 < len(lines):
                            graduation_status = lines[i + 3].strip()  # 졸업, 재학 등
                            
                            # 기본 정보 구성
                            education_record = {
                                "졸업년도": graduation_year,
                                "학력": education_level,
                                "학교명": school_name,
                                "졸업여부": graduation_status
                            }
                            
                            # 전공 및 학점 정보가 있는지 확인
                            if i + 4 < len(lines):
                                next_line = lines[i + 4].strip()
                                if "전공:" in next_line or "학점:" in next_line:
                                    education_record["전공및학점"] = next_line
                                    i += 5  # 5개 라인을 처리했으므로 5칸 이동
                                else:
                                    i += 4  # 4개 라인을 처리했으므로 4칸 이동
                            else:
                                i += 4  # 4개 라인을 처리했으므로 4칸 이동
                            
                            # 유효한 데이터인지 확인
                            if education_level and school_name and graduation_status:
                                education_records.append(education_record)
                        else:
                            i += 1
                    else:
                        i += 1
                else:
                    i += 1
            except Exception as e:
                i += 1
        else:
            i += 1
    
    return education_records

def process_education_field(field_content):
    """학력사항 필드 내용을 구조화된 형태로 변환"""
    if not field_content:
        return []
    
    return parse_education_data(field_content)

def parse_experience_data(experience_text):
    """
    경력사항 텍스트를 파싱하여 구조화된 형태로 변환
    """
    if not experience_text or experience_text.strip() == "":
        return []
    
    # \n을 기준으로 분리
    lines = experience_text.strip().split('\n')
    
    experience_records = []
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        # 빈 줄 건너뛰기
        if not line:
            i += 1
            continue
        
        # 회사명으로 시작하는 경우 (직위 정보가 없는 경우도 있음)
        if line and not line.startswith('-') and not re.match(r'^\d{4}', line):
            company_name = line
            
            # 다음 라인이 있는지 확인
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                
                # 다음 라인이 직위인지 확인 (괄호가 포함된 경우)
                if '(' in next_line and ')' in next_line:
                    position = next_line
                    i += 2  # 회사명과 직위를 처리했으므로 2칸 이동
                    
                    # 업무내용 수집
                    job_description = []
                    while i < len(lines) and lines[i].strip().startswith('-'):
                        job_description.append(lines[i].strip())
                        i += 1
                    
                    # 업무기간 찾기
                    work_period = ""
                    if i < len(lines):
                        period_line = lines[i].strip()
                        if re.match(r'^\d{4}', period_line):
                            work_period = period_line
                            # "현재"가 포함되어 있으면 "현재" 부분만 "2025-08-01"로 변경
                            if "현재" in work_period:
                                work_period = work_period.replace("현재", "2025-08")
                            i += 1
                    
                    # 경력 기록 생성
                    experience_record = {
                        "회사명": company_name,
                        "직위": position,
                        "업무내용": " ".join(job_description) if job_description else "",
                        "업무기간": work_period
                    }
                    
                    experience_records.append(experience_record)
                else:
                    # 직위 정보가 없는 경우
                    i += 1
                    
                    # 업무내용 수집
                    job_description = []
                    while i < len(lines) and lines[i].strip().startswith('-'):
                        job_description.append(lines[i].strip())
                        i += 1
                    
                    # 업무기간 찾기
                    work_period = ""
                    if i < len(lines):
                        period_line = lines[i].strip()
                        if re.match(r'^\d{4}', period_line):
                            work_period = period_line
                            # "현재"가 포함되어 있으면 "현재" 부분만 "2025-08-01"로 변경
                            if "현재" in work_period:
                                work_period = work_period.replace("현재", "2025-08-01")
                            i += 1
                    
                    # 경력 기록 생성
                    experience_record = {
                        "회사명": company_name,
                        "직위": "",
                        "업무내용": " ".join(job_description) if job_description else "",
                        "업무기간": work_period
                    }
                    
                    experience_records.append(experience_record)
            else:
                i += 1
        else:
            i += 1
    
    return experience_records

def process_experience_field(field_content):
    """경력사항 필드 내용을 구조화된 형태로 변환"""
    if not field_content:
        return []
    
    return parse_experience_data(field_content)

# LangChain 관련 import 추가
try:
    from langchain_openai import AzureChatOpenAI
    from langchain.prompts import ChatPromptTemplate
    from langchain.chains import RetrievalQA
    from langchain_openai import AzureOpenAIEmbeddings
    from langchain_community.retrievers import AzureCognitiveSearchRetriever
    LANGCHAIN_AVAILABLE = True
except ImportError as e:
    st.error(f"LangChain 모듈을 불러올 수 없습니다: {str(e)}")
    LANGCHAIN_AVAILABLE = False

def evaluate_candidate_fit(job_posting_text, resume_fields):
    """
    채용공고와 이력서 내용을 바탕으로 지원자의 적합성을 평가하는 함수
    """
    try:
        # 자격증 데이터 구조화
        certificate_data = resume_fields.get('자격증', [])
        if isinstance(certificate_data, str):
            certificate_data = process_certificate_field(certificate_data)
        
        # 수상경력 데이터 구조화
        award_data = resume_fields.get('수상경력', [])
        if isinstance(award_data, str):
            award_data = process_award_field(award_data)
        
        # 학력사항 데이터 구조화
        education_data = resume_fields.get('학력사항', [])
        if isinstance(education_data, str):
            education_data = process_education_field(education_data)
        
        # 경력사항 데이터 구조화
        experience_data = resume_fields.get('경력사항', [])
        if isinstance(experience_data, str):
            experience_data = process_experience_field(experience_data)
        
        # 자격증 정보를 문자열로 변환
        certificate_text = ""
        if certificate_data:
            certificate_text = "자격증 정보:\n"
            for cert in certificate_data:
                certificate_text += f"- {cert['자격증명']} ({cert['발급기관']}, {cert['취득일']})\n"
        else:
            certificate_text = "자격증: 없음"
        
        # 수상경력 정보를 문자열로 변환
        award_text = ""
        if award_data:
            award_text = "수상경력 정보:\n"
            for award in award_data:
                award_text += f"- {award['활동내용']} ({award['주관처']}, {award['수상일']})\n"
        else:
            award_text = "수상경력: 없음"
        
        # 학력사항 정보를 문자열로 변환
        education_text = ""
        if education_data:
            education_text = "학력사항 정보:\n"
            for edu in education_data:
                edu_info = f"- {edu['학력']} ({edu['학교명']}, {edu['졸업년도']}, {edu['졸업여부']})"
                if '전공및학점' in edu:
                    edu_info += f" - {edu['전공및학점']}"
                education_text += edu_info + "\n"
        else:
            education_text = "학력사항: 없음"
        
        # 경력사항 정보를 문자열로 변환
        experience_text = ""
        if experience_data:
            experience_text = "경력사항 정보:\n"
            for exp in experience_data:
                exp_info = f"- {exp['회사명']}"
                if exp['직위']:
                    exp_info += f" ({exp['직위']})"
                if exp['업무기간']:
                    exp_info += f" - {exp['업무기간']}"
                if exp['업무내용']:
                    exp_info += f" - {exp['업무내용']}"
                experience_text += exp_info + "\n"
        else:
            experience_text = "경력사항: 없음"
        
        # 프롬프트 구성
        prompt = f"""
너는 채용 심사관이야.
다음은 채용공고 내용이야:

---
{job_posting_text}
---

그리고 다음은 지원자의 이력서에서 추출한 주요 항목들이야:

{education_text}
{experience_text}
{certificate_text}
{award_text}

이 후보자가 이 채용공고에 얼마나 적합한지를 **0~100 사이 점수로 숫자를 출력**해줘.
점수에 대한 이유와 설명도 같이 출력해주세요.
"""
        
        # LangChain AzureChatOpenAI 사용 (챗봇과 동일한 방식)
        try:
            from langchain_openai import AzureChatOpenAI
            
            llm = AzureChatOpenAI(
                openai_api_version=OPENAI_API_VERSION,
                azure_deployment="gpt-4.1",
                azure_endpoint=AZURE_ENDPOINT,
                api_key=OPENAI_API_KEY,
                temperature=0.7
            )
            
            # LangChain을 사용한 응답 생성
            response = llm.invoke(prompt)
            
            return True, response.content.strip()
        except Exception as langchain_error:
            # LangChain 실패 시 기존 방식으로 폴백
            setup_openai_client()
            
            response = openai.chat.completions.create(
                model="gpt-4.1",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            return True, response.choices[0].message.content.strip()
    except Exception as e:
        return False, str(e)

def extract_score_from_evaluation(evaluation_text):
    """
    평가 결과에서 점수를 추출하는 함수
    """
    import re
    # 숫자 패턴 찾기 (0-100 사이)
    score_pattern = r'\b(\d{1,2}|100)\b'
    scores = re.findall(score_pattern, evaluation_text)
    
    if scores:
        # 첫 번째로 발견된 숫자를 점수로 사용
        try:
            score = int(scores[0])
            if 0 <= score <= 100:
                return score
        except ValueError:
            pass
    
    return None

@st.cache_resource
def get_llm():
    """LangChain LLM 클라이언트를 반환합니다."""
    if not LANGCHAIN_AVAILABLE:
        return None
    
    try:
        llm = AzureChatOpenAI(
            azure_deployment="gpt-4.1",
            openai_api_version=OPENAI_API_VERSION,
            azure_endpoint=AZURE_ENDPOINT,
            api_key=OPENAI_API_KEY,
            temperature=0.7
        )
        return llm
    except Exception as e:
        st.error(f"LLM 클라이언트 생성 실패: {str(e)}")
        return None

@st.cache_resource(ttl=60)
def get_embedding_model():
    """LangChain 임베딩 모델을 반환합니다."""
    if not LANGCHAIN_AVAILABLE:
        return None
    
    try:
        embeddings = AzureOpenAIEmbeddings(
            azure_deployment="text-embedding-3-large",
            openai_api_version=OPENAI_API_VERSION,
            azure_endpoint=AZURE_ENDPOINT,
            api_key=OPENAI_API_KEY
        )
        return embeddings
    except Exception as e:
        st.error(f"임베딩 모델 생성 실패: {str(e)}")
        return None

@st.cache_resource(ttl=60)
def get_retriever():
    """Azure AI Search 리트리버를 반환합니다."""
    if not LANGCHAIN_AVAILABLE:
        return None
    
    try:
        retriever = AzureCognitiveSearchRetriever(
            service_name=AZURE_SEARCH_SERVICE_NAME,
            index_name=AZURE_SEARCH_INDEX_NAME,
            api_key=AZURE_SEARCH_API_KEY,  # 실제 API 키로 교체 필요
            content_key="chunk",
            top_k=5
        )
        return retriever
    except Exception as e:
        st.error(f"검색 리트리버 생성 실패: {str(e)}")
        return None

@st.cache_resource
def get_qa_chain():
    """QA 체인을 반환합니다."""
    if not LANGCHAIN_AVAILABLE:
        return None
    
    try:
        llm = get_llm()
        retriever = get_retriever()
        
        if not llm or not retriever:
            return None
        
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=retriever,
            return_source_documents=True
        )
        return qa_chain
    except Exception as e:
        st.error(f"QA 체인 생성 실패: {str(e)}")
        return None 