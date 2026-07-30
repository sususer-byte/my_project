"""Web search and browser control tools."""

import logging
import urllib.parse
import webbrowser
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger("furgal.action.tools")

_ddg_available = False
BROWSER_PROCESS_NAMES = {
    "chrome": {"chrome.exe", "chrome"},
    "firefox": {"firefox.exe", "firefox"},
    "msedge": {"msedge.exe", "msedge"},
    "safari": {"safari"},
    "brave": {"brave.exe", "brave", "brave-browser.exe", "brave-browser"},
}

try:
    from duckduckgo_search import DDGS
    _ddg_available = True
except ImportError:
    logger.warning("duckduckgo_search not installed; web search limited")


class WebSearchParams(BaseModel):
    query: str = Field(min_length=1, max_length=300, description="Search query")
    max_results: int = Field(default=5, ge=1, le=10, description="Maximum number of results")


class OpenUrlParams(BaseModel):
    url: str = Field(min_length=1, max_length=2048, description="URL to open in the default browser")

    @field_validator("url")
    @classmethod
    def reject_unsafe_url_text(cls, value):
        if any(ch in value for ch in ("\r", "\n", "\x00")):
            raise ValueError("URL contains unsafe control characters")
        return value


class FetchWebContentParams(BaseModel):
    url: str = Field(min_length=1, max_length=2048, description="URL to fetch content from")
    max_length: int = Field(default=5000, ge=100, le=10000, description="Maximum content length to return")
    
    @field_validator("url")
    @classmethod
    def validate_fetch_url(cls, value):
        # [MODIFICATION]: Validate URL for web fetching
        if not value.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        if any(ch in value for ch in ("\r", "\n", "\x00", " ", "\t")):
            raise ValueError("URL contains unsafe characters")
        return value


class CloseBrowserParams(BaseModel):
    browser_name: Optional[str] = Field(
        default=None,
        description="Browser process name to close (e.g. chrome, firefox, msedge)",
    )


def _web_search(params: WebSearchParams) -> Dict[str, Any]:
    query = params.query.strip()
    if _ddg_available:
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=params.max_results))
            formatted = [
                {"title": r.get("title", ""), "url": r.get("href", ""), "snippet": r.get("body", "")}
                for r in results
            ]
            return {"success": True, "query": query, "results": formatted, "source": "duckduckgo"}
        except Exception as exc:
            logger.error("DuckDuckGo search failed: %s", exc)
    encoded = urllib.parse.quote_plus(query)
    fallback_url = f"https://www.google.com/search?q={encoded}"
    return {
        "success": True,
        "query": query,
        "results": [{"title": "Google Search", "url": fallback_url, "snippet": "Opened via fallback URL"}],
        "source": "fallback_url",
        "note": "Install duckduckgo_search for inline results",
    }


def _open_url(params: OpenUrlParams) -> Dict[str, Any]:
    # [MODIFICATION]: Enhanced URL opening with better validation and error handling
    url = params.url.strip()
    if not url:
        return {"success": False, "error": "URL cannot be empty"}
    
    # [MODIFICATION]: Add protocol if missing
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    
    # [MODIFICATION]: Validate URL structure
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return {"success": False, "error": f"Unsupported URL scheme: {parsed.scheme}"}
        if not parsed.netloc:
            return {"success": False, "error": "URL must include a domain name"}
        
        # [MODIFICATION]: Additional security checks
        if any(char in url for char in (' ', '\n', '\r', '\t')):
            return {"success": False, "error": "URL contains invalid characters"}
        
        # [MODIFICATION]: Try different browser opening methods
        try:
            opened = webbrowser.open(url)
            if opened:
                logger.info("Successfully opened URL: %s", url)
                return {"success": True, "url": url, "method": "webbrowser"}
        except webbrowser.Error as wb_err:
            logger.warning("webbrowser.open failed: %s", wb_err)
        
        # [MODIFICATION]: Fallback to platform-specific commands
        try:
            import platform
            import subprocess
            
            system = platform.system()
            if system == "Windows":
                subprocess.Popen(["cmd", "/c", "start", url], shell=True)
            elif system == "Darwin":
                subprocess.Popen(["open", url])
            else:
                subprocess.Popen(["xdg-open", url])
            
            logger.info("Opened URL via platform command: %s", url)
            return {"success": True, "url": url, "method": "platform_command"}
            
        except Exception as cmd_err:
            logger.error("Platform command failed: %s", cmd_err)
            return {"success": False, "error": f"All URL opening methods failed: {str(cmd_err)}"}
        
    except Exception as exc:
        logger.error("open_url validation failed: %s", exc)
        return {"success": False, "error": str(exc)}


def _fetch_web_content(params: FetchWebContentParams) -> Dict[str, Any]:
    # [MODIFICATION]: Add web content fetching for AI knowledge enrichment
    try:
        import requests
        from bs4 import BeautifulSoup
        import urllib.parse
        
        url = params.url.strip()
        max_length = params.max_length
        
        # [MODIFICATION]: Validate URL
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return {"success": False, "error": "Only http and https URLs are supported"}
        
        # [MODIFICATION]: Set reasonable headers and timeout
        headers = {
            "User-Agent": "FurgalAI/1.0 (Knowledge Enrichment Bot; +https://furgal.ai)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        
        try:
            # [MODIFICATION]: Fetch with timeout
            response = requests.get(
                url,
                headers=headers,
                timeout=10,
                allow_redirects=True,
                stream=True
            )
            response.raise_for_status()
            
            # [MODIFICATION]: Check content type
            content_type = response.headers.get("Content-Type", "").lower()
            if "text/html" not in content_type:
                return {
                    "success": False,
                    "error": f"Unsupported content type: {content_type}",
                    "url": url
                }
            
            # [MODIFICATION]: Parse HTML and extract main content
            soup = BeautifulSoup(response.content, "html.parser")
            
            # [MODIFICATION]: Remove script, style, and other non-content elements
            for element in soup(["script", "style", "nav", "footer", "iframe", "svg"]):
                element.decompose()
            
            # [MODIFICATION]: Get main content
            main_content = soup.find(["main", "article"]) or soup.body or soup
            text_content = main_content.get_text(separator="\n", strip=True)
            
            # [MODIFICATION]: Clean and truncate content
            lines = [line.strip() for line in text_content.split("\n") if line.strip()]
            cleaned = "\n".join(lines)
            
            if len(cleaned) > max_length:
                cleaned = cleaned[:max_length] + f"\n\n[Content truncated at {max_length} characters]"
            
            return {
                "success": True,
                "url": url,
                "content": cleaned,
                "content_length": len(cleaned),
                "original_length": len(text_content),
                "truncated": len(text_content) > max_length
            }
            
        except requests.RequestException as req_exc:
            logger.error("Web fetch request failed: %s", req_exc)
            return {"success": False, "error": f"Request failed: {str(req_exc)}", "url": url}
        except Exception as exc:
            logger.error("Web fetch processing failed: %s", exc)
            return {"success": False, "error": f"Processing failed: {str(exc)}", "url": url}
        
    except ImportError:
        logger.warning("Required libraries for web fetching not available")
        return {
            "success": False,
            "error": "Missing dependencies: requests and beautifulsoup4 required",
            "url": params.url
        }
    except Exception as exc:
        logger.error("fetch_web_content failed: %s", exc)
        return {"success": False, "error": str(exc)}


def _close_browser(params: CloseBrowserParams) -> Dict[str, Any]:
    try:
        import psutil
    except ImportError:
        return {"success": False, "error": "psutil not installed"}
    target = (params.browser_name or "").strip().lower()
    allowed_names: set[str] = set()
    if target:
        allowed_names = BROWSER_PROCESS_NAMES.get(target, {target, f"{target}.exe"})
    else:
        for names in BROWSER_PROCESS_NAMES.values():
            allowed_names.update(names)
    closed = []
    try:
        for proc in psutil.process_iter(["pid", "name"]):
            name = (proc.info.get("name") or "").lower()
            if name in allowed_names:
                proc.terminate()
                closed.append(proc.info["pid"])
        if not closed:
            return {"success": False, "error": "No matching browser process found"}
        return {"success": True, "closed_pids": closed}
    except Exception as exc:
        logger.error("close_browser failed: %s", exc)
        return {"success": False, "error": str(exc)}


def register_web_tools(registry) -> None:
    """Register web search and browser control tools."""
    registry.register_tool(
        name="web_search",
        description="Search the web for real-time information using DuckDuckGo",
        params_model=WebSearchParams,
        handler=_web_search,
    )
    registry.register_tool(
        name="open_url",
        description="Open a URL in the default web browser",
        params_model=OpenUrlParams,
        handler=_open_url,
    )
    registry.register_tool(
        name="close_browser",
        description="Close a browser process by name",
        params_model=CloseBrowserParams,
        handler=_close_browser,
    )
    # [MODIFICATION]: Add web content fetching tool for AI knowledge enrichment
    registry.register_tool(
        name="fetch_web_content",
        description="Fetch and extract text content from a web page for AI knowledge enrichment",
        params_model=FetchWebContentParams,
        handler=_fetch_web_content,
    )
