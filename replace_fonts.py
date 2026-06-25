import os
import re

inter_link = "https://cdn.jsdelivr.net/npm/@fontsource/inter@5.0.8/index.min.css"
material_link = "https://cdn.jsdelivr.net/npm/material-symbols@0.23.0/outlined.css"

template_dir = 'templates'
count = 0

for root, dirs, files in os.walk(template_dir):
    for str_file in files:
        if str_file.endswith('.html'):
            filepath = os.path.join(root, str_file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            orig_content = content

            # Replace Inter
            content = re.sub(
                r'https://fonts\.googleapis\.com/css2\?family=Inter[^"\']*',
                inter_link,
                content
            )

            # Replace Material Symbols Outlined
            content = re.sub(
                r'https://fonts\.googleapis\.com/css2\?family=Material\+Symbols\+Outlined[^"\']*',
                material_link,
                content
            )

            if content != orig_content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                count += 1
                print(f"Updated {filepath}")

print(f"Updated {count} files.")
