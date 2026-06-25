import os

def add_import_to_file(filepath):
    import_line = 'from utils.execution_tracer import log_execution\n'
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Check if import already exists
    for line in lines:
        if 'from utils.execution_tracer import log_execution' in line:
            return  # already present

    # Find where to insert import: after other imports, before first function/class or at top
    insert_at = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('import ') or stripped.startswith('from '):
            insert_at = i + 1
        elif stripped.startswith('def ') or stripped.startswith('class ') or stripped.startswith('if __name__'):
            break

    lines.insert(insert_at, import_line)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(lines)

def main():
    root = os.path.dirname(os.path.abspath(__file__))
    for dir_name in ['views', 'services']:
        dir_path = os.path.join(root, dir_name)
        if not os.path.isdir(dir_path):
            continue
        for file_name in os.listdir(dir_path):
            if file_name.endswith('.py') and file_name != '__init__.py':
                filepath = os.path.join(dir_path, file_name)
                print(f'Adding import to {filepath}')
                add_import_to_file(filepath)

if __name__ == '__main__':
    main()