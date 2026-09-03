import re
with open('vers_system.py', 'r') as f:
    content = f.read()

# INDEX_HTML is between INDEX_HTML = """ and the next """
parts = content.split('INDEX_HTML = """')
if len(parts) > 1:
    subparts = parts[1].split('"""', 1)
    if len(subparts) > 1:
        html = subparts[0]
        html = html.replace('{{', '{').replace('}}', '}')
        # restore valid JS template literals that might need ${...}
        new_content = parts[0] + 'INDEX_HTML = """' + html + '"""' + subparts[1]
        with open('vers_system.py', 'w') as f:
            f.write(new_content)
        print("Fixed braces!")
    else:
        print("Could not find end of INDEX_HTML")
else:
    print("Could not find INDEX_HTML")
