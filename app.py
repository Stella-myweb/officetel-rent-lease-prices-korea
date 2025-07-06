import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium
import numpy as np
from datetime import datetime, timedelta
import urllib3
import warnings

# SSL 경고 비활성화
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings('ignore')

# 페이지 설정
st.set_page_config(
    page_title="오피스텔 전월세 실거래가 지도",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 서비스키
SERVICE_KEY = "jUxxEMTFyxsIT2rt2P8JBO9y0EmFT9mx1zNPb31XLX27rFNH12NQ+6+ZLqqvW6k/ffQ5ZOOYzzcSo0Fq4u3Lfg=="

# 지역코드 및 좌표 매핑
REGION_DATA = {
    "서울특별시": {
        "강남구": {"code": "11680", "lat": 37.5172, "lon": 127.0473},
        "강동구": {"code": "11740", "lat": 37.5301, "lon": 127.1238},
        "강북구": {"code": "11305", "lat": 37.6396, "lon": 127.0254},
        "강서구": {"code": "11500", "lat": 37.5509, "lon": 126.8495},
        "관악구": {"code": "11620", "lat": 37.4784, "lon": 126.9516},
        "광진구": {"code": "11215", "lat": 37.5385, "lon": 127.0823},
        "구로구": {"code": "11530", "lat": 37.4955, "lon": 126.8876},
        "금천구": {"code": "11545", "lat": 37.4569, "lon": 126.8955},
        "노원구": {"code": "11350", "lat": 37.6541, "lon": 127.0565},
        "도봉구": {"code": "11320", "lat": 37.6688, "lon": 127.0471},
        "동대문구": {"code": "11230", "lat": 37.5744, "lon": 127.0395},
        "동작구": {"code": "11590", "lat": 37.5124, "lon": 126.9393},
        "마포구": {"code": "11440", "lat": 37.5661, "lon": 126.9019},
        "서대문구": {"code": "11410", "lat": 37.5791, "lon": 126.9368},
        "서초구": {"code": "11650", "lat": 37.4837, "lon": 127.0324},
        "성동구": {"code": "11200", "lat": 37.5636, "lon": 127.0365},
        "성북구": {"code": "11290", "lat": 37.5894, "lon": 127.0167},
        "송파구": {"code": "11710", "lat": 37.5145, "lon": 127.1059},
        "양천구": {"code": "11470", "lat": 37.5169, "lon": 126.8664},
        "영등포구": {"code": "11560", "lat": 37.5264, "lon": 126.8962},
        "용산구": {"code": "11170", "lat": 37.5324, "lon": 126.9906},
        "은평구": {"code": "11380", "lat": 37.6026, "lon": 126.9291},
        "종로구": {"code": "11110", "lat": 37.5735, "lon": 126.9788},
        "중구": {"code": "11140", "lat": 37.5640, "lon": 126.9975},
        "중랑구": {"code": "11260", "lat": 37.6063, "lon": 127.0925}
    },
    "부산광역시": {
        "강서구": {"code": "26440", "lat": 35.2122, "lon": 128.9802},
        "금정구": {"code": "26410", "lat": 35.2429, "lon": 129.0927},
        "남구": {"code": "26290", "lat": 35.1337, "lon": 129.0840},
        "동구": {"code": "26170", "lat": 35.1295, "lon": 129.0456},
        "동래구": {"code": "26260", "lat": 35.2048, "lon": 129.0784},
        "부산진구": {"code": "26230", "lat": 35.1628, "lon": 129.0530},
        "북구": {"code": "26320", "lat": 35.1966, "lon": 128.9897},
        "사상구": {"code": "26530", "lat": 35.1495, "lon": 128.9913},
        "사하구": {"code": "26380", "lat": 35.1043, "lon": 128.9744},
        "서구": {"code": "26140", "lat": 35.0972, "lon": 129.0240},
        "수영구": {"code": "26350", "lat": 35.1453, "lon": 129.1134},
        "연제구": {"code": "26470", "lat": 35.1762, "lon": 129.0783},
        "영도구": {"code": "26200", "lat": 35.0909, "lon": 129.0681},
        "중구": {"code": "26110", "lat": 35.1068, "lon": 129.0323},
        "해운대구": {"code": "26440", "lat": 35.1631, "lon": 129.1635}
    }
}

# 제목
st.title("🏢 오피스텔 전월세 실거래가 지도")
st.markdown("**국토교통부 실거래가 데이터 기반 히트맵 시각화**")

# API 호출 함수
@st.cache_data(ttl=3600)
def fetch_officetel_data(service_key, lawd_cd, deal_ymd):
    """오피스텔 전월세 데이터를 가져오는 함수"""
    
    url = "http://apis.data.go.kr/1613000/RTMSDataSvcOffiRent/getRTMSDataSvcOffiRent"
    
    params = {
        'serviceKey': service_key,
        'LAWD_CD': lawd_cd,
        'DEAL_YMD': deal_ymd,
        'pageNo': 1,
        'numOfRows': 10000
    }
    
    try:
        response = requests.get(url, params=params, verify=False, timeout=15)
        response.raise_for_status()
        
        # XML 파싱
        root = ET.fromstring(response.content)
        
        # 헤더 확인
        result_code = root.find('.//resultCode')
        if result_code is not None and result_code.text != '00':
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
        
    except Exception as e:
        st.error(f"데이터 로드 실패: {str(e)}")
        return None

# 데이터 전처리 함수
def preprocess_data(raw_data, region_info):
    """원시 데이터를 DataFrame으로 변환하고 좌표 추가"""
    
    if not raw_data:
        return pd.DataFrame()
    
    df = pd.DataFrame(raw_data)
    
    if df.empty:
        return df
    
    # 수치형 컬럼 변환
    numeric_columns = ['deposit', 'monthlyRent', 'excluUseAr', 'floor', 'buildYear']
    
    for col in numeric_columns:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(',', '').replace('', '0')
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # 결측치 처리
    df = df.fillna(0)
    
    # 계약 구분 생성
    df['contractCategory'] = df.apply(
        lambda x: '전세' if x['monthlyRent'] == 0 else '월세', axis=1
    )
    
    # 기본 좌표 추가 (지역 중심)
    base_lat = region_info['lat']
    base_lon = region_info['lon']
    
    # 각 거래에 대해 랜덤 좌표 생성 (실제로는 주소 기반 지오코딩 필요)
    np.random.seed(42)  # 일관성을 위한 시드 설정
    df['lat'] = base_lat + np.random.normal(0, 0.01, len(df))
    df['lon'] = base_lon + np.random.normal(0, 0.01, len(df))
    
    return df

# 사이드바 설정
st.sidebar.header("🔍 조회 조건")

# 지역 선택
selected_city = st.sidebar.selectbox(
    "시/도 선택",
    options=list(REGION_DATA.keys()),
    index=0
)

selected_district = st.sidebar.selectbox(
    "시/군/구 선택",
    options=list(REGION_DATA[selected_city].keys()),
    index=0
)

# 조회 월 선택
current_date = datetime.now()
year_options = list(range(2020, current_date.year + 1))
month_options = list(range(1, 13))

selected_year = st.sidebar.selectbox(
    "조회 연도",
    options=year_options,
    index=len(year_options) - 1
)

selected_month = st.sidebar.selectbox(
    "조회 월",
    options=month_options,
    index=current_date.month - 1
)

deal_ymd = f"{selected_year}{selected_month:02d}"

# 필터 옵션
st.sidebar.subheader("🔍 필터 옵션")

show_jeonse = st.sidebar.checkbox("전세 표시", value=True)
show_monthly = st.sidebar.checkbox("월세 표시", value=True)

# 데이터 로드
region_info = REGION_DATA[selected_city][selected_district]
lawd_cd = region_info['code']

with st.spinner(f"📡 {selected_city} {selected_district} {selected_year}년 {selected_month}월 데이터 로딩중..."):
    raw_data = fetch_officetel_data(SERVICE_KEY, lawd_cd, deal_ymd)
    
    if not raw_data:
        st.error("❌ 해당 조건의 데이터가 없습니다. 다른 지역이나 기간을 선택해주세요.")
        st.stop()
    
    df = preprocess_data(raw_data, region_info)
    
    if df.empty:
        st.warning("⚠️ 데이터가 비어있습니다.")
        st.stop()

# 필터 적용
filtered_df = df.copy()

if not show_jeonse:
    filtered_df = filtered_df[filtered_df['contractCategory'] != '전세']
if not show_monthly:
    filtered_df = filtered_df[filtered_df['contractCategory'] != '월세']

# 요약 통계
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("📍 총 거래 건수", f"{len(filtered_df):,}건")

with col2:
    avg_deposit = filtered_df['deposit'].mean() if len(filtered_df) > 0 else 0
    st.metric("💰 평균 보증금", f"{avg_deposit:,.0f}만원")

with col3:
    avg_monthly = filtered_df['monthlyRent'].mean() if len(filtered_df) > 0 else 0
    st.metric("🏠 평균 월세", f"{avg_monthly:,.0f}만원")

with col4:
    avg_area = filtered_df['excluUseAr'].mean() if len(filtered_df) > 0 else 0
    st.metric("📐 평균 면적", f"{avg_area:.1f}㎡")

# 지도 생성
st.markdown("### 🗺️ 거래 위치 히트맵")

if not filtered_df.empty:
    # 지도 중심 좌표
    center_lat = region_info['lat']
    center_lon = region_info['lon']
    
    # Folium 지도 생성
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=12,
        tiles='OpenStreetMap'
    )
    
    # 히트맵 데이터 준비 (위도, 경도, 가중치)
    heat_data = []
    for _, row in filtered_df.iterrows():
        # 보증금을 가중치로 사용 (정규화)
        weight = row['deposit'] / filtered_df['deposit'].max() if filtered_df['deposit'].max() > 0 else 1
        heat_data.append([row['lat'], row['lon'], weight])
    
    # 히트맵 추가
    if heat_data:
        HeatMap(
            heat_data,
            radius=15,
            blur=10,
            max_zoom=1,
            gradient={
                0.2: 'blue',
                0.4: 'lime', 
                0.6: 'orange',
                1.0: 'red'
            }
        ).add_to(m)
    
    # 개별 거래 마커 추가 (클릭 시 상세 정보)
    for idx, row in filtered_df.iterrows():
        # 마커 색상 (전세: 파랑, 월세: 빨강)
        color = 'blue' if row['contractCategory'] == '전세' else 'red'
        
        # 팝업 내용
        popup_html = f"""
        <div style="width: 300px;">
            <h4><b>{row.get('offiNm', '단지명 없음')}</b></h4>
            <hr>
            <p><b>📍 위치:</b> {row.get('umdNm', '')} {row.get('jibun', '')}</p>
            <p><b>🏢 층:</b> {row.get('floor', '')}층</p>
            <p><b>📐 전용면적:</b> {row['excluUseAr']:.1f}㎡</p>
            <p><b>🏗️ 건축년도:</b> {row.get('buildYear', '')}년</p>
            <hr>
            <p><b>💰 보증금:</b> {row['deposit']:,.0f}만원</p>
            <p><b>🏠 월세:</b> {row['monthlyRent']:,.0f}만원</p>
            <p><b>📋 구분:</b> {row['contractCategory']}</p>
            <p><b>📅 계약일:</b> {row.get('dealYear', '')}.{row.get('dealMonth', '')}.{row.get('dealDay', '')}</p>
            <p><b>⏰ 계약기간:</b> {row.get('contractTerm', '')}</p>
        </div>
        """
        
        folium.Marker(
            location=[row['lat'], row['lon']],
            popup=folium.Popup(popup_html, max_width=350),
            icon=folium.Icon(
                color=color, 
                icon='home',
                prefix='fa'
            ),
            tooltip=f"{row.get('offiNm', '단지명 없음')} - {row['deposit']:,.0f}만원"
        ).add_to(m)
    
    # 범례 추가
    legend_html = '''
    <div style="position: fixed; 
                bottom: 50px; left: 50px; width: 150px; height: 90px; 
                background-color: white; border:2px solid grey; z-index:9999; 
                font-size:14px; padding: 10px">
    <h4>범례</h4>
    <p><i class="fa fa-home" style="color:blue"></i> 전세</p>
    <p><i class="fa fa-home" style="color:red"></i> 월세</p>
    <p>🔥 히트맵: 보증금 높을수록 빨강</p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # 지도 표시
    map_data = st_folium(m, width=1000, height=600, returned_objects=["last_object_clicked"])
    
    # 클릭된 마커 정보 표시
    if map_data['last_object_clicked']:
        st.markdown("### 📋 클릭된 위치 정보")
        clicked_lat = map_data['last_object_clicked']['lat']
        clicked_lon = map_data['last_object_clicked']['lng']
        
        # 클릭 위치와 가장 가까운 거래 찾기
        distances = np.sqrt((filtered_df['lat'] - clicked_lat)**2 + (filtered_df['lon'] - clicked_lon)**2)
        closest_idx = distances.idxmin()
        closest_deal = filtered_df.loc[closest_idx]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.info(f"""
            **🏢 {closest_deal.get('offiNm', '단지명 없음')}**
            
            📍 **위치**: {closest_deal.get('umdNm', '')} {closest_deal.get('jibun', '')}
            
            🏢 **층**: {closest_deal.get('floor', '')}층
            
            📐 **전용면적**: {closest_deal['excluUseAr']:.1f}㎡
            
            🏗️ **건축년도**: {closest_deal.get('buildYear', '')}년
            """)
        
        with col2:
            st.success(f"""
            **💰 거래 정보**
            
            💰 **보증금**: {closest_deal['deposit']:,.0f}만원
            
            🏠 **월세**: {closest_deal['monthlyRent']:,.0f}만원
            
            📋 **구분**: {closest_deal['contractCategory']}
            
            📅 **계약일**: {closest_deal.get('dealYear', '')}.{closest_deal.get('dealMonth', '')}.{closest_deal.get('dealDay', '')}
            
            ⏰ **계약기간**: {closest_deal.get('contractTerm', '')}
            """)

# 데이터 테이블
st.markdown("### 📊 거래 내역")

if not filtered_df.empty:
    # 표시용 데이터 준비
    display_df = filtered_df[[
        'offiNm', 'umdNm', 'jibun', 'excluUseAr', 'floor', 'buildYear',
        'deposit', 'monthlyRent', 'contractCategory', 'contractTerm'
    ]].copy()
    
    # 컬럼명 변경
    display_df.columns = [
        '단지명', '법정동', '지번', '전용면적(㎡)', '층', '건축년도',
        '보증금(만원)', '월세(만원)', '계약구분', '계약기간'
    ]
    
    # 보증금 기준 내림차순 정렬
    display_df = display_df.sort_values('보증금(만원)', ascending=False)
    
    st.dataframe(display_df, use_container_width=True)
    
    # 데이터 다운로드
    col1, col2 = st.columns(2)
    
    with col1:
        csv = display_df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📁 CSV 다운로드",
            data=csv,
            file_name=f"오피스텔_실거래가_{selected_city}_{selected_district}_{deal_ymd}.csv",
            mime="text/csv"
        )
    
    with col2:
        json_data = display_df.to_json(orient='records', force_ascii=False, indent=2)
        st.download_button(
            label="📄 JSON 다운로드",
            data=json_data,
            file_name=f"오피스텔_실거래가_{selected_city}_{selected_district}_{deal_ymd}.json",
            mime="application/json"
        )

# 푸터
st.markdown("---")
st.markdown(
    f"""
    <div style='text-align: center; color: #666; font-size: 12px;'>
        🏢 <strong>오피스텔 전월세 실거래가 히트맵</strong><br>
        📊 데이터 출처: 국토교통부 실거래가 공개시스템<br>
        🔄 조회 지역: {selected_city} {selected_district} | 📅 조회 기간: {selected_year}년 {selected_month}월<br>
        🗺️ 히트맵: 보증금 기준 가중치 적용 | 📍 마커 클릭: 상세 정보 확인
    </div>
    """,
    unsafe_allow_html=True
)
