export interface ActivityPacket {tick:number;rates:Float32Array;spikes:{tick:number;neuron:number}[]}
export function decodeActivity(buffer:ArrayBuffer,maxEvents=Infinity):ActivityPacket {
 if(buffer.byteLength<16)throw new Error('Truncated neural packet');
 const header=new DataView(buffer);if(header.getUint32(0,true)!==0x31534e43)throw new Error('Unknown neural packet version');
 const tick=header.getUint32(4,true),n=header.getUint32(8,true),count=header.getUint32(12,true);
 if(buffer.byteLength!==16+n*4+count*8)throw new Error('Neural packet length mismatch');
 const rates=new Float32Array(buffer,16,n),pairs=new Uint32Array(buffer,16+n*4,count*2),spikes=[];
 for(let i=Math.max(0,count-Math.max(0,Math.floor(maxEvents)));i<count;i++){if(pairs[i*2]>tick||pairs[i*2+1]>=n)throw new Error('Invalid neural event');spikes.push({tick:pairs[i*2],neuron:pairs[i*2+1]});}
 return {tick,rates,spikes};
}
