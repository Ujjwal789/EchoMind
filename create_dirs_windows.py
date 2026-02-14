# create_dirs_windows.py
import os

directories = [
    'web_ui',
    'web_ui/static',
    'web_ui/static/css',
    'web_ui/static/js',
    'web_ui/static/images',
    'web_ui/templates'
]

for directory in directories:
    os.makedirs(directory, exist_ok=True)
    print(f"✓ Created: {directory}")

print("\n✅ All directories created successfully!")