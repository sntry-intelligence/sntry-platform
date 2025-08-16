"""
Legal Compliance and Respectful Scraping Practices
Ensures scraping activities comply with robots.txt, terms of service, and legal requirements
"""
import asyncio
import logging
import re
import urllib.robotparser
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse
from datetime import datetime, timedelta
import aiohttp

logger = logging.getLogger(__name__)


class RobotsChecker:
    """
    Checks and respects robots.txt files
    """
    
    def __init__(self):
        self.robots_cache: Dict[str, Tuple[urllib.robotparser.RobotFileParser, datetime]] = {}
        self.cache_duration = timedelta(hours=24)  # Cache robots.txt for 24 hours
    
    def _get_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            parsed = urlparse(url)
            return f"{parsed.scheme}://{parsed.netloc}"
        except Exception:
            return ""
    
    async def _fetch_robots_txt(self, domain: str) -> Optional[str]:
        """Fetch robots.txt content from domain"""
        robots_url = urljoin(domain, "/robots.txt")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(robots_url, timeout=10) as response:
                    if response.status == 200:
                        return await response.text()
                    else:
                        logger.debug(f"robots.txt not found for {domain} (status: {response.status})")
                        return None
        except Exception as e:
            logger.debug(f"Error fetching robots.txt for {domain}: {e}")
            return None
    
    async def can_fetch(self, url: str, user_agent: str = "*") -> bool:
        """
        Check if the URL can be fetched according to robots.txt
        
        Args:
            url: URL to check
            user_agent: User agent string to check against
            
        Returns:
            bool: True if URL can be fetched, False otherwise
        """
        domain = self._get_domain(url)
        if not domain:
            return True  # Allow if we can't parse the domain
        
        now = datetime.now()
        
        # Check cache
        if domain in self.robots_cache:
            rp, cached_time = self.robots_cache[domain]
            if now - cached_time < self.cache_duration:
                return rp.can_fetch(user_agent, url)
        
        # Fetch and parse robots.txt
        robots_content = await self._fetch_robots_txt(domain)
        
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(urljoin(domain, "/robots.txt"))
        
        if robots_content:
            # Parse robots.txt content manually for basic compliance
            try:
                # Simple robots.txt parsing
                lines = robots_content.strip().split('\n')
                current_user_agent = None
                rules = {}
                
                for line in lines:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    if line.lower().startswith('user-agent:'):
                        current_user_agent = line.split(':', 1)[1].strip()
                        if current_user_agent not in rules:
                            rules[current_user_agent] = {'allow': [], 'disallow': []}
                    elif line.lower().startswith('disallow:') and current_user_agent:
                        path = line.split(':', 1)[1].strip()
                        if path:
                            rules[current_user_agent]['disallow'].append(path)
                    elif line.lower().startswith('allow:') and current_user_agent:
                        path = line.split(':', 1)[1].strip()
                        if path:
                            rules[current_user_agent]['allow'].append(path)
                
                # Check if URL is allowed
                url_path = urlparse(url).path
                
                # Check specific user agent first, then wildcard
                agents_to_check = [user_agent, '*']
                
                for agent in agents_to_check:
                    if agent in rules:
                        # Check disallow rules first
                        for disallow_path in rules[agent]['disallow']:
                            if disallow_path == '/':
                                return False  # Disallow all
                            if url_path.startswith(disallow_path):
                                # Check if there's a more specific allow rule
                                allowed = False
                                for allow_path in rules[agent]['allow']:
                                    if url_path.startswith(allow_path):
                                        allowed = True
                                        break
                                if not allowed:
                                    return False
                        break
                
                # If we get here, it's allowed
                return True
                
            except Exception as e:
                logger.debug(f"Error parsing robots.txt manually: {e}")
                return True  # Allow if we can't parse
        else:
            # If no robots.txt, allow everything
            return True
    
    async def get_crawl_delay(self, url: str, user_agent: str = "*") -> Optional[float]:
        """
        Get the crawl delay specified in robots.txt
        
        Returns:
            Optional[float]: Crawl delay in seconds, or None if not specified
        """
        domain = self._get_domain(url)
        if not domain:
            return None
        
        # Fetch robots.txt content
        robots_content = await self._fetch_robots_txt(domain)
        
        if robots_content:
            try:
                # Parse for crawl-delay directive
                lines = robots_content.strip().split('\n')
                current_user_agent = None
                
                for line in lines:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    if line.lower().startswith('user-agent:'):
                        current_user_agent = line.split(':', 1)[1].strip()
                    elif line.lower().startswith('crawl-delay:') and current_user_agent:
                        if current_user_agent == user_agent or current_user_agent == '*':
                            try:
                                delay = float(line.split(':', 1)[1].strip())
                                return delay
                            except ValueError:
                                continue
                
            except Exception as e:
                logger.debug(f"Error parsing crawl delay: {e}")
        
        return None
    
    def get_robots_info(self, domain: str) -> Dict[str, any]:
        """Get information about robots.txt for a domain"""
        if domain not in self.robots_cache:
            return {"status": "not_cached"}
        
        rp, cached_time = self.robots_cache[domain]
        
        return {
            "status": "cached",
            "cached_at": cached_time.isoformat(),
            "robots_url": rp.url,
            "user_agents": list(rp.entries.keys()) if hasattr(rp, 'entries') else []
        }


class LegalComplianceChecker:
    """
    Comprehensive legal compliance checker for web scraping
    """
    
    def __init__(self):
        self.robots_checker = RobotsChecker()
        
        # Known problematic patterns that should be avoided
        self.restricted_patterns = [
            r'/admin',
            r'/private',
            r'/internal',
            r'/api/private',
            r'/user/.*',
            r'/account/.*',
            r'/login',
            r'/register',
            r'/checkout',
            r'/payment',
            r'/cart'
        ]
        
        # Rate limiting recommendations by site type
        self.site_recommendations = {
            'e-commerce': {
                'requests_per_minute': 10,
                'min_delay': 6.0,
                'respect_peak_hours': True
            },
            'news': {
                'requests_per_minute': 20,
                'min_delay': 3.0,
                'respect_peak_hours': False
            },
            'directory': {
                'requests_per_minute': 15,
                'min_delay': 4.0,
                'respect_peak_hours': False
            },
            'social_media': {
                'requests_per_minute': 5,
                'min_delay': 12.0,
                'respect_peak_hours': True,
                'requires_api': True
            }
        }
    
    async def check_url_compliance(self, url: str, user_agent: str = "JamaicaBusinessBot/1.0") -> Dict[str, any]:
        """
        Comprehensive compliance check for a URL
        
        Returns:
            Dict with compliance information and recommendations
        """
        result = {
            "url": url,
            "compliant": True,
            "issues": [],
            "recommendations": [],
            "robots_allowed": True,
            "crawl_delay": None,
            "risk_level": "low"
        }
        
        # Check robots.txt compliance
        try:
            robots_allowed = await self.robots_checker.can_fetch(url, user_agent)
            result["robots_allowed"] = robots_allowed
            
            if not robots_allowed:
                result["compliant"] = False
                result["issues"].append("URL blocked by robots.txt")
                result["risk_level"] = "high"
            
            # Get crawl delay
            crawl_delay = await self.robots_checker.get_crawl_delay(url, user_agent)
            result["crawl_delay"] = crawl_delay
            
            if crawl_delay and crawl_delay > 0:
                result["recommendations"].append(f"Respect crawl delay of {crawl_delay} seconds")
        
        except Exception as e:
            logger.warning(f"Error checking robots.txt for {url}: {e}")
            result["issues"].append(f"Could not verify robots.txt compliance: {e}")
        
        # Check for restricted URL patterns
        for pattern in self.restricted_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                result["compliant"] = False
                result["issues"].append(f"URL matches restricted pattern: {pattern}")
                result["risk_level"] = "high"
        
        # Domain-specific checks
        domain = urlparse(url).netloc.lower()
        
        # Social media platforms require special handling
        social_platforms = ['instagram.com', 'facebook.com', 'twitter.com', 'tiktok.com', 'linkedin.com']
        if any(platform in domain for platform in social_platforms):
            result["recommendations"].append("Consider using official API instead of scraping")
            result["recommendations"].append("Ensure compliance with platform Terms of Service")
            result["risk_level"] = "medium" if result["risk_level"] == "low" else result["risk_level"]
        
        # E-commerce sites
        ecommerce_indicators = ['shop', 'store', 'buy', 'cart', 'checkout', 'payment']
        if any(indicator in domain for indicator in ecommerce_indicators):
            result["recommendations"].append("Avoid scraping during peak shopping hours")
            result["recommendations"].append("Use conservative rate limits for e-commerce sites")
        
        return result
    
    async def check_scraping_session(
        self, 
        urls: List[str], 
        user_agent: str = "JamaicaBusinessBot/1.0"
    ) -> Dict[str, any]:
        """
        Check compliance for an entire scraping session
        
        Args:
            urls: List of URLs to be scraped
            user_agent: User agent string
            
        Returns:
            Session compliance report
        """
        session_report = {
            "total_urls": len(urls),
            "compliant_urls": 0,
            "non_compliant_urls": 0,
            "high_risk_urls": 0,
            "domains": set(),
            "overall_compliance": True,
            "recommendations": [],
            "url_reports": []
        }
        
        for url in urls:
            try:
                url_report = await self.check_url_compliance(url, user_agent)
                session_report["url_reports"].append(url_report)
                
                # Update counters
                if url_report["compliant"]:
                    session_report["compliant_urls"] += 1
                else:
                    session_report["non_compliant_urls"] += 1
                    session_report["overall_compliance"] = False
                
                if url_report["risk_level"] == "high":
                    session_report["high_risk_urls"] += 1
                
                # Track domains
                domain = urlparse(url).netloc
                session_report["domains"].add(domain)
                
            except Exception as e:
                logger.error(f"Error checking compliance for {url}: {e}")
                session_report["non_compliant_urls"] += 1
                session_report["overall_compliance"] = False
        
        # Generate session-level recommendations
        session_report["domains"] = list(session_report["domains"])
        
        if session_report["high_risk_urls"] > 0:
            session_report["recommendations"].append(
                f"Review {session_report['high_risk_urls']} high-risk URLs before scraping"
            )
        
        if len(session_report["domains"]) > 10:
            session_report["recommendations"].append(
                "Consider spreading scraping across multiple sessions to reduce server load"
            )
        
        # Domain-specific rate limiting recommendations
        for domain in session_report["domains"]:
            domain_urls = [url for url in urls if domain in url]
            if len(domain_urls) > 100:
                session_report["recommendations"].append(
                    f"Use conservative rate limits for {domain} ({len(domain_urls)} URLs)"
                )
        
        return session_report
    
    def generate_compliance_report(self, session_report: Dict[str, any]) -> str:
        """
        Generate a human-readable compliance report
        """
        report = []
        report.append("=== LEGAL COMPLIANCE REPORT ===")
        report.append(f"Total URLs: {session_report['total_urls']}")
        report.append(f"Compliant URLs: {session_report['compliant_urls']}")
        report.append(f"Non-compliant URLs: {session_report['non_compliant_urls']}")
        report.append(f"High-risk URLs: {session_report['high_risk_urls']}")
        report.append(f"Domains: {len(session_report['domains'])}")
        report.append("")
        
        if session_report["overall_compliance"]:
            report.append("✅ OVERALL COMPLIANCE: PASS")
        else:
            report.append("❌ OVERALL COMPLIANCE: FAIL")
        
        report.append("")
        
        if session_report["recommendations"]:
            report.append("RECOMMENDATIONS:")
            for rec in session_report["recommendations"]:
                report.append(f"• {rec}")
            report.append("")
        
        # Show non-compliant URLs
        non_compliant = [r for r in session_report["url_reports"] if not r["compliant"]]
        if non_compliant:
            report.append("NON-COMPLIANT URLS:")
            for url_report in non_compliant[:10]:  # Show first 10
                report.append(f"• {url_report['url']}")
                for issue in url_report["issues"]:
                    report.append(f"  - {issue}")
            
            if len(non_compliant) > 10:
                report.append(f"  ... and {len(non_compliant) - 10} more")
        
        return "\n".join(report)


class EthicalScrapingGuidelines:
    """
    Guidelines and best practices for ethical web scraping
    """
    
    @staticmethod
    def get_guidelines() -> Dict[str, List[str]]:
        """Get comprehensive ethical scraping guidelines"""
        return {
            "legal_compliance": [
                "Always check and respect robots.txt files",
                "Review website Terms of Service before scraping",
                "Avoid scraping copyrighted content without permission",
                "Respect data protection laws (GDPR, CCPA, etc.)",
                "Don't scrape personal or sensitive information",
                "Consider fair use principles for public data"
            ],
            "technical_respect": [
                "Use reasonable rate limits to avoid overloading servers",
                "Implement exponential backoff for failed requests",
                "Respect crawl delays specified in robots.txt",
                "Use appropriate User-Agent strings that identify your bot",
                "Don't scrape during peak traffic hours when possible",
                "Cache responses to avoid repeated requests for same data"
            ],
            "data_handling": [
                "Only collect data that is necessary for your use case",
                "Implement data retention policies",
                "Secure scraped data appropriately",
                "Don't republish scraped data without permission",
                "Respect data subject rights (deletion, correction, etc.)",
                "Anonymize personal data when possible"
            ],
            "business_ethics": [
                "Consider the impact on the website owner's business",
                "Don't scrape in ways that could harm website performance",
                "Respect competitive boundaries and fair competition",
                "Consider reaching out for data partnerships instead",
                "Be transparent about your scraping activities when appropriate",
                "Contribute back to the community when possible"
            ],
            "monitoring_and_maintenance": [
                "Monitor your scraping activities for compliance",
                "Regularly review and update scraping practices",
                "Implement logging and auditing for scraping activities",
                "Have procedures for handling cease and desist requests",
                "Keep up with changes in legal requirements",
                "Train team members on ethical scraping practices"
            ]
        }
    
    @staticmethod
    def create_scraping_policy(organization: str, contact_email: str) -> str:
        """Create a template scraping policy document"""
        policy = f"""
# Web Scraping Policy - {organization}

## Purpose
This policy outlines {organization}'s commitment to ethical and legal web scraping practices.

## Contact Information
For questions about our scraping activities: {contact_email}

## Our Commitments

### Legal Compliance
- We respect robots.txt files and website terms of service
- We comply with applicable data protection laws
- We avoid scraping personal or sensitive information
- We respect intellectual property rights

### Technical Respect
- We use reasonable rate limits (typically 10-30 requests per minute)
- We implement delays between requests (2-8 seconds)
- We use descriptive User-Agent strings
- We avoid scraping during peak hours when possible

### Data Handling
- We only collect publicly available data necessary for our business purposes
- We implement appropriate security measures for scraped data
- We respect data subject rights and handle requests promptly
- We have data retention policies in place

### Business Ethics
- We consider the impact of our scraping on website owners
- We are open to data partnerships and API usage when available
- We respond promptly to any concerns about our scraping activities

## User-Agent String
Our scrapers identify themselves as: "JamaicaBusinessBot/1.0 (+{contact_email})"

## Reporting Issues
If you have concerns about our scraping activities, please contact us at {contact_email}

Last Updated: {datetime.now().strftime('%Y-%m-%d')}
"""
        return policy


# Convenience functions
async def check_urls_compliance(urls: List[str]) -> Dict[str, any]:
    """Quick compliance check for a list of URLs"""
    checker = LegalComplianceChecker()
    return await checker.check_scraping_session(urls)


async def is_url_allowed(url: str, user_agent: str = "JamaicaBusinessBot/1.0") -> bool:
    """Quick check if a URL is allowed by robots.txt"""
    checker = RobotsChecker()
    return await checker.can_fetch(url, user_agent)


def get_ethical_guidelines() -> Dict[str, List[str]]:
    """Get ethical scraping guidelines"""
    return EthicalScrapingGuidelines.get_guidelines()


def create_scraping_policy(org_name: str, contact_email: str) -> str:
    """Create a scraping policy document"""
    return EthicalScrapingGuidelines.create_scraping_policy(org_name, contact_email)