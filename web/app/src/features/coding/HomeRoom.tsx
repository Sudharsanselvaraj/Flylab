import {memo,useMemo} from 'react';
import {RoundedBox} from '@react-three/drei';
import {CanvasTexture,RepeatWrapping,SRGBColorSpace} from 'three';
type P=[number,number,number];
function Block({p,s,c}:{p:P;s:P;c:string}){return <mesh position={p} castShadow receiveShadow><boxGeometry args={s}/><meshStandardMaterial color={c} roughness={.8}/></mesh>}
function Soft({p,s,c}:{p:P;s:P;c:string}){return <RoundedBox position={p} args={s} radius={.06} smoothness={3} castShadow receiveShadow><meshStandardMaterial color={c} roughness={.97}/></RoundedBox>}
function Lamp({p}:{p:P}){return <group position={p}><mesh position={[0,.02,0]} castShadow><cylinderGeometry args={[.18,.2,.04,24]}/><meshStandardMaterial color="#292a30"/></mesh><mesh position={[0,.3,0]}><cylinderGeometry args={[.018,.018,.55,12]}/><meshStandardMaterial color="#a28a69" metalness={.65}/></mesh><mesh position={[0,.6,0]} castShadow><cylinderGeometry args={[.17,.27,.3,32,1,true]}/><meshStandardMaterial color="#ece1cb" side={2}/></mesh><pointLight position={[0,.54,0]} color="#ffd39a" intensity={1.8} distance={3}/></group>}
export const HomeRoom=memo(function HomeRoom(){
 const wood=useMemo(()=>{const c=document.createElement('canvas');c.width=512;c.height=512;const x=c.getContext('2d')!;x.fillStyle='#a17b56';x.fillRect(0,0,512,512);let seed=42;const rand=()=>{seed=(seed*1664525+1013904223)>>>0;return seed/4294967296;};for(let i=0;i<500;i++){x.strokeStyle=`rgba(56,34,22,${rand()*.14})`;x.beginPath();const y=rand()*512;x.moveTo(0,y);x.bezierCurveTo(150,y+rand()*4,350,y-rand()*5,512,y+rand()*3);x.stroke();}for(let j=0;j<4;j++){x.fillStyle='#584232';x.fillRect(0,j*128,512,2);x.fillRect((j%2)*256,j*128,2,128);}const t=new CanvasTexture(c);t.colorSpace=SRGBColorSpace;t.wrapS=t.wrapT=RepeatWrapping;t.repeat.set(4,4);return t;},[]);
 return <group>
 <mesh rotation={[-Math.PI/2,0,0]} position={[-.6,-.018,0]} receiveShadow><planeGeometry args={[11,8]}/><meshStandardMaterial map={wood} roughness={.78}/></mesh>
 <Block p={[-.6,2,-2.6]} s={[11,4,.12]} c="#c5bba9"/><Block p={[-5.6,2,0]} s={[.12,4,5.3]} c="#aea99f"/>
 <Block p={[-.6,.09,-2.5]} s={[11,.18,.05]} c="#e0d7c6"/>
 {/* Bed stays beside the desk, with a clear path between chair and bed. */}
 <group position={[-3.75,0,.25]}>
 <Block p={[0,.25,0]} s={[1.72,.35,2.5]} c="#72503a"/><Block p={[0,.73,-1.22]} s={[1.8,1.1,.13]} c="#806047"/>
 <Soft p={[0,.52,0]} s={[1.65,.24,2.35]} c="#e9e1d4"/>
 <Soft p={[0,.67,.37]} s={[1.67,.10,1.62]} c="#3d4b63"/>
 <Soft p={[-.36,.7,-.81]} s={[.64,.17,.43]} c="#eee5d6"/><Soft p={[.36,.7,-.81]} s={[.64,.17,.43]} c="#eee5d6"/>
 {[-.68,.68].flatMap(x=>[-.97,.97].map(z=><Block key={`${x}${z}`} p={[x,.11,z]} s={[.09,.22,.09]} c="#28292d"/>))}
 </group>
 <group position={[-5.0,0,-.68]}><Block p={[0,.38,0]} s={[.65,.72,.58]} c="#977353"/><Block p={[0,.42,.303]} s={[.53,.028,.02]} c="#343238"/><Lamp p={[0,.75,0]}/><Block p={[.08,.76,.11]} s={[.27,.03,.22]} c="#a48971"/></group>
 {/* Window with a cool daylight surface, frame and sill. */}
 <group position={[-3.7,2.42,-2.48]}><Block p={[0,0,0]} s={[2.15,1.65,.09]} c="#e9e0d0"/><mesh position={[0,0,.055]}><planeGeometry args={[1.94,1.43]}/><meshBasicMaterial color="#8babc4"/></mesh><Block p={[0,0,.09]} s={[.055,1.45,.07]} c="#e7dfd3"/><Block p={[0,-.1,.09]} s={[1.94,.055,.07]} c="#e7dfd3"/><Block p={[0,-.86,.12]} s={[2.35,.08,.28]} c="#d9cbb8"/>
 <Soft p={[-1.24,0,.11]} s={[.35,1.95,.11]} c="#8f8174"/><Soft p={[1.24,0,.11]} s={[.35,1.95,.11]} c="#8f8174"/></group>
 <Block p={[.6,3.22,-2.34]} s={[2.8,.09,.46]} c="#8e6949"/>
 {['#394b62','#b69d79','#5b5562','#ceb995','#303948'].map((c,i)=><Block key={c} p={[-.45+i*.17,3.46,-2.3]} s={[.13,.4+(i%2)*.08,.25]} c={c}/>)}
 <group position={[1.5,3.29,-2.3]}><mesh position={[0,.12,0]} castShadow><cylinderGeometry args={[.13,.09,.24,18]}/><meshStandardMaterial color="#ae7050"/></mesh>{Array.from({length:7},(_,i)=><mesh key={i} position={[Math.sin(i*2.4)*.12,.36+Math.cos(i)*.07,Math.cos(i*2.4)*.11]} rotation={[.4,i,.6]} scale={[.07,.21,.025]} castShadow><sphereGeometry args={[1,12,8]}/><meshStandardMaterial color="#505b42" roughness={.9}/></mesh>)}</group>
 <mesh rotation={[-Math.PI/2,0,0]} position={[.05,-.006,1]} receiveShadow><planeGeometry args={[3.1,2.9]}/><meshStandardMaterial color="#64616a" roughness={1}/></mesh>
 </group>;
});
