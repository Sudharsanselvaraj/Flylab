import {useEffect,useRef,useState,useMemo,useCallback} from 'react';
import {PhysicalWorld,type View} from './PhysicalWorld';
import {CodingBrain} from './CodingBrain';
import {TrainingMonitor} from './TrainingMonitor';
import {CNSInstrument} from './CNSInstrument';
import {decodeActivity} from './neuralPacket';
import type {PhysicalCatalog,PhysicalFrame,NeuralMetrics} from './physicalTypes';
import './coding.css';
const pause=(ms:number)=>new Promise(r=>setTimeout(r,ms));
export function PhysicalCodingLab(){
 const [catalog,setCatalog]=useState<PhysicalCatalog|null>(null),[target,setTarget]=useState('Hello World'),[fault,setFault]=useState(false),[view,setView]=useState<View>('room');
 const [screen]=useState(()=>{const c=document.createElement('canvas');c.width=1200;c.height=600;return c;});
 const [version,setVersion]=useState(0),[pose,setPose]=useState<PhysicalFrame|null>(null),[tick,setTick]=useState(0),[rates,setRates]=useState<ArrayLike<number>>([]),[spikes,setSpikes]=useState<{tick:number;neuron:number}[]>([]);
 const [status,setStatus]=useState('Opening empty Chromium workspace…'),[running,setRunning]=useState(false),[ready,setReady]=useState(false),[issue,setIssue]=useState(''),[brain,setBrain]=useState(false),[drawer,setDrawer]=useState('');
 const [silenced,setSilenced]=useState<string[]>([]),[session,setSession]=useState(''),[result,setResult]=useState<PhysicalFrame|null>(null),[source,setSource]=useState(''),[events,setEvents]=useState<PhysicalFrame[]>([]),[selected,setSelected]=useState<PhysicalFrame|null>(null);
 const [savedRuns,setSavedRuns]=useState<{session:string;mode:string;target:string;success:boolean;status:string;corrections:number;ticks:number}[]>([]);
 const [mode,setMode]=useState('full-fast'),[fullIds,setFullIds]=useState<string[]>([]);
 const [metrics,setMetrics]=useState<NeuralMetrics|null>(null),[paused,setPaused]=useState(false),[pausePending,setPausePending]=useState(false),[brainSelection,setBrainSelection]=useState<string|undefined>();
 const pausedRef=useRef(false),replaying=useRef(false);
 const ids=useMemo(()=>mode==='subgraph'?catalog?.graph.nodes.map(n=>n.body_id)??[]:fullIds,[catalog,mode,fullIds]);
 
 const [baseline,setBaseline]=useState<ArrayLike<number>|undefined>();const currentRates=useRef<ArrayLike<number>>([]);
 const activity=useMemo(()=>({ids,rates,spikes,tick,dt:.002,baseline}),[ids,rates,spikes,tick,baseline]);
 const [recording,setRecording]=useState(false),[clip,setClip]=useState('');
 const rendered=useRef<{tick:number;resolve:()=>void}|null>(null);
 const acknowledge=useCallback((t:number)=>{if(rendered.current?.tick===t){rendered.current.resolve();rendered.current=null;}},[]);
 const socket=useRef<WebSocket|null>(null),stop=useRef(false),recorder=useRef<MediaRecorder|null>(null),latest=useRef({tick:0,status:''});
 const draw=async(url:string)=>{const image=new Image();image.src=url;await image.decode();screen.getContext('2d')!.drawImage(image,0,0,1200,600);setVersion(v=>v+1);};
 const consume=async(e:PhysicalFrame,replaySession?:string)=>{
   if(e.image)await draw(`data:image/png;base64,${e.image}`);else if(e.kind==='screen'&&e.file&&replaySession)await draw(`/api/physical-coding/session/${replaySession}/${e.file}`);
   setTick(e.tick);latest.current.tick=e.tick;
   if(e.activity_file&&replaySession){const packet=decodeActivity(await fetch(`/api/physical-coding/session/${replaySession}/${e.activity_file}`).then(r=>r.arrayBuffer()),20000);currentRates.current=packet.rates;setRates(packet.rates);setSpikes(old=>[...old,...packet.spikes].filter(s=>s.tick>packet.tick-500).slice(-20000));}
   if(e.rates){currentRates.current=e.rates;setRates(e.rates);}if(e.spikes)setSpikes(e.spikes);if(e.metrics)setMetrics(e.metrics);
   if(e.kind==='neural'&&e.phase==='warm-up'){setBaseline(Float32Array.from(currentRates.current));setStatus('Resting baseline measured · reading screen');}
   if(e.kind==='paused'&&!replaySession){setPaused(true);setPausePending(false);pausedRef.current=true;}
   if(e.kind==='resumed'&&!replaySession){setPaused(false);setPausePending(false);pausedRef.current=false;}
   if(e.kind==='motor')setPose(e);
   if(e.kind==='motor'&&e.phase==='contact')setEvents(old=>[...old,e]);
   if(e.kind==='decision'){setStatus(`${e.mode}${e.character?` · ${JSON.stringify(e.character)}`:''}`);setEvents(old=>[...old,e]);latest.current.status=e.mode??'';}
   if(e.kind==='audit'){setSource(e.source??'');setEvents(old=>[...old,e]);}
   if(e.kind==='ready'){setIssue('');setReady(true);setSession(e.session!);setStatus(mode==='subgraph'?'Empty editor · subgraph ready':'Empty editor · full CNS ready · slower than real time');}
   if(e.kind==='result'){setResult(e);setRunning(false);setPaused(false);pausedRef.current=false;setStatus(e.success?`Heading completed · ${e.corrections} corrective keypress${e.corrections===1?'':'es'}`:`Episode ${e.status} · inspect evidence`);setSession(e.session!);}
   if(e.kind==='error'){setIssue(e.detail??'Session failed');setRunning(false);}
 };
 const connect=(auto=false)=>{
   socket.current?.close();stop.current=false;setReady(false);setRunning(auto);setResult(null);setSource('');setEvents([]);setIssue('');setStatus('Opening empty Chromium workspace…');setTick(0);setPose(null);setBaseline(undefined);setRates([]);setSpikes([]);setMetrics(null);setPaused(false);pausedRef.current=false;setPausePending(false);
   const ws=new WebSocket(`${location.protocol==='https:'?'wss':'ws'}://${location.host}/api/physical-coding/stream`);socket.current=ws;ws.binaryType='arraybuffer';let chain=Promise.resolve();
   ws.onopen=()=>ws.send(JSON.stringify({target,fault,silenced,mode}));
   ws.onmessage=message=>{chain=chain.then(async()=>{
     if(socket.current!==ws)return;
     if(message.data instanceof ArrayBuffer){const p=decodeActivity(message.data,20000);currentRates.current=p.rates;setRates(p.rates);setTick(p.tick);latest.current.tick=p.tick;setSpikes(old=>[...old,...p.spikes].filter(e=>e.tick>p.tick-500).slice(-20000));return;}
     const e=JSON.parse(message.data) as PhysicalFrame;await consume(e);
     if(e.kind==='ready'&&auto){setRunning(true);ws.send(JSON.stringify({kind:'start'}));}
     if(e.kind==='motor'){
       // The backend waits until the same physical pose has rendered before it
       // can emit the contact-triggered Chromium keyboard event.
       await new Promise<void>(resolve=>{rendered.current={tick:e.tick,resolve};});
       if(ws.readyState===WebSocket.OPEN)ws.send(JSON.stringify({kind:'rendered',tick:e.tick}));
     }
   }).catch(error=>{setIssue(String(error));ws.close();setRunning(false);});};
   ws.onerror=()=>{if(socket.current!==ws)return;setIssue('Chromium bridge unavailable. Check the Python service.');setRunning(false);};
   ws.onclose=()=>{if(socket.current===ws){setReady(false);setRunning(false);}};
 };
 useEffect(()=>{let live=true;fetch('/api/physical-coding/catalog').then(r=>r.json()).then(c=>{if(live)setCatalog(c);}).catch(e=>setIssue(String(e)));connect();return()=>{live=false;socket.current?.close();stop.current=true;};
 // One dedicated browser connection per component; Start resets it explicitly.
 // eslint-disable-next-line react-hooks/exhaustive-deps
 },[]);
 useEffect(()=>{fetch('/api/physical-coding/full-neuron-ids').then(r=>{if(!r.ok)throw new Error('Full CNS not prepared');return r.arrayBuffer();}).then(b=>setFullIds(Array.from(new Uint32Array(b),String))).catch(()=>{});},[]);
 const start=()=>{setDrawer('');setIssue('');if(ready&&socket.current?.readyState===WebSocket.OPEN){setRunning(true);socket.current.send(JSON.stringify({kind:'start'}));}else connect(true);};
 const togglePause=()=>{if(replaying.current){pausedRef.current=!pausedRef.current;setPaused(pausedRef.current);}else{setPausePending(true);socket.current?.send(JSON.stringify({kind:paused?'resume':'pause'}));}};
 const replay=async(replayId=session,replayMode=mode)=>{if(!replayId)return;const ws=socket.current;socket.current=null;ws?.close();setReady(false);setSession(replayId);setMode(replayMode);setResult(null);setSelected(null);setBaseline(undefined);setRates([]);setSpikes([]);setMetrics(null);setIssue('');setDrawer('');setRunning(true);stop.current=false;setEvents([]);setSource('');setPose(null);setTick(0);setStatus('Replaying recorded session');replaying.current=true;pausedRef.current=false;setPaused(false);try{const data=await fetch(`/api/physical-coding/session/${replayId}/replay`).then(r=>r.json());let archived:Uint32Array|null=null,cursor=0,windowStart=0;if(replayMode==='subgraph'){const r=await fetch(`/api/physical-coding/session/${replayId}/spikes.bin`);if(r.ok)archived=new Uint32Array(await r.arrayBuffer());}for(const e of data){while(pausedRef.current&&!stop.current)await pause(50);if(stop.current)break;await consume(e,replayId);if(archived){while(cursor<archived.length&&archived[cursor]<=e.tick)cursor+=2;while(windowStart<cursor&&archived[windowStart]<e.tick-500)windowStart+=2;const recorded=[];for(let i=Math.max(windowStart,cursor-40000);i<cursor;i+=2)recorded.push({tick:archived[i],neuron:archived[i+1]});setSpikes(recorded);}if(e.kind==='motor')await pause(20);else if(e.kind==='neural')await pause(8);}}finally{replaying.current=false;setRunning(false);setPaused(false);setStatus(stop.current?'Replay stopped':'Recorded causal timeline replayed');}};
 const video=()=>{if(recording){recorder.current?.stop();setRecording(false);return;}const canvas=document.querySelector('.coding-world canvas') as HTMLCanvasElement;if(!canvas)return;const out=document.createElement('canvas');out.width=canvas.width;out.height=canvas.height;const ctx=out.getContext('2d')!;let raf=0;const render=()=>{const brainCanvas=document.querySelector('.coding-brain canvas') as HTMLCanvasElement|null;ctx.drawImage(brainCanvas??canvas,0,0,out.width,out.height);if(brainCanvas){const w=out.width*.26;ctx.drawImage(canvas,20,out.height-w*.73-20,w,w*.73);}const inset=document.querySelector('.coding-inset canvas') as HTMLCanvasElement|null;if(inset&&!brainCanvas){const w=out.width*.25;ctx.drawImage(inset,out.width-w-20,65,w,w);}ctx.fillStyle='#dae4f4';ctx.font='18px monospace';ctx.fillText(`FlyLab · ${(latest.current.tick*.002).toFixed(3)} s · ${latest.current.status}`,20,35);raf=requestAnimationFrame(render);};render();const stream=out.captureStream(30),media=new MediaRecorder(stream),chunks:BlobPart[]=[];recorder.current=media;media.ondataavailable=e=>chunks.push(e.data);media.onstop=async()=>{cancelAnimationFrame(raf);stream.getTracks().forEach(t=>t.stop());const r=await fetch('/api/coding/recording',{method:'POST',headers:{'Content-Type':'video/webm'},body:new Blob(chunks,{type:media.mimeType})});const saved=await r.json();setClip(saved.url);};media.start();setRecording(true);};
 const traceChar=(index:number)=>{const change=events.find(e=>e.kind==='audit'&&e.browser_events?.some(b=>b.type==='input'&&b.caret===index+1&&b.source?.[index]===source[index]));const decision=events.find(e=>e.id===change?.decision_id);setSelected(decision??change??null);};
 return <main className="coding-lab physical-lab"><div className="coding-world"><PhysicalWorld screen={screen} version={version} event={pose} view={view} keys={catalog?.keys??[]} onRendered={acknowledge}/></div>
 <header className="coding-chrome"><div><h1>FlyLab <span>/ physical coding lab</span></h1><p>Screen → modeled circuit → contact → Chromium key event</p></div><nav><button onClick={()=>setDrawer(drawer?'':'evidence')}>Evidence & source</button></nav></header>
 <div className="coding-status"><span>{status}</span><small>{(tick*.002).toFixed(3)} s · canonical simulation clock</small></div>
 {issue&&<div role="alert" className="coding-error">{issue}</div>}
 <footer className="coding-controls"><button className="coding-start" disabled={running||!catalog?.manifest||(mode!=='subgraph'&&(!catalog?.full_network||!fullIds.length))} onClick={start}>Start</button>{running&&<button disabled={pausePending} onClick={togglePause}>{pausePending?'Pausing…':paused?'Resume':'Pause'}</button>}{running&&<button onClick={()=>{stop.current=true;pausedRef.current=false;setPaused(false);socket.current?.close();setRunning(false);setStatus('Stopped');}}>Stop</button>}
 <select aria-label="Dynamics mode" value={mode} disabled={running} onChange={e=>{setMode(e.target.value);socket.current?.close();setReady(false);setBaseline(undefined);setRates([]);setSpikes([]);setMetrics(null);setTick(0);}}><option value="subgraph">Subgraph · 677</option><option value="full-fast" disabled={!catalog?.full_network}>Full CNS · float32</option><option value="full-precision" disabled={!catalog?.full_network}>Full CNS · float64</option></select>
 <select aria-label="Visual target" value={target} disabled={running} onChange={e=>{setTarget(e.target.value);socket.current?.close();setReady(false);}}>{catalog?.targets.map(t=><option key={t.label}>{t.label}</option>)}</select>
 <label style={{fontSize:11}}><input type="checkbox" checked={fault} disabled={running} onChange={e=>{setFault(e.target.checked);socket.current?.close();setReady(false);}}/> Wrong-key trial</label>
 <select aria-label="Camera" value={view} onChange={e=>setView(e.target.value as View)}><option value="room">World</option><option value="desk">Desk</option><option value="fly">Fly view</option><option value="keyboard">Keyboard</option><option value="follow">Follow action</option></select>
 <button onClick={()=>setBrain(true)}>Brain</button><button onClick={video}>{recording?'Stop recording':'Record'}</button>{clip&&<a href={clip} target="_blank" rel="noreferrer">Video ↗</a>}</footer>
 <div className="coding-caption">Actual browser pixels. Each character requires physical key contact.<br/><span>Learned heading transducer · engineered visual and motor interface · real MaleCNS structure, modeled dynamics</span></div>
 {catalog&&<CNSInstrument screen={screen} version={version} running={running} replaying={replaying.current} mode={mode} activity={activity} metrics={metrics} paused={paused} onInspect={id=>{setBrainSelection(id);setBrain(true);}}/>}
 {brain&&catalog&&<CodingBrain session={session} initialSelected={brainSelection} activity={activity} events={events} dt={.002} graph={catalog.graph} rates={rates} tick={tick} spikes={spikes} silenced={silenced} setSilenced={ids=>{setSilenced(ids);if(!running){socket.current?.close();setReady(false);}}} onClose={()=>setBrain(false)}/>}
 {drawer&&<aside className="coding-drawer"><header><h2>Causal evidence</h2><button onClick={()=>setDrawer('')}>Close</button></header>
 <p>Dynamics mode: {mode}. {catalog?.benchmark?.manifest.neurons.toLocaleString()} full-network neurons; {catalog?.benchmark?.manifest.edges.toLocaleString()} retained connections. Full-network CPU benchmark: {catalog?.benchmark?.benchmarks.map(b=>`${b.dtype}: ${b.real_time_factor.toFixed(2)}× real time`).join("; ")}. GPU sparse CSR was unavailable on this machine. Float64 increases numeric precision; neither mode is validated physiology.</p><p>Real: MaleCNS identities, connections, coordinates and available skeletons. Modeled: continuous rate dynamics and threshold spike markers. Trained: glyph readout, heading transducer and editing gate. Engineered: fixed retinal windows, kinematic legs, keyboard geometry and Chromium workspace.</p>
 <p>This checkpoint learns a single-line heading curriculum. It does not learn arbitrary programming. Motor motion is a kinematic contact model, not validated insect biomechanics. Browser time advances with neural and motor ticks; video display pacing is separate.</p>
 <p>{catalog?.manifest?.trainable_parameters.toLocaleString()} trained parameters. Offline component losses are not agent success rates.</p>
 <TrainingMonitor history={catalog?.full_network?.history??[]}/><details><summary>Measured subgraph training loss</summary>{catalog?.manifest?.history.filter((_,i,a)=>i===0||i===a.length-1||a[i+1]?.component!==a[i].component).map((m,i)=><p key={i}>{m.component} · epoch {m.epoch} · loss {m.loss.toFixed(6)}</p>)}</details>
 <h3>Measured full-network trials · 176,422 neurons</h3>{catalog?.full_evaluations?.map(e=><p key={e.session}>{e.condition} · {e.target}: {e.success?'pass':e.status} · {e.keystrokes} key-downs · {e.corrections} Backspace actions</p>)}<h3>Measured subgraph trials · 677 neurons</h3>{catalog?.evaluation?.episodes.map(e=><p key={e.session}>{e.condition} · {e.target}: {e.success?'pass':'fail'} · {e.corrections} Backspace actions</p>)}
 <details><summary onClick={()=>fetch('/api/physical-coding/sessions').then(r=>r.ok?r.json():[]).then(setSavedRuns)}>Saved completed runs</summary>{savedRuns.map(r=><button disabled={running} key={r.session} onClick={()=>{setTarget(r.target);replay(r.session,r.mode).catch(e=>setIssue(String(e)));}}>{r.mode} · {r.target} · {r.success?'pass':r.status} · replay</button>)}</details><h3>Current dynamics: {mode}</h3>{!result&&<p>Current run has not finished; no success result is claimed.</p>}{result&&<p>Current episode: {result.success?'pass':'fail'} · {result.keystrokes} native key-down events · {result.corrections} Backspace decisions.</p>}
 <pre className="physical-source" aria-label="Recorded source">{[...source].map((c,i)=><button key={i} onClick={()=>traceChar(i)} title="Inspect neural precursor">{c===' '?'␣':c}</button>)}</pre>
 {selected&&<p>Decision {selected.id??selected.decision_id} at {((selected.tick??0)*.002).toFixed(3)} s · {selected.mode} {JSON.stringify(selected.character)}<br/>Neural visual reading: target {JSON.stringify(selected.visual_reading?.target)}, editor {JSON.stringify(selected.visual_reading?.editor)}, preview {JSON.stringify(selected.visual_reading?.preview)}<br/>Retinal memory: {selected.retinal_refreshed_slots?.length??80} of 80 windows refreshed; unchanged windows retain their recorded sample timestamps.<br/>Readout checkpoint: {mode==='subgraph'?catalog?.manifest.checkpoint_sha256.slice(0,12):catalog?.full_network?.checkpoint_sha256.slice(0,12)}<br/>{selected.readout_file&&<a href={`/api/physical-coding/session/${session}/${selected.readout_file}`}>All 80 × 576 neural readout values</a>}<br/>Recorded readout events: {selected.neural_event_ids?.slice(-6).map(id=>{const index=Number(id.split(':')[1]);return <button key={id} title={id} onClick={()=>{setBrainSelection(ids[index]);setBrain(true);}}>Neuron {ids[index]??index}</button>;})}<br/>Physical contacts: {events.filter(e=>e.kind==='motor'&&e.decision_id===selected.id).map(e=>`${e.key} at ${e.time.toFixed(3)} s`).join('; ')}</p>}
 {result&&session&&<><button onClick={()=>replay().catch(e=>setIssue(String(e)))} disabled={running}>Replay full session</button><p><a href={`/api/physical-coding/session/${session}/index.html`} target="_blank" rel="noreferrer">Open source ↗</a> · <a href={`/api/physical-coding/session/${session}/project.zip`}>Download project</a></p><button onClick={()=>{const url=URL.createObjectURL(new Blob([source],{type:'text/html'}));window.open(url,'_blank','noopener,noreferrer');setTimeout(()=>URL.revokeObjectURL(url),60000);}}>Open preview</button><p><a href={`/api/physical-coding/session/${session}/episode.json`} target="_blank" rel="noreferrer">Episode + decisions ↗</a> · <a href={`/api/physical-coding/session/${session}/timeline.json.gz`}>Full timeline</a> · <a href={`/api/physical-coding/session/${session}/spikes.bin`}>Every threshold event (binary)</a></p></>}
 </aside>}
 </main>;
}
