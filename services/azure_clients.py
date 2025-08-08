import streamlit as st
from azure.storage.blob import ContainerClient
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
import openai
from dotenv import load_dotenv
import os
# from config import *

# .env 파일 로드
load_dotenv()

AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_STORAGE_CONTAINER = os.getenv("AZURE_STORAGE_CONTAINER")
DOCUMENT_INTELLIGENCE_ENDPOINT = os.getenv("DOCUMENT_INTELLIGENCE_ENDPOINT")
DOCUMENT_INTELLIGENCE_KEY = os.getenv("DOCUMENT_INTELLIGENCE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_TYPE = os.getenv("OPENAI_API_TYPE")
OPENAI_API_VERSION = os.getenv("OPENAI_API_VERSION")
AZURE_ENDPOINT = os.getenv("AZURE_ENDPOINT")

# Azure Blob 컨테이너 클라이언트 연결
@st.cache_resource
def get_container_client():
    """Azure Blob Storage 컨테이너 클라이언트를 반환합니다."""
    try:
        client = ContainerClient.from_connection_string(
            AZURE_STORAGE_CONNECTION_STRING, 
            AZURE_STORAGE_CONTAINER
        )
        
        # 연결 테스트
        client.get_container_properties()
        return client
        
    except Exception as e:
        st.error(f"❌ Azure Storage 연결 실패: {str(e)}")
        return None

# Azure Document Intelligence 클라이언트 생성
@st.cache_resource
def get_document_intelligence_client():
    """Azure Document Intelligence 클라이언트를 반환합니다."""
    try:
        client = DocumentIntelligenceClient(
            endpoint=DOCUMENT_INTELLIGENCE_ENDPOINT,
            credential=AzureKeyCredential(DOCUMENT_INTELLIGENCE_KEY)
        )
        
        return client
        
    except Exception as e:
        st.error(f"❌ Document Intelligence 클라이언트 생성 실패: {str(e)}")
        return None

# OpenAI 클라이언트 설정
def setup_openai_client():
    """OpenAI 클라이언트를 설정합니다."""
    try:
        openai.api_key = OPENAI_API_KEY
        openai.api_type = OPENAI_API_TYPE
        openai.api_version = OPENAI_API_VERSION
        openai.azure_endpoint = AZURE_ENDPOINT
        
    except Exception as e:
        st.error(f"❌ OpenAI 클라이언트 설정 실패: {str(e)}") 