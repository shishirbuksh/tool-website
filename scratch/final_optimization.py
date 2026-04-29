import os
import re

def process_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Replacements dictionary: Tailwind niche -> Bootstrap/Custom
        replacements = {
            r'\bborder-l-4\b': 'border-start border-4',
            r'\bborder-r-4\b': 'border-end border-4',
            r'\bmax-w-250\b': 'style="max-width: 250px;"',
            r'\bshadow-3xl\b': 'shadow-lg',
            r'\btext-accent\b': 'text-primary',
        }

        new_content = content
        for pattern, repl in replacements.items():
            new_content = re.sub(pattern, repl, new_content)

        # Standardize image attributes for PageSpeed
        # 1. Add loading="lazy" to <img> tags without it
        new_content = re.sub(r'<img(?!.*?loading=)(.*?)>', r'<img loading="lazy"\1>', new_content)

        # 2. Ensure alt tag exists
        new_content = re.sub(r'<img(?!.*?alt=)(.*?)>', r'<img alt="StoryBrain AI Module"\1>', new_content)

        if new_content != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f'Purged niche Tailwind & optimized images in: {filepath}')
    except Exception as e:
        print(f"Error processing {filepath}: {e}")

if __name__ == "__main__":
    templates_dir = r'e:\ruff1\tool\templates'
    for root, _, files in os.walk(templates_dir):
        for file in files:
            if file.endswith('.html'):
                process_file(os.path.join(root, file))
