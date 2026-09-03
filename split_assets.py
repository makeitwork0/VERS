import os
import re

html_path = 'templates/index.html'
os.makedirs('static', exist_ok=True)

with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

# Extract styles
style_pattern = re.compile(r'<style>(.*?)</style>', re.DOTALL)
styles = []
def style_replacer(match):
    styles.append(match.group(1).strip())
    return '' # We will insert the link tag manually in <head>

new_html = style_pattern.sub(style_replacer, html)

with open('static/style.css', 'w', encoding='utf-8') as f:
    f.write('\n'.join(styles))

# Insert the CSS link right before </head>
new_html = new_html.replace('</head>', '    <link rel="stylesheet" href="/static/style.css">\n</head>')

# Extract scripts
# Be careful to only extract scripts without a 'src' attribute
script_pattern = re.compile(r'<script(?![^>]*src=)>([\s\S]*?)</script>', re.DOTALL)
scripts = []
def script_replacer(match):
    scripts.append(match.group(1).strip())
    return ''

new_html = script_pattern.sub(script_replacer, new_html)

with open('static/app.js', 'w', encoding='utf-8') as f:
    f.write('\n\n'.join(scripts))

# Insert the JS script tag right before </body>
new_html = new_html.replace('</body>', '    <script src="/static/app.js"></script>\n</body>')

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(new_html)

print("Split completed successfully!")
