import yaml

def check_data():
    with open('data/blog.yaml', 'r', encoding='utf-8') as f:
        blog_data = yaml.safe_load(f)
    
    with open('data/tools.yaml', 'r', encoding='utf-8') as f:
        tools_data = yaml.safe_load(f)

    blog_posts = blog_data.get('posts', {})
    tools = tools_data.get('tools', {})
    print('Blog Posts:', list(blog_posts.keys()))

check_data()
