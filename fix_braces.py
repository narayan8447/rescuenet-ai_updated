import os
import re

directories = ['backend/agents', 'backend/rag']
for d in directories:
    for root, _, files in os.walk(d):
        for f in files:
            if f.endswith('.py'):
                path = os.path.join(root, f)
                with open(path, 'r', encoding='utf-8') as file:
                    content = file.read()
                
                # We need to replace instances of '{"key": "value"}'
                # with '{{"key": "value"}}' inside prompts.
                # Since the schema definitions are the only long strings starting with '{" 
                # inside the ChatPromptTemplate.from_messages
                
                def replacer(m):
                    # Replace all { and } with {{ and }} inside the matched JSON string
                    inner = m.group(1).replace('{', '{{').replace('}', '}}')
                    return f"'{inner}'"

                new_content = re.sub(r'\'(\{\".*?\})\'', replacer, content, flags=re.DOTALL)
                
                if new_content != content:
                    with open(path, 'w', encoding='utf-8') as file:
                        file.write(new_content)
                    print(f'Updated {path}')
