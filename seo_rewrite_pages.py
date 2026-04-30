import os
import re

pages_dir = r'e:\ruff1\tool\templates\pages'
pages = {
    "about.html": "About Us",
    "contact.html": "Contact Us",
    "disclaimer.html": "Disclaimer",
    "privacy.html": "Privacy Policy",
    "terms.html": "Terms of Service"
}

for filename, title in pages.items():
    filepath = os.path.join(pages_dir, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Update Title
    content = re.sub(
        r'{%\s*block\s+title\s*%}.*?{%\s*endblock\s*%}',
        f'{{% block title %}}{title} | StoryBrain AI{{% endblock %}}',
        content,
        flags=re.DOTALL
    )

    # Update Meta Description
    content = re.sub(
        r'{%\s*block\s+meta_description\s*%}.*?{%\s*endblock\s*%}',
        f'{{% block meta_description %}}Read the {title} of StoryBrain AI. Learn more about our free online tools, privacy commitments, and terms.{{% endblock %}}',
        content,
        flags=re.DOTALL
    )

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

print("Updated pages!")
