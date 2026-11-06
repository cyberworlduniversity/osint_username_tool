#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║              USERNAME OSINT TOOL  🕵️                             ║
║         Find accounts across the web by username                 ║
╚══════════════════════════════════════════════════════════════════╝

Author  : OSINT Toolkit
Version : 1.0.0
License : MIT
"""

import asyncio
import aiohttp
import argparse
import json
import csv
import sys
import os
import time
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field, asdict
from colorama import init, Fore, Style, Back

# Initialize colorama for cross-platform color support
init(autoreset=True)

# ─────────────────────────────────────────────
#  DATA STRUCTURES
# ─────────────────────────────────────────────

@dataclass
class SiteResult:
    """Holds the result of a single site check."""
    site_name: str
    url: str
    status: str          # FOUND | NOT FOUND | ERROR | TIMEOUT
    status_code: int = 0
    response_time_ms: float = 0.0
    error_msg: str = ""

@dataclass
class ScanReport:
    """Full report for a username scan."""
    username: str
    timestamp: str
    total_sites: int
    found: int
    not_found: int
    errors: int
    duration_seconds: float
    results: list = field(default_factory=list)


# ─────────────────────────────────────────────
#  SITE DEFINITIONS
# ─────────────────────────────────────────────

SITES = {
    # Social Media
    "GitHub":           {"url": "https://github.com/{}", "method": "status", "valid": [200]},
    "Twitter/X":        {"url": "https://twitter.com/{}", "method": "status", "valid": [200]},
    "Instagram":        {"url": "https://www.instagram.com/{}/", "method": "status", "valid": [200]},
    "TikTok":           {"url": "https://www.tiktok.com/@{}", "method": "status", "valid": [200]},
    "Reddit":           {"url": "https://www.reddit.com/user/{}", "method": "status", "valid": [200]},
    "Pinterest":        {"url": "https://www.pinterest.com/{}/", "method": "status", "valid": [200]},
    "Tumblr":           {"url": "https://{}.tumblr.com", "method": "status", "valid": [200]},
    "Facebook":         {"url": "https://www.facebook.com/{}", "method": "status", "valid": [200]},
    "LinkedIn":         {"url": "https://www.linkedin.com/in/{}", "method": "status", "valid": [200]},
    "Snapchat":         {"url": "https://www.snapchat.com/add/{}", "method": "status", "valid": [200]},

    # Dev / Tech
    "GitLab":           {"url": "https://gitlab.com/{}", "method": "status", "valid": [200]},
    "Bitbucket":        {"url": "https://bitbucket.org/{}", "method": "status", "valid": [200]},
    "HackerNews":       {"url": "https://news.ycombinator.com/user?id={}", "method": "status", "valid": [200]},
    "StackOverflow":    {"url": "https://stackoverflow.com/users/{}", "method": "status", "valid": [200]},
    "Replit":           {"url": "https://replit.com/@{}", "method": "status", "valid": [200]},
    "Dev.to":           {"url": "https://dev.to/{}", "method": "status", "valid": [200]},
    "Codepen":          {"url": "https://codepen.io/{}", "method": "status", "valid": [200]},
    "Kaggle":           {"url": "https://www.kaggle.com/{}", "method": "status", "valid": [200]},

    # Creative / Music
    "SoundCloud":       {"url": "https://soundcloud.com/{}", "method": "status", "valid": [200]},
    "Spotify":          {"url": "https://open.spotify.com/user/{}", "method": "status", "valid": [200]},
    "Bandcamp":         {"url": "https://{}.bandcamp.com", "method": "status", "valid": [200]},
    "Flickr":           {"url": "https://www.flickr.com/people/{}", "method": "status", "valid": [200]},
    "Behance":          {"url": "https://www.behance.net/{}", "method": "status", "valid": [200]},
    "Dribbble":         {"url": "https://dribbble.com/{}", "method": "status", "valid": [200]},
    "DeviantArt":       {"url": "https://www.deviantart.com/{}", "method": "status", "valid": [200]},
    "500px":            {"url": "https://500px.com/p/{}", "method": "status", "valid": [200]},

    # Gaming
    "Steam":            {"url": "https://steamcommunity.com/id/{}", "method": "status", "valid": [200]},
    "Twitch":           {"url": "https://www.twitch.tv/{}", "method": "status", "valid": [200]},
    "Roblox":           {"url": "https://www.roblox.com/user.aspx?username={}", "method": "status", "valid": [200]},
    "Minecraft":        {"url": "https://namemc.com/profile/{}", "method": "status", "valid": [200]},

    # Professional / Blogging
    "Medium":           {"url": "https://medium.com/@{}", "method": "status", "valid": [200]},
    "WordPress":        {"url": "https://{}.wordpress.com", "method": "status", "valid": [200]},
    "Substack":         {"url": "https://{}.substack.com", "method": "status", "valid": [200]},
    "About.me":         {"url": "https://about.me/{}", "method": "status", "valid": [200]},
    "Linktree":         {"url": "https://linktr.ee/{}", "method": "status", "valid": [200]},

    # Video
    "YouTube":          {"url": "https://www.youtube.com/@{}", "method": "status", "valid": [200]},
    "Vimeo":            {"url": "https://vimeo.com/{}", "method": "status", "valid": [200]},
    "Dailymotion":      {"url": "https://www.dailymotion.com/{}", "method": "status", "valid": [200]},

    # Forums / Community
    "Keybase":          {"url": "https://keybase.io/{}", "method": "status", "valid": [200]},
    "ProductHunt":      {"url": "https://www.producthunt.com/@{}", "method": "status", "valid": [200]},
    "AngelList":        {"url": "https://angel.co/u/{}", "method": "status", "valid": [200]},
}


# ─────────────────────────────────────────────
#  DISPLAY HELPERS
# ─────────────────────────────────────────────

BANNER = f"""
{Fore.CYAN}{Style.BRIGHT}
  ██████╗ ███████╗██╗███╗   ██╗████████╗
 ██╔═══██╗██╔════╝██║████╗  ██║╚══██╔══╝
 ██║   ██║███████╗██║██╔██╗ ██║   ██║   
 ██║   ██║╚════██║██║██║╚██╗██║   ██║   
 ╚██████╔╝███████║██║██║ ╚████║   ██║   
  ╚═════╝ ╚══════╝╚═╝╚═╝  ╚═══╝   ╚═╝  

{Fore.YELLOW}       Username Intelligence Tool 🕵️
{Fore.WHITE}   Find accounts across 40+ platforms
{Style.RESET_ALL}"""


def print_banner():
    print(BANNER)
    print(f"{Fore.CYAN}{'─'*55}{Style.RESET_ALL}\n")


def status_line(result: SiteResult) -> str:
    """Format a single result line with color."""
    if result.status == "FOUND":
        icon = f"{Fore.GREEN}[✓]{Style.RESET_ALL}"
        name_color = Fore.GREEN + Style.BRIGHT
        url_color = Fore.WHITE
        time_str = f"{Fore.CYAN}({result.response_time_ms:.0f}ms){Style.RESET_ALL}"
        return f"  {icon} {name_color}{result.site_name:<18}{Style.RESET_ALL} {url_color}{result.url}{Style.RESET_ALL} {time_str}"
    elif result.status == "NOT FOUND":
        icon = f"{Fore.RED}[✗]{Style.RESET_ALL}"
        return f"  {icon} {Fore.RED}{result.site_name:<18}{Style.RESET_ALL} {Fore.LIGHTBLACK_EX}not found{Style.RESET_ALL}"
    elif result.status == "TIMEOUT":
        icon = f"{Fore.YELLOW}[⏱]{Style.RESET_ALL}"
        return f"  {icon} {Fore.YELLOW}{result.site_name:<18}{Style.RESET_ALL} {Fore.LIGHTBLACK_EX}timeout{Style.RESET_ALL}"
    else:
        icon = f"{Fore.LIGHTBLACK_EX}[?]{Style.RESET_ALL}"
        return f"  {icon} {Fore.LIGHTBLACK_EX}{result.site_name:<18} error: {result.error_msg[:40]}{Style.RESET_ALL}"


def print_summary(report: ScanReport):
    found_pct = (report.found / report.total_sites * 100) if report.total_sites else 0
    bar_fill = int(found_pct / 5)
    bar = f"{Fore.GREEN}{'█' * bar_fill}{Fore.LIGHTBLACK_EX}{'░' * (20 - bar_fill)}{Style.RESET_ALL}"

    print(f"\n{Fore.CYAN}{'─'*55}{Style.RESET_ALL}")
    print(f"{Fore.WHITE}{Style.BRIGHT}  SCAN SUMMARY  —  @{report.username}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'─'*55}{Style.RESET_ALL}")
    print(f"  {Fore.WHITE}Scanned  : {Fore.CYAN}{report.total_sites} sites{Style.RESET_ALL}")
    print(f"  {Fore.WHITE}Found    : {Fore.GREEN}{report.found} accounts{Style.RESET_ALL}  [{bar}] {found_pct:.1f}%")
    print(f"  {Fore.WHITE}Not Found: {Fore.RED}{report.not_found}{Style.RESET_ALL}")
    print(f"  {Fore.WHITE}Errors   : {Fore.YELLOW}{report.errors}{Style.RESET_ALL}")
    print(f"  {Fore.WHITE}Duration : {Fore.CYAN}{report.duration_seconds:.2f}s{Style.RESET_ALL}")
    print(f"  {Fore.WHITE}Timestamp: {Fore.LIGHTBLACK_EX}{report.timestamp}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'─'*55}{Style.RESET_ALL}\n")


# ─────────────────────────────────────────────
#  CORE SCANNER
# ─────────────────────────────────────────────

async def check_site(
    session: aiohttp.ClientSession,
    site_name: str,
    site_config: dict,
    username: str,
    timeout: int = 10,
    verbose: bool = False
) -> SiteResult:
    """
    Asynchronously checks one site for the given username.
    Returns a SiteResult with status FOUND / NOT FOUND / ERROR / TIMEOUT.
    """
    url = site_config["url"].format(username)
    valid_codes = site_config.get("valid", [200])
    t_start = time.perf_counter()

    try:
        async with session.get(
            url,
            allow_redirects=True,
            timeout=aiohttp.ClientTimeout(total=timeout),
        ) as resp:
            elapsed = (time.perf_counter() - t_start) * 1000
            result = SiteResult(
                site_name=site_name,
                url=url,
                status="FOUND" if resp.status in valid_codes else "NOT FOUND",
                status_code=resp.status,
                response_time_ms=elapsed,
            )

    except asyncio.TimeoutError:
        result = SiteResult(site_name=site_name, url=url, status="TIMEOUT")
    except Exception as e:
        result = SiteResult(site_name=site_name, url=url, status="ERROR", error_msg=str(e)[:80])

    if verbose:
        print(status_line(result))

    return result


async def scan_username(
    username: str,
    sites: Optional[dict] = None,
    timeout: int = 10,
    concurrency: int = 20,
    verbose: bool = True,
    found_only: bool = False,
) -> ScanReport:
    """
    Main scan coroutine. Checks all sites concurrently.

    Parameters
    ----------
    username    : str   – The username to search for.
    sites       : dict  – Site definitions (defaults to SITES).
    timeout     : int   – Per-request timeout in seconds.
    concurrency : int   – Max simultaneous requests.
    verbose     : bool  – Print results as they arrive.
    found_only  : bool  – Only print FOUND results in verbose mode.

    Returns
    -------
    ScanReport  – Full structured report.
    """
    if sites is None:
        sites = SITES

    if verbose:
        print(f"\n{Fore.CYAN}  🔍 Scanning username: {Fore.YELLOW}{Style.BRIGHT}{username}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}  Checking {len(sites)} sites with concurrency={concurrency}, timeout={timeout}s{Style.RESET_ALL}\n")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        )
    }

    semaphore = asyncio.Semaphore(concurrency)
    t_start = time.perf_counter()

    async def bounded_check(name, config):
        async with semaphore:
            return await check_site(session, name, config, username, timeout, verbose)

    connector = aiohttp.TCPConnector(limit=concurrency)
    async with aiohttp.ClientSession(headers=headers, connector=connector) as session:
        tasks = [bounded_check(name, cfg) for name, cfg in sites.items()]
        results = await asyncio.gather(*tasks)

    duration = time.perf_counter() - t_start
    found    = [r for r in results if r.status == "FOUND"]
    errors   = [r for r in results if r.status in ("ERROR", "TIMEOUT")]

    # If not verbose or found_only, print a clean FOUND summary
    if verbose and found_only:
        print(f"\n{Fore.GREEN}{Style.BRIGHT}  ── Accounts Found ──{Style.RESET_ALL}")
        for r in found:
            print(status_line(r))

    report = ScanReport(
        username=username,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        total_sites=len(results),
        found=len(found),
        not_found=len([r for r in results if r.status == "NOT FOUND"]),
        errors=len(errors),
        duration_seconds=round(duration, 2),
        results=[asdict(r) for r in results],
    )
    return report


# ─────────────────────────────────────────────
#  EXPORT HELPERS
# ─────────────────────────────────────────────

def save_json(report: ScanReport, output_dir: str = ".") -> str:
    """Save report as JSON."""
    os.makedirs(output_dir, exist_ok=True)
    fname = os.path.join(output_dir, f"{report.username}_osint_{datetime.now():%Y%m%d_%H%M%S}.json")
    with open(fname, "w", encoding="utf-8") as f:
        json.dump(asdict(report), f, indent=2)
    return fname


def save_csv(report: ScanReport, output_dir: str = ".") -> str:
    """Save found accounts as CSV."""
    os.makedirs(output_dir, exist_ok=True)
    fname = os.path.join(output_dir, f"{report.username}_osint_{datetime.now():%Y%m%d_%H%M%S}.csv")
    found = [r for r in report.results if r["status"] == "FOUND"]
    with open(fname, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["site_name", "url", "status_code", "response_time_ms"])
        writer.writeheader()
        writer.writerows([{k: r[k] for k in ["site_name", "url", "status_code", "response_time_ms"]} for r in found])
    return fname


def save_txt(report: ScanReport, output_dir: str = ".") -> str:
    """Save human-readable report as TXT."""
    os.makedirs(output_dir, exist_ok=True)
    fname = os.path.join(output_dir, f"{report.username}_osint_{datetime.now():%Y%m%d_%H%M%S}.txt")
    with open(fname, "w", encoding="utf-8") as f:
        f.write(f"USERNAME OSINT REPORT\n")
        f.write(f"{'='*50}\n")
        f.write(f"Username  : {report.username}\n")
        f.write(f"Timestamp : {report.timestamp}\n")
        f.write(f"Duration  : {report.duration_seconds}s\n")
        f.write(f"Sites     : {report.total_sites}\n")
        f.write(f"Found     : {report.found}\n")
        f.write(f"Not Found : {report.not_found}\n")
        f.write(f"Errors    : {report.errors}\n")
        f.write(f"\n{'='*50}\n")
        f.write("FOUND ACCOUNTS:\n")
        f.write(f"{'='*50}\n")
        for r in report.results:
            if r["status"] == "FOUND":
                f.write(f"  [{r['site_name']}]  {r['url']}  ({r['response_time_ms']:.0f}ms)\n")
        f.write(f"\n{'='*50}\n")
        f.write("ALL RESULTS:\n")
        f.write(f"{'='*50}\n")
        for r in report.results:
            f.write(f"  {r['status']:<12} {r['site_name']:<20} {r['url']}\n")
    return fname


# ─────────────────────────────────────────────
#  CLI ENTRY POINT
# ─────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        prog="username_osint",
        description="🕵️  Username OSINT Tool — Find accounts across 40+ platforms",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python username_osint.py johndoe
  python username_osint.py johndoe --found-only
  python username_osint.py johndoe --output-dir results --format json csv txt
  python username_osint.py johndoe --timeout 15 --concurrency 30
  python username_osint.py johndoe alice bob  (scan multiple usernames)
        """
    )
    parser.add_argument("usernames", nargs="+", help="Username(s) to search for")
    parser.add_argument("--timeout",     type=int,   default=10,  help="Request timeout in seconds (default: 10)")
    parser.add_argument("--concurrency", type=int,   default=20,  help="Simultaneous requests (default: 20)")
    parser.add_argument("--found-only",  action="store_true",      help="Only show FOUND results in output")
    parser.add_argument("--quiet",       action="store_true",      help="Suppress per-site output")
    parser.add_argument("--output-dir",  default="osint_results",  help="Directory to save reports (default: osint_results)")
    parser.add_argument("--format",      nargs="*", choices=["json","csv","txt"], default=["json","txt"],
                        help="Output format(s): json csv txt (default: json txt)")
    return parser.parse_args()


async def main_async(args):
    print_banner()
    all_reports = []

    for username in args.usernames:
        report = await scan_username(
            username=username,
            timeout=args.timeout,
            concurrency=args.concurrency,
            verbose=not args.quiet,
            found_only=args.found_only,
        )
        print_summary(report)
        all_reports.append(report)

        # Save outputs
        saved = []
        if "json" in (args.format or []):
            saved.append(save_json(report, args.output_dir))
        if "csv" in (args.format or []):
            saved.append(save_csv(report, args.output_dir))
        if "txt" in (args.format or []):
            saved.append(save_txt(report, args.output_dir))

        for path in saved:
            print(f"  {Fore.GREEN}💾 Saved:{Style.RESET_ALL} {path}")

    print(f"\n{Fore.CYAN}  Scan complete for {len(args.usernames)} username(s).{Style.RESET_ALL}\n")
    return all_reports


def main():
    args = parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
