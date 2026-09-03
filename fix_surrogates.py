with open("vers_system.py", "r", encoding="utf-8", errors="surrogatepass") as f:
    content = f.read()

# Merge surrogate pairs by round-tripping through UTF-16
content = content.encode("utf-16", "surrogatepass").decode("utf-16")

with open("vers_system.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Surrogates fixed!")
