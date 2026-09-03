import os
import re

with open('vers_system.py', 'r') as f:
    code = f.read()

# 1. Extract INDEX_HTML
match = re.search(r'INDEX_HTML = """(.*?)"""\n', code, flags=re.DOTALL)
if match:
    html_content = match.group(1)
    
    os.makedirs('templates', exist_ok=True)
    with open('templates/index.html', 'w') as f:
        f.write(html_content)
        
    # Replace the massive HTML block with a dynamic loader
    loader_code = '''
def get_index_html():
    with open('templates/index.html', 'r') as f:
        return f.read()

INDEX_HTML = get_index_html()
'''
    code = code[:match.start()] + loader_code.strip() + '\n' + code[match.end():]
    print("Extracted INDEX_HTML to templates/index.html")

# 2. Refactor api_backup to use zipfile
backup_route_old = r'''
            # Attach files
            files_to_backup = ["vers_system.py", "vers_simulator.py"]
            for fname in files_to_backup:
                if os.path.exists(fname):
                    with open(fname, "rb") as f:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(f.read())
                        encoders.encode_base64(part)
                        part.add_header('Content-Disposition', f'attachment; filename="{fname}"')
                        msg.attach(part)
'''

backup_route_new = r'''
            import zipfile
            import io
            
            # Create a zip file in memory
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add Python files
                for py_file in ["vers_system.py", "vers_simulator.py"]:
                    if os.path.exists(py_file):
                        zipf.write(py_file)
                # Add templates
                if os.path.exists("templates"):
                    for root, _, files in os.walk("templates"):
                        for file in files:
                            zipf.write(os.path.join(root, file))
            
            zip_buffer.seek(0)
            part = MIMEBase("application", "zip")
            part.set_payload(zip_buffer.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', 'attachment; filename="vers_backup.zip"')
            msg.attach(part)
'''
if '# Attach files' in code:
    code = code.replace(backup_route_old.strip('\n'), backup_route_new.strip('\n'))
    print("Updated api_backup to use ZIP files.")

with open('vers_system.py', 'w') as f:
    f.write(code)
print("vers_system.py updated.")
