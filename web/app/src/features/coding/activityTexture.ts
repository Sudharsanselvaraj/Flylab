/** Display encoding only: R = measured rate/response, G = real spike recency.
 * The activity threshold matches the instrument's >1 Hz count. Display saturation
 * does not clamp simulation state. Neither channel creates events or advances time.
 */
export function fillActivityTexture(pixels:Float32Array,rates:ArrayLike<number>,spikes:{tick:number;neuron:number}[],tick:number,dt:number,baseline:ArrayLike<number>|undefined,response:boolean,trailMs:number){
 pixels.fill(0);
 const delta=response&&baseline!==undefined;
 for(let i=0;i<rates.length&&i*4<pixels.length;i++){
  const hz=delta?Math.abs(rates[i]-(baseline![i]??0)):rates[i];
  pixels[i*4]=delta?Math.min(1,Math.max(0,hz/8)):Math.min(1,Math.max(0,(hz-1)/39));
 }
 const trail=Math.max(dt,trailMs/1000);
 for(const e of spikes){
  const age=(tick-e.tick)*dt;
  if(e.neuron<0||e.neuron>=rates.length||e.neuron*4+1>=pixels.length||age<0||age>trail)continue;
  pixels[e.neuron*4+1]=Math.max(pixels[e.neuron*4+1],Math.pow(1-age/trail,2));
 }
}
