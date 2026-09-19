"""Canonical physical layout, kinematic contact gate, and native input actuator."""
from dataclasses import dataclass
import numpy as np

DT=.002
KEYS=[]
def row(labels,z,offset=0):
    x=-.86+offset
    for code,label,width in labels:
        KEYS.append({'code':code,'label':label,'position':[round(x+width*.055,4),1.385,z], 'width':width*.105})
        x+=width*.115
row([('Escape','Esc',1),('Tab','Tab',1),('Backquote','`',1),('Backslash','\\',1),('MetaLeft','Cmd',1.3),('ArrowUp','↑',1),('ArrowDown','↓',1),('Home','Home',1),('End','End',1),('Delete','Del',1)],-.20)
row([(f'Digit{c}',c,1) for c in '1234567890']+[('Minus','-',1),('Equal','=',1),('Backspace','⌫',1.7)],-.08)
row([(f'Key{c.upper()}',c,1) for c in 'qwertyuiop']+[('BracketLeft','[',1),('BracketRight',']',1)],.04,.06)
row([(f'Key{c.upper()}',c,1) for c in 'asdfghjkl']+[('Semicolon',';',1),('Quote',"'",1),('Enter','Enter',1.4)],.16,.09)
row([('ShiftLeft','Shift',1.4)]+[(f'Key{c.upper()}',c,1) for c in 'zxcvbnm']+[('Comma',',',1),('Period','.',1),('Slash','/',1)],.28,.02)
row([('ControlLeft','Ctrl',1.3),('AltLeft','Alt',1.2),('Space','Space',4.5),('ArrowLeft','←',1),('ArrowRight','→',1),('F8','Run F8',1.7)],.40,.09)
BY_CODE={k['code']:k for k in KEYS}
MOUSE=[1,1.405,.32]
REST=[.18,1.58,.53]
SHIFTED={'<':'Comma','>':'Period','?':'Slash',':':'Semicolon','"':'Quote','_':'Minus','+':'Equal','!':'Digit1','@':'Digit2','#':'Digit3','$':'Digit4','%':'Digit5','^':'Digit6','&':'Digit7','*':'Digit8','(':'Digit9',')':'Digit0','{':'BracketLeft','}':'BracketRight','~':'Backquote','|':'Backslash'}
UNSHIFTED={',':'Comma','.':'Period','/':'Slash',';':'Semicolon',"'":'Quote','-':'Minus','=':'Equal','[':'BracketLeft',']':'BracketRight',' ':'Space','\n':'Enter','\t':'Tab','`':'Backquote','\\':'Backslash'}

def physical_key(char):
    if len(char)!=1:raise ValueError('Only one character per motor decision')
    if char in SHIFTED:return SHIFTED[char],True
    if char in UNSHIFTED:return UNSHIFTED[char],False
    if char.isascii() and char.isalpha():return 'Key'+char.upper(),char.isupper()
    if char in '0123456789':return 'Digit'+char,False
    raise ValueError(f'No physical key for {char!r}')

@dataclass(frozen=True)
class MotorAction:
    kind:str
    key:str|None=None
    x:float|None=None
    y:float|None=None
    button:str='left'
    delta:float=0

class ComputerActuator:
    """No type/fill/insert_text/evaluate write capability exists here.

A contact resolves a physical key by geometry, not by the intended key name.
Callbacks publish the causal pose BEFORE Chromium receives the event.
"""
    def __init__(self,computer,advance,publish):
        self.computer=computer;self.advance=advance;self.publish=publish
        self.position=np.array(REST);self.left=np.array([-.18,1.58,.53]);self.held=set();self.pointer=[0,0]
    @staticmethod
    def contact(position):
        x,y,z=position
        for key in KEYS:
            kx,ky,kz=key['position']
            if abs(x-kx)<=key['width']/2 and abs(z-kz)<=.043 and ky-.023<=y<=ky-.013:return key['code']
        return None
    async def pose(self,pos,phase,code=None,left=False):
        if left:self.left=np.asarray(pos)
        else:self.position=np.asarray(pos)
        await self.publish({'kind':'motor','phase':phase,'effector':self.position.tolist(),'left_effector':self.left.tolist(),'key':code,'held':sorted(self.held),'pointer':self.pointer})
    async def travel(self,target,code,left=False):
        start=(self.left if left else self.position).copy();target=np.asarray(target)
        for i in range(1,5):
            u=i/4;s=u*u*(3-2*u);pos=start+(target-start)*s;pos[1]+=.025*np.sin(np.pi*u)
            await self.advance(5);await self.pose(pos,'reach',code,left)
    async def perform(self,action:MotorAction):
        if action.kind in ('key_down','key_up'):
            if action.key not in BY_CODE:raise ValueError('Unknown physical key')
            key=BY_CODE[action.key];left=action.key.endswith('Left') and action.key in ('ShiftLeft','ControlLeft','AltLeft','MetaLeft')
            if action.kind=='key_down':
                target=np.array(key['position']);target[1]+=.025
                await self.travel(target,action.key,left)
                for i in range(1,3):
                    pos=target.copy();pos[1]-=.043*i/2
                    await self.advance(6);await self.pose(pos,'press',action.key,left)
                contact=self.contact(pos)
                if contact is None:raise RuntimeError('No physical contact: input withheld')
                self.held.add(contact)
                await self.pose(pos,'contact',contact,left)
                await self.computer.page.keyboard.down(contact)
                await self.publish({'kind':'browser_input','type':'keydown','key':contact,'contact':pos.tolist()})
            else:
                if action.key not in self.held:raise ValueError('Release without contact')
                self.held.remove(action.key)
                target=np.array(key['position']);target[1]+=.025
                await self.advance(10);await self.pose(target,'release',action.key,left)
                await self.computer.page.keyboard.up(action.key)
                await self.publish({'kind':'browser_input','type':'keyup','key':action.key})
        elif action.kind in ('mouse_move','mouse_down','mouse_up','scroll'):
            if action.kind=='mouse_move':
                await self.travel(MOUSE,'Mouse')
                self.pointer=[float(action.x),float(action.y)]
                await self.computer.page.mouse.move(*self.pointer)
            elif action.kind=='mouse_down':
                await self.travel(MOUSE,'Mouse');pos=np.array(MOUSE);pos[1]-=.018
                await self.advance(5);await self.pose(pos,'contact','Mouse')
                await self.computer.page.mouse.down(button=action.button)
            elif action.kind=='mouse_up':await self.computer.page.mouse.up(button=action.button)
            else:
                await self.travel(MOUSE,'Mouse');await self.computer.page.mouse.wheel(0,action.delta)
            await self.publish({'kind':'browser_input','type':action.kind,'pointer':self.pointer,'button':action.button,'delta':action.delta})
        else:raise ValueError('Unknown individual motor primitive')
    async def stroke(self,key):
        await self.perform(MotorAction('key_down',key));await self.perform(MotorAction('key_up',key))
    async def character(self,char,override=None):
        code,shift=physical_key(char)
        if shift:await self.perform(MotorAction('key_down','ShiftLeft'))
        await self.stroke(override or code)
        if shift:await self.perform(MotorAction('key_up','ShiftLeft'))
    async def focus(self):
        await self.perform(MotorAction('mouse_move',x=420,y=124))
        await self.perform(MotorAction('mouse_down'));await self.perform(MotorAction('mouse_up'))
        # A real End key is unnecessary: initial focus happens with an empty editor.
