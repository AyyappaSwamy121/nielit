import re

with open('templates/registration/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace placeholders: placeholder="[ Something ]" -> placeholder="Something"
content = re.sub(r'placeholder="\[\s*(.*?)\s*\]"', r'placeholder="\1"', content)

# Replace dropdown dummy options: >[ Select Something ]< -> >Select Something<
content = re.sub(r'>\[\s*(.*?)\s*\]<', r'>\1<', content)

with open('templates/registration/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done placeholders')
