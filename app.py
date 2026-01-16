import streamlit as st
import pandas as pd
import plotly.express as px

# -----------------------------------------------------------------------------
# 1. 데이터 로드 및 전처리 함수
# -----------------------------------------------------------------------------
@st.cache_data
def load_data(file_path):
    # 헤더가 2줄(연도, 항목)로 되어 있으므로 header=None으로 읽어서 직접 처리
    df_raw = pd.read_csv(file_path, header=None)
    
    # 헤더 추출
    years = df_raw.iloc[0, 1:].values  # ['2022', '2022', '2023', ...]
    types = df_raw.iloc[1, 1:].values  # ['수출', '수입', '수출', ...]
    
    # 데이터 부분 추출
    data = df_raw.iloc[2:].copy()
    
    # 컬럼명 임시 생성 (예: 2022_수출)
    new_columns = ['Country'] + [f"{y}_{t}" for y, t in zip(years, types)]
    data.columns = new_columns
    
    # 국가명 공백 제거
    data['Country'] = data['Country'].str.strip()
    
    # 데이터 형태 변환 (Wide -> Long)
    # melt를 사용하여 [Country, Year, Type, Value] 형태로 변환
    df_melted = data.melt(id_vars=['Country'], var_name='Year_Type', value_name='Value')
    
    # Year, Type 분리
    df_melted[['Year', 'Type']] = df_melted['Year_Type'].str.split('_', expand=True)
    
    # 값(Value)을 숫자로 변환 ('-' 등은 NaN 처리)
    df_melted['Value'] = pd.to_numeric(df_melted['Value'], errors='coerce')
    
    # 다시 Pivot하여 [Country, Year, 수출, 수입] 형태로 정리
    df_final = df_melted.pivot_table(
        index=['Country', 'Year'], 
        columns='Type', 
        values='Value'
    ).reset_index()
    
    # 컬럼 정리
    df_final.columns.name = None
    
    # 추가 지표 계산
    # 1. 수출 대비 수입 비율 (수입 / 수출 * 100) -> 높을수록 수입 의존
    df_final['수출대비_수입비율'] = df_final['수입'] / df_final['수출'] * 100
    
    # 2. 무역 개방도 (수출 + 수입)
    df_final['무역개방도'] = df_final['수출'] + df_final['수입']
    
    # 3. 무역 수지 (수출 - 수입)
    df_final['무역수지'] = df_final['수출'] - df_final['수입']

    return df_final

# -----------------------------------------------------------------------------
# 2. 메인 앱 구성
# -----------------------------------------------------------------------------
st.set_page_config(page_title="세계 무역의존도 분석", layout="wide")

st.title("🌏 세계 무역의존도(GDP 대비) 분석 대시보드")
st.markdown("데이터 출처: 통계청 (2022~2024년)")

# 데이터 로드 (파일명은 실제 저장한 csv 이름으로 변경하세요)
try:
    # 업로드된 파일명을 여기에 입력 (예: '무역의존도_데이터.csv')
    df = load_data('무역의존도.xlsx - 데이터.csv') 
except FileNotFoundError:
    st.error("데이터 파일(csv)을 찾을 수 없습니다. 파일명을 확인해주세요.")
    st.stop()

# 사이드바 메뉴
menu = st.sidebar.radio("분석 메뉴 선택", [
    "1. 연도별 수출 상위 10개국",
    "2. 연도별 수입 상위 10개국",
    "3. 수출 대비 수입이 높은 국가 (Top 10)",
    "4. 수출 대비 수입이 낮은 국가 (Top 10)",
    "5. 수출 비중 증가 상위 10개국",
    "6. 수출 비중 감소 상위 10개국",
    "7. 수입 비중 증가 상위 10개국",
    "8. 수입 비중 감소 상위 10개국",
    "9. 국가별 상세 조회 (모든 연도)",
    "10. [추가] 무역 개방도 & 수지 분석"
])

# 공통 함수: 상위 10개국 막대 그래프
def plot_top10_bar(data, x_col, y_col, title, color_col=None):
    fig = px.bar(data, x=x_col, y=y_col, text=y_col, title=title, color=color_col if color_col else y_col)
    fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
    st.plotly_chart(fig, use_container_width=True)

# -----------------------------------------------------------------------------
# 메뉴별 로직 구현
# -----------------------------------------------------------------------------

# 1~4번 메뉴: 연도 선택이 필요함
if menu in ["1. 연도별 수출 상위 10개국", "2. 연도별 수입 상위 10개국", 
            "3. 수출 대비 수입이 높은 국가 (Top 10)", "4. 수출 대비 수입이 낮은 국가 (Top 10)"]:
    
    target_year = st.sidebar.selectbox("연도 선택", sorted(df['Year'].unique()))
    df_year = df[df['Year'] == target_year].copy()

    if menu == "1. 연도별 수출 상위 10개국":
        data = df_year.nlargest(10, '수출')
        st.subheader(f"{target_year}년 수출 의존도 상위 10개국")
        plot_top10_bar(data, 'Country', '수출', "수출 의존도(%)")
        
    elif menu == "2. 연도별 수입 상위 10개국":
        data = df_year.nlargest(10, '수입')
        st.subheader(f"{target_year}년 수입 의존도 상위 10개국")
        plot_top10_bar(data, 'Country', '수입', "수입 의존도(%)")
        
    elif menu == "3. 수출 대비 수입이 높은 국가 (Top 10)":
        # 수입이 수출보다 압도적으로 많은 나라 (무역 적자 성격)
        data = df_year.nlargest(10, '수출대비_수입비율')
        st.subheader(f"{target_year}년 수출 대비 수입 비율이 높은 상위 10개국")
        st.info("💡 비율이 100%를 넘으면 수출보다 수입이 많음을 의미합니다.")
        plot_top10_bar(data, 'Country', '수출대비_수입비율', "수출 대비 수입 비율(%)")
        
    elif menu == "4. 수출 대비 수입이 낮은 국가 (Top 10)":
        # 수입보다 수출이 압도적으로 많은 나라 (자원 부국 등)
        data = df_year.nsmallest(10, '수출대비_수입비율')
        st.subheader(f"{target_year}년 수출 대비 수입 비율이 낮은 상위 10개국")
        plot_top10_bar(data, 'Country', '수출대비_수입비율', "수출 대비 수입 비율(%)")

# 5~8번 메뉴: 증감 분석 (2022 vs 2024 비교)
elif menu in ["5. 수출 비중 증가 상위 10개국", "6. 수출 비중 감소 상위 10개국",
              "7. 수입 비중 증가 상위 10개국", "8. 수입 비중 감소 상위 10개국"]:
    
    st.sidebar.markdown("---")
    st.sidebar.info("💡 증감 분석은 2022년과 2024년 데이터가 모두 존재하는 국가를 대상으로 합니다.")
    
    # Pivot for comparison
    df_pivot = df.pivot(index='Country', columns='Year', values=['수출', '수입'])
    
    # 2022년과 2024년 컬럼이 있는지 확인하고 계산
    if ('수출', '2022') in df_pivot.columns and ('수출', '2024') in df_pivot.columns:
        df_pivot['수출_증감'] = df_pivot[('수출', '2024')] - df_pivot[('수출', '2022')]
        df_pivot['수입_증감'] = df_pivot[('수입', '2024')] - df_pivot[('수입', '2022')]
        
        # NaN 제거 (두 연도 중 하나라도 없으면 계산 불가)
        df_change = df_pivot.dropna(subset=['수출_증감', '수입_증감']).reset_index()
        
        if menu == "5. 수출 비중 증가 상위 10개국":
            data = df_change.nlargest(10, '수출_증감')
            st.subheader("수출 비중 증가폭 상위 10개국 (2022 대비 2024)")
            plot_top10_bar(data, 'Country', '수출_증감', "수출 비중 증가(%p)")
            
        elif menu == "6. 수출 비중 감소 상위 10개국":
            data = df_change.nsmallest(10, '수출_증감')
            # 감소폭이 큰 순서대로 보기 위해 절대값이나 정렬 처리
            st.subheader("수출 비중 감소폭 상위 10개국 (2022 대비 2024)")
            plot_top10_bar(data, 'Country', '수출_증감', "수출 비중 증감(%p)")
            
        elif menu == "7. 수입 비중 증가 상위 10개국":
            data = df_change.nlargest(10, '수입_증감')
            st.subheader("수입 비중 증가폭 상위 10개국 (2022 대비 2024)")
            plot_top10_bar(data, 'Country', '수입_증감', "수입 비중 증가(%p)")
            
        elif menu == "8. 수입 비중 감소 상위 10개국":
            data = df_change.nsmallest(10, '수입_증감')
            st.subheader("수입 비중 감소폭 상위 10개국 (2022 대비 2024)")
            plot_top10_bar(data, 'Country', '수입_증감', "수입 비중 증감(%p)")
    else:
        st.warning("2022년 또는 2024년 데이터가 부족하여 증감을 계산할 수 없습니다.")

# 9번 메뉴: 국가별 상세 조회
elif menu == "9. 국가별 상세 조회 (모든 연도)":
    countries = sorted(df['Country'].unique())
    selected_country = st.sidebar.selectbox("국가 선택", countries, index=countries.index('대한민국') if '대한민국' in countries else 0)
    
    st.subheader(f"🇰🇷 {selected_country}의 무역의존도 추이")
    
    country_data = df[df['Country'] == selected_country]
    
    # 표 보여주기
    st.dataframe(country_data[['Year', '수출', '수입']].set_index('Year'), use_container_width=True)
    
    # 라인 차트 그리기
    # Long format으로 변환해서 그리기 쉽게
    chart_data = country_data.melt(id_vars=['Year'], value_vars=['수출', '수입'], var_name='Type', value_name='Value')
    
    fig = px.line(chart_data, x='Year', y='Value', color='Type', markers=True, 
                  title=f"{selected_country} 수출 vs 수입 추이")
    st.plotly_chart(fig, use_container_width=True)

# 10번 메뉴: 추가 분석 (제안 사항)
elif menu == "10. [추가] 무역 개방도 & 수지 분석":
    target_year = st.sidebar.selectbox("연도 선택", sorted(df['Year'].unique()))
    df_year = df[df['Year'] == target_year].copy()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🌐 무역 개방도 Top 10")
        st.markdown("*(수출 + 수입)*")
        data_open = df_year.nlargest(10, '무역개방도')
        fig1 = px.bar(data_open, x='Country', y='무역개방도', title=f"{target_year}년 무역 개방도 상위 10")
        st.plotly_chart(fig1, use_container_width=True)
        
    with col2:
        st.markdown("### 💰 무역 수지(흑자) Top 10")
        st.markdown("*(수출 - 수입)*")
        data_bal = df_year.nlargest(10, '무역수지')
        fig2 = px.bar(data_bal, x='Country', y='무역수지', title=f"{target_year}년 무역 흑자 비중 상위 10", color_discrete_sequence=['green'])
        st.plotly_chart(fig2, use_container_width=True)