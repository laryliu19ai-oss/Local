import re

for p in ['/home/lary/skill/bvShortcut.il', '/home/lary/skill/skill/bvShortcut.il']:
    c = open(p).read()
    matches = list(re.finditer(r'procedure\(\s*bvSim\(', c))
    print(p, 'matches:', len(matches))
    if len(matches) > 1:
        first_idx = matches[0].start()
        last_idx = matches[-1].start()
        # Find where bvSimProcessData starts if present before last_idx
        proc_data_idx = c.rfind('procedure( bvSimProcessData', 0, last_idx)
        if proc_data_idx != -1:
            c = c[:proc_data_idx] + c[proc_data_idx:]
        else:
            c = c[:first_idx] + c[last_idx:]
        open(p, 'w').write(c)
        print('Cleaned in', p)
