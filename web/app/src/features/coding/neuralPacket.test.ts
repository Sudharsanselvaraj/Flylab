import {describe,it,expect} from 'vitest';
import {decodeActivity} from './neuralPacket';
describe('real neural binary frames',()=>{
 it('preserves simulation timestamps, rates and neuron identities',()=>{const b=new ArrayBuffer(40),h=new DataView(b);[0x31534e43,128,2,2].forEach((v,i)=>h.setUint32(i*4,v,true));new Float32Array(b,16,2).set([0,17.5]);new Uint32Array(b,24).set([119,1,128,1]);const p=decodeActivity(b);expect(p.tick).toBe(128);expect(Array.from(p.rates)).toEqual([0,17.5]);expect(p.spikes).toEqual([{tick:119,neuron:1},{tick:128,neuron:1}]);expect(decodeActivity(b,1).spikes).toEqual([{tick:128,neuron:1}]);expect(Array.from(decodeActivity(b,1).rates)).toEqual([0,17.5]);});
 it('rejects truncated transport and future events',()=>{expect(()=>decodeActivity(new ArrayBuffer(8))).toThrow();const b=new ArrayBuffer(28),h=new Uint32Array(b);h.set([0x31534e43,10,1,1,0,11,0]);expect(()=>decodeActivity(b)).toThrow('Invalid neural event');});
});
