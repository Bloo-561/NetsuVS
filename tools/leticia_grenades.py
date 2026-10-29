import re, math, os
R='/mnt/user-data/uploads/NetsuVSS/actors/leticia/'
G=200000.0          # bounce gravity, units/s^2 (20 m/s^2)
DELAY=15            # second grenade explodes this many frames after the first
APEX_SCALE=0.68     # peaks lowered from the sketches
END_HS={'A':0.8,'B':0.8,'C':1.2}   # explosion centre above the floor (m): low, the blast's bottom ~0.3 m under the floor (A/B blast 2.2 m, C 3.0 m)
KICK_SPEED=0.30     # m per frame along the kick line
HOP_V, HOP_G = 90000, 250000
HOP_X={'A':-12000,'B':30000,'C':-12000}
SPAWN_Y=0.80        # TargetPosition y (8000) in m
# hop height (m) at the spawn frame, ground versions
def hop_h(jf, sf):
    t=(sf-jf)/60; return (HOP_V*t-0.5*HOP_G*t*t)/10000
REL={'A':0.80+hop_h(6,22),'B':0.80+hop_h(6,24),'C':0.80+hop_h(4,15)}
# sketch paths, metres, x along her facing. floor = floor hit x from release;
# apex/end relative to the release x, heights above the floor. apex None = still rising at the end.
PATH={
 'A1':dict(floor=0.43, apex=(2.00,4.06), end=(3.19,1.58)),
 'A2':dict(floor=2.77, apex=(1.79,4.70), end=(1.18,1.90)),
 'B1':dict(floor=-2.18,apex=(0.88,4.04), end=(2.70,2.05)),
 'B2':dict(floor=-0.56,apex=(-0.06,2.95),end=(0.20,1.46)),
 'C1':dict(floor=5.10, apex=(2.30,2.63), end=(0.54,1.60)),
 'C2':dict(floor=0.94, apex=(1.90,1.90), end=(2.52,1.40)),
}
NAMES=['A1','A2','B1','B2','C1','C2']
def u(m_per_s): return int(round(m_per_s*10000/100)*100)

def shape(n):
    p=PATH[n]; END_H=END_HS[n[0]]
    ex=p['end'][0]
    if p['apex'] is None: return None,(ex,END_H)
    ax,ah=p['apex']; return (ax,max(ah*APEX_SCALE, END_H+0.5)),(ex,END_H)
GN={}   # per-piece gravity override (m/s^2)
def arc_plan(n):
    p=PATH[n]; f=p['floor']; g=GN.get(n,G/10000)
    apex,end=shape(n)
    if apex is None:
        ex,eh=end; t1=math.sqrt(2*eh/g); N1=max(1,round(t1*60)); vx1=(ex-f)/(N1/60)
        return dict(vy0=g*N1/60, N1=N1, N=N1, vx1=vx1, vx2=vx1)
    ax,ah=apex; ex,eh=end
    N1=round(math.sqrt(2*ah/g)*60); N2=max(1,round(math.sqrt(2*(ah-eh)/g)*60))
    return dict(vy0=g*N1/60, N1=N1, N=N1+N2, vx1=(ax-f)/(N1/60), vx2=(ex-ax)/(N2/60))

def kick_plan(n):
    h=REL[n[0]]; f=PATH[n]['floor']; d=math.hypot(f,h); T=max(3,round(d/KICK_SPEED))
    return u(f/(T/60)), u(-h/(T/60)), T

HDR='''[gd_resource type="Resource" script_class="FighterState" format=3]

[ext_resource type="Resource" path="res://actors/leticia/projectiles/AnimationData/{anim}" id="1"]
[ext_resource type="Script" uid="uid://bgwrlqrhqb2a4" path="res://engine/sakuga/Resources/FrameDataEvents/Actions/MoveXAction.cs" id="2"]
[ext_resource type="Script" uid="uid://bw1835rb2hj7y" path="res://engine/sakuga/Resources/FrameDataEvents/Actions/MoveYAction.cs" id="3"]
[ext_resource type="Script" uid="uid://c076jc3huncn2" path="res://engine/sakuga/Resources/FrameDataEvents/FrameDataEvent.cs" id="4"]
[ext_resource type="Script" uid="uid://50grsd2r3wl8" path="res://engine/sakuga/Resources/FrameDataEvents/Conditions/AtFrameCondition.cs" id="5"]
[ext_resource type="Script" uid="uid://da4kqpf635oin" path="res://engine/sakuga/Resources/FrameDataEvents/Actions/PlayStateAction.cs" id="6"]
[ext_resource type="Script" uid="uid://c42r1mjvviuhg" path="res://engine/sakuga/Resources/FrameDataEvents/Conditions/AtFrameRangeCondition.cs" id="7"]
[ext_resource type="Script" path="res://engine/sakuga/Resources/FrameDataEvents/Conditions/OnWallsCondition.cs" id="8"]
[ext_resource type="Script" uid="uid://n7xih8pqfpwo" path="res://engine/sakuga/Resources/FrameDataEvents/Actions/ChangeSideAction.cs" id="9"]
[ext_resource type="Script" uid="uid://bf60srwkccsm8" path="res://engine/sakuga/Resources/FighterState.cs" id="10"]
'''
def write_arc(i,n):
    pl=arc_plan(n); subs=[]; k=[0]
    def sub(body):
        k[0]+=1; subs.append(f'[sub_resource type="Resource" id="s{k[0]}"]\n{body}\n'); return f's{k[0]}'
    def ev(conds,acts):
        c=f'Conditions = [{", ".join(f"SubResource(\"{x}\")" for x in conds)}]\n' if conds else ''
        return sub(f'script = ExtResource("4")\n{c}Actions = [{", ".join(f"SubResource(\"{x}\")" for x in acts)}]')
    mx=lambda v: sub(f'script = ExtResource("2")\nVelocity = {v}')
    my=lambda v: sub(f'script = ExtResource("3")\nVelocity = {v}')
    at=lambda f: sub(f'script = ExtResource("5")\nFrame = {f}')
    rng=lambda a,b: sub(f'script = ExtResource("7")\nMinFrame = {a}\nMaxFrame = {b}')
    g=GN.get(n,G/10000)*10000
    vy=lambda f: int(round((pl['vy0']*10000 - g*(f+0.5)/60)/100)*100)
    vx1,vx2=u(pl['vx1']),u(pl['vx2'])
    enter=ev([], [mx(vx1), my(vy(0))])
    ticks=[]
    for f in range(1,pl['N']):
        acts=[my(vy(f))]
        if f==pl['N1'] and vx2!=vx1: acts.insert(0,mx(vx2))
        ticks.append(ev([at(f)],acts))
    # walls: bounce off (flip side, keep the phase's speed)
    ticks.append(ev([rng(1,pl['N1']-1), sub('script = ExtResource("8")')],[sub('script = ExtResource("9")'), mx(vx1)]))
    if pl['N']>pl['N1']:
        ticks.append(ev([rng(pl['N1'],pl['N']), sub('script = ExtResource("8")')],[sub('script = ExtResource("9")'), mx(vx2)]))
    boom=ev([at(pl['N'])],[sub(f'script = ExtResource("6")\nStateIndex = {14 if n[0]=="C" else 13}')])
    name=f'LFR_{i+7}_{n}_Arc'
    txt=HDR.format(anim=name+'_AnimData.tres')+'\n'+'\n'.join(subs)+f'''
[resource]
script = ExtResource("10")
StateName = "Fragment {n} bounce"
Type = 2
AnimationData = ExtResource("1")
TransitionEvents = [SubResource("{boom}")]
OnEnterEvents = [SubResource("{enter}")]
OnTickEvents = [{", ".join(f'SubResource("{t}")' for t in ticks)}]
OnExitEvents = null
OnHitConfirmEvents = null
OnHitReactionEvents = null
'''
    open(R+f'projectiles/States/{name}.tres','w').write(txt)
    # animation: glow cycles every 3 frames to the end
    ap=R+f'projectiles/AnimationData/{name}_AnimData.tres'; a=open(ap).read()
    head=a.split('[sub_resource')[0]
    tex=['1','4','5','6','7','8','9','10']; out=[]; refs=[]; s=0
    for j,fr in enumerate(range(0,pl['N']+4,3)):
        s+=1; out.append(f'[sub_resource type="Resource" id="s{s}"]\nscript = ExtResource("2")\nSprite = ExtResource("{tex[j%8]}")\nOffset = Vector2(-110, -20)\n')
        s+=1; out.append(f'[sub_resource type="Resource" id="s{s}"]\nscript = ExtResource("3")\n'+(f'AtFrame = {fr}\n' if fr else '')+f'Modifiers = [SubResource("s{s-1}")]\n'); refs.append(f's{s}')
    s+=1; out.append(f'[sub_resource type="Resource" id="s{s}"]\nscript = ExtResource("12")\nHitboxData = ExtResource("11")\n')
    a2=head+'\n'.join(out)+f'''
[resource]
script = ExtResource("13")
Duration = {pl['N']+4}
Animations = [{", ".join(f'SubResource("{r}")' for r in refs)}]
Hitboxes = [SubResource("s{s}")]
'''
    open(ap,'w').write(a2)
    return pl

def write_kick(i,n):
    vx,vy,T=kick_plan(n); p=R+f'projectiles/States/LFR_{i+1}_{n}_Kick.tres'; t=open(p).read()
    t=re.sub(r'(id="s1"\]\nscript = ExtResource\("2"\)\nVelocity = )-?\d+', rf'\g<1>{vx}', t)
    t=re.sub(r'(id="s2"\]\nscript = ExtResource\("3"\)\nVelocity = )-?\d+', rf'\g<1>{vy}', t)
    t=re.sub(r'(id="s14"\]\nscript = ExtResource\("2"\)\nVelocity = )-?\d+', rf'\g<1>{vx}', t)
    open(p,'w').write(t); return vx,vy,T

# stagger: the later grenade of each pair explodes DELAY frames after the earlier one
for v in 'ABC':
    a,b=v+'1',v+'2'
    tot=lambda n: kick_plan(n)[2]+arc_plan(n)['N']
    first,second=(a,b) if tot(a)<=tot(b) else (b,a)
    # only ever slow a grenade down: stretch whichever one closes the gap to DELAY
    if tot(second)-tot(first) < DELAY: who,target=second,tot(first)+DELAY
    else: who,target=first,tot(second)-DELAY
    lo,hi=4.0,G/10000
    for _ in range(60):
        mid=(lo+hi)/2; GN[who]=mid
        if tot(who)>target: lo=mid
        else: hi=mid
    if tot(who)<target: GN[who]=lo
    print(v,a,tot(a),b,tot(b),'stretched',who,'g %.1f'%GN[who])
for i,n in enumerate(NAMES):
    kv=write_kick(i,n); pl=arc_plan(n); write_arc(i,n)
    print(n,'kick vx,vy,T',kv,'| arc vy0 %.0f N1 %d N %d vx1 %d vx2 %d'%(pl['vy0']*10000,pl['N1'],pl['N'],u(pl['vx1']),u(pl['vx2'])))

DO_HOP_AND_SPRITES=False   # already applied Oct 28; re-running would add Scale twice
if DO_HOP_AND_SPRITES:
    # Leticia hop
    for v in 'ABC':
        for f in (f'States/LET_214{v}_Frag.tres', f'States/LET_j214{v}.tres'):
            t=open(R+f).read()
            t=t.replace('Velocity = 136000',f'Velocity = {HOP_V}').replace('Force = 320000',f'Force = {HOP_G}')
            t=re.sub(r'Velocity = -?28000', f'Velocity = {HOP_X[v]}', t)
            open(R+f,'w').write(t)
    # sprites: scale 0.8 (match her normal sprites), feet on the board deck
    S=0.8
    for v in 'ABC':
        for f in (f'AnimationData/LET_214{v}_Frag_AnimData.tres', f'AnimationData/LET_j214{v}_AnimData.tres'):
            t=open(R+f).read()
            def fix(m):
                spr,x,y=m.group(1),int(m.group(2)),int(m.group(3))
                if spr=='2': ny=0     # board, drawn at (-200,0) after scale
                else: ny=50           # body bottom at 40 px (on the deck)
                return f'Sprite = ExtResource("{spr}")\nOffset = Vector2({x}, {ny})\nScale = Vector2({S}, {S})'
            t=re.sub(r'Sprite = ExtResource\("(\d+)"\)\nOffset = Vector2\((-?\d+), (-?\d+)\)',fix,t)
            open(R+f,'w').write(t)
print(REL)
