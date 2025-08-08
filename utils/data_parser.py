import re
import json

def parse_certificate_data(certificate_text):
    """자격증 텍스트를 구조화된 데이터로 파싱합니다."""
    if not certificate_text:
        return []
    
    certificates = []
    
    # 줄바꿈으로 분리
    lines = certificate_text.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # 자격증명과 발급기관 분리
        # "자격증명 (발급기관)" 형태 파싱
        match = re.match(r'^(.+?)\s*[\(（](.+?)[\)）]', line)
        if match:
            cert_name = match.group(1).strip()
            issuer = match.group(2).strip()
            certificates.append({
                'name': cert_name,
                'issuer': issuer,
                'raw_text': line
            })
        else:
            # 괄호가 없는 경우 전체를 자격증명으로 처리
            certificates.append({
                'name': line,
                'issuer': '',
                'raw_text': line
            })
    
    return certificates

def process_certificate_field(field_content):
    """자격증 필드를 처리합니다."""
    if field_content is None or not field_content:
        return []
    
    if isinstance(field_content, list):
        return field_content
    elif isinstance(field_content, str):
        return parse_certificate_data(field_content)
    else:
        return [str(field_content)]

def parse_award_data(award_text):
    """수상경력 텍스트를 구조화된 데이터로 파싱합니다."""
    if not award_text:
        return []
    
    awards = []
    
    # 줄바꿈으로 분리
    lines = award_text.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # 수상명과 수상기관 분리
        # "수상명 (수상기관)" 형태 파싱
        match = re.match(r'^(.+?)\s*[\(（](.+?)[\)）]', line)
        if match:
            award_name = match.group(1).strip()
            organization = match.group(2).strip()
            awards.append({
                'name': award_name,
                'organization': organization,
                'raw_text': line
            })
        else:
            # 괄호가 없는 경우 전체를 수상명으로 처리
            awards.append({
                'name': line,
                'organization': '',
                'raw_text': line
            })
    
    return awards

def process_award_field(field_content):
    """수상경력 필드를 처리합니다."""
    if field_content is None or not field_content:
        return []
    
    if isinstance(field_content, list):
        return field_content
    elif isinstance(field_content, str):
        return parse_award_data(field_content)
    else:
        return [str(field_content)]

def parse_education_data(education_text):
    """학력 텍스트를 구조화된 데이터로 파싱합니다."""
    if not education_text:
        return []
    
    education_records = []
    
    # 줄바꿈으로 분리
    lines = education_text.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # 학력 정보 파싱 (학교명, 전공, 학위 등)
        # "학교명 - 전공 (학위)" 형태 파싱
        match = re.match(r'^(.+?)\s*[-–]\s*(.+?)\s*[\(（](.+?)[\)）]', line)
        if match:
            school = match.group(1).strip()
            major = match.group(2).strip()
            degree = match.group(3).strip()
            education_records.append({
                'school': school,
                'major': major,
                'degree': degree,
                'raw_text': line
            })
        else:
            # 기본 형태가 아닌 경우 전체를 학교명으로 처리
            education_records.append({
                'school': line,
                'major': '',
                'degree': '',
                'raw_text': line
            })
    
    return education_records

def process_education_field(field_content):
    """학력 필드를 처리합니다."""
    if field_content is None or not field_content:
        return []
    
    if isinstance(field_content, list):
        return field_content
    elif isinstance(field_content, str):
        return parse_education_data(field_content)
    else:
        return [str(field_content)]

def parse_experience_data(experience_text):
    """경력 텍스트를 구조화된 데이터로 파싱합니다."""
    if not experience_text:
        return []
    
    experience_records = []
    
    # 줄바꿈으로 분리
    lines = experience_text.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # 경력 정보 파싱 (회사명, 직책, 기간 등)
        # "회사명 - 직책 (기간)" 형태 파싱
        match = re.match(r'^(.+?)\s*[-–]\s*(.+?)\s*[\(（](.+?)[\)）]', line)
        if match:
            company = match.group(1).strip()
            position = match.group(2).strip()
            period = match.group(3).strip()
            experience_records.append({
                'company': company,
                'position': position,
                'period': period,
                'raw_text': line
            })
        else:
            # 기본 형태가 아닌 경우 전체를 회사명으로 처리
            experience_records.append({
                'company': line,
                'position': '',
                'period': '',
                'raw_text': line
            })
    
    return experience_records

def process_experience_field(field_content):
    """경력 필드를 처리합니다."""
    if field_content is None or not field_content:
        return []
    
    if isinstance(field_content, str):
        return parse_experience_data(field_content)
    elif isinstance(field_content, list):
        return field_content
    else:
        return [str(field_content)] 