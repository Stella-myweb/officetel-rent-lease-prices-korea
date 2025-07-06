import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import folium
from streamlit_folium import st_folium
import numpy as np
from datetime import datetime, timedelta
import urllib3
import warnings
from io import StringIO

# SSL 경고 비활성화
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings('ignore')

# 페이지 설정
st.set_page_config(
    page_title="오피스텔 전월세 실거래가 대시보드",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 서비스키
SERVICE_KEY = "jUxxEMTFyxsIT2rt2P8JBO9y0EmFT9mx1zNPb31XLX27rFNH12NQ+6+ZLqqvW6k/ffQ5ZOOYzzcSo0Fq4u3Lfg=="

# 지역코드 매핑 (주요 지역)
REGION_CODES = {
    "서울특별시": {
        "강남구": "11680", "강동구": "11740", "강북구": "11305", "강서구": "11500",
        "관악구": "11620", "광진구": "11215", "구로구": "11530", "금천구": "11545",
        "노원구": "11350", "도봉구": "11320", "동대문구": "11230", "동작구": "11590",
        "마포구": "11440", "서대문구": "11410", "서초구": "11650", "성동구": "11200",
        "성북구": "11290", "송파구": "11710", "양천구": "11470", "영등포구": "11560",
        "용산구": "11170", "은평구": "11380", "종로구": "11110", "중구": "11140",
        "중랑구": "11260"
    },
    "부산광역시": {
        "강서구": "26440", "금정구": "26410", "남구": "26290", "동구": "26170",
        "동래구": "26260", "부산진구": "26230", "북구": "26320", "사상구": "26530",
        "사하구": "26380", "서구": "26140", "수영구": "26350", "연제구": "26380",
        "영도구": "26200", "중구": "26110", "해운대구": "26440", "기장군": "26710"
    },
    "대구광역시": {
        "남구": "27200", "달서구": "27290", "동구": "27140", "북구": "27230",
        "서구": "27170", "수성구": "27260", "중구": "27110", "달성군": "27710"
    },
    "인천광역시": {
        "계양구": "28245", "남동구": "28200", "동구": "28140", "미추홀구": "28177",
        "부평구": "28237", "서구": "28260", "연수구": "28185", "중구": "28110",
        "강화군": "28710", "옹진군": "28720"
    },
    "광주광역시": {
        "광산구": "29200", "남구": "29155", "동구": "29110", "북구": "29170", "서구": "29140"
    },
    "대전광역시": {
        "대덕구": "30230", "동구": "30110", "서구": "30170", "유성구": "30200", "중구": "30140"
    },
    "울산광역시": {
        "남구": "31140", "동구": "31170", "북구": "31200", "중구": "31110", "울주군": "31710"
    }
}

# 제목 및 설명
st.title("🏢 오피스텔 전월세 실거래가 대시보드")
st.markdown("---")
st.markdown("**국토교통부 실거래가 데이터 기반 오피스텔 전월세 현황 분석**")

# API 호출 함수
@st.cache_data(ttl=3600)
def fetch_officetel_data(service_key, lawd_cd, deal_ymd, page_no=1, num_of_rows=1000):
    """오피스텔 전월세 데이터를 가져오는 함수"""
    
    url = "http://apis.data.go.kr/1613000/RTMSDataSvcOffiRent/getRTMSDataSvcOffiRent"
    
    params = {
        'serviceKey': service_key,
        'LAWD_CD': lawd_cd,
        'DEAL_YMD': deal_ymd,
        'pageNo': page_no,
        'numOfRows': num_of_rows
    }
    
    try:
        response = requests.get(url, params=params, verify=False, timeout=15)
        response.raise_for_status()
        
        # XML 파싱
        root = ET.fromstring(response.content)
        
        # 헤더 확인
        result_code = root.find('.//resultCode')
        if result_code is not None and result_code.text != '00':
            st.warning(f"API 응답 코드: {result_code.text}")
            return None
        
        # items 추출
        items = root.findall('.//item')
        if not items:
            return None
        
        # 데이터 변환
        data_list = []
        for item in items:
            data_dict = {}
            for child in item:
                data_dict[child.tag] = child.text if child.text else ""
            data_list.append(data_dict)
        
        return data_list
        
    except requests.exceptions.RequestException as e:
        st.error(f"🚨 API 호출 실패: {str(e)}")
        return None
    except ET.ParseError as e:
        st.error(f"🚨 XML 파싱 실패: {str(e)}")
        return None
    except Exception as e:
        st.error(f"🚨 예상치 못한 오류: {str(e)}")
        return None

# 데이터 전처리 함수
def preprocess_data(raw_data):
    """원시 데이터를 DataFrame으로 변환하고 전처리"""
    
    if not raw_data:
        return pd.DataFrame()
    
    df = pd.DataFrame(raw_data)
    
    if df.empty:
        return df
    
    # 수치형 컬럼 변환
    numeric_columns = ['deposit', 'monthlyRent', 'excluUseAr', 'floor', 'buildYear']
    
    for col in numeric_columns:
        if col in df.columns:
            # 콤마 제거 및 숫자형 변환
            df[col] = df[col].astype(str).str.replace(',', '').replace('', '0')
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # 결측치 처리
    df = df.fillna(0)
    
    # 날짜 컬럼 생성
    if all(col in df.columns for col in ['dealYear', 'dealMonth', 'dealDay']):
        df['dealDate'] = pd.to_datetime(
            df['dealYear'].astype(str) + '-' + 
            df['dealMonth'].astype(str).str.zfill(2) + '-' + 
            df['dealDay'].astype(str).str.zfill(2),
            errors='coerce'
        )
    
    # 계약 구분 생성 (전세/월세)
    df['contractCategory'] = df.apply(
        lambda x: '전세' if x['monthlyRent'] == 0 else '월세', axis=1
    )
    
    # 평균 가격 계산용 컬럼
    df['pricePerArea'] = df['deposit'] / df['excluUseAr']
    
    return df

# 사이드바 설정
st.sidebar.header("🔍 조회 조건 설정")

# 기간 설정
current_date = datetime.now()
st.sidebar.subheader("📅 조회 기간")

# 최근 12개월 기본 설정
default_start = current_date - timedelta(days=365)
start_year = st.sidebar.selectbox(
    "시작 연도",
    options=list(range(2020, current_date.year + 1)),
    index=list(range(2020, current_date.year + 1)).index(default_start.year)
)

start_month = st.sidebar.selectbox(
    "시작 월",
    options=list(range(1, 13)),
    index=default_start.month - 1
)

end_year = st.sidebar.selectbox(
    "종료 연도",
    options=list(range(2020, current_date.year + 1)),
    index=list(range(2020, current_date.year + 1)).index(current_date.year)
)

end_month = st.sidebar.selectbox(
    "종료 월",
    options=list(range(1, 13)),
    index=current_date.month - 1
)

# 지역 선택
st.sidebar.subheader("🏙️ 지역 선택")
selected_city = st.sidebar.selectbox(
    "시/도",
    options=list(REGION_CODES.keys()),
    index=0
)

selected_district = st.sidebar.selectbox(
    "시/군/구",
    options=list(REGION_CODES[selected_city].keys()),
    index=0
)

lawd_cd = REGION_CODES[selected_city][selected_district]

# 데이터 로드
@st.cache_data(ttl=1800)
def load_period_data(service_key, lawd_cd, start_year, start_month, end_year, end_month):
    """기간별 데이터 로드"""
    all_data = []
    
    # 시작월부터 종료월까지 반복
    current = datetime(start_year, start_month, 1)
    end = datetime(end_year, end_month, 1)
    
    progress_bar = st.progress(0)
    total_months = 0
    
    # 총 개월 수 계산
    temp_current = current
    while temp_current <= end:
        total_months += 1
        if temp_current.month == 12:
            temp_current = temp_current.replace(year=temp_current.year + 1, month=1)
        else:
            temp_current = temp_current.replace(month=temp_current.month + 1)
    
    month_count = 0
    
    while current <= end:
        deal_ymd = f"{current.year}{current.month:02d}"
        
        data = fetch_officetel_data(service_key, lawd_cd, deal_ymd)
        if data:
            all_data.extend(data)
        
        month_count += 1
        progress_bar.progress(month_count / total_months)
        
        # 다음 월로 이동
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)
    
    progress_bar.empty()
    return all_data

# 데이터 로드
with st.spinner(f"📡 {selected_city} {selected_district} 데이터를 불러오는 중..."):
    raw_data = load_period_data(
        SERVICE_KEY, lawd_cd, start_year, start_month, end_year, end_month
    )
    
    if not raw_data:
        st.error("❌ 해당 조건의 데이터가 없습니다. 다른 지역이나 기간을 선택해주세요.")
        st.stop()
    
    df = preprocess_data(raw_data)
    
    if df.empty:
        st.warning("⚠️ 데이터가 비어있습니다.")
        st.stop()

# 사이드바 추가 필터
st.sidebar.subheader("🔍 상세 필터")

# 보증금 범위
if 'deposit' in df.columns and df['deposit'].max() > 0:
    min_deposit = int(df['deposit'].min())
    max_deposit = int(df['deposit'].max())
    
    deposit_range = st.sidebar.slider(
        "💰 보증금 범위 (만원)",
        min_value=min_deposit,
        max_value=max_deposit,
        value=(min_deposit, max_deposit)
    )
else:
    deposit_range = (0, 100000)

# 전용면적 범위
if 'excluUseAr' in df.columns and df['excluUseAr'].max() > 0:
    min_area = float(df['excluUseAr'].min())
    max_area = float(df['excluUseAr'].max())
    
    area_range = st.sidebar.slider(
        "🏠 전용면적 범위 (㎡)",
        min_value=min_area,
        max_value=max_area,
        value=(min_area, max_area)
    )
else:
    area_range = (0.0, 200.0)

# 계약구분 필터
contract_types = ['전체'] + df['contractCategory'].unique().tolist()
selected_contract = st.sidebar.selectbox(
    "📋 계약구분",
    options=contract_types,
    index=0
)

# 데이터 필터링
filtered_df = df.copy()

# 필터 적용
filtered_df = filtered_df[
    (filtered_df['deposit'] >= deposit_range[0]) & 
    (filtered_df['deposit'] <= deposit_range[1]) &
    (filtered_df['excluUseAr'] >= area_range[0]) & 
    (filtered_df['excluUseAr'] <= area_range[1])
]

if selected_contract != '전체':
    filtered_df = filtered_df[filtered_df['contractCategory'] == selected_contract]

# 요약 통계
st.markdown("### 📊 요약 통계")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="📍 총 거래 건수",
        value=f"{len(filtered_df):,}건"
    )

with col2:
    avg_deposit = filtered_df['deposit'].mean() if len(filtered_df) > 0 else 0
    st.metric(
        label="💰 평균 보증금",
        value=f"{avg_deposit:,.0f}만원"
    )

with col3:
    avg_monthly = filtered_df['monthlyRent'].mean() if len(filtered_df) > 0 else 0
    st.metric(
        label="🏠 평균 월세",
        value=f"{avg_monthly:,.0f}만원"
    )

with col4:
    avg_area = filtered_df['excluUseAr'].mean() if len(filtered_df) > 0 else 0
    st.metric(
        label="📐 평균 전용면적",
        value=f"{avg_area:.1f}㎡"
    )

# 탭 생성
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🗺️ 지역별 현황", "💰 가격 분석", "📈 트렌드 분석", "🏢 단지별 현황", "📋 상세 데이터"])

with tab1:
    st.markdown("### 🗺️ 지역별 현황")
    
    if not filtered_df.empty:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Folium 지도 생성
            st.markdown("**📍 거래 위치 지도**")
            
            # 중심 좌표 (서울 기준)
            center_lat, center_lon = 37.5665, 126.9780
            
            # 지도 생성
            m = folium.Map(
                location=[center_lat, center_lon],
                zoom_start=11,
                tiles='OpenStreetMap'
            )
            
            # 법정동별 데이터 집계
            if 'umdNm' in filtered_df.columns:
                dong_summary = filtered_df.groupby('umdNm').agg({
                    'deposit': 'mean',
                    'monthlyRent': 'mean',
                    'excluUseAr': 'mean',
                    'offiNm': 'count'
                }).round(0)
                
                dong_summary.columns = ['평균보증금', '평균월세', '평균면적', '거래건수']
                
                # 마커 추가 (법정동별)
                for dong, data in dong_summary.iterrows():
                    # 임의 좌표 (실제로는 지오코딩 필요)
                    lat = center_lat + np.random.uniform(-0.1, 0.1)
                    lon = center_lon + np.random.uniform(-0.1, 0.1)
                    
                    popup_text = f"""
                    <b>{dong}</b><br>
                    거래건수: {data['거래건수']}건<br>
                    평균보증금: {data['평균보증금']:,.0f}만원<br>
                    평균월세: {data['평균월세']:,.0f}만원<br>
                    평균면적: {data['평균면적']:.1f}㎡
                    """
                    
                    folium.Marker(
                        location=[lat, lon],
                        popup=folium.Popup(popup_text, max_width=200),
                        icon=folium.Icon(color='blue', icon='home')
                    ).add_to(m)
            
            # 지도 표시
            map_data = st_folium(m, width=700, height=400)
        
        with col2:
            st.markdown("**📊 법정동별 통계**")
            if 'umdNm' in filtered_df.columns:
                dong_stats = filtered_df.groupby('umdNm').agg({
                    'deposit': ['mean', 'count'],
                    'monthlyRent': 'mean'
                }).round(0)
                
                dong_stats.columns = ['평균보증금', '거래건수', '평균월세']
                dong_stats = dong_stats.sort_values('거래건수', ascending=False)
                
                st.dataframe(dong_stats.head(10), use_container_width=True)

with tab2:
    st.markdown("### 💰 가격 분석")
    
    if not filtered_df.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**💰 보증금 vs 월세**")
            fig = px.scatter(
                filtered_df,
                x='deposit',
                y='monthlyRent',
                color='contractCategory',
                size='excluUseAr',
                hover_data=['offiNm', 'excluUseAr'],
                title="보증금 vs 월세 분포",
                labels={
                    'deposit': '보증금(만원)',
                    'monthlyRent': '월세(만원)',
                    'contractCategory': '계약구분'
                }
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("**📊 면적대별 평균 가격**")
            # 면적대 구분
            filtered_df_copy = filtered_df.copy()
            filtered_df_copy['area_group'] = pd.cut(
                filtered_df_copy['excluUseAr'],
                bins=[0, 30, 60, 100, float('inf')],
                labels=['소형(30㎡미만)', '중형(30-60㎡)', '대형(60-100㎡)', '초대형(100㎡이상)']
            )
            
            area_stats = filtered_df_copy.groupby('area_group').agg({
                'deposit': 'mean',
                'monthlyRent': 'mean'
            }).round(0)
            
            fig = px.bar(
                area_stats.reset_index(),
                x='area_group',
                y='deposit',
                title="면적대별 평균 보증금",
                labels={'area_group': '면적대', 'deposit': '평균보증금(만원)'}
            )
            st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.markdown("### 📈 트렌드 분석")
    
    if not filtered_df.empty and 'dealDate' in filtered_df.columns:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**📅 월별 거래량 추이**")
            monthly_count = filtered_df.groupby(
                filtered_df['dealDate'].dt.to_period('M')
            ).size().reset_index()
            
            monthly_count.columns = ['월', '거래건수']
            monthly_count['월'] = monthly_count['월'].astype(str)
            
            fig = px.line(
                monthly_count,
                x='월',
                y='거래건수',
                title="월별 거래량 변화",
                markers=True
            )
            fig.update_xaxes(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("**💰 월별 평균 보증금 추이**")
            monthly_price = filtered_df.groupby(
                filtered_df['dealDate'].dt.to_period('M')
            )['deposit'].mean().reset_index()
            
            monthly_price.columns = ['월', '평균보증금']
            monthly_price['월'] = monthly_price['월'].astype(str)
            
            fig = px.line(
                monthly_price,
                x='월',
                y='평균보증금',
                title="월별 평균 보증금 변화",
                markers=True
            )
            fig.update_xaxes(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.markdown("### 🏢 단지별 현황")
    
    if not filtered_df.empty and 'offiNm' in filtered_df.columns:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**🏆 거래량 상위 단지 (Top 20)**")
            top_complexes = filtered_df['offiNm'].value_counts().head(20)
            
            fig = px.bar(
                x=top_complexes.values,
                y=top_complexes.index,
                orientation='h',
                title="단지별 거래 건수",
                labels={'x': '거래건수', 'y': '단지명'}
            )
            fig.update_layout(height=600)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("**💰 평균 가격 상위 단지 (Top 20)**")
            complex_price = filtered_df.groupby('offiNm')['deposit'].mean().sort_values(ascending=False).head(20)
            
            fig = px.bar(
                x=complex_price.values,
                y=complex_price.index,
                orientation='h',
                title="단지별 평균 보증금",
                labels={'x': '평균보증금(만원)', 'y': '단지명'}
            )
            fig.update_layout(height=600)
            st.plotly_chart(fig, use_container_width=True)

with tab5:
    st.markdown("### 📋 상세 데이터")
    
    if not filtered_df.empty:
        # 컬럼명 한글화
        column_mapping = {
            'sggNm': '시군구',
            'umdNm': '법정동',
            'jibun': '지번',
            'offiNm': '단지명',
            'excluUseAr': '전용면적(㎡)',
            'dealYear': '계약년도',
            'dealMonth': '계약월',
            'dealDay': '계약일',
            'deposit': '보증금(만원)',
            'monthlyRent': '월세(만원)',
            'floor': '층',
            'buildYear': '건축년도',
            'contractTerm': '계약기간',
            'contractType': '계약구분',
            'contractCategory': '전월세구분'
        }
        
        display_df = filtered_df.copy()
        
        # 존재하는 컬럼만 매핑
        existing_columns = {k: v for k, v in column_mapping.items() if k in display_df.columns}
        display_df = display_df.rename(columns=existing_columns)
        
        # 표시할 컬럼 선택
        display_columns = [col for col in existing_columns.values() if col in display_df.columns]
        
        if display_columns:
            st.dataframe(
                display_df[display_columns].sort_values(
                    '보증금(만원)' if '보증금(만원)' in display_columns else display_columns[0],
                    ascending=False
                ),
                use_container_width=True
            )
            
            # 데이터 다운로드
            col1, col2 = st.columns(2)
            
            with col1:
                csv = display_df[display_columns].to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="📁 CSV 다운로드",
                    data=csv,
                    file_name=f"오피스텔_실거래가_{selected_city}_{selected_district}.csv",
                    mime="text/csv"
                )
            
            with col2:
                json_data = display_df[display_columns].to_json(
                    orient='records', 
                    force_ascii=False, 
                    indent=2
                )
                st.download_button(
                    label="📄 JSON 다운로드",
                    data=json_data,
                    file_name=f"오피스텔_실거래가_{selected_city}_{selected_district}.json",
                    mime="application/json"
                )

# 푸터
st.markdown("---")
st.markdown(
    f"""
    <div style='text-align: center; color: #666; font-size: 12px;'>
        🏢 <strong>오피스텔 전월세 실거래가 대시보드</strong><br>
        📊 데이터 출처: 국토교통부 실거래가 공개시스템<br>
        🔄 조회 지역: {selected_city} {selected_district}<br>
        📅 조회 기간: {start_year}년 {start_month}월 ~ {end_year}년 {end_month}월<br>
        💡 문의: 국토교통부 (☎ 044-201-3114)
    </div>
    """,
    unsafe_allow_html=True
)
