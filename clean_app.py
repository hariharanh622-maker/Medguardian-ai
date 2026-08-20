import io
from pathlib import Path
p = Path(r"C:\Users\DELL\Desktop\medGuardian-AI\app.py")
text = p.read_text(encoding='utf-8')
lines = text.splitlines()
new_lines = []
changed = False
for line in lines:
    if line.strip() == 'n':
        changed = True
        continue
    new_lines.append(line)
if changed:
    p.write_text('\n'.join(new_lines)+"\n", encoding='utf-8')
    print('Removed standalone n lines')
else:
    print('No standalone n lines found')
