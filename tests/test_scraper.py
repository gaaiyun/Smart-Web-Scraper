"""
智能网页爬虫单元测试
Unit Tests for Smart Web Scraper
"""

import pytest
import json
import os
from pathlib import Path

# 导入被测试模块
from scraper import SmartScraper


class TestSmartScraperInit:
    """测试初始化"""
    
    def test_default_headers(self):
        """测试默认请求头"""
        scraper = SmartScraper()
        assert 'User-Agent' in scraper.headers
        assert 'Mozilla' in scraper.headers['User-Agent']
    
    def test_custom_headers(self):
        """测试自定义请求头"""
        custom_headers = {'User-Agent': 'CustomBot/1.0'}
        scraper = SmartScraper(headers=custom_headers)
        assert scraper.headers['User-Agent'] == 'CustomBot/1.0'
    
    def test_session_created(self):
        """测试 session 对象创建"""
        scraper = SmartScraper()
        assert scraper.session is not None


class TestSmartScraperExtraction:
    """测试数据提取功能"""
    
    @pytest.fixture
    def scraper(self):
        return SmartScraper()
    
    @pytest.fixture
    def sample_html(self):
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>测试页面</title>
            <meta name="description" content="这是一个测试页面">
            <meta name="keywords" content="测试，示例">
            <meta property="og:title" content="OG 测试标题">
        </head>
        <body>
            <h1>主要内容</h1>
            <p>这是一个段落。</p>
            <script>alert('不应该被提取');</script>
            <style>.hidden { display: none; }</style>
            <a href="https://example.com">链接 1</a>
            <a href="/relative">链接 2</a>
            <img src="image.jpg" alt="测试图片">
            <img src="https://example.com/photo.png" alt="另一张图片">
            <table>
                <tr><th>列 1</th><th>列 2</th></tr>
                <tr><td>值 1</td><td>值 2</td></tr>
            </table>
        </body>
        </html>
        """
    
    def test_extract_text(self, scraper, sample_html):
        """测试文本提取"""
        text = scraper.extract_text(sample_html)
        assert '主要内容' in text
        assert '这是一个段落' in text
        assert 'alert' not in text  # 脚本不应被提取
        assert '.hidden' not in text  # 样式不应被提取
    
    def test_extract_links(self, scraper, sample_html):
        """测试链接提取"""
        links = scraper.extract_links(sample_html, 'https://base.com')
        assert len(links) == 2
        assert links[0]['url'] == 'https://example.com'
        assert links[0]['text'] == '链接 1'
        assert links[1]['url'] == 'https://base.com/relative'
    
    def test_extract_images(self, scraper, sample_html):
        """测试图片提取"""
        images = scraper.extract_images(sample_html, 'https://base.com')
        assert len(images) == 2
        assert images[0]['alt'] == '测试图片'
        assert 'image.jpg' in images[0]['src']
        assert images[1]['src'] == 'https://example.com/photo.png'
    
    def test_extract_metadata(self, scraper, sample_html):
        """测试元数据提取"""
        metadata = scraper.extract_metadata(sample_html, 'https://example.com')
        assert metadata['title'] == '测试页面'
        assert metadata['description'] == '这是一个测试页面'
        assert metadata['keywords'] == '测试，示例'
        assert metadata['og_title'] == 'OG 测试标题'
    
    def test_extract_tables(self, scraper, sample_html):
        """测试表格提取"""
        tables = scraper.extract_tables(sample_html)
        assert len(tables) == 1
        assert len(tables[0]) == 1  # 一行数据
        assert '列 1' in tables[0].columns
        assert '列 2' in tables[0].columns


class TestSmartScraperScrape:
    """测试爬取功能"""
    
    @pytest.fixture
    def scraper(self):
        return SmartScraper()
    
    def test_scrape_single_mock(self, scraper, monkeypatch):
        """测试单页爬取（模拟）"""
        mock_html = """
        <html><head><title>Mock Page</title></head>
        <body><p>Content</p></body></html>
        """
        
        def mock_fetch(url, timeout=10):
            return mock_html
        
        monkeypatch.setattr(scraper, 'fetch_page', mock_fetch)
        
        result = scraper.scrape_single('https://example.com')
        assert result['url'] == 'https://example.com'
        assert result['metadata']['title'] == 'Mock Page'
        assert 'Content' in result['text']
        assert 'error' not in result
    
    def test_scrape_single_failure(self, scraper, monkeypatch):
        """测试爬取失败处理"""
        def mock_fetch(url, timeout=10):
            return None
        
        monkeypatch.setattr(scraper, 'fetch_page', mock_fetch)
        
        result = scraper.scrape_single('https://invalid.com')
        assert 'error' in result
    
    def test_scrape_batch(self, scraper, monkeypatch):
        """测试批量爬取"""
        mock_html = """
        <html><head><title>Page</title></head>
        <body><p>Content</p></body></html>
        """
        
        def mock_scrape_single(url):
            return {'url': url, 'metadata': {'title': 'Page'}}
        
        monkeypatch.setattr(scraper, 'scrape_single', mock_scrape_single)
        
        urls = ['https://url1.com', 'https://url2.com', 'https://url3.com']
        results = scraper.scrape_batch(urls, delay=0)
        
        assert len(results) == 3
        assert all('url' in r for r in results)


class TestSmartScraperExport:
    """测试导出功能"""
    
    @pytest.fixture
    def scraper(self):
        return SmartScraper()
    
    @pytest.fixture
    def sample_data(self):
        return {
            'url': 'https://example.com',
            'metadata': {'title': 'Test Page', 'description': 'Test Desc'},
            'text': 'Sample text content',
            'links': [{'text': 'Link', 'url': 'https://link.com'}],
            'images': [{'src': 'https://img.com/pic.jpg', 'alt': 'Image'}],
            'tables': []
        }
    
    @pytest.fixture
    def temp_dir(self, tmp_path):
        return tmp_path
    
    def test_export_json(self, scraper, sample_data, temp_dir):
        """测试 JSON 导出"""
        filename = temp_dir / "test.json"
        success = scraper.export_to_json(sample_data, str(filename))
        
        assert success is True
        assert filename.exists()
        
        with open(filename, 'r', encoding='utf-8') as f:
            loaded = json.load(f)
        
        assert loaded['url'] == sample_data['url']
        assert loaded['metadata']['title'] == sample_data['metadata']['title']
    
    def test_export_csv(self, scraper, temp_dir):
        """测试 CSV 导出"""
        data = [
            {'url': 'https://url1.com', 'title': 'Page 1', 'text_length': 100},
            {'url': 'https://url2.com', 'title': 'Page 2', 'text_length': 200}
        ]
        
        filename = temp_dir / "test.csv"
        success = scraper.export_to_csv(data, str(filename))
        
        assert success is True
        assert filename.exists()
    
    def test_export_markdown(self, scraper, sample_data, temp_dir):
        """测试 Markdown 导出"""
        filename = temp_dir / "test.md"
        success = scraper.export_to_markdown(sample_data, str(filename))
        
        assert success is True
        assert filename.exists()
        
        content = filename.read_text(encoding='utf-8')
        assert '# Test Page' in content
        assert 'https://example.com' in content
        assert 'Sample text content' in content


class TestSmartScraperSitemap:
    """测试站点地图功能"""
    
    @pytest.fixture
    def scraper(self):
        return SmartScraper()
    
    def test_extract_urls_from_xml_sitemap(self, scraper, monkeypatch):
        """测试从 XML 站点地图提取 URL"""
        xml_sitemap = """
        <?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url><loc>https://example.com/page1</loc></url>
            <url><loc>https://example.com/page2</loc></url>
            <url><loc>https://example.com/page3</loc></url>
        </urlset>
        """
        
        def mock_fetch(url, timeout=10):
            return xml_sitemap
        
        monkeypatch.setattr(scraper, 'fetch_page', mock_fetch)
        
        urls = scraper.extract_urls_from_sitemap('https://example.com/sitemap.xml')
        assert len(urls) == 3
        assert 'https://example.com/page1' in urls
        assert 'https://example.com/page2' in urls
        assert 'https://example.com/page3' in urls
    
    def test_extract_urls_from_html_sitemap(self, scraper, monkeypatch):
        """测试从 HTML 站点地图提取 URL"""
        html_sitemap = """
        <html><body>
            <a href="https://example.com/page1">Page 1</a>
            <a href="https://example.com/page2">Page 2</a>
        </body></html>
        """
        
        def mock_fetch(url, timeout=10):
            return html_sitemap
        
        monkeypatch.setattr(scraper, 'fetch_page', mock_fetch)
        
        urls = scraper.extract_urls_from_sitemap('https://example.com/sitemap.html')
        assert len(urls) == 2


class TestSmartScraperEdgeCases:
    """测试边界情况"""
    
    @pytest.fixture
    def scraper(self):
        return SmartScraper()
    
    def test_empty_html(self, scraper):
        """测试空 HTML"""
        text = scraper.extract_text('')
        assert text == ''
    
    def test_no_metadata(self, scraper):
        """测试没有元数据的页面"""
        html = "<html><body><p>Content</p></body></html>"
        metadata = scraper.extract_metadata(html, 'https://example.com')
        assert metadata['title'] == ''
        assert metadata['description'] == ''
    
    def test_malformed_links(self, scraper):
        """测试格式错误的链接"""
        html = """
        <a href="">空链接</a>
        <a href="javascript:void(0)">JS 链接</a>
        <a href="mailto:test@example.com">邮件链接</a>
        <a href="tel:+1234567890">电话链接</a>
        <a href="#section">锚点链接</a>
        <a href="https://valid.com">有效链接</a>
        """
        links = scraper.extract_links(html, 'https://base.com')
        assert len(links) == 1
        assert links[0]['url'] == 'https://valid.com'
    
    def test_export_empty_data(self, scraper, tmp_path):
        """测试导出空数据"""
        filename = tmp_path / "empty.json"
        success = scraper.export_to_json([], str(filename))
        assert success is True


class TestSmartScraperIntegration:
    """集成测试"""
    
    @pytest.fixture
    def scraper(self):
        return SmartScraper()
    
    def test_full_scrape_workflow(self, scraper, monkeypatch, tmp_path):
        """测试完整爬取工作流"""
        # 模拟爬取
        mock_result = {
            'url': 'https://example.com',
            'metadata': {'title': 'Example', 'description': 'Example Site'},
            'text': 'Example content text',
            'links': [{'text': 'Link', 'url': 'https://link.com'}],
            'images': [{'src': 'https://img.com/pic.jpg', 'alt': 'Pic'}],
            'tables': []
        }
        
        def mock_scrape_single(url):
            return mock_result
        
        monkeypatch.setattr(scraper, 'scrape_single', mock_scrape_single)
        
        # 爬取
        result = scraper.scrape_single('https://example.com')
        assert result['url'] == 'https://example.com'
        
        # 导出 JSON
        json_file = tmp_path / "result.json"
        scraper.export_to_json([result], str(json_file))
        assert json_file.exists()
        
        # 导出 CSV
        csv_data = [{'url': result['url'], 'title': result['metadata']['title']}]
        csv_file = tmp_path / "result.csv"
        scraper.export_to_csv(csv_data, str(csv_file))
        assert csv_file.exists()
        
        # 导出 Markdown
        md_file = tmp_path / "result.md"
        scraper.export_to_markdown(result, str(md_file))
        assert md_file.exists()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
