import re

with open('templates/registration/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Pattern for input/select and label inside form-floating
# We need to capture the input/select tag, and the label tag.
# There might be whitespace.
# It's better to find all <div class="form-floating">...</div> blocks and process them.

def replace_floating(match):
    block = match.group(0)
    
    # Extract label
    label_match = re.search(r'<label\s+for="([^"]+)">([^<]+)</label>', block)
    if not label_match:
        return block
    label_for = label_match.group(1)
    label_text = label_match.group(2)
    
    # Remove the label from the block
    block_without_label = re.sub(r'<label\s+for="[^"]+">[^<]+</label>', '', block)
    
    # Replace form-floating with empty or keep the div
    block_without_label = block_without_label.replace('class="form-floating"', 'class="form-group"')
    
    # Create new label
    new_label = f'<label for="{label_for}" class="fw-bold mb-2">{label_text}</label>'
    
    # Insert new label right after the <div class="form-group">
    return block_without_label.replace('<div class="form-group">', f'<div class="form-group">\n                        {new_label}\n')

new_content = re.sub(r'<div class="form-floating">.*?</div>', replace_floating, content, flags=re.DOTALL)

with open('templates/registration/index.html', 'w', encoding='utf-8') as f:
    f.write(new_content)

print('Done')
