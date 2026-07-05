#!/usr/bin/env python3
"""Pre-commit secret scanner — checks staged changes for secrets.

Usage:
    python scripts/scan-secrets.py          # check staged changes
    python scripts/scan-secrets.py --all     # check entire repo

Exit code 0 = clean, 1 = secrets found.
"""

import argparse
import os
import re
import subprocess
import sys

SUSPICIOUS_PATTERNS = [
    (r'(?i)password\s*[=:]\s*["\']?.+?["\']?$', 'password'),
    (r'(?i)secret\s*[=:]\s*["\']?.{8,}?["\']?$', 'secret'),
    (r'(?i)api[_-]?key\s*[=:]\s*["\']?.{8,}?["\']?$', 'API key'),
    (r'(?i)api_key\s*[=:]\s*["\']?.{8,}?["\']?$', 'api_key'),
    (r'(?i)token\s*[=:]\s*["\']?.{8,}?["\']?$', 'token'),
    (r'(?i)auth_token\s*[=:]\s*["\']?.{8,}?["\']?$', 'auth token'),
    (r'(?i)sk-[A-Za-z0-9]{20,}', 'OpenAI API key'),
    (r'(?i)-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----', 'private key'),
    (r'(?i)ghp_[A-Za-z0-9]{36}', 'GitHub token'),
    (r'(?i)gho_[A-Za-z0-9]{36}', 'GitHub OAuth token'),
    (r'(?i)ghu_[A-Za-z0-9]{36}', 'GitHub user token'),
    (r'(?i)AKIA[0-9A-Z]{16}', 'AWS access key'),
    (r'(?i)eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}', 'JWT token'),
]

SKIP_PATTERNS = [
    r'^\s*#',
    r'^\s*//',
    r'^\s*\*',
    r'password_hash',
    r'hashed_password',
]


def is_comment_or_placeholder(line):
    for pat in SKIP_PATTERNS:
        if re.match(pat, line.strip()):
            return True
    if 'your-' in line.lower() or 'placeholder' in line.lower() or 'xxx' in line.lower():
        return True
    return False


def scan_lines(filepath, lines):
    findings = []
    for i, line in enumerate(lines, 1):
        if is_comment_or_placeholder(line):
            continue
        for pattern, label in SUSPICIOUS_PATTERNS:
            if re.search(pattern, line):
                findings.append((filepath, i, label, line.strip()[:120]))
                break
    return findings


def scan_staged():
    result = subprocess.run(
        ['git', 'diff', '--cached', '--diff-filter=ACMR', '--name-only'],
        capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        print("error: could not get staged files", file=sys.stderr)
        return 1

    files = [f for f in result.stdout.strip().split('\n') if f]
    all_findings = []

    for filepath in files:
        if not os.path.isfile(filepath):
            continue

        diff_result = subprocess.run(
            ['git', 'diff', '--cached', '-U999999', '--', filepath],
            capture_output=True, text=True, check=False
        )

        added_lines = []
        for line in diff_result.stdout.split('\n'):
            if line.startswith('+') and not line.startswith('+++'):
                added_lines.append(line[1:])

        if added_lines:
            all_findings.extend(scan_lines(filepath, added_lines))

    return all_findings


def scan_all():
    findings = []
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        for filename in files:
            filepath = os.path.join(root, filename)
            try:
                with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                    lines = f.readlines()
                findings.extend(scan_lines(filepath, lines))
            except Exception:
                pass
    return findings


def main():
    parser = argparse.ArgumentParser(description='Scan for secrets in code')
    parser.add_argument('--all', action='store_true', help='Scan entire repo (not just staged)')
    args = parser.parse_args()

    if args.all:
        findings = scan_all()
    else:
        findings = scan_staged()

    if isinstance(findings, int):
        return findings

    if not findings:
        return 0

    scope = "repository" if args.all else "staged changes"
    for filepath, line, label, content in findings:
        loc = f"{filepath}:{line}"
        print(f"  {loc:50s} {label:20s} {content[:60]}")

    print(f"\n!! Found {len(findings)} potential secret(s) in {scope}.")
    return 1


if __name__ == '__main__':
    sys.exit(main())
