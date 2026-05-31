"""
智能网页爬虫核心模块
Smart Web Scraper Core Module
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import io
import json
import re
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Optional, Any
import time


class SmartScraper:
    """智能网页爬虫类"""
    
    def __init__(self, headers: Optional[Dict] = None):
        """
        初始化爬虫
        
        Args:
            headers: 自定义请求头
        """
        self.headers = headers or {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
    def fetch_page(self, url: str, timeout: int = 10, verify_ssl: bool = True) -> Optional[str]:
        """
        获取网页内容
        
        Args:
            url: 目标 URL
            timeout: 超时时间（秒）
            verify_ssl: 是否验证 SSL 证书
            
        Returns:
            网页 HTML 内容，失败返回 None
        """
        try:
            response = self.session.get(url, timeout=timeout, verify=verify_ssl)
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            return response.text
        except Exception as e:
            print(f"获取网页失败 {url}: {str(e)}")
            return None
    
    def extract_text(self, html: str) -> str:
        """
        提取网页文本内容
        
        Args:
            html: 网页 HTML
            
        Returns:
            纯文本内容
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # 移除脚本和样式
        for tag in soup(['script', 'style', 'meta', 'link']):
            tag.decompose()
        
        # 获取文本
        text = soup.get_text(separator='\n', strip=True)
        
        # 清理多余空白
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return '\n'.join(lines)
    
    def extract_links(self, html: str, base_url: str) -> List[Dict[str, str]]:
        """
        提取网页链接
        
        Args:
            html: 网页 HTML
            base_url: 基础 URL
            
        Returns:
            链接列表 [{'text': '链接文本', 'url': '完整 URL'}]
        """
        soup = BeautifulSoup(html, 'html.parser')
        links = []
        
        for tag in soup.find_all('a', href=True):
            href = tag.get('href', '').strip()
            if href and not href.startswith(('javascript:', 'mailto:', 'tel:', '#')):
                full_url = urljoin(base_url, href)
                links.append({
                    'text': tag.get_text(strip=True),
                    'url': full_url
                })
        
        return links
    
    def extract_images(self, html: str, base_url: str) -> List[Dict[str, str]]:
        """
        提取图片链接
        
        Args:
            html: 网页 HTML
            base_url: 基础 URL
            
        Returns:
            图片列表 [{'src': '图片 URL', 'alt': '替代文本'}]
        """
        soup = BeautifulSoup(html, 'html.parser')
        images = []
        
        for tag in soup.find_all('img'):
            src = tag.get('src', '').strip()
            if src:
                full_url = urljoin(base_url, src)
                images.append({
                    'src': full_url,
                    'alt': tag.get('alt', '')
                })
        
        return images
    
    def extract_tables(self, html: str) -> List[pd.DataFrame]:
        """
        提取网页表格
        
        Args:
            html: 网页 HTML
            
        Returns:
            DataFrame 列表
        """
        soup = BeautifulSoup(html, 'html.parser')
        tables = []
        
        for table_tag in soup.find_all('table'):
            try:
                df = pd.read_html(io.StringIO(str(table_tag)))[0]
                tables.append(df)
            except (ValueError, ImportError):
                continue
        
        return tables
    
    def extract_metadata(self, html: str, url: str) -> Dict[str, Any]:
        """
        提取网页元数据
        
        Args:
            html: 网页 HTML
            url: 网页 URL
            
        Returns:
            元数据字典
        """
        soup = BeautifulSoup(html, 'html.parser')
        metadata = {
            'url': url,
            'title': '',
            'description': '',
            'keywords': '',
            'author': '',
            'og_title': '',
            'og_description': '',
            'og_image': ''
        }
        
        # 标题
        title_tag = soup.find('title')
        if title_tag:
            metadata['title'] = title_tag.get_text(strip=True)
        
        # Meta 标签
        meta_tags = soup.find_all('meta')
        for tag in meta_tags:
            name = tag.get('name', '').lower()
            content = tag.get('content', '')
            prop = tag.get('property', '').lower()
            
            if name == 'description':
                metadata['description'] = content
            elif name == 'keywords':
                metadata['keywords'] = content
            elif name == 'author':
                metadata['author'] = content
            elif prop == 'og:title':
                metadata['og_title'] = content
            elif prop == 'og:description':
                metadata['og_description'] = content
            elif prop == 'og:image':
                metadata['og_image'] = content
        
        return metadata
    
    def scrape_single(self, url: str) -> Dict[str, Any]:
        """
        爬取单个网页
        
        Args:
            url: 目标 URL
            
        Returns:
            包含所有提取数据的字典
        """
        html = self.fetch_page(url)
        if not html:
            return {'error': f'无法获取网页：{url}'}
        
        result = {
            'url': url,
            'metadata': self.extract_metadata(html, url),
            'text': self.extract_text(html),
            'links': self.extract_links(html, url),
            'images': self.extract_images(html, url),
            'tables': []
        }
        
        # 提取表格
        tables = self.extract_tables(html)
        result['tables'] = [df.to_dict('records') for df in tables]
        
        return result
    
    def scrape_batch(self, urls: List[str], delay: float = 1.0) -> List[Dict[str, Any]]:
        """
        批量爬取多个 URL
        
        Args:
            urls: URL 列表
            delay: 请求间隔（秒）
            
        Returns:
            结果列表
        """
        results = []
        total = len(urls)
        
        for i, url in enumerate(urls, 1):
            print(f"进度：{i}/{total} - {url}")
            result = self.scrape_single(url)
            results.append(result)
            
            if i < total and delay > 0:
                time.sleep(delay)
        
        return results
    
    def extract_urls_from_sitemap(self, sitemap_url: str) -> List[str]:
        """
        从站点地图提取 URL
        
        Args:
            sitemap_url: 站点地图 URL
            
        Returns:
            URL 列表
        """
        html = self.fetch_page(sitemap_url)
        if not html:
            return []
        
        urls = []
        
        # 尝试解析 XML 站点地图
        if '<?xml' in html or '<urlset' in html:
            soup = BeautifulSoup(html, 'xml')
            for loc in soup.find_all('loc'):
                if loc.get_text():
                    urls.append(loc.get_text(strip=True))
        
        # 如果是 HTML 站点地图
        if not urls:
            soup = BeautifulSoup(html, 'html.parser')
            for tag in soup.find_all('a', href=True):
                href = tag.get('href', '').strip()
                if href and href.startswith('http'):
                    urls.append(href)
        
        return urls
    
    def scrape_sitemap(self, sitemap_url: str, delay: float = 1.0) -> List[Dict[str, Any]]:
        """
        爬取站点地图中的所有页面
        
        Args:
            sitemap_url: 站点地图 URL
            delay: 请求间隔（秒）
            
        Returns:
            结果列表
        """
        urls = self.extract_urls_from_sitemap(sitemap_url)
        print(f"从站点地图找到 {len(urls)} 个 URL")
        return self.scrape_batch(urls, delay)
    
    def export_to_json(self, data: Any, filename: str, indent: int = 2) -> bool:
        """
        导出为 JSON
        
        Args:
            data: 数据
            filename: 文件名
            indent: 缩进
            
        Returns:
            是否成功
        """
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=indent)
            return True
        except Exception as e:
            print(f"导出 JSON 失败：{str(e)}")
            return False
    
    def export_to_csv(self, data: List[Dict], filename: str) -> bool:
        """
        导出为 CSV
        
        Args:
            data: 数据列表
            filename: 文件名
            
        Returns:
            是否成功
        """
        try:
            df = pd.DataFrame(data)
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            return True
        except Exception as e:
            print(f"导出 CSV 失败：{str(e)}")
            return False
    
    def export_to_markdown(self, data: Dict, filename: str) -> bool:
        """
        导出为 Markdown
        
        Args:
            data: 数据字典
            filename: 文件名
            
        Returns:
            是否成功
        """
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"# {data.get('metadata', {}).get('title', '网页内容')}\n\n")
                f.write(f"**URL**: {data.get('url', 'N/A')}\n\n")
                
                if data.get('metadata', {}).get('description'):
                    f.write(f"**描述**: {data['metadata']['description']}\n\n")
                
                f.write("## 内容\n\n")
                f.write(data.get('text', '') + '\n\n')
                
                if data.get('images'):
                    f.write("## 图片\n\n")
                    for img in data['images']:
                        f.write(f"- ![{img.get('alt', '')}]({img.get('src', '')})\n")
                    f.write("\n")
                
                if data.get('links'):
                    f.write("## 链接\n\n")
                    for link in data['links']:
                        f.write(f"- [{link.get('text', link.get('url'))}]({link.get('url', '')})\n")
            
            return True
        except Exception as e:
            print(f"导出 Markdown 失败：{str(e)}")
            return False


if __name__ == "__main__":
    # 测试示例
    scraper = SmartScraper()
    
    # 测试单个网页
    print("测试单个网页爬取...")
    result = scraper.scrape_single("https://www.example.com")
    print(f"标题：{result['metadata']['title']}")
    print(f"文本长度：{len(result['text'])}")
    print(f"链接数：{len(result['links'])}")
    print(f"图片数：{len(result['images'])}")
