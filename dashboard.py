"""
智能网页爬虫 Streamlit Dashboard
Smart Web Scraper Streamlit Dashboard
"""

import streamlit as st
import pandas as pd
import json
from pathlib import Path
from datetime import datetime
import os

from scraper import SmartScraper

# 页面配置
st.set_page_config(
    page_title="智能网页爬虫",
    page_icon="🕷️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义 CSS 样式
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .result-box {
        background-color: #f5f5f5;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .progress-text {
        font-size: 1rem;
        color: #1E88E5;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """初始化会话状态"""
    if 'scraper' not in st.session_state:
        st.session_state.scraper = SmartScraper()
    if 'results' not in st.session_state:
        st.session_state.results = None
    if 'scrape_mode' not in st.session_state:
        st.session_state.scrape_mode = '单页爬取'
    if 'progress' not in st.session_state:
        st.session_state.progress = 0


def render_header():
    """渲染头部"""
    st.markdown('<p class="main-header">🕷️ 智能网页爬虫工具</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Smart Web Scraper - 单页爬取 | 批量爬取 | 站点地图爬取</p>', unsafe_allow_html=True)


def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        st.header("⚙️ 设置")
        
        # 爬取模式选择
        mode = st.radio(
            "爬取模式",
            ["单页爬取", "批量 URL 爬取", "站点地图爬取"],
            index=["单页爬取", "批量 URL 爬取", "站点地图爬取"].index(st.session_state.scrape_mode)
        )
        st.session_state.scrape_mode = mode
        
        st.divider()
        
        # 高级设置
        st.subheader("高级选项")
        delay = st.slider("请求间隔（秒）", 0.0, 5.0, 1.0, 0.1)
        timeout = st.number_input("超时时间（秒）", min_value=5, max_value=60, value=10)
        
        st.divider()
        
        # 导出选项
        st.subheader("📥 导出格式")
        export_json = st.checkbox("JSON", value=True)
        export_csv = st.checkbox("CSV", value=False)
        export_md = st.checkbox("Markdown", value=False)
        
        return {
            'mode': mode,
            'delay': delay,
            'timeout': timeout,
            'export_json': export_json,
            'export_csv': export_csv,
            'export_md': export_md
        }


def render_single_page_mode(settings):
    """渲染单页爬取模式"""
    st.header("📄 单页爬取")
    
    url = st.text_input(
        "输入网页 URL",
        placeholder="https://www.example.com",
        help="请输入完整的网页地址，包括 http:// 或 https://"
    )
    
    col1, col2 = st.columns([3, 1])
    with col1:
        start_btn = st.button("🚀 开始爬取", type="primary", use_container_width=True, disabled=not url)
    with col2:
        if st.session_state.results:
            if st.button("🗑️ 清除结果", use_container_width=True):
                st.session_state.results = None
                st.rerun()
    
    if start_btn and url:
        with st.spinner("正在爬取网页..."):
            try:
                result = st.session_state.scraper.scrape_single(url)
                st.session_state.results = [result]
                st.success("✅ 爬取成功！")
                st.rerun()
            except Exception as e:
                st.error(f"❌ 爬取失败：{str(e)}")


def render_batch_mode(settings):
    """渲染批量爬取模式"""
    st.header("📋 批量 URL 爬取")
    
    urls_text = st.text_area(
        "输入多个 URL（每行一个）",
        placeholder="https://www.example.com\nhttps://www.example.org\nhttps://www.example.net",
        height=150,
        help="每行输入一个完整的 URL 地址"
    )
    
    col1, col2 = st.columns([3, 1])
    with col1:
        start_btn = st.button("🚀 开始批量爬取", type="primary", use_container_width=True, disabled=not urls_text)
    with col2:
        if st.session_state.results:
            if st.button("🗑️ 清除结果", use_container_width=True):
                st.session_state.results = None
                st.rerun()
    
    if start_btn and urls_text:
        urls = [url.strip() for url in urls_text.split('\n') if url.strip()]
        if urls:
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            results = []
            total = len(urls)
            
            for i, url in enumerate(urls, 1):
                status_text.text(f"进度：{i}/{total} - {url}")
                try:
                    result = st.session_state.scraper.scrape_single(url)
                    results.append(result)
                    progress_bar.progress(i / total)
                except Exception as e:
                    results.append({'url': url, 'error': str(e)})
                
                if i < total and settings['delay'] > 0:
                    import time
                    time.sleep(settings['delay'])
            
            st.session_state.results = results
            status_text.text("✅ 批量爬取完成！")
            st.success(f"成功爬取 {len([r for r in results if 'error' not in r])}/{total} 个网页")
            st.rerun()


def render_sitemap_mode(settings):
    """渲染站点地图爬取模式"""
    st.header("🗺️ 站点地图爬取")
    
    sitemap_url = st.text_input(
        "输入站点地图 URL",
        placeholder="https://www.example.com/sitemap.xml",
        help="请输入站点地图的完整地址（XML 或 HTML 格式）"
    )
    
    st.info("💡 提示：站点地图通常位于 /sitemap.xml 或 /sitemap_index.xml")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        start_btn = st.button("🚀 开始爬取站点地图", type="primary", use_container_width=True, disabled=not sitemap_url)
    with col2:
        if st.session_state.results:
            if st.button("🗑️ 清除结果", use_container_width=True):
                st.session_state.results = None
                st.rerun()
    
    if start_btn and sitemap_url:
        with st.spinner("正在解析站点地图并爬取..."):
            try:
                results = st.session_state.scraper.scrape_sitemap(sitemap_url, delay=settings['delay'])
                st.session_state.results = results
                st.success(f"✅ 完成！共爬取 {len(results)} 个页面")
                st.rerun()
            except Exception as e:
                st.error(f"❌ 爬取失败：{str(e)}")


def render_results(settings):
    """渲染结果展示"""
    if not st.session_state.results:
        return
    
    st.divider()
    st.header("📊 爬取结果")
    
    results = st.session_state.results
    
    # 统计信息
    col1, col2, col3, col4 = st.columns(4)
    total_pages = len(results)
    successful = len([r for r in results if 'error' not in r])
    total_links = sum(len(r.get('links', [])) for r in results if 'error' not in r)
    total_images = sum(len(r.get('images', [])) for r in results if 'error' not in r)
    
    col1.metric("总页面数", total_pages)
    col2.metric("成功爬取", successful)
    col3.metric("提取链接", total_links)
    col4.metric("提取图片", total_images)
    
    st.divider()
    
    # 结果预览
    st.subheader("📑 结果预览")
    
    # 选项卡展示
    tabs = st.tabs(["📝 文本内容", "🔗 链接列表", "🖼️ 图片列表", "📊 表格数据", "📋 元数据", "📁 原始数据"])
    
    with tabs[0]:
        if results and 'text' in results[0]:
            for i, result in enumerate(results):
                if 'error' not in result:
                    with st.expander(f"页面 {i+1}: {result['metadata'].get('title', '无标题')[:50]}"):
                        st.text(result.get('text', '')[:2000] + "..." if len(result.get('text', '')) > 2000 else result.get('text', ''))
    
    with tabs[1]:
        all_links = []
        for result in results:
            if 'error' not in result and result.get('links'):
                for link in result['links']:
                    all_links.append({
                        '页面': result['metadata'].get('title', '')[:30],
                        '链接文本': link.get('text', ''),
                        'URL': link.get('url', '')
                    })
        if all_links:
            st.dataframe(pd.DataFrame(all_links), use_container_width=True)
        else:
            st.info("未找到链接")
    
    with tabs[2]:
        all_images = []
        for result in results:
            if 'error' not in result and result.get('images'):
                for img in result['images']:
                    all_images.append({
                        '页面': result['metadata'].get('title', '')[:30],
                        '替代文本': img.get('alt', ''),
                        '图片 URL': img.get('src', '')
                    })
        if all_images:
            st.dataframe(pd.DataFrame(all_images), use_container_width=True)
        else:
            st.info("未找到图片")
    
    with tabs[3]:
        has_tables = False
        for i, result in enumerate(results):
            if 'error' not in result and result.get('tables'):
                has_tables = True
                st.subheader(f"页面 {i+1} 的表格")
                for j, table in enumerate(result['tables']):
                    if table:
                        st.write(f"**表格 {j+1}**")
                        st.dataframe(pd.DataFrame(table), use_container_width=True)
        if not has_tables:
            st.info("未找到表格数据")
    
    with tabs[4]:
        for i, result in enumerate(results):
            if 'error' not in result:
                with st.expander(f"页面 {i+1}: {result['metadata'].get('title', '无标题')[:50]}"):
                    st.json(result.get('metadata', {}))
    
    with tabs[5]:
        st.json(results)
    
    # 导出功能
    st.divider()
    st.subheader("💾 导出数据")
    
    col1, col2, col3 = st.columns(3)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    with col1:
        if settings['export_json'] or st.button("导出 JSON", use_container_width=True):
            filename = output_dir / f"scrape_result_{timestamp}.json"
            st.session_state.scraper.export_to_json(results, str(filename))
            st.success(f"✅ JSON 已保存：{filename}")
    
    with col2:
        if settings['export_csv'] or st.button("导出 CSV", use_container_width=True):
            # 准备 CSV 数据
            csv_data = []
            for result in results:
                if 'error' not in result:
                    csv_data.append({
                        'url': result.get('url', ''),
                        'title': result['metadata'].get('title', ''),
                        'description': result['metadata'].get('description', ''),
                        'text_length': len(result.get('text', '')),
                        'links_count': len(result.get('links', [])),
                        'images_count': len(result.get('images', []))
                    })
            
            if csv_data:
                filename = output_dir / f"scrape_result_{timestamp}.csv"
                st.session_state.scraper.export_to_csv(csv_data, str(filename))
                st.success(f"✅ CSV 已保存：{filename}")
    
    with col3:
        if settings['export_md'] or st.button("导出 Markdown", use_container_width=True):
            for i, result in enumerate(results):
                if 'error' not in result:
                    filename = output_dir / f"page_{i+1}_{timestamp}.md"
                    st.session_state.scraper.export_to_markdown(result, str(filename))
            st.success(f"✅ Markdown 已保存到 output/ 目录")


def main():
    """主函数"""
    init_session_state()
    render_header()
    settings = render_sidebar()
    
    # 根据模式渲染不同界面
    if settings['mode'] == "单页爬取":
        render_single_page_mode(settings)
    elif settings['mode'] == "批量 URL 爬取":
        render_batch_mode(settings)
    elif settings['mode'] == "站点地图爬取":
        render_sitemap_mode(settings)
    
    # 渲染结果
    render_results(settings)
    
    # 页脚
    st.divider()
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 1rem;'>
        <p>🕷️ 智能网页爬虫工具 v1.0 | Powered by Streamlit + BeautifulSoup</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
