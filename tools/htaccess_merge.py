"""Puts the KeikoArts SEO block at the top of the server's .htaccess, keeping everything else as it is.
Never prints the server file itself (the repo and its logs are public)."""
import re, sys, os
orig = open(sys.argv[1], encoding='utf-8', errors='surrogateescape').read() if os.path.exists(sys.argv[1]) else ''
block = open(sys.argv[2], encoding='utf-8').read().strip() + '\n\n'
rest = re.sub(r'# BEGIN KeikoArts SEO.*?# END KeikoArts SEO\n*', '', orig, flags=re.S)
open(sys.argv[3], 'w', encoding='utf-8', errors='surrogateescape').write(block + rest)
print(f'server .htaccess: {"found, " + str(orig.count(chr(10))) + " lines" if orig else "not found (new file)"}; '
      f'WordPress rules: {"yes" if "BEGIN WordPress" in orig else "no"}; PHP handler lines: {len(re.findall(r"(?im)^\s*(AddHandler|SetHandler|php_value)", orig))}; '
      f'previous KeikoArts block: {"replaced" if "BEGIN KeikoArts SEO" in orig else "none"}')
