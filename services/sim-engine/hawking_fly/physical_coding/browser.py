"""The only source-writing capability is Chromium's native input handling.

set_content is used once, BEFORE a session starts, to create an empty IDE.
The evaluator can read source/audit records. The policy receives PNG bytes only.
"""
import html
import io
from datetime import datetime, timezone
from PIL import Image
from playwright.async_api import async_playwright

WIDTH, HEIGHT = 1200, 600
FONT = "20px/28px 'Courier New',monospace"
# Fixed retinal windows are an engineered sensor; none reads DOM information.
REGIONS = [(16,112,24), (416,112,32), (816,112,24)]

def workspace(target, starter=''):
    # starter is used by OFFLINE training fixtures only; live sessions require ''.
    return '''<!doctype html><meta charset="utf-8"><style>
*{box-sizing:border-box}body{margin:0;background:#161c28;color:#dbe3ef;font:14px Arial}header{height:60px;padding:20px;border-bottom:1px solid #354056}main{display:grid;grid-template-columns:400px 400px 400px}section{height:540px;border-right:1px solid #354056}h2{height:52px;font:12px Arial;letter-spacing:2px;margin:0;padding:20px 16px}iframe{width:400px;height:420px;border:0;background:white}textarea{display:block;box-sizing:border-box;width:400px;height:420px;padding:0 16px;border:0;outline:none;resize:none;white-space:pre;overflow:hidden;background:#fff;color:#111;font:20px/28px 'Courier New',monospace;caret-color:#1fffff;caret-animation:manual}iframe,textarea{filter:invert(1)}textarea:focus{box-shadow:inset 0 -5px #387dce}button{margin:12px 16px;padding:8px 22px;background:#354e79;color:white;border:0}#dirty{display:inline-block;width:20px;height:20px;background:#b9b9b9}#focus{position:absolute;left:780px;top:72px;width:10px;height:10px;background:#bbb}
</style><header>FlyLab · actual Chromium workspace · F8 runs index.html</header><main>
<section><h2>BUILD THIS</h2><iframe id="target" sandbox srcdoc="'''+html.escape(render_doc('<h1>'+html.escape(target)+'</h1>'),quote=True)+'''"></iframe></section>
<section><h2>INDEX.HTML · EMPTY PROJECT</h2><span id="focus"></span><textarea id="editor" spellcheck="false" autocomplete="off" autocorrect="off" autocapitalize="off" wrap="off" aria-label="index.html">'''+html.escape(starter)+'''</textarea><button id="run">Run · F8</button><span id="dirty"></span></section>
<section><h2>ACTUAL BROWSER OUTPUT</h2><iframe id="preview" sandbox="allow-scripts"></iframe></section></main><div id="console" style="position:absolute;bottom:0;left:0;right:0;height:25px;padding:5px 16px;background:#101622;color:#a6b6ce;font:11px monospace">CONSOLE · ready</div>
<script>
const editor=document.querySelector('#editor'), preview=document.querySelector('#preview');
window.audit={events:[],revision:0,runs:0,errors:[],runSource:''};
const theme=`<meta http-equiv='Content-Security-Policy' content=\"default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'\"><style>body{margin:0;padding:0 16px;color:#111;background:white;font:20px/28px 'Courier New',monospace}h1{margin:0;font:inherit;white-space:pre}</style>`;
const errorReporter="<script>window.addEventListener('error',e=>parent.postMessage({codingError:e.message},'*'))<"+"/script>";
const render=()=>{preview.srcdoc=theme+errorReporter+editor.value;window.audit.runSource=editor.value;window.audit.runs++;document.querySelector('#dirty').style.background='#387dce';};
window.addEventListener('message',e=>{if(e.source===preview.contentWindow&&e.data?.codingError){window.audit.errors.push({message:String(e.data.codingError),time:performance.now()});document.querySelector('#console').textContent='ERROR · '+String(e.data.codingError);}});
// Native input changes the textarea. This listener ONLY observes and runs it.
editor.addEventListener('input',e=>{window.audit.revision++;window.audit.events.push({type:'input',trusted:e.isTrusted,data:e.data,inputType:e.inputType,source:editor.value,caret:editor.selectionStart,revision:window.audit.revision,time:performance.now()});document.querySelector('#dirty').style.background='#c29036';preview.srcdoc=theme+errorReporter+editor.value;});
for(const type of ['keydown','keyup','mousedown','mouseup','wheel'])document.addEventListener(type,e=>{window.audit.events.push({type,key:e.key,code:e.code,button:e.button,trusted:e.isTrusted,time:performance.now()});});
editor.addEventListener('focus',()=>document.querySelector('#focus').style.background='#387dce');
editor.addEventListener('blur',()=>document.querySelector('#focus').style.background='#bbb');
document.querySelector('#run').addEventListener('click',render);
document.addEventListener('keydown',e=>{if(e.key==='F8'){e.preventDefault();render();}});
preview.srcdoc=theme;
</script>'''

def render_doc(source):
    return "<style>body{margin:0;padding:0 16px;color:#111;background:white;font:"+FONT+"}h1{margin:0;font:inherit;white-space:pre}</style>"+source

class BrowserComputer:
    async def open(self,target,*,starter='',training=False):
        if starter and not training:raise ValueError('Live editor must begin empty')
        self.pw=await async_playwright().start()
        try:
            self.browser=await self.pw.chromium.launch(headless=True)
            self.context=await self.browser.new_context(viewport={'width':WIDTH,'height':HEIGHT},device_scale_factor=1)
            self.page=await self.context.new_page()
            # Freeze browser timers; session ticks explicitly advance this clock.
            now=datetime(2026,1,1,tzinfo=timezone.utc)
            await self.page.clock.install(time=now)
            await self.page.clock.pause_at(now)
            await self.page.set_content(workspace(target,starter))
            await self.page.locator('#target').wait_for()
            await self.page.screenshot() # wait for layout/fonts before first observation
            self.started=True
            return self
        except BaseException:
            await self.close();raise
    async def advance(self,ms):await self.page.clock.run_for(ms)
    async def screenshot(self):return await self.page.screenshot(type='png',caret='initial')
    async def audit(self):
        # Privileged READ-ONLY audit boundary, never passed to the policy.
        return await self.page.evaluate("({source:document.querySelector('#editor').value,...window.audit})")
    async def close(self):
        if hasattr(self,'browser'):await self.browser.close()
        if hasattr(self,'pw'):await self.pw.stop()

def retinal_patches(png):
    import numpy as np
    img=Image.open(io.BytesIO(png)).convert('RGB')
    # Courier New 20px is exactly 12 pixels per glyph on the pinned browser.
    patches=[]
    for x,y,count in REGIONS:
        for i in range(count):
            crop=np.asarray(img.crop((x+i*12,y,x+(i+1)*12,y+28))).copy()
            caret=(crop[:,:,0]>150)&(crop[:,:,1]<70)
            if np.median(crop)<128:crop=255-crop
            crop[caret]=255
            patches.append(np.asarray(Image.fromarray(crop).resize((12,12))).mean(2).reshape(-1)/127.5-1)
    arr=np.asarray(img)
    focused=bool(arr[76,784,2]>arr[76,784,0]*1.5)
    ran=bool(arr[550,535,2]>arr[550,535,0]*1.5)
    red=(arr[114:137,415:800,0]>150)&(arr[114:137,415:800,1]<70)
    columns=np.flatnonzero(red.sum(axis=0)>12)
    caret=int(round((int(columns[0])-1)/12)) if len(columns) else None
    return np.asarray(patches),focused,ran,caret
