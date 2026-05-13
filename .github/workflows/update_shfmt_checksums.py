from __future__ import annotations

import os
import re
import sys

import requests

# File paths and URLs
SHFMT_VERSION_FILE = 'setup.py'
# mvdan/sh stopped shipping sha256sums.txt in v3.13.0+; GitHub now exposes
# per-asset sha256 digests natively via the releases API.
GITHUB_API_URL = 'https://api.github.com/repos/mvdan/sh/releases/tags/v{version}'

ARCH_MAP = {
    'shfmt_v{version}_linux_arm': 'linux_arm',
    'shfmt_v{version}_linux_arm64': 'linux_arm64',
    'shfmt_v{version}_linux_amd64': 'linux_amd64',
    'shfmt_v{version}_darwin_amd64': 'darwin_amd64',
    'shfmt_v{version}_darwin_arm64': 'darwin_arm64',
    'shfmt_v{version}_windows_amd64.exe': 'windows_amd64_exe',
    'shfmt_v{version}_windows_386.exe': 'windows_386_exe',
}

# Step 1: Get the current SHFMT version from setup.py
print('[INFO] Reading SHFMT_VERSION from setup.py...')
try:
    with open(SHFMT_VERSION_FILE) as f:
        content = f.read()
except FileNotFoundError:
    print('[ERROR] setup.py not found!')
    sys.exit(1)

match = re.search(r"SHFMT_VERSION = '([^']+)'", content)
if not match:
    print('[ERROR] Could not find SHFMT_VERSION in setup.py!')
    sys.exit(1)

shfmt_version = match.group(1)
print(f"[INFO] Found SHFMT_VERSION: {shfmt_version}")

api_url = GITHUB_API_URL.format(version=shfmt_version)
print(f"[INFO] Fetching release metadata from: {api_url}")

# Step 2: Fetch release metadata from GitHub
# Use GITHUB_TOKEN if available to avoid the 60 req/hr unauthenticated limit;
# GitHub Actions populates this automatically when the step has the env wired.
headers = {}
token = os.environ.get('GITHUB_TOKEN')
if token:
    headers['Authorization'] = f'Bearer {token}'
response = requests.get(api_url, headers=headers, timeout=30)
if response.status_code != 200:
    print(f"[ERROR] Failed to fetch release metadata (HTTP {response.status_code})")
    sys.exit(1)

assets = response.json().get('assets', [])
print(f"[INFO] Got {len(assets)} release assets. Processing...")

checksums = {}
for asset in assets:
    name = asset['name']
    expected_key = name.replace(shfmt_version, '{version}')

    if expected_key not in ARCH_MAP:
        print(f"[DEBUG] Skipping unrecognized asset: {name}")
        continue

    digest = asset.get('digest', '')
    if not re.fullmatch(r'sha256:[a-fA-F0-9]{64}', digest):
        print(f"[WARNING] Asset {name} has no valid sha256 digest (got: {digest!r})")
        continue

    var_name = ARCH_MAP[expected_key].format(version=shfmt_version)
    checksums[var_name] = digest.split(':', 1)[1].lower()
    print(f"[INFO] Found checksum: {var_name} -> {checksums[var_name]}")

if not checksums:
    print('[ERROR] No checksums extracted! The release format may have changed again.')
    sys.exit(1)

# Partial extraction would silently leave stale hashes in setup.py for any
# missing platform — fail loud instead.
expected = set(ARCH_MAP.values())
missing = expected - set(checksums)
if missing:
    print(f"[ERROR] Missing checksums for expected platforms: {sorted(missing)}")
    sys.exit(1)


# Step 3: Update `setup.py`
print('[INFO] Updating setup.py with new checksums...')

new_content = content
updated = False

# Directly update variables in setup.py with the new checksums
for var_name, sha in checksums.items():
    print(f"[DEBUG] var_name: {var_name}")
    pattern = fr"({var_name}\s*=\s*)\'[a-fA-F0-9]{{64}}\'"
    replacement = fr"\1'{sha}'"  # Corrected line

    # Debug: print the pattern we are searching for
    print(f"[DEBUG] Searching for pattern: {pattern}")

    if re.search(pattern, new_content):
        new_content = re.sub(pattern, replacement, new_content)
        print(f"[INFO] Updated checksum for {var_name}: {sha}")
        updated = True
    else:
        print(f"[WARNING] Could not find pattern for {var_name}. Check your setup.py format.")

if not updated:
    print('[WARNING] No checksums were updated. Maybe they are already correct?')
else:
    with open(SHFMT_VERSION_FILE, 'w') as f:
        f.write(new_content)
    print('[SUCCESS] setup.py updated with new checksums!')
