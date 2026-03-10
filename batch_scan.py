#!/usr/bin/env python3
"""
batch_scan.py  —  Scan multiple usernames from a text file.

Usage:
    python batch_scan.py wordlist.txt
    python batch_scan.py wordlist.txt --format json csv --output-dir batch_results
"""

import asyncio
import argparse
import sys
import os
from username_osint import scan_username, save_json, save_csv, save_txt, print_banner, print_summary
from colorama import Fore, Style, init

init(autoreset=True)


def parse_args():
    p = argparse.ArgumentParser(description="Batch Username OSINT Scanner")
    p.add_argument("wordlist",  help="Path to a text file with one username per line")
    p.add_argument("--timeout",     type=int, default=10,              help="Request timeout (default: 10)")
    p.add_argument("--concurrency", type=int, default=20,              help="Simultaneous requests (default: 20)")
    p.add_argument("--output-dir",  default="batch_results",           help="Output directory (default: batch_results)")
    p.add_argument("--format",      nargs="*", choices=["json","csv","txt"], default=["json","txt"])
    p.add_argument("--found-only",  action="store_true")
    return p.parse_args()


async def run(args):
    print_banner()

    if not os.path.isfile(args.wordlist):
        print(f"{Fore.RED}  Error: file not found → {args.wordlist}{Style.RESET_ALL}")
        sys.exit(1)

    with open(args.wordlist, "r") as f:
        usernames = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    print(f"{Fore.CYAN}  📋 Loaded {len(usernames)} usernames from {args.wordlist}{Style.RESET_ALL}\n")

    for i, username in enumerate(usernames, 1):
        print(f"{Fore.CYAN}  [{i}/{len(usernames)}] Scanning: {Fore.YELLOW}{username}{Style.RESET_ALL}")
        report = await scan_username(
            username=username,
            timeout=args.timeout,
            concurrency=args.concurrency,
            verbose=True,
            found_only=args.found_only,
        )
        print_summary(report)

        if "json" in (args.format or []):
            save_json(report, args.output_dir)
        if "csv" in (args.format or []):
            save_csv(report, args.output_dir)
        if "txt" in (args.format or []):
            save_txt(report, args.output_dir)

    print(f"\n{Fore.GREEN}  ✅ Batch scan complete. Results saved to: {args.output_dir}{Style.RESET_ALL}\n")


def main():
    asyncio.run(run(parse_args()))


if __name__ == "__main__":
    main()
