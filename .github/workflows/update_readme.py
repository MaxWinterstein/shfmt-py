from __future__ import annotations

import re

# Function to extract version from setup.py


def extract_version_from_setup():
    print('[DEBUG] Opening setup.py to read the version...')
    with open('setup.py') as setup_file:
        setup_content = setup_file.read()

    shfmt_match = re.search(r"SHFMT_VERSION\s*=\s*'(\d+\.\d+\.\d+)'", setup_content)
    if not shfmt_match:
        raise ValueError('SHFMT_VERSION not found in setup.py')

    py_match = re.search(r"PY_VERSION\s*=\s*'(\d+)'", setup_content)
    if not py_match:
        raise ValueError('PY_VERSION not found in setup.py')

    shfmt_version = shfmt_match.group(1)
    py_version = py_match.group(1)
    print(f"[DEBUG] Found in setup.py: SHFMT_VERSION={shfmt_version}, PY_VERSION={py_version}")
    return shfmt_version, py_version

# Function to update the version in README.md


def update_readme_version():
    try:
        shfmt_version, py_version = extract_version_from_setup()

        # README uses the full pip package version: SHFMT_VERSION.PY_VERSION
        adjusted_version = f"{shfmt_version}.{py_version}"
        print(f"[DEBUG] Adjusted version: {adjusted_version}")

        # Open and read the README.md file
        print('[DEBUG] Opening README.md to read its content...')  # Debug log for reading README.md
        with open('README.md') as readme_file:
            readme_content = readme_file.read()

        # Search for the version pattern and replace it
        pattern = r'(rev:\s*v\d+\.\d+\.\d+\.\d+)'
        print(f"[DEBUG] Searching for pattern: {pattern}")  # Log the pattern being searched for
        new_readme_content = re.sub(pattern, f"rev: v{adjusted_version}", readme_content)

        # Check if any changes were made to the README.md content
        if new_readme_content != readme_content:
            print('[DEBUG] Changes detected in README.md. Updating...')  # Debug log for changes found
            with open('README.md', 'w') as readme_file:
                readme_file.write(new_readme_content)
            print(f"[INFO] Updated README.md with new version: {adjusted_version}")
        else:
            print('[INFO] No changes needed to README.md.')  # Debug log for no changes found

    except ValueError as e:
        print(f"[ERROR] {e}")  # Error log if version is not found in setup.py


# Run the function
update_readme_version()
