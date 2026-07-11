import re

with open('G:\\tool\\templates\\tools\\retirement_planning_calculator.html', 'r', encoding='utf-8') as f:
    content = f.read()

issues = []

opens = content.count('{')
closes = content.count('}')
if opens != closes:
    issues.append(f'Brace mismatch: {opens} opens vs {closes} closes')

opens = content.count('(')
closes = content.count(')')
if opens != closes:
    issues.append(f'Paren mismatch: {opens} opens vs {closes} closes')

opens = content.count('[')
closes = content.count(']')
if opens != closes:
    issues.append(f'Bracket mismatch: {opens} opens vs {closes} closes')

script_start = content.find('<script nonce=')
script_end = content.find('</script>', script_start)
js = content[script_start:script_end]

dollar_in_js = re.findall(r'"\$\d', js)
if dollar_in_js:
    issues.append(f'Hardcoded dollar amounts in JS: {dollar_in_js}')

if issues:
    for i in issues:
        print(f'ISSUE: {i}')
else:
    print('All checks passed: balanced delimiters, no hardcoded $ in JS')

# Count total lines
lines = content.split('\n')
print(f'Total lines: {len(lines)}')
print(f'Total bytes: {len(content)}')
