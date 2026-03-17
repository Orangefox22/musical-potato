# -*- coding: utf-8 -*-
"""
PubMed 关键词发文量趋势分析 Web 应用 (Streamlit 版)
基于原命令行脚本适配，支持交互式查询与可视化
"""


import time
import logging
import socket
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from Bio import Entrez
from sklearn.linear_model import LinearRegression
import streamlit as st

# ==================== 配置 ====================
# 请务必在 Streamlit Cloud 的 Secrets 中设置 ENTREZ_EMAIL
Entrez.email = st.secrets.get("ENTREZ_EMAIL", "your_email@example.com")
REQUEST_DELAY = 0.34      # 两次请求间隔（秒）
MAX_RETRIES = 3           # 查询失败重试次数
SOCKET_TIMEOUT = 15       # 网络超时（秒）
# ==============================================

# 设置中文字体（如果系统无中文字体，可注释掉或改用英文标签）
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

# 配置日志（Streamlit 中可用 st.write 代替，此处保留便于调试）
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 设置全局网络超时
socket.setdefaulttimeout(SOCKET_TIMEOUT)


@st.cache_data(ttl=3600, show_spinner="正在从 PubMed 获取数据...")
def fetch_pubmed_counts(keyword, start, end):
    """
    获取指定关键词在每一年的发文量（带重试机制）
    返回 DataFrame，包含 year 和 count 两列
    """
    if ' ' in keyword:
        safe_keyword = f'"{keyword}"'
    else:
        safe_keyword = keyword

    records = []
    for year in range(start, end + 1):
        query = f'{safe_keyword} AND {year}[pdat]'
        count = None
        for attempt in range(MAX_RETRIES):
            try:
                handle = Entrez.esearch(db="pubmed", term=query, retmax=0)
                record = Entrez.read(handle)
                count = int(record["Count"])
                break
            except Exception as e:
                logging.warning(f"第 {attempt+1} 次查询 {year} 失败: {e}")
                if attempt == MAX_RETRIES - 1:
                    count = 0
                time.sleep(REQUEST_DELAY * 2)
            finally:
                try:
                    handle.close()
                except:
                    pass
        records.append({"year": year, "count": count})
        time.sleep(REQUEST_DELAY)
    return pd.DataFrame(records)


def simple_linear_regression_predict(df, years_to_predict):
    """
    使用线性回归预测未来发文量
    返回包含实际值和预测值的 DataFrame
    """
    if len(df) < 2:
        df_copy = df.copy()
        df_copy['type'] = '实际'
        return df_copy

    X = df[['year']].values
    y = df['count'].values

    model = LinearRegression()
    model.fit(X, y)

    last_year = df['year'].max()
    future_years = np.arange(last_year + 1, last_year + years_to_predict + 1).reshape(-1, 1)
    future_counts = model.predict(future_years)
    future_counts = np.maximum(future_counts, 0)

    future_df = pd.DataFrame({
        'year': future_years.flatten(),
        'count': future_counts,
        'type': '预测'
    })

    df_copy = df.copy()
    df_copy['type'] = '实际'
    result = pd.concat([df_copy, future_df], ignore_index=True)
    return result


def plot_trend(df_result, keyword):
    """
    绘制实际值与预测值的折线图，返回 matplotlib figure 对象
    """
    fig, ax = plt.subplots(figsize=(10, 5))
    actual = df_result[df_result['type'] == '实际']
    predicted = df_result[df_result['type'] == '预测']

    ax.plot(actual['year'], actual['count'], 'o-', label='实际发文量', color='blue')
    if not predicted.empty:
        ax.plot(predicted['year'], predicted['count'], 'x--', label='预测发文量', color='red')

    ax.set_xlabel('年份')
    ax.set_ylabel('发文量 (篇)')
    ax.set_title(f'PubMed 关键词趋势: {keyword}')
    ax.legend()
    ax.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout()
    return fig


# ------------------ Streamlit 界面 ------------------
st.set_page_config(page_title="PubMed 趋势分析", layout="wide")
st.title("📊 PubMed 关键词发文量趋势分析")
st.markdown("输入关键词和年份范围，获取年度发文量及未来趋势预测。")

with st.sidebar:
    st.header("⚙️ 参数设置")
    keyword = st.text_input("关键词", value="cGAS-STING")
    col1, col2 = st.columns(2)
    with col1:
        start_year = st.number_input("起始年份", min_value=1900, max_value=2025, value=2015)
    with col2:
        end_year = st.number_input("结束年份", min_value=1900, max_value=2025, value=2025)
    predict_years = st.slider("预测未来几年", min_value=0, max_value=10, value=3)
    run_button = st.button("🚀 开始分析")

if run_button:
    if start_year > end_year:
        st.error("起始年份不能大于结束年份！")
    else:
        # 获取数据
        with st.spinner("正在连接 PubMed 并获取数据，可能需要几分钟..."):
            df = fetch_pubmed_counts(keyword, start_year, end_year)

        if df.empty or df['count'].sum() == 0:
            st.warning("未检索到任何文献，请尝试其他关键词或年份范围。")
        else:
            st.success("数据获取完成！")

            # 显示原始数据
            st.subheader("📋 原始年度发文量")
            st.dataframe(df, use_container_width=True)

            # 下载原始数据
            csv_raw = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 下载原始数据 (CSV)", data=csv_raw,
                               file_name=f"pubmed_raw_{keyword}.csv", mime="text/csv")

            # 预测
            if predict_years > 0:
                df_result = simple_linear_regression_predict(df, predict_years)
                pred_part = df_result[df_result['type'] == '预测']
                if not pred_part.empty:
                    st.subheader("🔮 预测结果")
                    st.dataframe(pred_part, use_container_width=True)

                    # 下载预测结果
                    csv_pred = df_result.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 下载完整数据（含预测）", data=csv_pred,
                                       file_name=f"pubmed_pred_{keyword}.csv", mime="text/csv")

                # 绘制图表
                fig = plot_trend(df_result, keyword)
                st.subheader("📈 趋势图")
                st.pyplot(fig)
            else:
                # 不预测，只画实际数据
                df_actual = df.copy()
                df_actual['type'] = '实际'
                fig = plot_trend(df_actual, keyword)
                st.subheader("📈 趋势图")
                st.pyplot(fig)

else:
    st.info("👈 请在左侧设置参数并点击「开始分析」")
