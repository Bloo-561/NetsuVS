"""Tiny reader/writer for Godot .tres text resources (enough for AnimationData / HitboxSettings)."""
import re
class Tres:
    def __init__(self, text=None):
        self.header=''; self.ext=[]; self.sub=[]; self.res=[]   # ext: dict(type,uid,path,id); sub: (id,type,body_lines); res: lines
        if text: self.parse(text)
    def parse(self, s):
        s=s.replace('\r\n','\n')
        blocks=re.split(r'\n(?=\[(?:ext_resource|sub_resource|resource)\b)', s)
        self.header=blocks[0].split('\n')[0]
        rest=blocks[0].split('\n',1)[1] if '\n' in blocks[0] else ''
        if rest.strip(): blocks.insert(1, rest.strip())
        for b in blocks[1:]:
            b=b.strip('\n')
            if not b.strip(): continue
            first,_,body=b.partition('\n')
            if first.startswith('[ext_resource'):
                a=dict(re.findall(r'(\w+)="([^"]*)"', first)); self.ext.append(a)
                if body.strip(): self.res_tail=body
            elif first.startswith('[sub_resource'):
                a=dict(re.findall(r'(\w+)="([^"]*)"', first))
                self.sub.append([a['id'], a.get('type','Resource'), [l for l in body.split('\n') if l.strip()]])
            elif first.startswith('[resource]'):
                self.res=[l for l in body.split('\n') if l.strip()]
    def uid(self):
        m=re.search(r'uid="([^"]+)"', self.header); return m.group(1) if m else None
    def ext_by_id(self, i):
        for e in self.ext:
            if e['id']==i: return e
    def ext_id_for_path(self, path):
        for e in self.ext:
            if e.get('path')==path: return e['id']
    def add_ext(self, typ, path, uid=None, prefer_id=None):
        i=self.ext_id_for_path(path)
        if i: return i
        ids={e['id'] for e in self.ext}
        i=prefer_id or 'x%d'%len(self.ext)
        n=0; base=i
        while i in ids: n+=1; i='%s_%d'%(base,n)
        e={'type':typ,'path':path,'id':i}
        if uid: e['uid']=uid
        self.ext.append(e); return i
    def sub_get(self, i):
        for s in self.sub:
            if s[0]==i: return s
    def script_of(self, body):
        for l in body:
            m=re.match(r'script = ExtResource\("([^"]+)"\)', l)
            if m:
                e=self.ext_by_id(m.group(1)); return e.get('path','') if e else ''
        return ''
    def res_get(self, key):
        for l in self.res:
            if l.startswith(key+' = '): return l[len(key)+3:]
    def res_set(self, key, value, after=None):
        for k,l in enumerate(self.res):
            if l.startswith(key+' = '):
                if value is None: del self.res[k]
                else: self.res[k]=f'{key} = {value}'
                return
        if value is None: return
        pos=len(self.res)
        if after:
            for k,l in enumerate(self.res):
                if l.startswith(after+' = '): pos=k+1
        self.res.insert(pos, f'{key} = {value}')
    def used_ids(self):
        txt='\n'.join(['\n'.join(s[2]) for s in self.sub]+self.res)
        return set(re.findall(r'ExtResource\("([^"]+)"\)',txt)), set(re.findall(r'SubResource\("([^"]+)"\)',txt))
    def prune(self):
        # drop sub/ext resources nothing references (repeat until stable)
        while True:
            ue,us=self.used_ids()
            n1=len(self.sub); self.sub=[s for s in self.sub if s[0] in us]
            n2=len(self.ext); self.ext=[e for e in self.ext if e['id'] in ue]
            if n1==len(self.sub) and n2==len(self.ext): break
    def order_subs(self):
        # a sub_resource must come after every sub_resource it references
        done=[]; seen=set(); bymap={s[0]:s for s in self.sub}
        def visit(s, stack=()):
            if s[0] in seen: return
            for r in re.findall(r'SubResource\("([^"]+)"\)','\n'.join(s[2])):
                if r in bymap and r not in stack: visit(bymap[r], stack+(s[0],))
            seen.add(s[0]); done.append(s)
        for s in self.sub: visit(s)
        self.sub=done
    def text(self):
        self.order_subs()
        out=[self.header,'']
        for e in self.ext:
            attrs=' '.join(f'{k}="{e[k]}"' for k in ['type','uid','path','id'] if k in e)
            out.append(f'[ext_resource {attrs}]')
        out.append('')
        for i,t,body in self.sub:
            out.append(f'[sub_resource type="{t}" id="{i}"]'); out+=body; out.append('')
        out.append('[resource]'); out+=self.res; out.append('')
        return '\n'.join(out)
