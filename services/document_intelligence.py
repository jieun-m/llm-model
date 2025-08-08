import streamlit as st
import io
import PyPDF2
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
from services.azure_clients import get_document_intelligence_client, get_container_client
# from config import MODEL_ID
from dotenv import load_dotenv
import os

# .env 파일 로드
load_dotenv()

MODEL_ID = os.getenv("MODEL_ID")

def list_blobs_by_prefix(container_client, prefix):
    """특정 접두사로 시작하는 blob들을 반환합니다."""
    try:
        if not container_client:
            st.error("컨테이너 클라이언트가 None입니다.")
            return []
        
        blobs = container_client.list_blobs(name_starts_with=prefix)
        if blobs is None:
            st.warning(f"'{prefix}' 접두사로 시작하는 파일을 찾을 수 없습니다.")
            return []
        
        blob_list = [blob.name for blob in blobs]
        # st.info(f"'{prefix}' 접두사로 시작하는 파일 {len(blob_list)}개를 찾았습니다.")
        return blob_list
        
    except Exception as e:
        st.error(f"Blob 목록 가져오기 오류: {str(e)}")
        return []

def extract_job_posting_text(blob_name, container_client):
    """채용공고 파일에서 텍스트를 추출합니다."""
    try:
        blob_client = container_client.get_blob_client(blob_name)
        blob_data = blob_client.download_blob()
        
        # PDF 파일인 경우
        if blob_name.lower().endswith('.pdf'):
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(blob_data.readall()))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text
        
        # 텍스트 파일인 경우
        elif blob_name.lower().endswith(('.txt', '.doc', '.docx')):
            return blob_data.readall().decode('utf-8')
        
        else:
            st.warning(f"지원하지 않는 파일 형식입니다: {blob_name}")
            return None
            
    except Exception as e:
        st.error(f"파일 읽기 오류: {str(e)}")
        return None

def analyze_resume_with_ai(blob_name):
    """Azure Document Intelligence를 사용하여 이력서를 분석합니다."""
    try:
        # Azure 클라이언트들 가져오기
        container_client = get_container_client()
        doc_client = get_document_intelligence_client()
        
        if not container_client or not doc_client:
            st.error("Azure 클라이언트를 가져올 수 없습니다.")
            return None
        
        # Blob에서 파일 다운로드
        blob_client = container_client.get_blob_client(blob_name)
        blob_data = blob_client.download_blob()
        document_content = blob_data.readall()
        
        # Document Intelligence로 분석
        poller = doc_client.begin_analyze_document(
            MODEL_ID, 
            document_content
        )
        result = poller.result()
        
        # check3-1.py와 동일한 구조로 분석 결과 구성
        analysis_result = {
            "model_id": result.model_id,
            "documents": [],
            "pages": [],
            "tables": [],
            "key_value_pairs": []
        }
        
        # 문서 정보 추출 (안전한 처리)
        if hasattr(result, 'documents') and result.documents:
            for document in result.documents:
                doc_info = {
                    "doc_type": getattr(document, 'doc_type', 'unknown'),
                    "confidence": getattr(document, 'confidence', 0.0),
                    "fields": {}
                }
                if hasattr(document, 'fields') and document.fields:
                    for name, field in document.fields.items():
                        doc_info["fields"][name] = {
                            "type": getattr(field, 'type', 'unknown'),
                            "content": getattr(field, 'content', ''),
                            "confidence": getattr(field, 'confidence', 0.0)
                        }
                analysis_result["documents"].append(doc_info)
        
        # 페이지 정보 추출 (안전한 처리)
        if hasattr(result, 'pages') and result.pages:
            for page in result.pages:
                page_info = {
                    "page_number": getattr(page, 'page_number', 0),
                    "lines": [line.content for line in page.lines] if hasattr(page, 'lines') and page.lines else [],
                    "words": [word.content for word in page.words] if hasattr(page, 'words') and page.words else []
                }
                analysis_result["pages"].append(page_info)
        
        # 테이블 정보 추출 (안전한 처리)
        if hasattr(result, 'tables') and result.tables:
            for table in result.tables:
                table_info = {
                    "row_count": getattr(table, 'row_count', 0),
                    "column_count": getattr(table, 'column_count', 0),
                    "cells": []
                }
                if hasattr(table, 'cells') and table.cells:
                    for cell in table.cells:
                        cell_info = {
                            "row_index": getattr(cell, 'row_index', 0),
                            "column_index": getattr(cell, 'column_index', 0),
                            "content": getattr(cell, 'content', '')
                        }
                        table_info["cells"].append(cell_info)
                analysis_result["tables"].append(table_info)
        
        # 키-값 쌍 추출 (안전한 처리)
        if hasattr(result, 'key_value_pairs') and result.key_value_pairs:
            for kv_pair in result.key_value_pairs:
                kv_info = {
                    "key": kv_pair.key.content if hasattr(kv_pair, 'key') and kv_pair.key else "",
                    "value": kv_pair.value.content if hasattr(kv_pair, 'value') and kv_pair.value else ""
                }
                analysis_result["key_value_pairs"].append(kv_info)
        
        return analysis_result
        
    except Exception as e:
        st.error(f"Document Intelligence 분석 실패: {str(e)}")
        st.error(f"파일: {blob_name}")
        st.error(f"Model ID: {MODEL_ID}")
        return None 