import os, re

def update_file(filepath, state_key, array_name, mutate_code_regex, legacy_code_regex):
    with open(filepath, 'r') as f:
        content = f.read()

    # Add memory_manager import
    if 'from backend.core.memory import memory_manager' not in content:
        content = content.replace('from backend.utils import haversine_km', 'from backend.utils import haversine_km\nfrom backend.core.memory import memory_manager\nimport time')

    # Update LLM post-process mutation
    llm_pattern = re.compile(mutate_code_regex, re.DOTALL)
    
    def repl_llm(m):
        code_block = m.group(1)
        # add indentation to code_block
        indented_code = '\n'.join(('    ' + line if line.strip() else line) for line in code_block.split('\n'))
        return f'''            while not memory_manager.acquire_lock(\"live_state_{state_key}\", timeout=10):
                time.sleep(0.1)
            try:
{indented_code}
            finally:
                memory_manager.release_lock(\"live_state_{state_key}\")
            logger.info'''
    
    content = llm_pattern.sub(repl_llm, content)

    # Update Legacy mutation
    leg_pattern = re.compile(legacy_code_regex, re.DOTALL)
    
    def repl_leg(m):
        code_block = m.group(1)
        indented_code = '\n'.join(('    ' + line if line.strip() else line) for line in code_block.split('\n'))
        return f'''        while not memory_manager.acquire_lock(\"live_state_{state_key}\", timeout=10):
            time.sleep(0.1)
        try:
{indented_code}
        finally:
            memory_manager.release_lock(\"live_state_{state_key}\")
        return assignments'''
            
    content = leg_pattern.sub(repl_leg, content)

    with open(filepath, 'w') as f:
        f.write(content)

# Shelter Allocation
shelter_llm = r'            for s in ranked_shelters:(.*?)\s+logger\.info'
shelter_leg = r'        for s in ranked:(.*?)\s+return assignments'
update_file('backend/agents/shelter_allocation.py', 'shelters', 'shelters', shelter_llm, shelter_leg)

# Volunteer
vol_llm = r'            for llm_assign in assignments:(.*?)\s+logger\.info'
vol_leg = r'        for t in targets:(.*?)\s+return assignments'
update_file('backend/agents/volunteer_coordination.py', 'volunteers', 'volunteers', vol_llm, vol_leg)

# Resource
res_llm = r'            for assignment in assignments:(.*?)\s+logger\.info'
res_leg = r'        for t in targets:(.*?)\s+return assignments'
update_file('backend/agents/resource_allocation.py', 'resources', 'resources', res_llm, res_leg)
