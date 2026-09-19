import {useState,useRef,useEffect,useCallback,useMemo} from 'react';
import {Canvas} from '@react-three/fiber';
import {WholeCNS,type AnatomyMeta,type CNSActivity} from './Anatomy';
import type {NeuralMetrics} from './physicalTypes';
export function CNSInstrument({activity,metrics,onInspect,paused,mode,running,replaying,screen,version}:{screen:HTMLCanvasElement;version:number;running:boolean;replaying:boolean;mode:string;activity:CNSActivity;metrics:NeuralMetrics|null;onInspect:(id?:string)=>void;paused:boolean}){
 const [meta,setMeta]=useState<AnatomyMeta|null>(null),[error,setError]=useState(''),[response,setResponse]=useState(false);
 const ready=useCallback((m:AnatomyMeta)=>setMeta(m),[]);
 const responsive=useMemo(()=>{if(!activity.baseline)return null;let n=0;for(let i=0;i<activity.rates.length;i++)if(Math.abs(activity.rates[i]-activity.baseline[i])>1)n++;return n;},[activity.rates,activity.baseline]);
 const raster=useRef<HTMLCanvasElement>(null),vision=useRef<HTMLCanvasElement>(null);
 useEffect(()=>{vision.current?.getContext('2d')?.drawImage(screen,0,0,600,300);},[screen,version]);
 useEffect(()=>{const c=raster.current,x=c?.getContext('2d');if(!x)return;x.clearRect(0,0,270,38);x.fillStyle='#92ddff';const stride=Math.max(1,Math.ceil(activity.spikes.length/1000));for(let i=0;i<activity.spikes.length;i+=stride){const e=activity.spikes[i];if(e.tick<=activity.tick&&e.tick>activity.tick-500)x.fillRect(270*(1-(activity.tick-e.tick)/500),3+32*e.neuron/Math.max(1,activity.ids.length),1,1);}},[activity]);
 return <aside className="cns-instrument coding-inset" aria-label="Live MaleCNS instrument">
  <header><b>MALECNS <span>{paused?'PAUSED':replaying?'REPLAY':running?'LIVE':activity.tick?'RECORDED':'READY'}</span></b><button onClick={()=>onInspect()}>Expand ↗</button></header>
  <div className="cns-view"><Canvas gl={{preserveDrawingBuffer:true}} camera={{position:[0,0,12],fov:45}}><color attach="background" args={['#090d15']}/><WholeCNS compact activity={activity} responseMode={response} onReady={ready} onError={setError} onSelect={onInspect}/></Canvas><div className="cns-legend">brain<br/><span>↓</span><br/>ventral nerve cord</div></div>
  <div className="cns-counts"><div><b>{meta?.queried_neurons.toLocaleString()??'…'}</b><span>Anatomy</span></div><div><b>{activity.ids.length.toLocaleString()}</b><span>Dynamics</span></div><div><b>{(metrics?.active??0).toLocaleString()}</b><span>Active &gt;1 Hz</span></div></div>
  <canvas ref={raster} width={270} height={38} className="cns-raster" role="img" aria-label="Recorded threshold events in the preceding simulated second"/>
  <div className="cns-timing"><span>{(activity.tick*activity.dt).toFixed(3)} s</span><span>RTF {metrics?.real_time_factor.toFixed(2)??'—'}×</span><span>{Math.round(metrics?.spikes_per_second??0).toLocaleString()} spikes/s</span></div>
  <div className="cns-mode"><button aria-pressed={!response} onClick={()=>setResponse(false)}>Current activity</button><button aria-pressed={response} onClick={()=>setResponse(true)}>Change from rest</button></div><div className="activity-key"><span className="anatomy-dot">Anatomy</span><span className="activity-dot">Rate</span><span className="spike-dot">Spike</span></div>
  <small>{response?(responsive===null?'Waiting for a measured resting baseline':`${responsive.toLocaleString()} cells changed >1 Hz from rest`):'Blue → cyan → blue-white: rate · white flash: spike'}</small>
  <div className="vision-label">FLY VISION <span>MONITOR INPUT</span></div><canvas className="vision-view" ref={vision} width={600} height={300} role="img" aria-label="Actual monitor screenshot supplied to the visual controller"/>
  <details><summary>Model & display details</summary><small>{mode!=='subgraph'?'Full network · modeled rates':'Subgraph dynamics · full anatomy'} · {metrics?.engine}<br/>{meta?.located_neurons.toLocaleString()??'…'} positioned; {meta?.missing_locations.toLocaleString()??'…'} unplaced. Thumbnail anatomy samples 1 in 8 located cells; the activity layer includes every located active cell. Expand shows all anatomy. Rates above 1 Hz become blue, reaching blue-white at 40 Hz; higher rates remain in the data. Change from rest shows |rate − resting rate|, saturated at 8 Hz. White flashes are actual threshold events with a 12 ms simulation-time trail. Amber is reserved for selection. Full events are archived; display retains 20k. Vision is the controller's fixed monitor crop, not compound-eye physiology or head-dependent vision.</small></details>{error&&<p role="alert">{error}</p>}
 </aside>;
}
