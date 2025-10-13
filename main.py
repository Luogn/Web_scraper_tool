import requests
from bs4 import BeautifulSoup
import csv
import time
from datetime import datetime
import json
import os
from urllib.parse import urljoin

class VnExpressScraper:
    def __init__(self):
        self.base_url = "https://vnexpress.net/khoa-hoc"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.articles = []
    
    def get_article_links(self, page=1):
        """Lấy danh sách link bài viết từ trang chủ mục"""
        try:
            url = f"{self.base_url}-p{page}" if page > 1 else self.base_url
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            articles = soup.find_all('article', class_='item-news')
            
            links = []
            for article in articles:
                link_tag = article.find('a', href=True)
                if link_tag:
                    links.append(link_tag['href'])
            
            return links
        except Exception as e:
            print(f"Lỗi khi lấy links từ trang {page}: {e}")
            return []
    
    def scrape_article_full_content(self, url):
        """Thu thập thông tin chi tiết từ một bài báo (nội dung đầy đủ)"""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 1. Lấy tiêu đề chính
            title_tag = soup.find('h1', class_='title-detail')
            title = title_tag.get_text(strip=True) if title_tag else "N/A"
            
            # 2. Lấy mô tả/sapo
            desc_tag = soup.find('p', class_='description')
            description = desc_tag.get_text(strip=True) if desc_tag else "N/A"
            
            # 3. Lấy NỘI DUNG ĐẦY ĐỦ
            content = self.extract_full_content(soup)
            
            # 4. Lấy tác giả
            author = self.extract_author(soup)
            
            # 5. Lấy thời gian xuất bản
            pub_date = self.extract_publish_date(soup)
            
            # 6. Lấy danh mục
            category = self.extract_category(soup)
            
            # 7. Lấy hình ảnh (nếu có)
            images = self.extract_images(soup, url)
            
            # 8. Lấy tags
            tags = self.extract_tags(soup)
            
            # 9. Lấy số lượt xem, bình luận (nếu có)
            stats = self.extract_stats(soup)
            
            return {
                'url': url,
                'title': title,
                'description': description,
                'full_content': content,  # Nội dung đầy đủ
                'content_length': len(content),
                'author': author,
                'published_date': pub_date,
                'category': category,
                'images': images,
                'tags': tags,
                'views': stats.get('views', 'N/A'),
                'comments': stats.get('comments', 'N/A'),
                'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            print(f"Lỗi khi scrape {url}: {e}")
            return None
    
    def extract_full_content(self, soup):
        """Trích xuất nội dung bài báo đầy đủ"""
        content_parts = []
        
        # Tìm phần nội dung chính
        article_body = soup.find('article', class_='fck_detail')
        
        if article_body:
            # Lấy tất cả các đoạn văn
            paragraphs = article_body.find_all(['p', 'h2', 'h3', 'blockquote'])
            
            for para in paragraphs:
                text = para.get_text(strip=True)
                if text:  # Bỏ qua các đoạn trống
                    content_parts.append(text)
        
        # Nếu không tìm thấy, thử cách khác
        if not content_parts:
            article = soup.find('article')
            if article:
                paragraphs = article.find_all('p')
                for para in paragraphs:
                    text = para.get_text(strip=True)
                    if text and len(text) > 20:
                        content_parts.append(text)
        
        # Ghép nội dung lại
        full_content = '\n\n'.join(content_parts)
        return full_content if full_content else "N/A"
    
    def extract_author(self, soup):
        """Trích xuất thông tin tác giả"""
        # Cách 1: Tìm trong tag author
        author_tag = soup.find('p', class_='author_mail')
        if author_tag:
            return author_tag.get_text(strip=True)
        
        # Cách 2: Tìm trong meta
        meta_author = soup.find('meta', {'name': 'author'})
        if meta_author:
            return meta_author.get('content', 'N/A')
        
        return "N/A"
    
    def extract_publish_date(self, soup):
        """Trích xuất ngày xuất bản"""
        # Cách 1: Tìm trong span date
        time_tag = soup.find('span', class_='date')
        if time_tag:
            return time_tag.get_text(strip=True)
        
        # Cách 2: Tìm trong meta
        meta_date = soup.find('meta', {'property': 'article:published_time'})
        if meta_date:
            return meta_date.get('content', 'N/A')
        
        return "N/A"
    
    def extract_category(self, soup):
        """Trích xuất danh mục"""
        breadcrumb = soup.find('ul', class_='breadcrumb')
        if breadcrumb:
            cats = breadcrumb.find_all('li')
            if len(cats) > 1:
                return cats[1].get_text(strip=True)
        
        return "N/A"
    
    def extract_images(self, soup, base_url):
        """Trích xuất các hình ảnh trong bài"""
        images = []
        
        # Tìm tất cả hình ảnh
        img_tags = soup.find_all('img')
        
        for img in img_tags[:5]:  # Giới hạn 5 hình ảnh
            src = img.get('src', '')
            alt = img.get('alt', 'No description')
            
            if src:
                # Nếu là URL tương đối, chuyển thành URL tuyệt đối
                if not src.startswith('http'):
                    src = urljoin(base_url, src)
                
                images.append({
                    'src': src,
                    'alt': alt
                })
        
        return images
    
    def extract_tags(self, soup):
        """Trích xuất tags/keywords"""
        tags = []
        
        # Tìm các tag
        tag_elements = soup.find_all('a', class_='tag')
        
        for tag in tag_elements[:10]:  # Giới hạn 10 tags
            tag_text = tag.get_text(strip=True)
            if tag_text:
                tags.append(tag_text)
        
        return tags if tags else []
    
    def extract_stats(self, soup):
        """Trích xuất thống kê (lượt xem, bình luận)"""
        stats = {'views': 'N/A', 'comments': 'N/A'}
        
        # Tìm số lượt xem
        view_tag = soup.find('span', class_='view')
        if view_tag:
            stats['views'] = view_tag.get_text(strip=True)
        
        # Tìm số bình luận
        comment_tag = soup.find('span', class_='comment')
        if comment_tag:
            stats['comments'] = comment_tag.get_text(strip=True)
        
        return stats
    
    def scrape_multiple_articles(self, num_articles=100):
        """Thu thập nhiều bài viết"""
        print(f"Bắt đầu thu thập {num_articles} bài viết...")
        
        page = 1
        collected = 0
        
        while collected < num_articles:
            print(f"\n{'='*60}")
            print(f"Đang xử lý trang {page}...")
            print(f"{'='*60}")
            links = self.get_article_links(page)
            
            if not links:
                print("Không tìm thấy thêm bài viết.")
                break
            
            for idx, link in enumerate(links, 1):
                if collected >= num_articles:
                    break
                
                print(f"\n[{collected + 1}/{num_articles}] Thu thập: {link[:80]}...")
                article_data = self.scrape_article_full_content(link)
                
                if article_data:
                    self.articles.append(article_data)
                    collected += 1
                    print(f"✓ Thành công! Nội dung: {article_data['content_length']} ký tự")
                
                # Nghỉ giữa các request để tránh bị chặn
                time.sleep(1)
            
            page += 1
            time.sleep(2)  # Nghỉ lâu hơn giữa các trang
        
        print(f"\n{'='*60}")
        print(f"✓ Hoàn thành! Đã thu thập {len(self.articles)} bài viết.")
        print(f"{'='*60}")
        return self.articles
    
    def save_to_csv(self, filename='vnexpress_articles.csv'):
        """Lưu dữ liệu vào file CSV"""
        if not self.articles:
            print("Không có dữ liệu để lưu.")
            return
        
        # Tạo thư mục data nếu chưa tồn tại
        os.makedirs('data', exist_ok=True)
        filepath = os.path.join('data', filename)
        
        # Lưu CSV với các trường chính (không lưu hình ảnh/tags để CSV sạch)
        keys = ['url', 'title', 'description', 'author', 'published_date', 
                'category', 'content_length', 'views', 'comments', 'scraped_at']
        
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            
            for article in self.articles:
                row = {k: article.get(k, 'N/A') for k in keys}
                writer.writerow(row)
        
        print(f"✓ Đã lưu dữ liệu vào {filepath}")
    
    def save_to_json(self, filename='vnexpress_articles.json'):
        """Lưu dữ liệu vào file JSON (đầy đủ)"""
        if not self.articles:
            print("Không có dữ liệu để lưu.")
            return
        
        # Tạo thư mục data nếu chưa tồn tại
        os.makedirs('data', exist_ok=True)
        filepath = os.path.join('data', filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.articles, f, ensure_ascii=False, indent=2)
        
        print(f"✓ Đã lưu dữ liệu vào {filepath}")
    
    def save_full_content_to_txt(self, filename='vnexpress_articles_full.txt'):
        """Lưu nội dung đầy đủ vào file text"""
        if not self.articles:
            print("Không có dữ liệu để lưu.")
            return
        
        # Tạo thư mục data nếu chưa tồn tại
        os.makedirs('data', exist_ok=True)
        filepath = os.path.join('data', filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            for idx, article in enumerate(self.articles, 1):
                f.write(f"\n{'='*80}\n")
                f.write(f"BÀI {idx}\n")
                f.write(f"{'='*80}\n\n")
                f.write(f"Tiêu đề: {article['title']}\n")
                f.write(f"URL: {article['url']}\n")
                f.write(f"Tác giả: {article['author']}\n")
                f.write(f"Ngày đăng: {article['published_date']}\n")
                f.write(f"Danh mục: {article['category']}\n")
                f.write(f"Tags: {', '.join(article['tags']) if article['tags'] else 'N/A'}\n")
                f.write(f"\n{'-'*80}\n")
                f.write(f"Mô tả:\n{article['description']}\n")
                f.write(f"\n{'-'*80}\n")
                f.write(f"Nội dung đầy đủ:\n{article['full_content']}\n")
                f.write(f"\n{'-'*80}\n")
                f.write(f"Lượt xem: {article['views']} | Bình luận: {article['comments']}\n")
        
        print(f"✓ Đã lưu nội dung đầy đủ vào {filepath}")
    
    def print_statistics(self):
        """In ra thống kê"""
        if not self.articles:
            print("Không có dữ liệu.")
            return
        
        total_content = sum(article['content_length'] for article in self.articles)
        avg_content = total_content / len(self.articles)
        
        print(f"\n{'='*60}")
        print(f"THỐNG KÊ DỰ ÁN")
        print(f"{'='*60}")
        print(f"Tổng số bài viết: {len(self.articles)}")
        print(f"Tổng ký tự nội dung: {total_content:,}")
        print(f"Trung bình ký tự/bài: {avg_content:,.0f}")
        print(f"Bài ngắn nhất: {min(a['content_length'] for a in self.articles)} ký tự")
        print(f"Bài dài nhất: {max(a['content_length'] for a in self.articles)} ký tự")
        print(f"\nBài viết đầu tiên:")
        print(f"  - {self.articles[0]['title']}")
        print(f"\nBài viết cuối cùng:")
        print(f"  - {self.articles[-1]['title']}")
        print(f"{'='*60}\n")


# Cách sử dụng
if __name__ == "__main__":
    # Khởi tạo scraper
    scraper = VnExpressScraper()
    
    # Thu thập 100 bài viết (có nội dung đầy đủ)
    articles = scraper.scrape_multiple_articles(num_articles=100)
    
    # Lưu vào các định dạng khác nhau
    scraper.save_to_csv('vnexpress_articles.csv')
    scraper.save_to_json('vnexpress_articles.json')
    scraper.save_full_content_to_txt('vnexpress_articles_full.txt')
    
    # In thống kê
    scraper.print_statistics()