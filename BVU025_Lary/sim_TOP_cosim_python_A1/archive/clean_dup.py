import re

for p in ['/home/lary/skill/bvShortcut.il', '/home/lary/skill/skill/bvShortcut.il']:
    c = open(p).read()
    matches = list(re.finditer(r'procedure\(\s*bvSim\(', c))
    print(p, 'matches:', len(matches))
    if len(matches) > 1:
        first_idx = matches[0].start()
        last_idx = matches[-1].start()
        c = c[:first_idx] + c[last_idx:]
        open(p, 'w').write(c)
        print('Cleaned duplicate in', p)
