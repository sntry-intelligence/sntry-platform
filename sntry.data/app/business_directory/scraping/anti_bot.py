"""
Anti-Bot Countermeasures and Rate Limiting for Web Scraping
Implements human-like behavior simulation, proxy rotation, and respectful scraping practices
"""
import asyncio
import random
import time
import logging
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from urllib.parse import urlparse
import json
import os

from playwright.async_api import Browser, BrowserContext, Page

logger = logging.getLogger(__name__)


@dataclass
class ProxyConfig:
    """Configuration for proxy servers"""
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    protocol: str = "http"  # http, https, socks5
    
    def to_playwright_format(self) -> Dict[str, Any]:
        """Convert to Playwright proxy format"""
        proxy_config = {
            "server": f"{self.protocol}://{self.host}:{self.port}"
        }
        if self.username and self.password:
            proxy_config["username"] = self.username
            proxy_config["password"] = self.password
        return proxy_config


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting"""
    requests_per_minute: int = 30
    requests_per_hour: int = 1000
    requests_per_day: int = 10000
    min_delay_seconds: float = 2.0
    max_delay_seconds: float = 8.0
    burst_limit: int = 5  # Max requests in quick succession
    burst_window_seconds: int = 10
    
    # Exponential backoff settings
    max_retries: int = 3
    base_backoff_seconds: float = 1.0
    max_backoff_seconds: float = 300.0  # 5 minutes


@dataclass
class RequestRecord:
    """Record of a request for rate limiting"""
    timestamp: datetime
    url: str
    success: bool
    response_time: float = 0.0


class RateLimiter:
    """
    Intelligent rate limiter that respects website policies and prevents overloading
    """
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.request_history: List[RequestRecord] = []
        self.domain_limits: Dict[str, List[RequestRecord]] = {}
        self.failed_requests: Dict[str, int] = {}  # Track failures per domain
        
    def _get_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            return urlparse(url).netloc.lower()
        except Exception:
            return "unknown"
    
    def _clean_old_records(self, domain: str):
        """Remove old request records to prevent memory bloat"""
        now = datetime.now()
        cutoff_time = now - timedelta(days=1)
        
        if domain in self.domain_limits:
            self.domain_limits[domain] = [
                record for record in self.domain_limits[domain]
                if record.timestamp > cutoff_time
            ]
    
    async def wait_if_needed(self, url: str) -> float:
        """
        Wait if necessary to respect rate limits
        
        Returns:
            float: Actual delay time in seconds
        """
        domain = self._get_domain(url)
        now = datetime.now()
        
        # Clean old records
        self._clean_old_records(domain)
        
        # Get domain-specific request history
        if domain not in self.domain_limits:
            self.domain_limits[domain] = []
        
        domain_requests = self.domain_limits[domain]
        
        # Check various rate limits
        delay_needed = 0.0
        
        # 1. Check burst limit (requests in short window)
        burst_window_start = now - timedelta(seconds=self.config.burst_window_seconds)
        recent_requests = [r for r in domain_requests if r.timestamp > burst_window_start]
        
        if len(recent_requests) >= self.config.burst_limit:
            oldest_in_window = min(recent_requests, key=lambda x: x.timestamp)
            delay_needed = max(delay_needed, 
                             (oldest_in_window.timestamp + timedelta(seconds=self.config.burst_window_seconds) - now).total_seconds())
        
        # 2. Check per-minute limit
        minute_ago = now - timedelta(minutes=1)
        minute_requests = [r for r in domain_requests if r.timestamp > minute_ago]
        
        if len(minute_requests) >= self.config.requests_per_minute:
            oldest_in_minute = min(minute_requests, key=lambda x: x.timestamp)
            delay_needed = max(delay_needed,
                             (oldest_in_minute.timestamp + timedelta(minutes=1) - now).total_seconds())
        
        # 3. Check per-hour limit
        hour_ago = now - timedelta(hours=1)
        hour_requests = [r for r in domain_requests if r.timestamp > hour_ago]
        
        if len(hour_requests) >= self.config.requests_per_hour:
            oldest_in_hour = min(hour_requests, key=lambda x: x.timestamp)
            delay_needed = max(delay_needed,
                             (oldest_in_hour.timestamp + timedelta(hours=1) - now).total_seconds())
        
        # 4. Add base delay for human-like behavior
        base_delay = random.uniform(self.config.min_delay_seconds, self.config.max_delay_seconds)
        delay_needed = max(delay_needed, base_delay)
        
        # 5. Add exponential backoff for domains with recent failures
        failure_count = self.failed_requests.get(domain, 0)
        if failure_count > 0:
            backoff_delay = min(
                self.config.base_backoff_seconds * (2 ** failure_count),
                self.config.max_backoff_seconds
            )
            delay_needed = max(delay_needed, backoff_delay)
            logger.info(f"Adding backoff delay of {backoff_delay:.2f}s for {domain} (failures: {failure_count})")
        
        # Wait if needed
        if delay_needed > 0:
            logger.debug(f"Rate limiting: waiting {delay_needed:.2f}s before requesting {url}")
            await asyncio.sleep(delay_needed)
        
        return delay_needed
    
    def record_request(self, url: str, success: bool, response_time: float = 0.0):
        """Record a request for rate limiting purposes"""
        domain = self._get_domain(url)
        
        record = RequestRecord(
            timestamp=datetime.now(),
            url=url,
            success=success,
            response_time=response_time
        )
        
        # Add to domain-specific history
        if domain not in self.domain_limits:
            self.domain_limits[domain] = []
        self.domain_limits[domain].append(record)
        
        # Update failure count
        if not success:
            self.failed_requests[domain] = self.failed_requests.get(domain, 0) + 1
        else:
            # Reset failure count on success
            if domain in self.failed_requests:
                self.failed_requests[domain] = max(0, self.failed_requests[domain] - 1)
    
    def get_stats(self, domain: str = None) -> Dict[str, Any]:
        """Get rate limiting statistics"""
        now = datetime.now()
        
        if domain:
            domains_to_check = [domain]
        else:
            domains_to_check = list(self.domain_limits.keys())
        
        stats = {}
        
        for d in domains_to_check:
            if d not in self.domain_limits:
                continue
                
            domain_requests = self.domain_limits[d]
            
            # Calculate stats for different time windows
            minute_ago = now - timedelta(minutes=1)
            hour_ago = now - timedelta(hours=1)
            day_ago = now - timedelta(days=1)
            
            minute_requests = [r for r in domain_requests if r.timestamp > minute_ago]
            hour_requests = [r for r in domain_requests if r.timestamp > hour_ago]
            day_requests = [r for r in domain_requests if r.timestamp > day_ago]
            
            stats[d] = {
                "requests_last_minute": len(minute_requests),
                "requests_last_hour": len(hour_requests),
                "requests_last_day": len(day_requests),
                "success_rate_last_hour": (
                    sum(1 for r in hour_requests if r.success) / len(hour_requests)
                    if hour_requests else 1.0
                ),
                "average_response_time": (
                    sum(r.response_time for r in hour_requests) / len(hour_requests)
                    if hour_requests else 0.0
                ),
                "current_failure_count": self.failed_requests.get(d, 0)
            }
        
        return stats


class HumanBehaviorSimulator:
    """
    Simulates human-like browsing behavior to avoid detection
    """
    
    def __init__(self):
        self.mouse_positions = []
        self.last_action_time = time.time()
    
    async def simulate_human_page_load(self, page: Page):
        """Simulate human behavior when loading a page"""
        # Random delay before interacting
        await asyncio.sleep(random.uniform(1.0, 3.0))
        
        # Simulate reading time based on page content
        try:
            content_length = len(await page.content())
            reading_time = min(5.0, max(1.0, content_length / 10000))  # Rough estimate
            await asyncio.sleep(random.uniform(reading_time * 0.5, reading_time * 1.5))
        except Exception:
            await asyncio.sleep(random.uniform(2.0, 4.0))
    
    async def simulate_mouse_movement(self, page: Page):
        """Simulate random mouse movements"""
        try:
            viewport = page.viewport_size
            if viewport:
                # Generate random mouse positions
                for _ in range(random.randint(2, 5)):
                    x = random.randint(0, viewport['width'])
                    y = random.randint(0, viewport['height'])
                    
                    await page.mouse.move(x, y)
                    await asyncio.sleep(random.uniform(0.1, 0.5))
        except Exception as e:
            logger.debug(f"Error simulating mouse movement: {e}")
    
    async def simulate_scrolling(self, page: Page, scroll_count: int = None):
        """Simulate human-like scrolling behavior"""
        if scroll_count is None:
            scroll_count = random.randint(2, 6)
        
        try:
            for _ in range(scroll_count):
                # Random scroll amount
                scroll_amount = random.randint(200, 800)
                
                # Scroll down
                await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
                
                # Random pause between scrolls
                await asyncio.sleep(random.uniform(0.5, 2.0))
                
                # Occasionally scroll back up a bit
                if random.random() < 0.3:
                    back_scroll = random.randint(50, 200)
                    await page.evaluate(f"window.scrollBy(0, -{back_scroll})")
                    await asyncio.sleep(random.uniform(0.3, 1.0))
        except Exception as e:
            logger.debug(f"Error simulating scrolling: {e}")
    
    async def simulate_typing(self, page: Page, selector: str, text: str):
        """Simulate human-like typing"""
        try:
            await page.focus(selector)
            await asyncio.sleep(random.uniform(0.2, 0.5))
            
            # Type character by character with random delays
            for char in text:
                await page.keyboard.type(char)
                # Human typing speed variation
                await asyncio.sleep(random.uniform(0.05, 0.2))
                
                # Occasional longer pauses (thinking)
                if random.random() < 0.1:
                    await asyncio.sleep(random.uniform(0.5, 1.5))
        except Exception as e:
            logger.debug(f"Error simulating typing: {e}")
    
    async def simulate_click_with_movement(self, page: Page, selector: str):
        """Simulate clicking with mouse movement"""
        try:
            element = await page.wait_for_selector(selector, timeout=5000)
            if element:
                # Get element position
                box = await element.bounding_box()
                if box:
                    # Move mouse to element with some randomness
                    target_x = box['x'] + box['width'] / 2 + random.randint(-10, 10)
                    target_y = box['y'] + box['height'] / 2 + random.randint(-5, 5)
                    
                    await page.mouse.move(target_x, target_y)
                    await asyncio.sleep(random.uniform(0.1, 0.3))
                    
                    # Click
                    await page.mouse.click(target_x, target_y)
                    return True
        except Exception as e:
            logger.debug(f"Error simulating click: {e}")
        
        return False


class ProxyRotator:
    """
    Manages proxy rotation for avoiding IP-based blocking
    """
    
    def __init__(self, proxies: List[ProxyConfig] = None):
        self.proxies = proxies or []
        self.current_proxy_index = 0
        self.proxy_stats = {}  # Track success/failure rates
        self.blocked_proxies = set()  # Temporarily blocked proxies
        
    def add_proxy(self, proxy: ProxyConfig):
        """Add a proxy to the rotation"""
        self.proxies.append(proxy)
    
    def get_next_proxy(self) -> Optional[ProxyConfig]:
        """Get the next proxy in rotation"""
        if not self.proxies:
            return None
        
        # Find next available proxy
        attempts = 0
        while attempts < len(self.proxies):
            proxy = self.proxies[self.current_proxy_index]
            proxy_key = f"{proxy.host}:{proxy.port}"
            
            # Skip blocked proxies
            if proxy_key not in self.blocked_proxies:
                self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
                return proxy
            
            self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
            attempts += 1
        
        # If all proxies are blocked, unblock them and try again
        if self.blocked_proxies:
            logger.warning("All proxies blocked, resetting blocked list")
            self.blocked_proxies.clear()
            return self.get_next_proxy()
        
        return None
    
    def report_proxy_result(self, proxy: ProxyConfig, success: bool):
        """Report the result of using a proxy"""
        proxy_key = f"{proxy.host}:{proxy.port}"
        
        if proxy_key not in self.proxy_stats:
            self.proxy_stats[proxy_key] = {"success": 0, "failure": 0}
        
        if success:
            self.proxy_stats[proxy_key]["success"] += 1
            # Remove from blocked list if it was there
            self.blocked_proxies.discard(proxy_key)
        else:
            self.proxy_stats[proxy_key]["failure"] += 1
            
            # Block proxy if failure rate is too high
            stats = self.proxy_stats[proxy_key]
            total_requests = stats["success"] + stats["failure"]
            failure_rate = stats["failure"] / total_requests
            
            if total_requests >= 5 and failure_rate > 0.7:
                logger.warning(f"Blocking proxy {proxy_key} due to high failure rate: {failure_rate:.2f}")
                self.blocked_proxies.add(proxy_key)
    
    def get_proxy_stats(self) -> Dict[str, Any]:
        """Get statistics for all proxies"""
        return {
            "total_proxies": len(self.proxies),
            "blocked_proxies": len(self.blocked_proxies),
            "proxy_stats": self.proxy_stats
        }


class CaptchaSolver:
    """
    Basic CAPTCHA detection and handling
    
    Note: This is a placeholder implementation. For production use:
    - Integrate with services like 2captcha, Anti-Captcha, or Death By Captcha
    - Implement specific solvers for different CAPTCHA types
    - Add machine learning-based CAPTCHA detection
    """
    
    def __init__(self):
        self.captcha_indicators = [
            "captcha", "recaptcha", "hcaptcha", "verify", "robot",
            "human verification", "security check", "prove you're human"
        ]
    
    async def detect_captcha(self, page: Page) -> bool:
        """Detect if a CAPTCHA is present on the page"""
        try:
            page_content = await page.content()
            page_text = page_content.lower()
            
            # Check for CAPTCHA indicators in page content
            for indicator in self.captcha_indicators:
                if indicator in page_text:
                    logger.warning(f"CAPTCHA detected: {indicator}")
                    return True
            
            # Check for common CAPTCHA elements
            captcha_selectors = [
                ".g-recaptcha",
                ".h-captcha",
                "#captcha",
                ".captcha",
                "iframe[src*='recaptcha']",
                "iframe[src*='hcaptcha']"
            ]
            
            for selector in captcha_selectors:
                try:
                    element = await page.wait_for_selector(selector, timeout=1000)
                    if element:
                        logger.warning(f"CAPTCHA element detected: {selector}")
                        return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.debug(f"Error detecting CAPTCHA: {e}")
            return False
    
    async def handle_captcha(self, page: Page) -> bool:
        """
        Handle CAPTCHA if detected
        
        Returns:
            bool: True if CAPTCHA was solved, False otherwise
        """
        logger.warning("CAPTCHA detected - manual intervention may be required")
        
        # For now, just wait and hope it goes away
        # In production, integrate with CAPTCHA solving services
        await asyncio.sleep(30)
        
        # Check if CAPTCHA is still present
        return not await self.detect_captcha(page)


class AntiBot:
    """
    Comprehensive anti-bot system that combines all countermeasures
    """
    
    def __init__(
        self,
        rate_limit_config: RateLimitConfig = None,
        proxies: List[ProxyConfig] = None,
        enable_human_simulation: bool = True
    ):
        self.rate_limiter = RateLimiter(rate_limit_config or RateLimitConfig())
        self.proxy_rotator = ProxyRotator(proxies)
        self.human_simulator = HumanBehaviorSimulator() if enable_human_simulation else None
        self.captcha_solver = CaptchaSolver()
        
        # User agent rotation
        self.user_agents = [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0"
        ]
        self.current_user_agent_index = 0
    
    def get_next_user_agent(self) -> str:
        """Get next user agent in rotation"""
        user_agent = self.user_agents[self.current_user_agent_index]
        self.current_user_agent_index = (self.current_user_agent_index + 1) % len(self.user_agents)
        return user_agent
    
    async def create_context(self, browser: Browser) -> BrowserContext:
        """Create a browser context with anti-bot measures"""
        # Get proxy if available
        proxy = self.proxy_rotator.get_next_proxy()
        proxy_config = proxy.to_playwright_format() if proxy else None
        
        # Create context with anti-detection measures
        context = await browser.new_context(
            user_agent=self.get_next_user_agent(),
            viewport={"width": random.randint(1200, 1920), "height": random.randint(800, 1080)},
            proxy=proxy_config,
            extra_http_headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Cache-Control": "max-age=0"
            }
        )
        
        # Add stealth measures
        await context.add_init_script("""
            // Remove webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            // Mock plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            
            // Mock languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
            
            // Mock permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)
        
        return context
    
    async def safe_navigate(self, page: Page, url: str) -> bool:
        """
        Safely navigate to a URL with all anti-bot measures
        
        Returns:
            bool: True if navigation was successful
        """
        start_time = time.time()
        success = False
        
        try:
            # Apply rate limiting
            await self.rate_limiter.wait_if_needed(url)
            
            # Navigate to page
            response = await page.goto(url, wait_until="networkidle", timeout=30000)
            
            if response and response.status < 400:
                success = True
                
                # Simulate human behavior
                if self.human_simulator:
                    await self.human_simulator.simulate_human_page_load(page)
                
                # Check for CAPTCHA
                if await self.captcha_solver.detect_captcha(page):
                    logger.warning(f"CAPTCHA detected on {url}")
                    success = await self.captcha_solver.handle_captcha(page)
            
        except Exception as e:
            logger.error(f"Error navigating to {url}: {e}")
            success = False
        
        # Record request for rate limiting
        response_time = time.time() - start_time
        self.rate_limiter.record_request(url, success, response_time)
        
        return success
    
    async def safe_click(self, page: Page, selector: str) -> bool:
        """Safely click an element with human simulation"""
        try:
            if self.human_simulator:
                return await self.human_simulator.simulate_click_with_movement(page, selector)
            else:
                await page.click(selector)
                return True
        except Exception as e:
            logger.debug(f"Error clicking {selector}: {e}")
            return False
    
    async def safe_type(self, page: Page, selector: str, text: str) -> bool:
        """Safely type text with human simulation"""
        try:
            if self.human_simulator:
                await self.human_simulator.simulate_typing(page, selector, text)
            else:
                await page.fill(selector, text)
            return True
        except Exception as e:
            logger.debug(f"Error typing in {selector}: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive anti-bot statistics"""
        return {
            "rate_limiter": self.rate_limiter.get_stats(),
            "proxy_rotator": self.proxy_rotator.get_proxy_stats(),
            "current_user_agent": self.user_agents[self.current_user_agent_index]
        }


# Convenience functions
def create_default_anti_bot(proxies: List[ProxyConfig] = None) -> AntiBot:
    """Create an AntiBot instance with sensible defaults"""
    rate_config = RateLimitConfig(
        requests_per_minute=20,
        requests_per_hour=800,
        min_delay_seconds=3.0,
        max_delay_seconds=8.0
    )
    
    return AntiBot(
        rate_limit_config=rate_config,
        proxies=proxies,
        enable_human_simulation=True
    )


def load_proxies_from_file(file_path: str) -> List[ProxyConfig]:
    """Load proxy configurations from a JSON file"""
    try:
        with open(file_path, 'r') as f:
            proxy_data = json.load(f)
        
        proxies = []
        for proxy_info in proxy_data:
            proxy = ProxyConfig(
                host=proxy_info['host'],
                port=proxy_info['port'],
                username=proxy_info.get('username'),
                password=proxy_info.get('password'),
                protocol=proxy_info.get('protocol', 'http')
            )
            proxies.append(proxy)
        
        return proxies
    except Exception as e:
        logger.error(f"Error loading proxies from {file_path}: {e}")
        return []