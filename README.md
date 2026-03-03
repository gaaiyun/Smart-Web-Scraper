# 🕷️ 智能网页爬虫工具 (Smart Web Scraper)

一个功能强大的智能网页爬虫工具，带有友好的 Streamlit 用户界面。

## ✨ 功能特性

### 🎯 多种爬取模式
- **单页爬取**: 快速抓取单个网页的完整内容
- **批量 URL 爬取**: 同时处理多个 URL，支持自定义请求间隔
- **站点地图爬取**: 自动解析 sitemap.xml 并爬取所有页面

### 📊 数据提取能力
- **文本内容**: 智能提取网页主体文本，自动过滤广告和导航
- **图片链接**: 提取所有图片及其替代文本
- **表格数据**: 自动识别并提取网页中的表格
- **元数据**: 提取标题、描述、关键词、Open Graph 数据等

### 💾 导出格式
- **JSON**: 完整的结构化数据
- **CSV**: 适合数据分析的表格格式
- **Markdown**: 可读性强的文档格式

### 🎨 Streamlit Dashboard
- 直观的 URL 输入界面
- 实时爬取进度显示
- 结果预览（文本、链接、图片、表格、元数据）
- 一键数据下载

## 🚀 快速开始

### 1. 安装依赖

```bash
cd smart-web-scraper
pip install -r requirements.txt
```

### 2. 运行 Dashboard

```bash
streamlit run dashboard.py
```

浏览器会自动打开 http://localhost:8501

### 3. 使用示例

#### 单页爬取
1. 选择"单页爬取"模式
2. 输入 URL（如：https://www.example.com）
3. 点击"🚀 开始爬取"
4. 查看结果并导出

#### 批量爬取
1. 选择"批量 URL 爬取"模式
2. 每行输入一个 URL
3. 设置请求间隔（避免被封禁）
4. 点击开始爬取

#### 站点地图爬取
1. 选择"站点地图爬取"模式
2. 输入 sitemap 地址（如：https://www.example.com/sitemap.xml）
3. 自动爬取所有页面

## 📁 项目结构

```
smart-web-scraper/
├── dashboard.py          # Streamlit 主界面
├── scraper.py            # 爬虫核心模块
├── requirements.txt      # Python 依赖
├── README.md            # 项目说明
├── tests/               # 单元测试
│   ├── __init__.py
│   └── test_scraper.py
└── output/              # 导出文件目录（自动生成）
```

## 🔧 核心 API

### SmartScraper 类

```python
from scraper import SmartScraper

scraper = SmartScraper()

# 单页爬取
result = scraper.scrape_single("https://www.example.com")

# 批量爬取
urls = ["https://url1.com", "https://url2.com"]
results = scraper.scrape_batch(urls, delay=1.0)

# 站点地图爬取
results = scraper.scrape_sitemap("https://www.example.com/sitemap.xml")

# 导出数据
scraper.export_to_json(results, "output.json")
scraper.export_to_csv(results, "output.csv")
scraper.export_to_markdown(results, "output.md")
```

### 提取的数据结构

```python
{
    'url': 'https://...',
    'metadata': {
        'title': '页面标题',
        'description': '页面描述',
        'keywords': '关键词',
        'author': '作者',
        'og_title': 'OG 标题',
        'og_description': 'OG 描述',
        'og_image': 'OG 图片'
    },
    'text': '页面纯文本内容',
    'links': [
        {'text': '链接文本', 'url': 'https://...'}
    ],
    'images': [
        {'src': 'https://...', 'alt': '替代文本'}
    ],
    'tables': [
        [{'列 1': '值 1', '列 2': '值 2'}]
    ]
}
```

## 🧪 运行测试

```bash
# 运行所有测试
pytest tests/

# 运行测试并查看覆盖率
pytest tests/ --cov=scraper --cov-report=html

# 运行特定测试
pytest tests/test_scraper.py -v
```

## ⚙️ 高级配置

### 自定义请求头

```python
scraper = SmartScraper(headers={
    'User-Agent': 'Custom User Agent',
    'Accept-Language': 'en-US'
})
```

### 调整爬取速度

在 Dashboard 侧边栏设置"请求间隔"，建议：
- 快速爬取：0.5-1 秒
- 礼貌爬取：2-3 秒
- 大规模爬取：5+ 秒

## 📝 使用场景

- 📰 新闻网站内容采集
- 🛒 电商产品价格监控
- 📊 竞品数据分析
- 📚 学术资源收集
- 🔍 SEO 分析
- 📈 市场研究

## ⚠️ 注意事项

1. **遵守 robots.txt**: 爬取前请检查目标网站的 robots.txt 文件
2. **控制频率**: 设置合理的请求间隔，避免对目标服务器造成压力
3. **合法合规**: 仅爬取公开数据，遵守相关法律法规
4. **版权尊重**: 不要滥用爬取的数据

## 🛠️ 技术栈

- **Python 3.8+**
- **requests**: HTTP 请求
- **BeautifulSoup4**: HTML 解析
- **pandas**: 数据处理
- **streamlit**: Web 界面
- **pytest**: 单元测试

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📧 联系方式

如有问题或建议，请提交 Issue。

---

**Made with ❤️ by Smart Web Scraper Team**
