import { useMemo } from 'react';
import { BufferGeometry, DoubleSide, Float32BufferAttribute, Quaternion, Shape, ShapeGeometry, Vector3 } from 'three';
type P=[number,number,number];

function Rod({a,b,r=.012,color='#b0b6b4',metal=.75}:{a:P;b:P;r?:number;color?:string;metal?:number}){
  const shape=useMemo(()=>{
    const from=new Vector3(...a),to=new Vector3(...b),axis=to.clone().sub(from);
    return {center:from.add(to).multiplyScalar(.5),length:axis.length(),rotation:new Quaternion().setFromUnitVectors(new Vector3(0,1,0),axis.normalize())};
  },[a,b]);
  return <mesh position={shape.center} quaternion={shape.rotation} castShadow><cylinderGeometry args={[r,r,shape.length,12]}/><meshStandardMaterial color={color} metalness={metal} roughness={.32}/></mesh>;
}
function Wing({side,folded=false}:{side:number;folded?:boolean}){
  const shape=useMemo(()=>{
    const s=new Shape();s.moveTo(0,0);s.bezierCurveTo(.09,.015,.24,.19,.21,.36);s.bezierCurveTo(.16,.53,.015,.43,-.018,.26);s.bezierCurveTo(-.04,.13,-.015,.035,0,0);return new ShapeGeometry(s,24);
  },[]);
  const veins=useMemo(()=>{
    const lines=[[[0,0],[.11,.14],[.15,.36]],[[0,0],[.055,.18],[.04,.39]],[[.05,.14],[.18,.22]],[[.06,.24],[.17,.33]]];
    const positions:number[]=[];for(const line of lines)for(let i=1;i<line.length;i++)positions.push(line[i-1][0],line[i-1][1],.002,line[i][0],line[i][1],.002);
    return new BufferGeometry().setAttribute('position',new Float32BufferAttribute(positions,3));
  },[]);
  return <group position={[side*.075,1.06,.15]} rotation={[Math.PI/2,0,-side*.16]} scale={[side*(folded?.72:1),folded?.72:1,1]}>
    <mesh geometry={shape}><meshPhysicalMaterial color="#cad5cb" transparent opacity={.56} roughness={.19} metalness={.08} side={DoubleSide} depthWrite={false}/></mesh>
    <lineSegments geometry={veins}><lineBasicMaterial color="#748176" transparent opacity={.6}/></lineSegments>
  </group>;
}
export function FlyBody({seated=false,typing=false,effectors,legPoses,foldedWings=false}:{seated?:boolean;typing?:boolean;effectors?:{left:P;right:P};legPoses?:{left:P[][];right:P[][]};foldedWings?:boolean}={}){
  const bristles=useMemo(()=>{
    const vertices:number[]=[];
    for(let i=0;i<70;i++){
      const a=i*2.39996,v=-.8+1.6*((i%17)/16),q=Math.sqrt(1-v*v);
      const x=Math.cos(a)*q*.125,y=.98+v*.15,z=.15+Math.sin(a)*q*.18;
      vertices.push(x,y,z,x*1.18,y+(y-.98)*.2,z+(z-.15)*.16);
    }
    return new BufferGeometry().setAttribute('position',new Float32BufferAttribute(vertices,3));
  },[]);
  return <group>
    <mesh position={[0,.94,.35]} scale={[.145,.145,.245]} rotation={[-.16,0,0]} castShadow><sphereGeometry args={[1,48,32]}/><meshPhysicalMaterial color="#493426" metalness={.22} roughness={.34} clearcoat={.5}/></mesh>
    {[.28,.37,.45].map((z,i)=><mesh key={z} position={[0,.94-i*.008,z]} rotation={[.08,0,0]} scale={[1,.91,1]}><torusGeometry args={[.14-i*.015,.006,8,40]}/><meshStandardMaterial color="#241d18" roughness={.65}/></mesh>)}
    <mesh position={[0,.99,.15]} scale={[.125,.155,.17]} castShadow><sphereGeometry args={[1,48,32]}/><meshPhysicalMaterial color="#8a7052" roughness={.65} metalness={.13}/></mesh>
    <lineSegments geometry={bristles}><lineBasicMaterial color="#30261c"/></lineSegments>
    <mesh position={[0,1.13,-.015]} scale={[.132,.11,.105]} castShadow><sphereGeometry args={[1,40,28]}/><meshStandardMaterial color="#9d8060" roughness={.6}/></mesh>
    {[-1,1].map(side=><group key={side}>
      <mesh position={[side*.097,1.15,-.045]} scale={[.069,.095,.077]} rotation={[0,side*-.23,-side*.2]} castShadow><icosahedronGeometry args={[1,4]}/><meshPhysicalMaterial color="#a4412c" roughness={.37} clearcoat={.35} flatShading/></mesh>
      <mesh position={[side*.036,1.15,-.109]} scale={[.018,.019,.035]}><sphereGeometry args={[1,12,10]}/><meshStandardMaterial color="#433126"/></mesh>
      <Rod a={[side*.04,1.16,-.13]} b={[side*.077,1.195,-.19]} r={.0025} color="#433126" metal={0}/>
      {/* Six legs. Desk forelegs respond only to actual computer input. */}
      {(legPoses?.[side<0?'left':'right']??[
        effectors ? [[side*.09,.95,.04],[side*.3,.8,-.05],[(side<0?effectors.left:effectors.right)[0],.6,(side<0?effectors.left:effectors.right)[2]+.12],side<0?effectors.left:effectors.right] : seated ? [[side*.09,.95,.04],[side*.19,.72,-.1],[side*.19,.42,-.29],[side*.2,typing?.35:.38,-.43]] : [[side*.09,.95,.04],[side*.19,.85,-.09],[side*.19,.49,-.31],[side*.2,.30,-.4]],
        seated ? [[side*.11,.95,.15],[side*.23,.78,.3],[side*.26,.68,.5],[side*.2,.68,.6]] : [[side*.11,.95,.15],[side*.23,.88,.05],[side*.26,.76,-.02],[side*.2,.765,-.12]],
        seated ? [[side*.09,.92,.25],[side*.22,.8,.45],[side*.22,.68,.58],[side*.16,.68,.68]] : [[side*.09,.92,.25],[side*.22,.86,.36],[side*.22,.765,.35],[side*.16,.765,.4]],
      ]).map((leg,i)=><group key={i}>{leg.slice(1).map((to,j)=><Rod key={j} a={leg[j] as P} b={to as P} r={j===0?.008:.005} color="#45382e" metal={.12}/>)}</group>)}
      <Wing side={side} folded={foldedWings}/>
    </group>)}
  </group>;
}
