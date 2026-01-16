import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.font_manager as fm
import os

# -----------------------------------------------------------------------------
# 1. 파일 경로 및 폰트 설정
# -----------------------------------------------------------------------------

# 현재 파일(app.py)의 절대 경로를 기준으로 데이터와 폰트 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, 'data', '무역의존도.csv')
FONT_PATH = os.path.join(BASE_DIR, 'fonts', 'NanumGothic.ttf') # 확장자(.ttf) 확인 필요

def init_font():
    """
    지정된 경로(fonts 폴더)에 있는 폰트 파일을 로드하여 Matplotlib 설정에 적용
    """
    if os.path.exists(FONT_PATH):
        # 폰트 속성 로드
        font_prop = fm.FontProperties(fname=FONT_PATH)
        font_name = font_prop.get_name()
        
        # Matplotlib 전역 폰트 설정
        plt.rc('font', family=font_name)
        plt.rc('axes', unicode_minus=False) # 마이너스 기호 깨짐 방지
        # st.success(f"폰트 로드 성공: {font_name}") # 디버깅용
    else:
        st.error(f"폰트 파일을 찾을 수 없습니다: {FONT_PATH}")
        # 폰트가 없을 경우 시스템 기본 폰트로 폴백(Fallback)
        plt.rc('axes', unicode_minus=False)

# 앱 실행 시 폰트 초기화
init_font()

# -----------------------------------------------------------------------------
# 2. 데이터 로드 및 전처리 함수
# -----------------------------------------------------------------------------
@st.cache_data
def load_data(file_path):
    # 헤더가 2줄(연도, 항목)로 되어 있으므로 header=None으로 읽어서 직접 처리
    try:
        df_raw = pd.read_csv(file_path, header=None)
    except FileNotFoundError:
        return None
    
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
    df_melted = data.melt(id_vars=['Country'], var_name='Year_Type', value_name='Value')
    
    # Year, Type 분리
    df_melted[['Year', 'Type']] = df_melted['Year_Type'].str.split('_', expand=True)
    
    # 값(Value)을 숫자로 변환 ('-' 등은 NaN 처리)
    df_melted['Value'] = pd.to_numeric(df_melted['Value'], errors='coerce')
    
    # Pivot하여 [Country, Year, 수출, 수입] 형태로 정리
    df_final = df_melted.pivot_table(
        index=['Country', 'Year'], 
        columns='Type', 
        values='Value'
    ).reset_index()
    
    # 컬럼 정리
    df_final.columns.name = None
    
    # 추가 지표 계산
    # 1. 수출 대비 수입 비율 (수입 / 수출 * 100)
    df_final['수출대비_수입비율'] = df_final['수입'] / df_final['수출'] * 100
    
    return df_final

# -----------------------------------------------------------------------------
# 3. 시각화 헬퍼 함수 (Matplotlib/Seaborn)
# -----------------------------------------------------------------------------
def plot_bar_chart(data, x_col, y_col, title, ylabel=None):
    # 폰트 재설정 (Seaborn 테마 적용 시 폰트가 리셋될 수 있음)
    sns.set_theme(style="whitegrid", font=plt.rcParams['font.family'])
    plt.rc('axes', unicode_minus=False)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # 막대 그래프 그리기
    # palette warning 방지를 위해 hue 설정
    sns.barplot(data=data, x=x_col, y=y_col, ax=ax, palette="viridis", hue=x_col, legend=False)
    
    # 제목 및 라벨 설정
    ax.set_title(title, fontsize=16, pad=20, fontweight='bold')
    ax.set_xlabel("국가", fontsize=12)
    ax.set_ylabel(ylabel if ylabel else y_col, fontsize=12)
    
    # 막대 위에 값 표시
    for p in ax.patches:
        height = p.get_height()
        if not pd.isna(height): # NaN이 아닐 때만 표시
            ax.text(p.get_x() + p.get_width() / 2., height, 
                    f'{height:.1f}', ha="center", va="bottom", fontsize=10)
    
    plt.xticks(rotation=45) # x축 라벨 회전
    st.pyplot(fig) # Streamlit에 출력

def plot_line_chart(data, x_col, y_cols, title):
    sns.set_theme(style="whitegrid", font=plt.rcParams['font.family'])
    plt.rc('axes', unicode_minus=False)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # 여러 개의 라인 그리기 (수출, 수입)
    for y_col in y_cols:
        sns.lineplot(data=data, x=x_col, y=y_col, marker='o', label=y_col, ax=ax)
        
    ax.set_title(title, fontsize=16, pad=20, fontweight='bold')
    ax.set_ylabel("비중 (%)", fontsize=12)
    ax.legend()
    
    st.pyplot(fig)

# -----------------------------------------------------------------------------
# 4. 메인 앱 구성
# -----------------------------------------------------------------------------
st.set_page_config(page_title="세계 무역의존도 분석", layout="wide")

st.title("📊 세계 무역의존도 분석 대시보드")

# 데이터 로드
df = load_data(DATA_PATH)

if df is None:
    st.error(f"데이터 파일을 찾을 수 없습니다. 다음 경로를 확인해주세요: {DATA_PATH}")
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
    "9. 국가별 상세 조회 (모든 연도)"
])

# -----------------------------------------------------------------------------
# 메뉴별 로직 구현
# -----------------------------------------------------------------------------

if menu in ["1. 연도별 수출 상위 10개국", "2. 연도별 수입 상위 10개국", 
            "3. 수출 대비 수입이 높은 국가 (Top 10)", "4. 수출 대비 수입이 낮은 국가 (Top 10)"]:
    
    target_year = st.sidebar.selectbox("연도 선택", sorted(df['Year'].unique()))
    df_year = df[df['Year'] == target_year].copy()

    if menu == "1. 연도별 수출 상위 10개국":
        data = df_year.nlargest(10, '수출')
        st.subheader(f"{target_year}년 수출 의존도 상위 10개국")
        plot_bar_chart(data, 'Country', '수출', f"{target_year}년 수출 의존도 Top 10", ylabel="수출 의존도 (%)")
        
    elif menu == "2. 연도별 수입 상위 10개국":
        data = df_year.nlargest(10, '수입')
        st.subheader(f"{target_year}년 수입 의존도 상위 10개국")
        plot_bar_chart(data, 'Country', '수입', f"{target_year}년 수입 의존도 Top 10", ylabel="수입 의존도 (%)")
        
    elif menu == "3. 수출 대비 수입이 높은 국가 (Top 10)":
        data = df_year.nlargest(10, '수출대비_수입비율')
        st.subheader(f"{target_year}년 수출 대비 수입 비율이 높은 상위 10개국")
        st.info("💡 비율이 100%를 넘으면 수출보다 수입이 많음을 의미합니다.")
        plot_bar_chart(data, 'Country', '수출대비_수입비율', "수출 대비 수입 비율 Top 10", ylabel="수출 대비 수입 비율 (%)")
        
    elif menu == "4. 수출 대비 수입이 낮은 국가 (Top 10)":
        data = df_year.nsmallest(10, '수출대비_수입비율')
        st.subheader(f"{target_year}년 수출 대비 수입 비율이 낮은 상위 10개국")
        plot_bar_chart(data, 'Country', '수출대비_수입비율', "수출 대비 수입 비율 Bottom 10", ylabel="수출 대비 수입 비율 (%)")

elif menu in ["5. 수출 비중 증가 상위 10개국", "6. 수출 비중 감소 상위 10개국",
              "7. 수입 비중 증가 상위 10개국", "8. 수입 비중 감소 상위 10개국"]:
    
    st.sidebar.markdown("---")
    st.sidebar.info("💡 2022년과 2024년 데이터가 모두 존재하는 국가 대상")
    
    # Pivot for comparison
    df_pivot = df.pivot(index='Country', columns='Year', values=['수출', '수입'])
    
    # 증감 계산
    if ('수출', '2022') in df_pivot.columns and ('수출', '2024') in df_pivot.columns:
        df_pivot['수출_증감'] = df_pivot[('수출', '2024')] - df_pivot[('수출', '2022')]
        df_pivot['수입_증감'] = df_pivot[('수입', '2024')] - df_pivot[('수입', '2022')]
        
        df_change = df_pivot.dropna(subset=['수출_증감', '수입_증감']).reset_index()
        
        if menu == "5. 수출 비중 증가 상위 10개국":
            data = df_change.nlargest(10, '수출_증감')
            st.subheader("수출 비중 증가폭 상위 10개국 (22 대비 24)")
            plot_bar_chart(data, 'Country', '수출_증감', "수출 비중 증가폭", ylabel="증가폭 (%p)")
            
        elif menu == "6. 수출 비중 감소 상위 10개국":
            data = df_change.nsmallest(10, '수출_증감')
            st.subheader("수출 비중 감소폭 상위 10개국 (22 대비 24)")
            plot_bar_chart(data, 'Country', '수출_증감', "수출 비중 감소폭", ylabel="증감폭 (%p)")
            
        elif menu == "7. 수입 비중 증가 상위 10개국":
            data = df_change.nlargest(10, '수입_증감')
            st.subheader("수입 비중 증가폭 상위 10개국 (22 대비 24)")
            plot_bar_chart(data, 'Country', '수입_증감', "수입 비중 증가폭", ylabel="증가폭 (%p)")
            
        elif menu == "8. 수입 비중 감소 상위 10개국":
            data = df_change.nsmallest(10, '수입_증감')
            st.subheader("수입 비중 감소폭 상위 10개국 (22 대비 24)")
            plot_bar_chart(data, 'Country', '수입_증감', "수입 비중 감소폭", ylabel="증감폭 (%p)")
    else:
        st.warning("비교할 연도 데이터가 부족합니다.")

elif menu == "9. 국가별 상세 조회 (모든 연도)":
    countries = sorted(df['Country'].unique())
    # 대한민국을 기본값으로, 없으면 첫 번째 국가
    default_idx = countries.index('대한민국') if '대한민국' in countries else 0
    selected_country = st.sidebar.selectbox("국가 선택", countries, index=default_idx)
    
    st.subheader(f"🇰🇷 {selected_country}의 무역의존도 추이")
    
    country_data = df[df['Country'] == selected_country].sort_values('Year')
    
    # 데이터프레임 표시
    st.dataframe(country_data[['Year', '수출', '수입']].set_index('Year'), use_container_width=True)
    
    # 꺾은선 그래프 그리기
    plot_line_chart(country_data, 'Year', ['수출', '수입'], f"{selected_country} 수출 vs 수입 추이")