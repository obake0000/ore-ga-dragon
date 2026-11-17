"""Build the four-chapter Red Dragon edition from a reviewed full game."""
import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re

from PIL import Image

HERE = Path(__file__).resolve().parent
CHAPTERS = ('valley', 'dungeon', 'golem', 'maou')
SAVE_KEYS = ('best', 'easy', 'q', 'save', 'scn')

STYLE = '''
/* HONPEN_1118 */
.honpen #select .select-rail,.honpen #select #scn{display:none!important}
.honpen #select #seld{display:grid;max-width:560px;margin:0 auto 6px}
.honpen #select .select-info{width:min(560px,100%)}
.honpen #select .select-menu a{display:inline-flex;align-items:center;text-decoration:none}
.honpen #select .ttl .sub{margin-top:5px}
'''

MIGRATION = '''function migrateHonpenSave(){
 if(localStorage.getItem('dragon_honpen_save')!==null)return;
 if(Number(localStorage.getItem('dragon_scn')||1)!==1)return;
 const previous=localStorage.getItem('dragon_save');if(!previous)return;
 const save=JSON.parse(previous);
 if(!save||save.ch!=='dragon'||!Number.isInteger(save.reached)||save.reached<1||save.reached>=STAGES.length)return;
 if(save.ck&&(save.ck.ch!=='dragon'||save.ck.stage!==save.reached))return;
 localStorage.setItem('dragon_honpen_save',previous);
}
'''

def unique(source, old, new):
    if source.count(old) != 1:
        raise ValueError(f'Invalid or repeated full-game anchor: {old[:120]}')
    return source.replace(old, new, 1)

def unique_regex(source, pattern, replacement):
    result, count = re.subn(pattern, replacement, source)
    if count != 1:
        raise ValueError(f'Invalid or repeated full-game regex anchor: {pattern[:120]} ({count})')
    return result

def clean_text(data):
    return data.decode('utf-8').replace('\r\r\n', '\n').replace('\r\n', '\n')

def patch_game(data):
    s = clean_text(data)
    if '/* HONPEN_1118 */' in s:
        raise ValueError('Expected the full game as input')
    edits = {
        'models/manifest.json\',{cache:': 'models/honpen-manifest.json\',{cache:',
        'let light=mobileSmall()&&typeof entry.mobileFile': 'let light=typeof entry.mobileFile',
        '<body>':'<body class="honpen">',
        '<title>俺がドラゴン。転生したらドラゴンだったので勇者も魔王も丸焼きにします。</title>':
          '<title>俺がドラゴン。 本編</title>',
        '<meta property="og:url" content="https://obake0000.github.io/ore-ga-dragon/">':
          '<meta property="og:url" content="https://obake0000.github.io/ore-ga-dragon/honpen.html">',
        '<div class="sub">キャラをえらんで、魔物・軍隊・海の怪物・古の竜を倒せ</div>':
          '<div class="sub">本編 · レッドドラゴンで地下の迷宮へ</div>',
        '<button class="btn sm" id="quit">竜をえらびなおす</button>':
          '<button class="btn sm" id="quit">本編メニューに戻る</button>',
        "function scnHas(n){return !!SCK[n]": "function scnHas(n){return n===1&&!!SCK[n]",
        'function setScn(n){SCN=scnHas(n)?n:1;': 'function setScn(n){SCN=1;',
        "const scnApply=n=>{if(state!=='select')return;": "const scnApply=n=>{if(n!==1||state!=='select')return;",
        'function setChar(k){P.dvE=': "function setChar(k){k='dragon';P.dvE=",
        "setChar=function(k){if(mobileArt.start&&mobileArt.start.key!==k)":
          "setChar=function(k){k='dragon';if(mobileArt.start&&mobileArt.start.key!==k)",
        "return CH[s.ch]?s.ch:null;": "return 'dragon';",
        "if(s&&s.reached>0&&s.reached<STAGES.length)": "if(s&&Number.isInteger(s.reached)&&s.reached>0&&s.reached<STAGES.length)",
        'function mobileWaveIds(i,n){const key=STAGES[i]?.key;return MOBILE_DEPS.waves?.[key]?.[n]||[];}':
          "function mobileWaveIds(i,n){const key=STAGES[i]?.key;return key==='valley'&&n>=2?[]:MOBILE_DEPS.waves?.[key]?.[n]||[];}",
        "rcCards();krCards();": "",
        "skvPreview(charKey,o[0],true)": "skvPreview(charKey,o[0])",
        "function frame(now){\n  requestAnimationFrame(frame);":
          "function frame(now){\n  requestAnimationFrame(frame);\n  if(!$('title').dataset.off){last=now;return;}",
    }
    for old, new in edits.items():
        s = unique(s, old, new)
    s = unique_regex(s, r'(<link rel="icon"[^\n]+)\n', lambda m:m[0]+'<style>'+STYLE+'</style>\n')
    s = unique_regex(s, r'<video class="v1"[^<]+</video><video class="v2"[^<]+</video>', '')
    s = unique_regex(s, r'(?s)// 表紙の動く2コマ[^\n]+\n.*?(?=let bannerT=0,speechT=0;)', '')
    s = unique_regex(s, r'(?m)^.*font\.href=[^\n]+\n.*document\.head\.appendChild\(font\);\n.*\}\n', '')
    s = unique_regex(s, r'(?m)^ if\(!mobileSmall\(\)&&matchMedia\(\'\(pointer:fine\)\'\)[^\n]+\n[^\n]+font\.rel=\'stylesheet\';\n', '')
    s = unique_regex(s, r'(<button class="btn sm" id="scn") title="[^"]+"', r'\1 hidden disabled')
    s = unique_regex(s, r'(<a class="btn sm" id="zukanBtn"[^\n]+?</a>)', r'\1<a class="btn sm" href="index.html">入口へ</a>')
    s = unique_regex(s, r"(\$\('wazaG'\)\.innerHTML=)\['dragon'[^\n]+?\.map\(k=>", r"\1['dragon'].map(k=>")
    s = unique_regex(s, r"(const box_=\$\('cards'\);for\(const k of )\['dragon'[^\]\n]+\](\)\{const c=CH\[k\])", r"\1['dragon']\2")
    s, card_writers = re.subn(r"(document\.querySelector\('#cards \.card\[data-k=[^\n]+?\.ds'\))\.textContent=(CH[^;]+);",
                              r'\1?.replaceChildren(\2);',s)
    if card_writers != 3:
        raise ValueError(f'Full-game card writer count changed: {card_writers}')
    s = unique_regex(s, r"(?m)^\{const im=new Image\(\);im\.onload=\(\)=>\{TPT\['大天使'\].*?im\.src='chara/archangel\.webp';\}\n", '')
    s = unique_regex(s, r"(?m)^\{const im=new Image\(\);im\.onload=\(\)=>\{S7\.face=true;.*?im\.src='chara/seaking\.webp';\}\n", '')
    s = unique_regex(s, r"(?m)^\{const im=new Image\(\);im\.onload=\(\)=>\{TPT\['黒い騎士'\].*?im\.src='chara/blackknight\.webp';\}\n", '')
    s = unique_regex(s, r"(?m)^setTimeout\(\(\)=>\{try\{PTE\.dking='👑';PTE\.gkeep='💀';\nfetch\('chara/npc_dragonking\.webp'[^\n]+\n", '')
    preload = "sl.forEach(o=>{const im=new Image();im.src=storyImageV2(o.img);});"
    if s.count(preload) != 2:
        raise ValueError('Expected both chapter and mid-battle slideshow prefetches')
    s = s.replace(preload, '')
    if s.count('story/kv2.webp') < 3:
        raise ValueError('Title and menu cover references missing')
    s = s.replace('story/kv2.webp','story/honpen-cover.webp')
    # Existing listeners still read these controls when returning from a fight.
    s = s.replace('竜をえらびなおす','本編メニューに戻る').replace('キャラをえらびなおす','本編メニューに戻る')
    for key in SAVE_KEYS:
        old = f"'dragon_{key}'"
        if not s.count(old):
            raise ValueError(f'Expected storage key {old}')
        s = s.replace(old, f"'dragon_honpen_{key}'")
    return unique(s, 'function loadGame(){try{', MIGRATION+'function loadGame(){try{migrateHonpenSave();')

def authored_dependencies(s):
    packed = re.search(r'const MOBILE_DEPS=(\{[^\n]+\});',s)
    deps = json.loads(packed[1])
    allow = set(deps['characters']['dragon'])
    for chapter in CHAPTERS:
        allow.update(deps['stages'][chapter])
        waves = deps['waves'][chapter][:2] if chapter=='valley' else deps['waves'][chapter]
        for wave in waves:
            allow.update(wave)
    return allow

def small_cover(original):
    with Image.open(original) as image:
        image.thumbnail((768,768), Image.Resampling.LANCZOS)
        out = BytesIO()
        image.save(out,format='WEBP',quality=83,method=6)
        return out.getvalue()

def build(game, manifest_path, cover, output, dependency_path):
    original = game.read_bytes()
    html = patch_game(original)
    manifest = json.loads(manifest_path.read_bytes())
    audited = json.loads(dependency_path.read_bytes())
    expected = authored_dependencies(html)|set(audited['dynamic_ids'])
    missing = expected-set(manifest)-set(audited.get('intentional_fallback_ids',[]))
    if missing:
        raise ValueError(f'Manifest audit must resolve IDs with no published model: {sorted(missing)}')
    filtered = {key:value for key,value in manifest.items() if key in expected}
    missing_mobile = [key for key,row in filtered.items() if not row.get('mobileFile') or not row.get('mobileVersion')]
    if missing_mobile:
        raise ValueError(f'Missing mobile file for {missing_mobile}')
    files = {'honpen.html':html.encode('utf-8'),
             'models/honpen-manifest.json':(json.dumps(filtered,ensure_ascii=False,separators=(',',':'))+'\n').encode(),
             'story/honpen-cover.webp':small_cover(cover)}
    for name, value in files.items():
        path=output/name
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(value)
    details={'from_index_sha256':hashlib.sha256(original).hexdigest(),
             'models':len(filtered),'full_models':len(manifest),
             'active_enemy_chapters':list(CHAPTERS),'active_player':'dragon', 'MODEL_IDS':list(filtered),
             'files':[{'path':path,'bytes':len(value),'sha256':hashlib.sha256(value).hexdigest()} for path,value in files.items()],
             'cover_source_bytes':cover.stat().st_size,
             'mobile_asset_bytes':sum(row['mobileBytes'] for row in filtered.values())}
    return details

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    repository = HERE.parent
    parser.add_argument('--game',type=Path,default=repository/'source/game.html')
    parser.add_argument('--manifest',type=Path,default=repository/'models/manifest.json')
    parser.add_argument('--cover',type=Path,default=repository/'story/kv2.webp')
    parser.add_argument('--out',type=Path,default=repository)
    parser.add_argument('--dependencies',type=Path,default=HERE/'honpen-dependencies.json')
    parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    result=build(args.game,args.manifest,args.cover,args.out,args.dependencies)
    if args.report:
        args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f"Built honpen.html and {result['models']} model entries")
