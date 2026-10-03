with open('utilities/image_optimizer.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if line.strip() == '"\"\"':
        new_lines.append(line.replace('"\"\"', '\"\"\"'))
    else:
        new_lines.append(line)

with open('utilities/image_optimizer.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
