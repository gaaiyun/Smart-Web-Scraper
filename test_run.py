"""
实际测试运行脚本
测试爬虫功能的实际运行
"""

from scraper import SmartScraper
import json

def test_single_page():
    """Test single page scraping"""
    print("=" * 60)
    print("Test 1: Single Page Scrape (https://example.com)")
    print("=" * 60)
    
    scraper = SmartScraper(timeout=10)
    result = scraper.scrape_single("https://example.com")
    
    print(f"\n[OK] URL: {result.url}")
    print(f"[OK] Title: {result.title}")
    print(f"[OK] Status Code: {result.status_code}")
    print(f"[OK] Description: {result.description}")
    print(f"[OK] Text Length: {len(result.text_content)} chars")
    print(f"[OK] Images: {len(result.images)}")
    print(f"[OK] Links: {len(result.links)}")
    print(f"[OK] Tables: {len(result.tables)}")
    
    if result.error:
        print(f"[ERROR] Error: {result.error}")
    
    return result

def test_batch_pages():
    """Test batch scraping"""
    print("\n" + "=" * 60)
    print("Test 2: Batch Scrape")
    print("=" * 60)
    
    urls = [
        "https://example.com",
        "https://example.org"
    ]
    
    scraper = SmartScraper(timeout=10)
    
    def progress_callback(current, total):
        print(f"Progress: {current}/{total} ({int(current/total*100)}%)")
    
    results = scraper.scrape_batch(urls, progress_callback)
    
    print(f"\n[OK] Successfully scraped {len(results)} pages")
    for i, result in enumerate(results, 1):
        status = "[OK]" if result.status_code == 200 else "[FAIL]"
        print(f"  {status} Page {i}: {result.url} - {result.title[:50] if result.title else 'N/A'}")
    
    return results

def test_export(results):
    """测试导出功能"""
    print("\n" + "=" * 60)
    print("测试 3: 导出功能")
    print("=" * 60)
    
    scraper = SmartScraper()
    
    # 导出 JSON
    json_file = "test_output.json"
    scraper.export_to_json(results, json_file)
    print(f"✅ JSON 导出：{json_file}")
    
    # 导出 CSV
    csv_file = "test_output.csv"
    scraper.export_to_csv(results, csv_file)
    print(f"✅ CSV 导出：{csv_file}")
    
    # 导出 Markdown
    md_file = "test_output.md"
    scraper.export_to_markdown(results, md_file)
    print(f"✅ Markdown 导出：{md_file}")

def test_sitemap():
    """测试站点地图解析"""
    print("\n" + "=" * 60)
    print("测试 4: 站点地图解析")
    print("=" * 60)
    
    scraper = SmartScraper(timeout=10)
    
    # 测试一个公开的 sitemap
    sitemap_url = "https://example.com/sitemap.xml"
    urls = scraper.extract_sitemap_urls(sitemap_url)
    
    if urls:
        print(f"✅ 从站点地图解析到 {len(urls)} 个 URL")
        for url in urls[:5]:
            print(f"  - {url}")
        if len(urls) > 5:
            print(f"  ... 还有 {len(urls) - 5} 个")
    else:
        print("ℹ️  该站点没有 sitemap 或无法访问")
    
    return urls

def main():
    """主测试函数"""
    print("\nSmart Web Scraper - Test Run")
    print("=" * 60)
    
    # 测试 1: 单页爬取
    single_result = test_single_page()
    
    # 测试 2: 批量爬取
    batch_results = test_batch_pages()
    
    # 测试 3: 导出功能
    test_export(batch_results)
    
    # 测试 4: 站点地图
    test_sitemap()
    
    print("\n" + "=" * 60)
    print("✅ 所有测试完成！")
    print("=" * 60)
    
    # 显示导出的文件
    print("\n📁 导出的文件:")
    import os
    for f in ["test_output.json", "test_output.csv", "test_output.md"]:
        if os.path.exists(f):
            size = os.path.getsize(f)
            print(f"  ✅ {f} ({size} 字节)")

if __name__ == "__main__":
    main()
