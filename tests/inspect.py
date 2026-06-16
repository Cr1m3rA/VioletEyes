import re, sys
html = open(r'C:\Users\Jerome\Documents\VioletEyes\tests\fixtures\code-audit-report.html', encoding='utf-8').read()
m = re.search(r'<article id="FND-0001".*?</article>', html, re.DOTALL)
if not m:
    print("no FND-0001"); sys.exit(1)
s = m.group(0)
print('article length:', len(s))
print('chain-tabs in FND-0001:', s.count('chain-tabs'))
print('chain-tree in FND-0001:', s.count('chain-tree'))
print('mermaid in FND-0001:', s.count('mermaid'))
print('mermaid-render callsite in this article:', s.count("mermaid.render"))
m2 = re.search(r'调用链.*?(?=漏洞代码|复现步骤|PoC|修复)', s, re.DOTALL)
if m2:
    print('--- call-chain block (first 2000) ---')
    print(m2.group(0)[:2000])