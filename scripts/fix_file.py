content = open('scripts/distribute_questions.py', 'r', encoding='utf-8').read()
content = content.replace('{updated})"', '{updated})"  # temp').replace('{updated})"  # temp', '{updated})"')  # cleanup
content = content.replace('"{updated})"', '"{updated}"')
open('scripts/distribute_questions.py', 'w', encoding='utf-8').write(content)
print('Fixed')
