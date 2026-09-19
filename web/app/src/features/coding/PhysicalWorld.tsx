import {useEffect,useMemo,memo} from 'react';
import {Canvas,useThree,useFrame} from '@react-three/fiber';
import {OrbitControls,ContactShadows} from '@react-three/drei';
import {CanvasTexture,SRGBColorSpace,PCFShadowMap} from 'three';
import {HomeRoom} from './HomeRoom';
import {DeskChair,SeatedDeskFly} from './DeskSeat';
import type {PhysicalKey,PhysicalFrame} from './physicalTypes';
export type View='room'|'desk'|'fly'|'keyboard'|'follow';
function Box({p,s,color}:{p:[number,number,number];s:[number,number,number];color:string}){return <mesh position={p} castShadow receiveShadow><boxGeometry args={s}/><meshStandardMaterial color={color} roughness={.68}/></mesh>;}
function Camera({view,event}:{view:View;event:PhysicalFrame|null}){
 const {camera,size}=useThree();const focusX=view==='follow'?(event?.effector?.[0]??0):view==='room'?-1.35:0;
 const close=view==='keyboard'||view==='follow';const desk=view==='desk'||view==='room';const targetY=close?1.4:desk?1.65:1.95;const targetZ=close?.2:desk?.15:-.55;const target:[number,number,number]=[focusX,targetY,targetZ];
 useEffect(()=>{const positions={room:[4.6,3.8,7.3],desk:[3.4,2.8,4.2],fly:[.0,1.72,.81],keyboard:[1.5,2.6,-.25],follow:[focusX+.25,2.25,-.35]};const p=positions[view];const f=view==='fly'||view==='follow'?1:Math.max(1,.78/(size.width/size.height));camera.position.set(p[0]*f,1.95+(p[1]-1.95)*f,-.55+(p[2]+.55)*f);camera.lookAt(focusX,targetY,targetZ);camera.updateProjectionMatrix();},[camera,view,size.width,size.height,focusX,targetY,targetZ]);
 return <OrbitControls key={view} target={target} minDistance={.5} maxDistance={12} maxPolarAngle={Math.PI/2-.02}/>;
}
function Scene({screen,version,event,view,keys,onRendered}:{screen:HTMLCanvasElement;version:number;event:PhysicalFrame|null;view:View;keys:PhysicalKey[];onRendered?:(tick:number)=>void}){
 const texture=useMemo(()=>{const t=new CanvasTexture(screen);t.colorSpace=SRGBColorSpace;return t;},[screen]);
 // Three.js GPU texture invalidation is intentionally imperative.
 // eslint-disable-next-line react/immutability
 useEffect(()=>{texture.needsUpdate=true;},[texture,version]);useEffect(()=>()=>texture.dispose(),[texture]);
 return <><color attach="background" args={['#292c35']}/><ambientLight intensity={.65}/><directionalLight position={[-4,5,1]} intensity={2.8} color="#ffe4bd" castShadow shadow-mapSize={[2048,2048]}/><pointLight position={[1.5,2.8,-.6]} intensity={3} color="#fff0cc"/>
 <HomeRoom/>
 <Box p={[0,1.2,-.25]} s={[4.8,.15,1.8]} color="#aa805a"/>{[-1,1].flatMap(x=>[-1,1].map(z=><Box key={`${x}${z}`} p={[x*2.1,.58,-.25+z*.64]} s={[.12,1.15,.12]} color="#303139"/>))}
 <Box p={[0,1.3,-.7]} s={[.8,.07,.43]} color="#242831"/><Box p={[0,1.7,-1.03]} s={[.16,.8,.13]} color="#303139"/>
 <Box p={[0,2.28,-.91]} s={[3.16,1.64,.12]} color="#171b24"/>
 <mesh position={[0,2.29,-.842]}><planeGeometry args={[3,1.5]}/><meshBasicMaterial map={texture} toneMapped={false}/></mesh>
 <Box p={[0,1.32,.17]} s={[1.86,.06,.65]} color="#242831"/>
 {keys.map(k=><Keycap key={k.code} item={k} down={event?.held?.includes(k.code)??false} contact={event?.key===k.code?(k.code==='ShiftLeft'?event.left_effector:event.effector):undefined}/>)}
 <mesh position={[1,1.36,.32]} scale={[.115,.055,.18]} castShadow><sphereGeometry args={[1,24,16]}/><meshStandardMaterial color={event?.key==='Mouse'?'#d5b57b':'#c9cbd1'}/></mesh>
 <DeskChair/><SeatedDeskFly frame={event}/>
 <Box p={[1.8,1.3,-.65]} s={[.38,.045,.28]} color="#454957"/><Box p={[1.8,1.79,-.7]} s={[.04,.98,.04]} color="#454957"/><mesh position={[1.72,2.26,-.58]} rotation={[0,0,.25]} castShadow><coneGeometry args={[.26,.24,40,1,true]}/><meshStandardMaterial color="#777d8b" side={2}/></mesh>
 <Box p={[-1.83,1.31,.1]} s={[.48,.06,.65]} color="#c7c2ac"/><Box p={[-1.78,1.355,.12]} s={[.44,.03,.61]} color="#e7e1cd"/>
 <ContactShadows position={[0,.001,0]} opacity={.3} scale={12} blur={2} far={5}/><Camera view={view} event={event}/><RenderProof tick={event?.tick??-1} onRendered={onRendered}/></>;
}
export const PhysicalWorld=memo(function PhysicalWorld(props:{screen:HTMLCanvasElement;version:number;event:PhysicalFrame|null;view:View;keys:PhysicalKey[];onRendered?:(tick:number)=>void}){return <Canvas shadows={{type:PCFShadowMap}} dpr={[1,1.5]} camera={{fov:43,near:.05,far:50}} gl={{preserveDrawingBuffer:true}}><Scene {...props}/></Canvas>;});

function Keycap({item,down,contact}:{item:PhysicalKey;down:boolean;contact?:number[]}){
 const texture=useMemo(()=>{const c=document.createElement('canvas');c.width=128;c.height=64;const x=c.getContext('2d')!;x.fillStyle='#c9cbd1';x.fillRect(0,0,128,64);x.fillStyle='#242b38';x.font='25px monospace';x.textAlign='center';x.fillText(item.label,64,42);const t=new CanvasTexture(c);t.colorSpace=SRGBColorSpace;return t;},[item.label]);
 useEffect(()=>()=>texture.dispose(),[texture]);
 const travel=down?.018:contact?Math.max(0,Math.min(.018,1.385-contact[1])):0;
 return <group position={[item.position[0],item.position[1]-.018-travel,item.position[2]]}><Box p={[0,0,0]} s={[item.width,.036,.086]} color={down?'#d5ae72':'#c9cbd1'}/><mesh position={[0,.0181,0]} rotation={[-Math.PI/2,0,0]}><planeGeometry args={[item.width*.96,.077]}/><meshBasicMaterial map={texture}/></mesh></group>;
}

function RenderProof({tick,onRendered}:{tick:number;onRendered?: (tick:number)=>void}){
 useFrame(({gl,scene,camera})=>{gl.render(scene,camera);onRendered?.(tick);},1);return null;
}
