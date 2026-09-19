import {describe,it,expect} from 'vitest';
import {fillActivityTexture} from './activityTexture';
describe('measured CNS display',()=>{
 it('leaves inactive cells neutral and uses independent white spike recency',()=>{
  const p=new Float32Array(20);fillActivityTexture(p,[0,1,2,20,70],[{tick:100,neuron:0}],100,.002,undefined,false,12);
  expect(p[0]).toBe(0);expect(p[4]).toBe(0);expect(p[8]).toBeCloseTo(1/39);expect(p[12]).toBeCloseTo(19/39);expect(p[16]).toBe(1);
  expect(p[1]).toBe(1);expect(p[5]).toBe(0); // an actual event can outlast its cell's rate
 });
 it('does not suppress a real spike when its rate equals the resting baseline',()=>{
  const p=new Float32Array(4);fillActivityTexture(p,[20],[{tick:90,neuron:0}],100,.002,[20],true,40);
  expect(p[0]).toBe(0);expect(p[1]).toBe(.25);
 });
 it('separates resting rates from measured responses without generating events',()=>{
  const p=new Float32Array(12);fillActivityTexture(p,[30,12,6],[],100,.002,[30,4,10],true,20);
  expect([p[0],p[4],p[8]]).toEqual([0,1,.5]);expect([p[1],p[5],p[9]]).toEqual([0,0,0]);
 });
 it('uses only real in-window spikes, decays in simulation time, and clears stale values',()=>{
  const p=new Float32Array(12);fillActivityTexture(p,[30,12,6],[{tick:100,neuron:1},{tick:101,neuron:0},{tick:80,neuron:2}],100,.002,[30,4,10],true,20);
  expect(p[5]).toBe(1);expect(p[1]).toBe(0);expect(p[9]).toBe(0);
  fillActivityTexture(p,[30,12,6],[{tick:100,neuron:1}],105,.002,[30,4,10],true,20);expect(p[5]).toBe(.25);
  fillActivityTexture(p,[30,12,6],[],106,.002,undefined,false,20);expect(p[5]).toBe(0);expect(p[0]).toBeCloseTo(29/39);
 });
});
