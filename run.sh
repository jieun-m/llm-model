#!/bin/bash

# RecruitSupport MVP 실행 스크립트

echo "🚀 RecruitSupport MVP 시작 중..."

# 가상환경 확인 및 활성화
if [ ! -d "venv" ]; then
    echo "📦 가상환경을 생성합니다..."
    python3 -m venv venv
fi

echo "🔧 가상환경을 활성화합니다..."
source venv/bin/activate

echo "📚 의존성 패키지를 설치합니다..."
pip install -r requirements.txt

echo "🎯 애플리케이션을 시작합니다..."
streamlit run app.py 