import os
import sys

def add_decorator_to_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        new_lines.append(line)
        # Check if line is a function definition
        stripped = line.lstrip()
        if stripped.startswith('def ') and not stripped.startswith('def __'):
            # Look for indentation
            indent = len(line) - len(line.lstrip())
            # Insert decorator line before the def line
            decorator = ' ' * indent + '@log_execution\n'
            # Insert before current line
            new_lines[-1] = decorator + line
        i += 1

    # Write back
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

def main():
    # Import the tracer to ensure it's importable
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    # Add import statement at top of each file? We'll handle separately
    # For now, just add decorator
    root = os.path.dirname(os.path.abspath(__file__))
    for dir_name in ['views', 'services']:
        dir_path = os.path.join(root, dir_name)
        if not os.path.isdir(dir_path):
            continue
        for file_name in os.listdir(dir_path):
            if file_name.endswith('.py') and file_name != '__init__.py':
                filepath = os.path.join(dir_path, file_name)
                print(f'Processing {filepath}')
                add_decorator_to_file(filepath)

if __name__ == '__main__':
    main()