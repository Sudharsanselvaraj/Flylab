import { useEffect,useMemo,useState } from 'react';
import { OrbitControls } from '@react-three/drei';
import { BufferGeometry,BufferAttribute,DataTexture,FloatType,RGBAFormat,ShaderMaterial } from 'three';
import {fillActivityTexture} from './activityTexture';

export interface AnatomyMeta {classes?:string[];queried_neurons:number;located_neurons:number;missing_locations:number;soma_count:number;tosoma_count:number;bounds:number[][];scope:string;source:string}
export interface NeuronAnatomy {body_id:string;type:string;side:string|null;position:number[]|null;position_kind:string|null;superclass:string|null}
interface Overview {meta:AnatomyMeta;positions:Float32Array;ids:Uint32Array;classes:Uint8Array}
const json=async<T,>(url:string):Promise<T>=>{const r=await fetch(url);if(!r.ok)throw new Error(`Anatomy unavailable (${r.status})`);return r.json();};
const binary=async(url:string)=>{const r=await fetch(url);if(!r.ok)throw new Error(`Morphology unavailable (${r.status})`);return r.arrayBuffer();};
let overviewCache:Promise<Overview>|null=null;
function overviewData(){return overviewCache??=Promise.all([json<AnatomyMeta>('/api/anatomy/overview/overview.json'),binary('/api/anatomy/overview/positions.bin'),binary('/api/anatomy/overview/body_ids.bin'),binary('/api/anatomy/overview/classes.bin')]).then(([meta,p,i,c])=>({meta,positions:new Float32Array(p),ids:new Uint32Array(i),classes:new Uint8Array(c)}));}
function transform(raw:Float32Array,center:number[],scale:number){const p=new Float32Array(raw.length);for(let i=0;i<raw.length;i+=3){p[i]=(raw[i]-center[0])*scale;p[i+1]=-(raw[i+2]-center[2])*scale;p[i+2]=-(raw[i+1]-center[1])*scale;}return p;}

export interface CNSActivity {baseline?:ArrayLike<number>;ids:string[];rates:ArrayLike<number>;spikes:{tick:number;neuron:number}[];tick:number;dt:number}
export function WholeCNS({onReady,onError,onSelect,activity,activeOnly=false,compact=false,responseMode=false,population='all',trailMs=12,selectedBody,showActivity=true}:{onReady:(m:AnatomyMeta)=>void;onError:(e:string)=>void;onSelect:(body:string)=>void;activity?:CNSActivity;activeOnly?:boolean;compact?:boolean;responseMode?:boolean;population?:string;trailMs?:number;selectedBody?:string;showActivity?:boolean}){
 const [data,setData]=useState<Overview|null>(null);
 useEffect(()=>{let active=true;overviewData().then(d=>{if(active){setData(d);onReady(d.meta);}}).catch(e=>active&&onError(String(e)));return()=>{active=false;};},[onReady,onError]);
 const ids=activity?.ids;
 const count=Math.max(1,ids?.length??0),width=Math.min(2048,count),height=Math.ceil(count/width);
 const texture=useMemo(()=>{const t=new DataTexture(new Float32Array(width*height*4),width,height,RGBAFormat,FloatType);t.needsUpdate=true;return t;},[width,height]);
 const visible=useMemo(()=>{if(!data)return new Uint32Array();const rows=[];for(let i=0;i<data.ids.length;i++){const c=data.meta.classes?.[data.classes[i]]??'unclassified';if(population==='all'||(population==='optic'&&(c.startsWith('ol_')||c.startsWith('visual_')))||(population==='central'&&c.startsWith('cb_'))||(population==='vnc'&&c.startsWith('vnc_'))||(population==='motor'&&c.includes('motor')))rows.push(i);}return Uint32Array.from(rows);},[data,population]);
 const geometry=useMemo(()=>{if(!data)return null;const center=[0,1,2].map(a=>(data.meta.bounds[0][a]+data.meta.bounds[1][a])/2);const scale=8/Math.max(...center.map((_,a)=>data.meta.bounds[1][a]-data.meta.bounds[0][a]));const index=new Map(ids?.map((id,i)=>[id,i])??[]);const raw=new Float32Array(visible.length*3),owners=new Float32Array(visible.length);for(let i=0;i<visible.length;i++){const row=visible[i];raw.set(data.positions.subarray(row*3,row*3+3),i*3);owners[i]=index.get(String(data.ids[row]))??-1;}const g=new BufferGeometry();g.setAttribute('position',new BufferAttribute(transform(raw,center,scale),3));g.setAttribute('owner',new BufferAttribute(owners,1));g.setAttribute('anatomyRow',new BufferAttribute(Float32Array.from(visible),1));return g;},[data,ids,visible]);

 // The anatomical and dynamic layers share real coordinates, but not colour or
 // visibility. Compact LOD samples only anatomy; no active cell is LOD-culled.
 const materials=useMemo(()=>[0,1].map(layer=>new ShaderMaterial({
  transparent:true,depthWrite:false,toneMapped:false,
  uniforms:{activity:{value:texture},dimensions:{value:[width,height]},layer:{value:layer},compact:{value:compact?1:0},activeOnly:{value:0},selectedRow:{value:-1}},
  vertexShader:`
   attribute float owner; attribute float anatomyRow;
   uniform sampler2D activity; uniform vec2 dimensions;
   uniform float layer; uniform float compact; uniform float activeOnly; uniform float selectedRow;
   varying vec4 tint; varying float dynamicPoint;
   void main(){
    vec4 a=owner<0.?vec4(0.):texture2D(activity,vec2((mod(owner,dimensions.x)+.5)/dimensions.x,(floor(owner/dimensions.x)+.5)/dimensions.y));
    float chosen=1.-step(.1,abs(anatomyRow-selectedRow));
    float rate=pow(clamp(a.r,0.,1.),1.2),spike=a.g;
    float live=max(rate,spike);
    vec4 p=modelViewMatrix*vec4(position,1.);
    float perspective=12./max(3.,-p.z);
    dynamicPoint=layer;
    if(layer<.5){
     float keep=compact>.5?(1.-step(.1,mod(anatomyRow,8.))):1.;
     tint=vec4(mix(vec3(.44,.49,.57),vec3(1.,.57,.19),chosen),max(.24*keep*(1.-activeOnly),chosen*.95));
     gl_PointSize=clamp((1.25+chosen*2.)*perspective,1.,5.);
    }else{
     vec3 low=vec3(.10,.29,.53),cyan=vec3(.08,.72,1.),high=vec3(.77,.94,1.);
     vec3 colour=rate<.65?mix(low,cyan,rate/.65):mix(cyan,high,(rate-.65)/.35);
     colour=mix(colour,vec3(1.),spike);
     colour=mix(colour,vec3(1.,.57,.19),chosen);
     float alpha=live>0.?(.05+.82*live):0.;
     tint=vec4(colour,mix(alpha,.95,chosen));
     gl_PointSize=clamp((1.2+rate*1.65+spike*1.8+chosen*2.)*perspective,1.,9.);
    }
    gl_Position=projectionMatrix*p;
   }`,
  fragmentShader:`varying vec4 tint; varying float dynamicPoint;
   void main(){float d=length(gl_PointCoord-.5)*2.;if(d>1.||tint.a<.001)discard;
    float core=dynamicPoint>.5?mix(.18,1.,1.-smoothstep(.3,1.,d)):1.;
    gl_FragColor=vec4(tint.rgb,tint.a*core);
   }`,
 })),[texture,width,height,compact]);
 // Three.js GPU buffers/uniforms are imperative external state.
 useEffect(()=>{
  const pixels=texture.image.data as Float32Array;
  if(activity)fillActivityTexture(pixels,activity.rates,activity.spikes,activity.tick,activity.dt,activity.baseline,responseMode,trailMs);else pixels.fill(0);
  // eslint-disable-next-line react/immutability
  texture.needsUpdate=true;
  const row=selectedBody&&data?data.ids.indexOf(Number(selectedBody)):-1;
  // eslint-disable-next-line react/immutability
  for(const material of materials){material.uniforms.activeOnly.value=activeOnly?1:0;material.uniforms.selectedRow.value=row;}
 },[activity,texture,materials,activeOnly,responseMode,trailMs,selectedBody,data]);
 useEffect(()=>()=>geometry?.dispose(),[geometry]);
 useEffect(()=>()=>texture.dispose(),[texture]);
 useEffect(()=>()=>materials.forEach(m=>m.dispose()),[materials]);
 const pick=(index:number|undefined)=>{if(index!==undefined&&data)onSelect(String(data.ids[visible[index]]));};
 return <>{geometry&&<>
  <points geometry={geometry} material={materials[0]} onClick={e=>{e.stopPropagation();pick(e.index);}}/>
  {showActivity&&<points geometry={geometry} material={materials[1]} onClick={e=>{e.stopPropagation();pick(e.index);}}/>}
 </>}<OrbitControls makeDefault minDistance={2} maxDistance={22}/></>;

}

export function SelectedSkeleton({body,onStatus}:{body:string;onStatus:(s:string)=>void}){
 const [raw,setRaw]=useState<Float32Array|null>(null);
 useEffect(()=>{let active=true;binary(`/api/anatomy/skeleton/${body}`).then(b=>{if(active){setRaw(new Float32Array(b));onStatus(`Neuron ${body} · real SWC centerline`);}}).catch(e=>active&&onStatus(String(e)));return()=>{active=false;};},[body,onStatus]);
 const geometry=useMemo(()=>{if(!raw?.length)return null;const lo=[Infinity,Infinity,Infinity],hi=[-Infinity,-Infinity,-Infinity];for(let i=0;i<raw.length;i++) {lo[i%3]=Math.min(lo[i%3],raw[i]);hi[i%3]=Math.max(hi[i%3],raw[i]);}const center=lo.map((x,i)=>(x+hi[i])/2),scale=7/Math.max(...lo.map((x,i)=>hi[i]-x));const g=new BufferGeometry();g.setAttribute('position',new BufferAttribute(transform(raw,center,scale),3));return g;},[raw]);
 useEffect(()=>()=>geometry?.dispose(),[geometry]);
 return <>{geometry&&<lineSegments geometry={geometry}><lineBasicMaterial color="#e7a55f" transparent opacity={.8}/></lineSegments>}<OrbitControls makeDefault minDistance={2} maxDistance={22}/></>;
}
