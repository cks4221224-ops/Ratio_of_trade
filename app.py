import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.font_manager as fm
import os

# -----------------------------------------------------------------------------
# 1. 파일 경로 및 폰트 설정
# -----------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, 'data', '무역의존도.csv')
FONT_PATH = os.path.join(BASE_DIR, 'fonts', 'NanumGothic.ttf')

def init_font():
    """
    지정된 폰트 파일을 matplotlib 폰트 매니저에 직접 추가하여 설정
    """
    if os.path.exists(FONT_PATH):
        try:
            fm.fontManager.addfont(FONT_PATH)
            font_prop = fm.FontProperties(fname=FONT_PATH)
            font_name = font_prop.get_name()
            plt.rc('font', family=font_name)
            plt.rc('axes', unicode_minus=False) 
        except Exception as e:
            st.error(f"폰트 로딩 중 오류 발생: {e}")
            plt.rc('axes', unicode_minus=False)
    else:
        st.warning(f"⚠️ 폰트 파일을 찾을 수 없습니다: {FONT_PATH}")
        plt.rc('axes', unicode_minus=False)

init_font()

# -----------------------------------------------------------------------------
# 2. 데이터 로드 및 전처리
# -----------------------------------------------------------------------------
@st.cache_data
def load_data(file_path):
    try:
        df_raw = pd.read_csv(file_path, header=None)
    except FileNotFoundError:
        return None
    
    years = df_raw.iloc[0, 1:].values  
    types = df_raw.iloc[1, 1:].values  
    data = df_raw.iloc[2:].copy()
    
    new_columns = ['Country'] + [f"{y}_{t}" for y, t in zip(years, types)]
    data.columns = new_columns
    data['Country'] = data['Country'].str.strip()
    
    df_melted = data.melt(id_vars=['Country'], var_name='Year_Type', value_name='Value')
    df_melted[['Year', 'Type']] = df_melted['Year_Type'].str.split('_', expand=True)
    df_melted['Value'] = pd.to_numeric(df_melted['Value'], errors='coerce')
    
    df_final = df_melted.pivot_table(
        index=['Country', 'Year'], 
        columns='Type', 
        values='Value'
    ).reset_index()
    
    df_final.columns.name = None
    df_final['수출대비_수입비율'] = df_final['수입'] / df_final['수출'] * 100
    
    return df_final

# -----------------------------------------------------------------------------
# 3. 시각화 함수
# -----------------------------------------------------------------------------
def plot_bar_chart(data, x_col, y_col, title, ylabel=None):
    # [수정] 막대가 길수록 오른쪽으로 가도록 오름차순 정렬 (작은 값 -> 큰 값)
    data = data.sort_values(by=y_col, ascending=True)
    
    sns.set_theme(style="whitegrid", rc={"font.family": plt.rcParams['font.family']})
    plt.rc('axes', unicode_minus=False)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # 막대 그래프
    sns.barplot(data=data, x=x_col, y=y_col, ax=ax, palette="viridis", hue=x_col, legend=False)
    
    ax.set_title(title, fontsize=16, pad=20, fontweight='bold')
    ax.set_xlabel("국가", fontsize=12)
    ax.set_ylabel(ylabel if ylabel else y_col, fontsize=12)
    
    # 막대 위에 값 표시
    for p in ax.patches:
        height = p.get_height()
        if not pd.isna(height):
            # 절대값 그래프라도 원래 값이 음수였다면 '-'를 붙여줄 수도 있지만,
            # 현재 로직은 절대값 변환된 데이터 자체를 그리므로 그냥 양수로 표현합니다.
            ax.text(p.get_x() + p.get_width() / 2., height, 
                    f'{height:.1f}', ha="center", va="bottom", fontsize=10)
    
    plt.xticks(rotation=45) 
    st.pyplot(fig)

def plot_line_chart(data, x_col, y_cols, title):
    sns.set_theme(style="whitegrid", rc={"font.family": plt.rcParams['font.family']})
    plt.rc('axes', unicode_minus=False)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    for y_col in y_cols:
        sns.lineplot(data=data, x=x_col, y=y_col, marker='o', label=y_col, ax=ax)
        
    ax.set_title(title, fontsize=16, pad=20, fontweight='bold')
    ax.set_ylabel("비중 (%)", fontsize=12)
    ax.legend()
    
    st.pyplot(fig)

# -----------------------------------------------------------------------------
# 4. 메인 앱
# -----------------------------------------------------------------------------
st.set_page_config(page_title="세계 무역의존도 분석", layout="wide")

st.title("📊 세계 무역의존도 분석 대시보드")

df = load_data(DATA_PATH)

if df is None:
    st.error(f"데이터 파일을 찾을 수 없습니다. 경로: {DATA_PATH}")
    st.stop()

# 사이드바
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
# 로직 구현
# -----------------------------------------------------------------------------
if menu in ["1. 연도별 수출 상위 10개국", "2. 연도별 수입 상위 10개국", 
            "3. 수출 대비 수입이 높은 국가 (Top 10)", "4. 수출 대비 수입이 낮은 국가 (Top 10)"]:
    
    years_list = sorted(df['Year'].unique())
    target_year = st.sidebar.selectbox("연도 선택", years_list)
    df_year = df[df['Year'] == target_year].copy()

    if menu == "1. 연도별 수출 상위 10개국":
        data = df_year.nlargest(10, '수출')
        st.subheader(f"{target_year}년 수출 의존도 상위 10개국")
        plot_bar_chart(data, 'Country', '수출', f"{target_year}년 수출 Top 10", ylabel="수출 의존도 (%)")
        
    elif menu == "2. 연도별 수입 상위 10개국":
        data = df_year.nlargest(10, '수입')
        st.subheader(f"{target_year}년 수입 의존도 상위 10개국")
        plot_bar_chart(data, 'Country', '수입', f"{target_year}년 수입 Top 10", ylabel="수입 의존도 (%)")
        
    elif menu == "3. 수출 대비 수입이 높은 국가 (Top 10)":
        data = df_year.nlargest(10, '수출대비_수입비율')
        st.subheader(f"{target_year}년 수출 대비 수입 비율 Top 10")
        st.info("💡 비율 > 100%: 수출보다 수입이 많음")
        plot_bar_chart(data, 'Country', '수출대비_수입비율', "수출 대비 수입 비율 (%)")
        
    elif menu == "4. 수출 대비 수입이 낮은 국가 (Top 10)":
        data = df_year.nsmallest(10, '수출대비_수입비율')
        st.subheader(f"{target_year}년 수출 대비 수입 비율 Bottom 10")
        plot_bar_chart(data, 'Country', '수출대비_수입비율', "수출 대비 수입 비율 (%)")

elif menu in ["5. 수출 비중 증가 상위 10개국", "6. 수출 비중 감소 상위 10개국",
              "7. 수입 비중 증가 상위 10개국", "8. 수입 비중 감소 상위 10개국"]:
    
    st.sidebar.markdown("---")
    st.sidebar.info("💡 2022년과 2024년 데이터가 모두 존재하는 국가 대상")
    
    df_pivot = df.pivot(index='Country', columns='Year', values=['수출', '수입'])
    # 컬럼 평탄화
    df_pivot.columns = [f'{col[0]}_{col[1]}' for col in df_pivot.columns]
    
    if '수출_2022' in df_pivot.columns and '수출_2024' in df_pivot.columns:
        # 증감 계산
        df_pivot['수출_증감'] = df_pivot['수출_2024'] - df_pivot['수출_2022']
        df_pivot['수입_증감'] = df_pivot['수입_2024'] - df_pivot['수입_2022']
        
        df_change = df_pivot.dropna(subset=['수출_증감', '수입_증감']).reset_index()
        
        # [수정] 용어 '22년도 대비 24년도'로 변경
        
        if menu == "5. 수출 비중 증가 상위 10개국":
            data = df_change.nlargest(10, '수출_증감')
            st.subheader("수출 비중 증가폭 Top 10 (22년도 대비 24년도)")
            plot_bar_chart(data, 'Country', '수출_증감', "수출 비중 증가폭", ylabel="증가폭 (%p)")
            
        elif menu == "6. 수출 비중 감소 상위 10개국":
            # [수정] 감소폭이 큰 순서대로(값이 작은 순서대로) 추출
            data = df_change.nsmallest(10, '수출_증감').copy()
            # [수정] 그래프를 위로 향하게 하기 위해 절대값 처리
            data['수출_증감'] = data['수출_증감'].abs()
            
            st.subheader("수출 비중 감소폭 Top 10 (22년도 대비 24년도)")
            plot_bar_chart(data, 'Country', '수출_증감', "수출 비중 감소폭 (절대값)", ylabel="감소폭 (%p)")
            
        elif menu == "7. 수입 비중 증가 상위 10개국":
            data = df_change.nlargest(10, '수입_증감')
            st.subheader("수입 비중 증가폭 Top 10 (22년도 대비 24년도)")
            plot_bar_chart(data, 'Country', '수입_증감', "수입 비중 증가폭", ylabel="증가폭 (%p)")
            
        elif menu == "8. 수입 비중 감소 상위 10개국":
            # [수정] 감소폭이 큰 순서대로 추출
            data = df_change.nsmallest(10, '수입_증감').copy()
            # [수정] 절대값 처리
            data['수입_증감'] = data['수입_증감'].abs()
            
            st.subheader("수입 비중 감소폭 Top 10 (22년도 대비 24년도)")
            plot_bar_chart(data, 'Country', '수입_증감', "수입 비중 감소폭 (절대값)", ylabel="감소폭 (%p)")
    else:
        st.warning("비교할 연도(2022, 2024) 데이터가 부족합니다.")

elif menu == "9. 국가별 상세 조회 (모든 연도)":
    countries = sorted(df['Country'].unique())
    default_idx = countries.index('대한민국') if '대한민국' in countries else 0
    selected_country = st.sidebar.selectbox("국가 선택", countries, index=default_idx)
    
    st.subheader(f"🇰🇷 {selected_country}의 무역의존도 추이")
    
    country_data = df[df['Country'] == selected_country].sort_values('Year')
    
    st.dataframe(country_data[['Year', '수출', '수입']].set_index('Year'), use_container_width=True)
    plot_line_chart(country_data, 'Year', ['수출', '수입'], f"{selected_country} 추이")