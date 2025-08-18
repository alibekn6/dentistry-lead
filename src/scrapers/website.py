"""Website scraper for extracting email addresses from dental clinic websites."""

import re
import logging
import time
from typing import List, Set, Optional
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Common email patterns
EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')

# URLs to check for contact info
CONTACT_PATHS = [
    '/contact',
    '/contact-us', 
    '/about',
    '/about-us',
    '/team',
    '/staff',
    '/enquiries',
    '/booking',
    '/appointments'
]

# Common email prefixes for dental clinics
COMMON_EMAIL_PREFIXES = [
    'info',
    'contact', 
    'hello',
    'enquiries',
    'appointments',
    'reception',
    'admin',
    'office'
]


def get_domain_from_url(url: str) -> Optional[str]:
    """Extract domain from URL."""
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower().replace('www.', '')
    except:
        return None


def generate_common_emails(domain: str) -> List[str]:
    """Generate common email patterns for a domain."""
    emails = []
    for prefix in COMMON_EMAIL_PREFIXES:
        emails.append(f"{prefix}@{domain}")
    return emails


def fetch_page_content(url: str, timeout: int = 10) -> Optional[str]:
    """Fetch page content safely."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.text
    except Exception as e:
        logger.warning(f"Failed to fetch {url}: {e}")
        return None


def extract_emails_from_text(text: str) -> Set[str]:
    """Extract email addresses from text."""
    emails = set()
    
    # Find all email patterns
    matches = EMAIL_PATTERN.findall(text)
    for email in matches:
        email = email.lower().strip()
        
        # Filter out common false positives
        if not any(bad in email for bad in [
            'example.com', 'test.com', 'domain.com', 
            'yoursite.com', 'website.com', 'lorem',
            'sample.com', 'placeholder'
        ]):
            emails.add(email)
    
    return emails


def find_contact_pages(base_url: str) -> List[str]:
    """Find potential contact pages."""
    urls = [base_url]  # Always check homepage
    
    for path in CONTACT_PATHS:
        contact_url = urljoin(base_url, path)
        urls.append(contact_url)
    
    return urls


def scrape_website_for_emails(website_url: str) -> dict:
    """
    Scrape a website for email addresses.
    
    Returns:
        dict with 'emails' (set), 'domain' (str), 'common_emails' (list)
    """
    result = {
        'emails': set(),
        'domain': None,
        'common_emails': [],
        'pages_checked': 0,
        'success': False
    }
    
    if not website_url:
        return result
    
    # Ensure URL has protocol
    if not website_url.startswith(('http://', 'https://')):
        website_url = 'https://' + website_url
    
    domain = get_domain_from_url(website_url)
    if not domain:
        logger.warning(f"Could not extract domain from {website_url}")
        return result
    
    result['domain'] = domain
    result['common_emails'] = generate_common_emails(domain)
    
    # Get list of pages to check
    pages_to_check = find_contact_pages(website_url)
    
    logger.info(f"Checking {len(pages_to_check)} pages for {domain}")
    
    for url in pages_to_check:
        try:
            content = fetch_page_content(url)
            if content:
                result['pages_checked'] += 1
                
                # Parse with BeautifulSoup to get clean text
                soup = BeautifulSoup(content, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()
                
                # Get text content
                text = soup.get_text()
                
                # Extract emails
                page_emails = extract_emails_from_text(text)
                result['emails'].update(page_emails)
                
                if page_emails:
                    logger.info(f"Found {len(page_emails)} emails on {url}")
                
                # Small delay between requests
                time.sleep(1)
                
        except Exception as e:
            logger.warning(f"Error processing {url}: {e}")
            continue
    
    # Filter emails to only include ones from this domain
    domain_emails = {email for email in result['emails'] 
                    if domain in email}
    
    result['emails'] = domain_emails
    result['success'] = len(domain_emails) > 0 or result['pages_checked'] > 0
    
    logger.info(f"Website scraping complete for {domain}: {len(domain_emails)} emails found")
    
    return result


def test_email_exists(email: str) -> bool:
    """
    Simple test if email might exist (very basic).
    In production, you might want to use email verification services.
    """
    # For now, just check if it follows basic patterns
    return '@' in email and '.' in email.split('@')[1]


if __name__ == "__main__":
    # Test with a known dental website
    test_url = "https://www.harleystreetdentalstudio.com/"
    
    print(f"Testing email extraction from: {test_url}")
    result = scrape_website_for_emails(test_url)
    
    print(f"\nResults:")
    print(f"Domain: {result['domain']}")
    print(f"Pages checked: {result['pages_checked']}")
    print(f"Emails found: {len(result['emails'])}")
    
    for email in result['emails']:
        print(f"  ✅ {email}")
    
    if not result['emails']:
        print(f"\nCommon email suggestions:")
        for email in result['common_emails'][:5]:
            print(f"  💡 {email} (suggestion)")
