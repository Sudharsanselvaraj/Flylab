import {useEffect,useState} from 'react';
type Row={phase?:string;repeat?:number;ticks?:number;glyphs?:number;component?:string;epoch?:number;loss?:number;offline_accuracy?:number};
type Job={id?:string;status:string;events:Row[];error?:string;wall_seconds?:number};
export function TrainingMonitor({history}:{history:Row[]}){
 const [job,setJob]=useState<Job>({status:'idle',events:[]}),[error,setError]=useState('');
 useEffect(()=>{let alive=true;const read=()=>fetch('/api/physical-coding/training/status').then(r=>r.json()).then(j=>{if(alive)setJob(j);}).catch(e=>alive&&setError(String(e)));read();const timer=setInterval(read,2000);return()=>{alive=false;clearInterval(timer);};},[]);
 const train=async(resume=false)=>{const r=await fetch(`/api/physical-coding/training/start${resume?`?resume_id=${job.id}`:""}`,{method:'POST'});if(!r.ok){setError(await r.text());return;}setJob({...await r.json(),events:[]});};
 const rows=job.events.length?job.events:history,losses=rows.filter(r=>r.loss!==undefined),last=rows.at(-1);
 const min=Math.min(...losses.map(r=>Math.log10(Math.max(1e-8,r.loss!)))),max=Math.max(...losses.map(r=>Math.log10(Math.max(1e-8,r.loss!))));
 return <section className="training-monitor"><h3>Training / test evidence</h3><p>Full-network glyph readout: actual Adam optimization on recorded Chromium glyph pixels and full-network responses. The learned heading and editing components retain their separate checkpoint. Training accuracy is not held-out coding success.</p>
 <button disabled={job.status==='running'} onClick={()=>train().catch(e=>setError(String(e)))}>{job.status==='running'?'Training candidate…':'Train a new full-network readout'}</button>{job.status==='completed'&&<button onClick={()=>train(true).catch(e=>setError(String(e)))}>Resume optimizer · 100 epochs</button>}
 <p>{job.status==='idle'?'Recorded training history':`Candidate ${job.id?.slice(0,8)} · ${job.status}`}{last?.phase&&` · ${last.phase} · ${last.ticks?.toLocaleString()} neural ticks`}</p>
 {!!losses.length&&<><svg viewBox="0 0 340 110" role="img" aria-label="Measured training loss on a logarithmic vertical scale"><path d={losses.map((r,i)=>`${i?'L':'M'} ${10+i*320/Math.max(1,losses.length-1)} ${10+90*(max-Math.log10(Math.max(1e-8,r.loss!)))/Math.max(.001,max-min)}`).join(' ')} fill="none" stroke="#487753" strokeWidth="2"/></svg><p>Epoch {losses.at(-1)?.epoch} · loss {losses.at(-1)?.loss?.toPrecision(5)} · training accuracy {((losses.at(-1)?.offline_accuracy??0)*100).toFixed(1)}%</p></>}
 <small>New jobs save candidate weights, optimizer state, losses and hashes under training_runs. They do not replace the tested controller automatically.</small>{error&&<p role="alert">{error}</p>}</section>;
}
