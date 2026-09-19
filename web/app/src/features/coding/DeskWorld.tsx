import {useEffect,useMemo} from 'react';
import {Canvas,useThree} from '@react-three/fiber';
import {OrbitControls,ContactShadows} from '@react-three/drei';
import {CanvasTexture,SRGBColorSpace,PCFShadowMap} from 'three';
import {FlyBody} from './FlyBody';
import type {MotorEvent} from './computer';
export type View='room'|'desk'|'fly';
function Box({p,s,color}:{p:[number,number,number];s:[number,number,number];color:string}){return <mesh position={p} castShadow receiveShadow><boxGeometry args={s}/><meshStandardMaterial color={color} roughness={.68}/></mesh>;}
function Camera({view}:{view:View}){const {camera,size}=useThree();useEffect(()=>{const positions={room:[4.7,3.6,5.3],desk:[2.5,2.9,5.1],fly:[.1,1.99,.66]};const p=positions[view];const f=view==='fly'?1:Math.max(1,.78/(size.width/size.height));camera.position.set(p[0]*f,1.95+(p[1]-1.95)*f,-.55+(p[2]+.55)*f);camera.lookAt(0,1.95,-.55);camera.updateProjectionMatrix();},[camera,view,size.width,size.height]);return <OrbitControls key={view} target={[0,1.95,-.55]} minDistance={.5} maxDistance={12} maxPolarAngle={Math.PI/2-.02}/>;}
function Scene({screen,version,event,view}:{screen:HTMLCanvasElement;version:number;event:MotorEvent|null;view:View}){
 const texture=useMemo(()=>{const t=new CanvasTexture(screen);t.colorSpace=SRGBColorSpace;return t;},[screen]);
 // Three.js GPU texture invalidation is intentionally imperative.
 // eslint-disable-next-line react/immutability
 useEffect(()=>{texture.needsUpdate=true;},[texture,version]);useEffect(()=>()=>texture.dispose(),[texture]);
 const activeKey=event?.type==='keydown'||event?.type==='input';
 return <><color attach="background" args={['#d6d6cd']}/><ambientLight intensity={1.2}/><directionalLight position={[-3,6,3]} intensity={3} castShadow shadow-mapSize={[2048,2048]}/><pointLight position={[1.5,2.8,-.6]} intensity={8} color="#fff0cc"/>
 <Box p={[0,-.12,0]} s={[14,.2,12]} color="#ada99e"/><Box p={[0,2,-3]} s={[14,4,.15]} color="#e6e5db"/><Box p={[-4,2,0]} s={[.15,4,6]} color="#d0d6cd"/>
 <Box p={[0,1.2,0]} s={[4.8,.15,2.3]} color="#aa805a"/>{[-1,1].flatMap(x=>[-1,1].map(z=><Box key={`${x}${z}`} p={[x*2.1,.58,z*.86]} s={[.12,1.15,.12]} color="#39443f"/>))}
 <Box p={[0,1.3,-.7]} s={[.8,.07,.43]} color="#343b37"/><Box p={[0,1.7,-1.03]} s={[.16,.8,.13]} color="#39443f"/>
 <Box p={[0,2.28,-.91]} s={[3.16,1.94,.12]} color="#252e2a"/>
 <mesh position={[0,2.29,-.842]}><planeGeometry args={[3,1.8]}/><meshBasicMaterial map={texture} toneMapped={false}/></mesh>
 <Box p={[0,1.32,.25]} s={[1.43,.06,.45]} color="#313a36"/>
 {Array.from({length:48},(_,i)=>{const row=Math.floor(i/12),col=i%12;const selected=activeKey&&i===((event?.key?.charCodeAt(0)??0)%48);return <Box key={i} p={[-.645+col*.116,1.361-(selected?.012:0),.09+row*.104]} s={[.097,.035,.082]} color={selected?'#d5b57b':'#ccd0c5'}/>;})}
 <mesh position={[1,1.36,.32]} scale={[.115,.055,.18]} castShadow><sphereGeometry args={[1,24,16]}/><meshStandardMaterial color={event?.type.startsWith('pointer')?'#d5b57b':'#d1d4c9'}/></mesh>
 <Box p={[0,1.55,1.03]} s={[.75,.1,.65]} color="#53645b"/><Box p={[0,1.67,1.35]} s={[.75,.18,.09]} color="#53645b"/>{[-1,1].flatMap(x=>[-1,1].map(z=><Box key={`c${x}${z}`} p={[x*.29,.75,1.03+z*.23]} s={[.05,1.5,.05]} color="#454d46"/>))}
 <group position={[0,.98,.55]} scale={.9} rotation={[activeKey?-.015:0,0,0]}><FlyBody seated typing={activeKey}/></group>
 <Box p={[1.8,1.3,-.65]} s={[.38,.045,.28]} color="#666f5d"/><Box p={[1.8,1.79,-.7]} s={[.04,.98,.04]} color="#66755d"/><mesh position={[1.72,2.26,-.58]} rotation={[0,0,.25]} castShadow><coneGeometry args={[.26,.24,40,1,true]}/><meshStandardMaterial color="#6b795f" side={2}/></mesh>
 <Box p={[-1.83,1.31,.1]} s={[.48,.06,.65]} color="#c7c2ac"/><Box p={[-1.78,1.355,.12]} s={[.44,.03,.61]} color="#e7e1cd"/>
 <ContactShadows position={[0,.001,0]} opacity={.3} scale={12} blur={2} far={5}/><Camera view={view}/></>;
}
export function DeskWorld(props:{screen:HTMLCanvasElement;version:number;event:MotorEvent|null;view:View}){return <Canvas shadows={{type:PCFShadowMap}} dpr={[1,1.5]} camera={{fov:43,near:.05,far:50}} gl={{preserveDrawingBuffer:true}}><Scene {...props}/></Canvas>;}
