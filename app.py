from flask import Flask, render_template, request, jsonify, flash
import requests
from bs4 import BeautifulSoup
import re
import time
import random
import logging
import os

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this in production

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdvancedFBScraper:
    def __init__(self):
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        }
        self.session.headers.update(self.headers)
    
    def get_public_page(self, page_name):
        """Get public page content"""
        # Clean the page name
        page_name = page_name.strip().replace('https://facebook.com/', '').replace('https://www.facebook.com/', '')
        url = f"https://www.facebook.com/{page_name}"
        
        logger.info(f"Attempting to scrape: {url}")
        
        try:
            # Add random delay to be respectful
            time.sleep(random.uniform(2, 4))
            
            response = self.session.get(url, timeout=15)
            logger.info(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                return self.parse_page_content(response.text, page_name)
            else:
                return {
                    'error': f'Failed to fetch page. Status code: {response.status_code}',
                    'page_name': page_name,
                    'url': url
                }
                
        except requests.exceptions.Timeout:
            return {'error': 'Request timed out. Please try again.'}
        except requests.exceptions.ConnectionError:
            return {'error': 'Connection error. Please check your internet connection.'}
        except Exception as e:
            logger.error(f"Error scraping {page_name}: {str(e)}")
            return {'error': f'An error occurred: {str(e)}'}
    
    def parse_page_content(self, html, page_name):
        """Parse HTML content for data"""
        soup = BeautifulSoup(html, 'html.parser')
        
        data = {
            'page_name': page_name,
            'page_title': '',
            'description': '',
            'basic_info': [],
            'found_elements': [],
            'url': f'https://www.facebook.com/{page_name}',
            'success': True
        }
        
        # Extract page title
        title_tag = soup.find('title')
        if title_tag:
            data['page_title'] = title_tag.text.strip()
        
        # Look for meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if not meta_desc:
            meta_desc = soup.find('meta', attrs={'property': 'og:description'})
        if meta_desc:
            data['description'] = meta_desc.get('content', '').strip()
        
        # Extract various page elements
        elements_found = []
        
        # Common Facebook selectors
        selectors = [
            'div[data-pagelet]',
            'div[role="article"]',
            'div[data-testid]',
            'h1',
            'h2',
            'h3',
            '.bi',
            '.bj',
            '[class*="profile"]',
            '[class*="page"]',
            '[class*="content"]'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            for element in elements[:5]:  # Limit to first 5 of each type
                text = element.get_text(strip=True)
                if text and len(text) > 5 and len(text) < 500:
                    element_data = {
                        'selector': selector,
                        'text': text,
                        'attrs': dict(element.attrs)
                    }
                    elements_found.append(element_data)
        
        data['found_elements'] = elements_found[:20]  # Limit total elements
        
        # Extract links
        links = []
        for link in soup.find_all('a', href=True)[:10]:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            if text and href and not href.startswith('javascript:'):
                links.append({'text': text, 'href': href})
        
        data['links'] = links
        
        return data

# Initialize scraper
scraper = AdvancedFBScraper()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scrape', methods=['POST'])
def scrape_facebook():
    page_name = request.form.get('page_name', '').strip()
    
    if not page_name:
        flash('Please enter a Facebook page name', 'error')
        return render_template('index.html')
    
    # Validate input
    if len(page_name) > 100:
        flash('Page name is too long', 'error')
        return render_template('index.html')
    
    # Check for dangerous characters
    if any(char in page_name for char in ['<', '>', '"', "'", '&', '%']):
        flash('Invalid characters in page name', 'error')
        return render_template('index.html')
    
    logger.info(f"Scraping request for: {page_name}")
    
    try:
        data = scraper.get_public_page(page_name)
        
        if 'error' in data:
            flash(data['error'], 'error')
            return render_template('index.html')
        
        return render_template('results.html', data=data)
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        flash('An unexpected error occurred. Please try again.', 'error')
        return render_template('index.html')

@app.route('/api/scrape/<page_name>')
def api_scrape(page_name):
    """API endpoint for JSON responses"""
    if not page_name or len(page_name) > 100:
        return jsonify({'error': 'Invalid page name'}), 400
    
    data = scraper.get_public_page(page_name)
    return jsonify(data)

@app.errorhandler(404)
def not_found(error):
    return render_template('index.html', error='Page not found'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('index.html', error='Internal server error'), 500

if __name__ == '__main__':
    # Get port from environment variable or default to 5000
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)