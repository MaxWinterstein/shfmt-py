from __future__ import annotations

import re
import sys

import requests

# File paths and URLs
SHFMT_VERSION_FILE = 'setup.py'
GITHUB_RELEASES_URL = 'https://github.com/mvdan/sh/releases/download/v{version}/sha256sums.txt'

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

checksum_url = GITHUB_RELEASES_URL.format(version=shfmt_version)
print(f"[INFO] Downloading checksum file from: {checksum_url}")

# Step 2: Download `sha256sums.txt`
response = requests.get(checksum_url)
if response.status_code != 200:
    print(f"[ERROR] Failed to download {checksum_url} (HTTP {response.status_code})")
    sys.exit(1)

checksums = {}
lines = response.text.splitlines()
print(f"[INFO] Downloaded checksum file ({len(lines)} lines). Processing...")

for line in lines:
    parts = line.split()
    if len(parts) != 2:
        print(f"[WARNING] Skipping malformed line: {line}")
        continue

    sha, filename = parts
    expected_key = filename.replace(shfmt_version, '{version}')

    if expected_key in ARCH_MAP:
        var_name = ARCH_MAP[expected_key].format(version=shfmt_version)
        checksums[var_name] = sha
        print(f"[INFO] Found checksum: {var_name} -> {sha}")
    else:
        print(f"[DEBUG] Skipping unrecognized file: {filename}")

if not checksums:
    print('[ERROR] No matching checksums found! Check the `sha256sums.txt` format.')
    sys.exit(1)


# Step 3: Update `setup.py`
print('[INFO] Updating setup.py with new checksums...')

new_content = content
updated = False

# Directly update variables in setup.py with the new checksums
for var_name, sha in checksums.items():
    print(f"[DEBUG] var_name: {var_name}")
    pattern = fr"({var_name}\s*=\s*)\"[a-fA-F0-9]{{64}}\""
    replacement = fr'\1"{sha}"'  # Corrected line

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
