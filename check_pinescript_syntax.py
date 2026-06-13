import sys

def check_balance(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # We want to check matching parens, brackets, braces, and quotes
    # but we must ignore comments (lines starting with //) and strings
    
    lines = content.split('\n')
    clean_code = []
    
    in_multiline_comment = False
    
    for line in lines:
        stripped = line.strip()
        # Pine script v6 doesn't have /* */ multiline comments by default, but let's check for standard //
        if stripped.startswith('//'):
            continue
        
        # Strip trailing comments if any
        # (Very simple check: find // not inside a string)
        in_string = False
        quote_char = None
        cleaned_line = []
        i = 0
        while i < len(line):
            char = line[i]
            if char in ('"', "'"):
                if not in_string:
                    in_string = True
                    quote_char = char
                    cleaned_line.append(char)
                elif char == quote_char:
                    # check if escaped
                    if i > 0 and line[i-1] == '\\':
                        # escaped quote
                        cleaned_line.append(char)
                    else:
                        in_string = False
                        cleaned_line.append(char)
                else:
                    cleaned_line.append(char)
            elif char == '/' and i + 1 < len(line) and line[i+1] == '/' and not in_string:
                # Comment starts, ignore rest of line
                break
            else:
                cleaned_line.append(char)
            i += 1
        clean_code.append(''.join(cleaned_line))
    
    full_clean = '\n'.join(clean_code)
    
    # Now check matching delimiters in full_clean
    stack = []
    delimiters = {')': '(', ']': '[', '}': '{'}
    openers = set(delimiters.values())
    
    in_string = False
    quote_char = None
    
    errors = []
    
    i = 0
    while i < len(full_clean):
        char = full_clean[i]
        if char in ('"', "'"):
            if not in_string:
                in_string = True
                quote_char = char
            elif char == quote_char:
                if i > 0 and full_clean[i-1] == '\\':
                    pass
                else:
                    in_string = False
        elif not in_string:
            if char in openers:
                stack.append((char, i))
            elif char in delimiters:
                expected = delimiters[char]
                if not stack:
                    errors.append(f"Unmatched closing '{char}' at index {i}")
                else:
                    top_char, top_idx = stack.pop()
                    if top_char != expected:
                        errors.append(f"Mismatched closing '{char}' at index {i}, expected '{top_char}' from index {top_idx}")
        i += 1
    
    while stack:
        top_char, top_idx = stack.pop()
        errors.append(f"Unmatched opening '{top_char}' at index {top_idx}")
        
    if errors:
        print(f"Found {len(errors)} errors:")
        for err in errors[:20]:
            print(" ", err)
    else:
        print("All delimiters balanced perfectly!")

if __name__ == '__main__':
    check_balance(r"c:\Users\ronan\.gemini\antigravity\scratch\india-swing-scanner\shaktimaan_v4.pine")
