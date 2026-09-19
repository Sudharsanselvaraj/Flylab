export interface CodingNode{body_id:string;type:string;side:string|null;position:number[]|null;input:boolean}
export interface CodingGraph{nodes:CodingNode[];edges:{pre:number;post:number;weight:number}[];sha256:string;dataset:string}
export interface Task{id:number;state:number[];split:'train'|'validation'|'test';source:string}
export interface Manifest{run_id:string;trainable_parameters:number;offline_action_accuracy:Record<string,number>;checkpoint_sha256:string;split:Record<string,number[][]>}
export interface Catalog{graph:CodingGraph;actions:{name:string;token:string|null}[];base:string;dt:number;manifest:Manifest|null;tasks:Task[];curriculum:{state:number[];source:string}[]}
export interface Decision{kind:'decision';tick:number;time:number;action:number;label:string;neural:{rates:number[];spikes:{tick:number;neuron:number}[];trajectory:{tick:number;rates:number[]}[]};observation_sha256:string;logits:number[]}
