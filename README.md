# PubMed 关键词发文量趋势分析 Web App

这是一个基于 Streamlit 的交互式工具，可以查询 PubMed 数据库中任意关键词的年度发文量，并使用线性回归预测未来趋势。

## 功能
- 输入关键词、起始年份、结束年份
- 获取每年发文量（实时查询 PubMed）
- 显示原始数据表格并支持下载 CSV
- 可选预测未来 0-10 年的发文量
- 绘制实际值与预测值的折线图

## 部署到 Streamlit Cloud
1. Fork 或下载本仓库
2. 在 [Streamlit Cloud](https://streamlit.io/cloud) 中创建新应用
3. 选择仓库、分支，主文件路径填 `app.py`
4. 在应用设置中添加 Secrets：
   - `ENTREZ_EMAIL` = 你的邮箱（PubMed API 要求）
5. 点击 Deploy 即可

## 本地运行
```bash
pip install -r requirements.txt
streamlit run app.py
