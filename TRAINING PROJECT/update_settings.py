import sys

with open('config/settings.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for i, line in enumerate(lines):
    if line.startswith('ALLOWED_HOSTS'):
        new_lines.append('ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "*").split(",")\n')
        new_lines.append('SITE_URL = os.environ.get("SITE_URL", "https://www.csc.gov.in")\n')
    elif line.strip() == "'django.contrib.messages',":
        new_lines.append(line)
        new_lines.append("    'django.contrib.sitemaps',\n")
    elif line.strip() == "'django.middleware.clickjacking.XFrameOptionsMiddleware',":
        new_lines.append(line)
        new_lines.append("    'config.middleware.XRobotsTagMiddleware',\n")
    else:
        new_lines.append(line)

with open('config/settings.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
