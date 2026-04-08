import sys
sys.stdout.reconfigure(errors='replace')
import json, os, glob
import imagen_client

# 실제 저장된 이미지 플랜에서 테스트
data_dir = os.path.join('data', 'blogs')
files = sorted(glob.glob(os.path.join(data_dir, '*.json')), key=os.path.getmtime, reverse=True)
if files:
    with open(files[0], 'r', encoding='utf-8') as f:
        data = json.load(f)
    for key, val in data.items():
        if isinstance(val, dict) and val.get('naver_images'):
            plan = val['naver_images']
            prompts = imagen_client.parse_image_prompts(plan)
            print(f'Parsed {len(prompts)} prompts from topic {key}:')
            for i, p in enumerate(prompts):
                print(f'  [{i+1}] {p[:120]}...')
            break
