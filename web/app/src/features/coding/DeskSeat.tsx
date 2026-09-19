import {useMemo,memo} from 'react';
import {RoundedBox} from '@react-three/drei';
import {Euler,Matrix4,Quaternion,Vector3} from 'three';
import {FlyBody} from './FlyBody';
import type {PhysicalFrame} from './physicalTypes';
type P=[number,number,number];

// Seat top is 1.03 m, below the 1.275 m desktop. The abdomen's lowest
// point is 1.038 m. Chair front (z=.70) clears the desk edge (z=.65).
const ORIGIN:P=[0,.62,.064];
const SCALE=1.2;
const PITCH=.65;
const INVERSE=new Matrix4().compose(new Vector3(...ORIGIN),new Quaternion().setFromEuler(new Euler(PITCH,0,0)),new Vector3(SCALE,SCALE,SCALE)).invert();
function local(p:number[]):P{return new Vector3(...p).applyMatrix4(INVERSE).toArray() as P;}

function Beam({from,to,r=.024,color='#33363e'}:{from:P;to:P;r?:number;color?:string}){
 const transform=useMemo(()=>{const a=new Vector3(...from),b=new Vector3(...to),axis=b.clone().sub(a);return {position:a.add(b).multiplyScalar(.5),length:axis.length(),rotation:new Quaternion().setFromUnitVectors(new Vector3(0,1,0),axis.normalize())};},[from,to]);
 return <mesh position={transform.position} quaternion={transform.rotation} castShadow><cylinderGeometry args={[r,r,transform.length,12]}/><meshStandardMaterial color={color} metalness={.45} roughness={.48}/></mesh>;
}
function Pad({position,size,color='#40434c',rotation=0}:{position:P;size:P;color?:string;rotation?:number}){
 return <RoundedBox args={size} position={position} rotation={[rotation,0,0]} radius={.045} smoothness={3} castShadow receiveShadow><meshStandardMaterial color={color} roughness={.91}/></RoundedBox>;
}
export const DeskChair=memo(function DeskChair(){
 return <group>
  <Pad position={[0,.935,1.10]} size={[.80,.11,.80]} color="#292c34"/>
  <Pad position={[0,.985,1.10]} size={[.76,.09,.76]}/>
  <Pad position={[0,1.36,1.465]} size={[.70,.55,.13]} rotation={.10}/>
  <Pad position={[0,1.29,1.39]} size={[.62,.18,.105]} color="#50535c" rotation={.10}/>
  {[-1,1].map(side=><group key={side}>
   <Beam from={[side*.26,.90,1.39]} to={[side*.26,1.50,1.575]} r={.022}/>
   <Beam from={[side*.35,.94,1.2]} to={[side*.35,1.22,1.2]} r={.021}/>
   <Pad position={[side*.36,1.245,1.07]} size={[.085,.075,.46]} color="#292c34"/>
   <Beam from={[side*.25,.91,.84]} to={[side*.25,.63,.88]} r={.018}/>
  </group>)}
  <Beam from={[-.34,.625,.9]} to={[.34,.625,.9]} r={.026} color="#666b76"/>
  <Beam from={[0,.14,1.11]} to={[0,.90,1.11]} r={.047} color="#828997"/>
  <Beam from={[0,.15,1.11]} to={[0,.53,1.11]} r={.070}/>
  {Array.from({length:5},(_,i)=>{const angle=i*Math.PI*2/5;const x=Math.sin(angle)*.49,z=1.11+Math.cos(angle)*.49;return <group key={i}>
   <Beam from={[0,.18,1.11]} to={[x,.115,z]} r={.038}/>
   <mesh position={[x,.055,z]} rotation={[0,angle,Math.PI/2]} castShadow><cylinderGeometry args={[.07,.07,.065,20]}/><meshStandardMaterial color="#20232b" roughness={.85}/></mesh>
  </group>;})}
 </group>;
});

export const SeatedDeskFly=memo(function SeatedDeskFly({frame}:{frame:PhysicalFrame|null}){
 const legs=(side:number):P[][]=>{
  const tip=side<0?(frame?.left_effector??[-.18,1.58,.53]):(frame?.effector??[.18,1.58,.53]);
  return [
   // Only the body/root pose changes: the fingertip remains at the exact
   // backend contact coordinate, including replay and held modifier keys.
   [[side*.09,.95,.04],local([side*.30,1.46,.64]),local([tip[0],tip[1]+.10,tip[2]+.11]),local(tip)],
   [[side*.11,.95,.15],local([side*.27,1.19,.83]),local([side*.28,1.08,.76]),local([side*.23,1.03,.82])],
   [[side*.09,.92,.25],local([side*.29,1.10,1.15]),local([side*.28,.79,1.0]),local([side*.26,.651,.90])],
  ];
 };
 return <group position={ORIGIN} rotation={[PITCH,0,0]} scale={SCALE}><FlyBody seated legPoses={{left:legs(-1),right:legs(1)}} foldedWings/></group>;
});
