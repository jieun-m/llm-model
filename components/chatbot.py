import streamlit as st
import re
import openai
# import config
from dotenv import load_dotenv
import os
from services.llm_service import process_certificate_field, process_award_field, process_education_field, process_experience_field

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

# LangChain 관련 import (선택적)
try:
    from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
    from langchain_community.retrievers import AzureCognitiveSearchRetriever
    from langchain.chains import RetrievalQA
    from langchain.prompts import ChatPromptTemplate, FewShotChatMessagePromptTemplate
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

def analyze_resume_for_question(question, analysis_results):
    """
    이력서 분석 결과를 기반으로 질문에 답변하는 함수
    """
    try:
        # 질문에서 키워드 추출
        keywords = extract_keywords_from_question(question)
        
        # 지원자들의 정보를 구조화
        candidates_info = []
        for result in analysis_results:
            file_name = result["file_name"]
            analysis = result["analysis"]
            
            candidate_info = {
                "file_name": file_name,
                "fields": {},
                "fitness_score": result.get("fitness_score")
            }
            
            # 필드 정보 추출
            if analysis["documents"] and analysis["documents"][0]["fields"]:
                fields = analysis["documents"][0]["fields"]
                
                # 주요 필드들 처리
                for field_name in ["학력사항", "경력사항", "자격증", "수상경력", "기본정보"]:
                    if field_name in fields:
                        field_content = fields[field_name]['content']
                        
                        # 구조화된 데이터로 변환
                        if field_name == "학력사항":
                            candidate_info["fields"][field_name] = process_education_field(field_content)
                        elif field_name == "경력사항":
                            candidate_info["fields"][field_name] = process_experience_field(field_content)
                        elif field_name == "자격증":
                            candidate_info["fields"][field_name] = process_certificate_field(field_content)
                        elif field_name == "수상경력":
                            candidate_info["fields"][field_name] = process_award_field(field_content)
                        else:
                            candidate_info["fields"][field_name] = field_content
            
            candidates_info.append(candidate_info)
        
        # 질문에 맞는 지원자 분석
        if keywords:
            return analyze_candidates_by_keywords(question, keywords, candidates_info)
        
        return None
        
    except Exception as e:
        st.error(f"이력서 분석 중 오류 발생: {str(e)}")
        return None

def extract_keywords_from_question(question):
    """
    질문에서 키워드를 추출하는 함수
    """
    keywords = []
    
    # 기술 스택 관련 키워드
    tech_keywords = [
        "java", "python", "javascript", "react", "vue", "angular", "node.js", "spring",
        "django", "flask", "mysql", "postgresql", "mongodb", "redis", "docker", "kubernetes",
        "aws", "azure", "gcp", "git", "jenkins", "jira", "agile", "scrum"
    ]
    
    # 경험 관련 키워드
    experience_keywords = [
        "경력", "경험", "프로젝트", "개발", "프로그래밍", "코딩", "시니어", "주니어",
        "신입", "중급", "고급", "리드", "매니저", "팀장"
    ]
    
    # 학력 관련 키워드
    education_keywords = [
        "학력", "학위", "대학교", "대학원", "석사", "박사", "학사", "전공"
    ]
    
    # 자격증 관련 키워드
    certificate_keywords = [
        "자격증", "인증", "certificate", "license", "aws", "azure", "oracle", "microsoft"
    ]
    
    question_lower = question.lower()
    
    # 기술 스택 키워드 검색
    for keyword in tech_keywords:
        if keyword in question_lower:
            keywords.append(keyword)
    
    # 경험 키워드 검색
    for keyword in experience_keywords:
        if keyword in question_lower:
            keywords.append(keyword)
    
    # 학력 키워드 검색
    for keyword in education_keywords:
        if keyword in question_lower:
            keywords.append(keyword)
    
    # 자격증 키워드 검색
    for keyword in certificate_keywords:
        if keyword in question_lower:
            keywords.append(keyword)
    
    return keywords

def analyze_candidates_by_keywords(question, keywords, candidates_info):
    """
    키워드를 기반으로 지원자들을 분석하는 함수
    """
    try:
        matching_candidates = []
        
        for candidate in candidates_info:
            score = 0
            matched_keywords = []
            
            # 각 키워드에 대해 점수 계산
            for keyword in keywords:
                candidate_text = ""
                
                # 모든 필드의 텍스트를 하나로 합치기
                for field_name, field_content in candidate["fields"].items():
                    if isinstance(field_content, str):
                        candidate_text += field_content + " "
                    elif isinstance(field_content, list):
                        for item in field_content:
                            if isinstance(item, dict):
                                candidate_text += str(item) + " "
                            else:
                                candidate_text += str(item) + " "
                    else:
                        candidate_text += str(field_content) + " "
                
                candidate_text_lower = candidate_text.lower()
                
                # 키워드 매칭 확인
                if keyword in candidate_text_lower:
                    score += 1
                    matched_keywords.append(keyword)
            
            # 매칭된 키워드가 있으면 결과에 추가
            if score > 0:
                candidate["match_score"] = score
                candidate["matched_keywords"] = matched_keywords
                matching_candidates.append(candidate)
        
        # 점수순으로 정렬
        matching_candidates.sort(key=lambda x: x["match_score"], reverse=True)
        
        return matching_candidates
        
    except Exception as e:
        st.error(f"지원자 분석 중 오류 발생: {str(e)}")
        return None

@st.cache_resource
def get_llm():
    """Azure OpenAI LLM을 반환합니다."""
    try:
        llm = AzureChatOpenAI(
            openai_api_version=OPENAI_API_VERSION,
            azure_deployment="gpt-4.1",
            azure_endpoint=AZURE_ENDPOINT,
            api_key=OPENAI_API_KEY,
            temperature=0.1
        )
        return llm
    except Exception as e:
        st.error(f"LLM 초기화 실패: {str(e)}")
        return None

@st.cache_resource(ttl=60)
def get_embedding_model():
    """Azure OpenAI Embedding 모델을 반환합니다."""
    try:
        embeddings = AzureOpenAIEmbeddings(
            azure_deployment="text-embedding-3-large",
            azure_endpoint=AZURE_ENDPOINT,
            api_key=OPENAI_API_KEY,
            openai_api_version=OPENAI_API_VERSION
        )
        return embeddings
    except Exception as e:
        st.error(f"Embedding 모델 초기화 실패: {str(e)}")
        return None

@st.cache_resource(ttl=60)
def get_retriever():
    """Azure AI Search 리트리버를 반환합니다."""
    try:
        # .env 파일에서 직접 환경변수 가져오기
        azure_search_service_name = AZURE_SEARCH_SERVICE_NAME
        azure_search_index_name = AZURE_SEARCH_INDEX_NAME
        azure_search_api_key = AZURE_SEARCH_API_KEY
        azure_search_api_version = AZURE_SEARCH_API_VERSION
        
        retriever = AzureCognitiveSearchRetriever(
            service_name=AZURE_SEARCH_SERVICE_NAME,
            index_name=AZURE_SEARCH_INDEX_NAME,
            api_key=AZURE_SEARCH_API_KEY,
            api_version=AZURE_SEARCH_API_VERSION,
            top_k=10,
            content_key="chunk"
        )
        return retriever
    except Exception as e:
        st.error(f"리트리버 초기화 실패: {str(e)}")
        return None

@st.cache_resource
def get_qa_chain():
    """RetrievalQA 체인을 반환합니다."""
    try:
        llm = get_llm()
        retriever = get_retriever()
        
        if not llm or not retriever:
            return None
            
        # Few-shot 예시 데이터 정의
        examples = [
            {
                "question": "백엔드 개발 경험이 있는 지원자를 찾아주세요",
                "context": "지원자 A: Java/Spring 백엔드 개발 3년 경험\n지원자 B: Node.js/Express 백엔드 개발 2년 경험",
                "answer": "검색된 문서를 확인한 결과, 백엔드 개발 경험이 있는 지원자를 찾았습니다:\n\n- 지원자 A: Java/Spring을 사용한 백엔드 개발 3년 경험\n- 지원자 B: Node.js/Express 백엔드 개발 2년 경험"
            },
            {
                "question": "머신러닝 전문가를 찾아주세요",
                "context": "지원자 A: 웹 개발 경험\n지원자 B: 모바일 앱 개발 경험",
                "answer": "검색된 문서를 확인했지만, 머신러닝 관련 경험이 있는 지원자 정보를 찾을 수 없습니다."
            },
            {
                "question": "안녕하세요",
                "context": "",
                "answer": "안녕하세요! 저는 채용 지원 시스템의 AI 어시스턴트입니다.\n\n지원자와 채용공고에 대한 다양한 질문에 답변해드릴 수 있습니다. 예를 들어:\n\n• 지원자들의 학력사항이나 경력사항을 물어보실 수 있어요\n• 특정 지원자의 적합성이나 평가 기준을 알아보실 수 있어요\n• 면접에서 물어볼 수 있는 질문들을 알아보실 수 있어요\n• 특정 기술이나 경험을 가진 지원자를 찾아보실 수 있어요\n\n궁금한 점이 있으시면 언제든 편하게 물어보세요!"
            }
        ]

        # 예시 포맷팅 템플릿
        example_prompt = ChatPromptTemplate.from_messages([
            ("human", "질문: {question}\n\n지원자 정보:\n{context}"),
            ("assistant", "{answer}")
        ])

        # Few-shot 프롬프트 템플릿 생성
        few_shot_prompt = FewShotChatMessagePromptTemplate(
            example_prompt=example_prompt,
            examples=examples
        )

        # 최종 프롬프트 템플릿 구성
        final_prompt = ChatPromptTemplate.from_messages([
            ("system", """당신은 채용 지원 시스템의 AI 어시스턴트입니다. 지원자와 채용공고에 대한 질문에 답변해주세요.

다음 규칙에 따라 답변해주세요:

1. 일반적인 인사말이나 대화에는 다음 형식으로 답변해주세요:
   "안녕하세요! 저는 채용 지원 시스템의 AI 어시스턴트입니다.\n\n지원자와 채용공고에 대한 다양한 질문에 답변해드릴 수 있습니다. 예를 들어:\n\n• 지원자들의 학력사항이나 경력사항을 물어보실 수 있어요\n• 특정 지원자의 적합성이나 평가 기준을 알아보실 수 있어요\n• 면접에서 물어볼 수 있는 질문들을 알아보실 수 있어요\n• 특정 기술이나 경험을 가진 지원자를 찾아보실 수 있어요\n\n궁금한 점이 있으시면 언제든 편하게 물어보세요!"
2. 지원자나 채용공고에 대한 구체적인 질문이면, 제공된 문서를 참고하여 정확하고 구체적으로 답변해주세요.
3. 특정 기술이나 경험에 대한 질문인 경우, 해당 기술을 사용한 경험이나 관련 자격증을 가진 지원자를 우선적으로 추천해주세요.
4. 경력사항에서 해당 기술을 사용한 구체적인 프로젝트나 업무 내용을 언급해주세요.
5. 답변은 한국어로 해주세요.
6. 가능하면 구체적인 예시나 설명을 포함해주세요.
7. 분석되지 않은 이력서나 존재하지 않는 지원자에 대해서는 언급하지 마세요.
8. 제공된 문서에 없는 내용은 추측하지 마세요.
9. 정보가 부족한 경우 "해당 정보를 찾을 수 없습니다"라고 답변하세요.
10. 경력사항, 자격증, 학력사항, 수상경력을 종합적으로 고려해서 답변해주세요.
11. 가장 적합한 지원자부터 순서대로 설명해주세요."""),
            few_shot_prompt,
            ("human", "다음은 지원자의 이력 정보 및 채용공고와 관련된 문서들입니다:\n\n<지원자 정보 및 검색된 문서>\n{context}\n\n---\n\n사용자 질문: {question}")
        ])

        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            retriever=retriever,
            chain_type="stuff",
            chain_type_kwargs={"prompt": final_prompt},
            return_source_documents=True
        )
        return qa_chain
    except Exception as e:
        st.error(f"QA 체인 초기화 실패: {str(e)}")
        return None

def chat_with_llm():
    """챗봇 인터페이스를 제공합니다."""
    st.subheader("🤖 AI 챗봇")
    
    # 세션 상태 초기화
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # 이전 메시지들 표시
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # 사용자 입력
    if prompt := st.chat_input("질문을 입력하세요..."):
        # 사용자 메시지 추가
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # AI 응답 생성
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            
            try:
                # QA 체인 가져오기
                qa_chain = get_qa_chain()
                
                if qa_chain:
                    # 질문에 대한 응답 생성
                    response = qa_chain.invoke({"query": prompt})
                    
                    if response and "result" in response:
                        full_response = response["result"]
                    else:
                        full_response = "죄송합니다. 응답을 생성할 수 없습니다."
                else:
                    full_response = "죄송합니다. AI 서비스를 초기화할 수 없습니다."
                
            except Exception as e:
                full_response = f"오류가 발생했습니다: {str(e)}"
            
            # 응답 표시
            message_placeholder.markdown(full_response)
        
        # AI 응답을 세션에 추가
        st.session_state.messages.append({"role": "assistant", "content": full_response})
    
    # 채팅 기록 초기화 버튼
    if st.button("채팅 기록 초기화"):
        st.session_state.messages = []
        st.rerun() 