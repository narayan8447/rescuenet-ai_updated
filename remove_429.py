import os
import glob
import re

directories = ['backend/agents']
for d in directories:
    for root, _, files in os.walk(d):
        for f in files:
            if f.endswith('.py'):
                path = os.path.join(root, f)
                with open(path, 'r', encoding='utf-8') as file:
                    content = file.read()
                
                new_content = re.sub(r'(\s+)if "429" in str\(e\):\s+logger\.warning\("rate_limit_hit_retrying", error=str\(e\)\)\s+raise e', '', content)
                
                if new_content != content:
                    with open(path, 'w', encoding='utf-8') as file:
                        file.write(new_content)
                    print(f'Updated {path}')
