import json, os, glob, sys, re
sys.stdout.reconfigure(errors='replace')

data_dir = os.path.join('data', 'blogs')
files = sorted(glob.glob(os.path.join(data_dir, '*.json')), key=os.path.getmtime, reverse=True)
if files:
    with open(files[0], 'r', encoding='utf-8') as f:
        data = json.load(f)
    for key, val in data.items():
        if isinstance(val, dict) and val.get('naver_images'):
            plan = val['naver_images']
            for i, line in enumerate(plan.split('\n')):
                low = line.lower()
                if any(k in low for k in ['이미지', 'gemini', 'imagen', '프롬프트', 'prompt']):
                    print(f'L{i:03d}: {line[:150]}')
                if '```' in line:
                    print(f'L{i:03d}: {line[:150]}')
            break
