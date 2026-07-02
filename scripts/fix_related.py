import glob
import re

count = 0
for filepath in glob.glob('templates/tools/*.html'):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if '{% set seo =' in content and '"related": seo_data.related' not in content:
        # Find the line that ends the dictionary: `} %}`
        # We replace `\n} %}` with `,\n  "related": seo_data.related\n} %}`
        
        new_content = re.sub(r'(\n\} %\})', r',\n  "related": seo_data.related\1', content)
        
        if new_content != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            count += 1
            print(f'Fixed {filepath}')

print(f'Total fixed: {count}')
