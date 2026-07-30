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
    url = params.url.strip()
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return {"success": False, "error": "Only absolute http(s) URLs are allowed"}
    try:
        opened = webbrowser.open(url)
        return {"success": bool(opened), "url": url}
    except Exception as exc:
        logger.error("open_url failed: %s", exc)
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
