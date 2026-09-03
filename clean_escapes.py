import re

with open("vers_system.py", "r", encoding="utf-8") as f:
    text = f.read()

# Find literal \ u d 8 3 c type escapes and replace them
# We can just replace the specific ones we know:
# \ud83c\udf10 -> 🌐
text = text.replace(r"\ud83c\udf10", "🌐")
text = text.replace(r"\uD83C\uDF10", "🌐")

# Rain radar: \uD83C\uDF27
text = text.replace(r"\uD83C\uDF27\uFE0F", "🌧️")
text = text.replace(r"\ud83c\udf27\ufe0f", "🌧️")

# Incident heat: \uD83D\uDD25
text = text.replace(r"\uD83D\uDD25", "🔥")
text = text.replace(r"\ud83d\udd25", "🔥")

# Just to be sure, let's also remove any other \ud8 escapes if they exist
def repl(m):
    return ""
text = re.sub(r"\\u[dD][89aAbB][0-9a-fA-F]{2}\\u[dD][c-fC-F][0-9a-fA-F]{2}", repl, text)

with open("vers_system.py", "w", encoding="utf-8") as f:
    f.write(text)
print("Escapes cleaned!")
