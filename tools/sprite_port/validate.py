"""Checks every .tres/.tscn of a fighter: res:// paths exist, ext_resources come first, sub_resources
are defined before use, every ExtResource/SubResource id exists.   python validate.py cecilia"""
import os, re, sys, glob
PROJ=os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','..'))
def check(path):
    s=open(path,encoding='utf-8',errors='ignore').read(); errs=[]
    first_sub=min([i for i in [s.find('[sub_resource'),s.find('[node'),s.find('[resource]')] if i>=0] or [len(s)])
    heads=list(re.finditer(r'\[ext_resource(?:[^\]"]|"[^"]*")*\]',s))   # a quoted path may contain ']'
    for m in heads:
        if m.start()>first_sub: errs.append('ext_resource after sub/node: '+m.group(0)[:80])
        p=re.search(r'path="res://([^"]+)"',m.group(0))
        if p and not os.path.exists(os.path.join(PROJ,p.group(1))): errs.append('missing file: '+p.group(1))
    ext={i for m in heads for i in re.findall(r'(?<![a-z])id="([^"]+)"',m.group(0))}
    for i in set(re.findall(r'ExtResource\("([^"]+)"\)',s))-ext: errs.append('undefined ExtResource '+i)
    seen=set()
    for m in re.finditer(r'\[sub_resource(?:[^\]"]|"[^"]*")*?(?<![a-z])id="([^"]+)"(?:[^\]"]|"[^"]*")*\]|SubResource\("([^"]+)"\)|\[resource\]|\[node',s):
        if m.group(1): seen.add(m.group(1))
        elif m.group(2) and m.group(2) not in seen: errs.append('SubResource used before defined: '+m.group(2)); seen.add(m.group(2))
    return errs
if __name__=='__main__':
    char=sys.argv[1]; bad=0; n=0
    for f in glob.glob(os.path.join(PROJ,'actors',char,'**','*.tres'),recursive=True)+glob.glob(os.path.join(PROJ,'actors',char,'**','*.tscn'),recursive=True):
        fs=f.replace('\\','/')
        if '/3d' in fs or '_claude_checks' in fs: continue
        n+=1; e=check(f)
        if e: bad+=1; print(os.path.relpath(f,PROJ)); [print('   ',x) for x in e[:6]]
    print('checked',n,'files,',bad,'with problems')
