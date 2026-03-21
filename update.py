import os

def replace_in_dir(d):
    for root, _, files in os.walk(d):
        for f in files:
            if f.endswith('.html'):
                path = os.path.join(root, f)
                with open(path, 'r', encoding='utf-8') as file:
                    content = file.read()
                if 'ToolBox Pro' in content:
                    content = content.replace('ToolBox Pro', 'StoryBrain AI')
                    with open(path, 'w', encoding='utf-8') as file:
                        file.write(content)

if __name__ == "__main__":
    replace_in_dir('templates')
    print("Branding replaced.")
