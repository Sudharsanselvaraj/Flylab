/** One virtual computer. Human and policy input both pass through DOM key events.
 * Tokens only expand to primitives; this module never chooses a task solution. */
export type MotorEvent={tick:number;type:'pointermove'|'pointerdown'|'pointerup'|'keydown'|'keyup'|'input'|'run';key?:string;x?:number;y?:number;revision:number;decisionTick:number};
export class Computer {
  editor:HTMLTextAreaElement;runButton:HTMLButtonElement;tick=0;revision=0;events:MotorEvent[]=[];decisionTick=0;
  onEvent:(e:MotorEvent)=>void=()=>{};
  constructor(editor:HTMLTextAreaElement,runButton:HTMLButtonElement){this.editor=editor;this.runButton=runButton;editor.addEventListener('keydown',this.handleKey);}
  dispose(){this.editor.removeEventListener('keydown',this.handleKey);}
  emit(event:Omit<MotorEvent,'tick'|'revision'|'decisionTick'>){const e={...event,tick:++this.tick,revision:this.revision,decisionTick:this.decisionTick};this.events.push(e);this.onEvent(e);}
  handleKey=(event:KeyboardEvent)=>{
    if(event.isTrusted)return; // Native typing retains the browser's native editing behaviour.
    const el=this.editor;let a=el.selectionStart,b=el.selectionEnd;const k=event.key;
    if(k==='End'){el.setSelectionRange(el.value.length,el.value.length);return;}
    if(k==='Home'){el.setSelectionRange(0,0);return;}
    if(k==='ArrowLeft'||k==='ArrowRight'){a=Math.max(0,Math.min(el.value.length,a+(k==='ArrowLeft'?-1:1)));el.setSelectionRange(a,a);return;}
    if(k.length===1||k==='Enter'||k==='Backspace'||k==='Delete'||k==='Tab'){
      event.preventDefault();let text=k==='Enter'?'\n':k==='Tab'?'  ':k;
      if(k==='Backspace'){a=a===b?Math.max(0,a-1):a;text='';}
      if(k==='Delete'){b=a===b?Math.min(el.value.length,b+1):b;text='';}
      el.setRangeText(text,a,b,'end');this.revision++;
      el.dispatchEvent(new InputEvent('input',{bubbles:true,inputType:text?'insertText':'deleteContentBackward',data:text}));
      this.emit({type:'input',key:text});
    }
  };
  key(key:string){this.emit({type:'keydown',key});this.editor.dispatchEvent(new KeyboardEvent('keydown',{key,bubbles:true,cancelable:true}));this.emit({type:'keyup',key});this.editor.dispatchEvent(new KeyboardEvent('keyup',{key,bubbles:true}));}
  pointer(target:'editor'|'run'){
    const node=target==='editor'?this.editor:this.runButton;const x=target==='editor'?100:420,y=target==='editor'?170:42;
    for(const type of ['pointermove','pointerdown','pointerup'] as const){this.emit({type,x,y});node.dispatchEvent(new MouseEvent(type,{bubbles:true,clientX:x,clientY:y}));}
    node.focus();node.dispatchEvent(new MouseEvent('click',{bubbles:true}));
  }
  async perform(token:string|null,decisionTick:number,pace:boolean,abort:()=>boolean){
    this.tick=decisionTick;this.decisionTick=decisionTick;this.events=[];
    if(token!==null){this.pointer('editor');this.key('End');
      for(const key of '\n'+token){if(abort())throw new Error('Session stopped');this.key(key);if(pace)await new Promise(r=>setTimeout(r,25));}
      this.pointer('run');this.emit({type:'run'});
    }
    return this.events.slice();
  }
}

/** Executes the real page in an opaque-origin iframe, then rasterizes its DOM
 * snapshot with the browser SVG foreignObject renderer. Not an OS screenshot.
 * This bounded capture supports the benchmark's inline HTML/CSS/text. */
export class Preview {
  iframe:HTMLIFrameElement;
  constructor(iframe:HTMLIFrameElement){this.iframe=iframe;}
  async render(source:string):Promise<HTMLCanvasElement>{
    const nonce=crypto.randomUUID();
    const bridge=`<script>addEventListener('load',()=>{setTimeout(()=>{const body=document.body.cloneNode(true);body.querySelectorAll('script').forEach(x=>x.remove());const styles=[...document.querySelectorAll('head style')].map(x=>x.outerHTML).join('');const cs=getComputedStyle(document.body),wrap=document.createElement('div');wrap.style.cssText='position:relative;width:240px;height:180px;overflow:hidden;';wrap.style.background=cs.backgroundColor;wrap.style.font=cs.font;wrap.style.color=cs.color;wrap.style.padding=cs.padding;wrap.innerHTML=styles+body.innerHTML;parent.postMessage({kind:'coding-paint',nonce:${JSON.stringify(nonce)},html:new XMLSerializer().serializeToString(wrap)},'*')},0)});addEventListener('error',e=>parent.postMessage({kind:'coding-error',nonce:${JSON.stringify(nonce)},message:e.message},'*'))</script>`;
    const csp=`<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; connect-src 'none'; form-action 'none'; base-uri 'none'">`;
    const result=new Promise<string>((resolve,reject)=>{
      const timer=setTimeout(()=>{window.removeEventListener('message',handle);reject(new Error('Preview did not produce a capture within 5 seconds'));},5000);
      const handle=(event:MessageEvent)=>{if(event.source!==this.iframe.contentWindow||event.data?.nonce!==nonce)return;if(event.data.kind==='coding-paint'){clearTimeout(timer);window.removeEventListener('message',handle);resolve(event.data.html);}else if(event.data.kind==='coding-error'){clearTimeout(timer);window.removeEventListener('message',handle);reject(new Error(event.data.message));}};
      window.addEventListener('message',handle);
    });
    // CSP and bridge execute before any user-supplied markup. Opaque origin and no network.
    this.iframe.srcdoc=csp+bridge+source;
    const html=await result;
    const image=new Image();
    const loaded=new Promise<void>((resolve,reject)=>{image.onload=()=>resolve();image.onerror=()=>reject(new Error('Browser DOM rasterization failed'));});
    image.src='data:image/svg+xml;charset=utf-8,'+encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="240" height="180"><foreignObject width="240" height="180">${html}</foreignObject></svg>`);
    await loaded;const canvas=document.createElement('canvas');canvas.width=240;canvas.height=180;canvas.getContext('2d')!.drawImage(image,0,0);return canvas;
  }
}
export function pagePixels(canvas:HTMLCanvasElement){const small=document.createElement('canvas');small.width=16;small.height=24;const cx=small.getContext('2d')!;cx.drawImage(canvas,0,0,16,24);const p=cx.getImageData(0,0,16,24).data;return Array.from(p).filter((_,i)=>i%4!==3);}
export function observation(target:HTMLCanvasElement,preview:HTMLCanvasElement){
  const canvas=document.createElement('canvas');canvas.width=32;canvas.height=24;const cx=canvas.getContext('2d')!;cx.drawImage(target,0,0,16,24);cx.drawImage(preview,16,0,16,24);const p=cx.getImageData(0,0,32,24).data;return Array.from(p).filter((_,i)=>i%4!==3);
}
export function reward(target:HTMLCanvasElement,preview:HTMLCanvasElement,actions:number){const a=target.getContext('2d')!.getImageData(0,0,240,180).data,b=preview.getContext('2d')!.getImageData(0,0,240,180).data;let err=0;for(let i=0;i<a.length;i++)if(i%4!==3)err+=Math.abs(a[i]-b[i]);const mae=err/(240*180*3*255);return {pixel_mae:mae,similarity:1-mae,action_cost:actions*.001,reward:1-mae-actions*.001,success:mae<.005};}
