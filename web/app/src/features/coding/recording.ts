/** A readable recording layout; all images come from the running application. */
export function drawRecordingFrame(ctx:CanvasRenderingContext2D,{world,brain,activity,screen,tick,status}:{world:HTMLCanvasElement;brain:HTMLCanvasElement|null;activity:HTMLCanvasElement|null;screen:HTMLCanvasElement;tick:number;status:string}){
 const fit=(source:HTMLCanvasElement,x:number,y:number,w:number,h:number)=>{if(!source.width||!source.height)return;const scale=Math.min(w/source.width,h/source.height),sw=source.width*scale,sh=source.height*scale;ctx.drawImage(source,x+(w-sw)/2,y+(h-sh)/2,sw,sh);};
 const label=(text:string,x:number,y:number,size=16,color='#aab8ca')=>{ctx.fillStyle=color;ctx.font=`${size}px system-ui, sans-serif`;ctx.fillText(text,x,y);};
 ctx.fillStyle='#0c1018';ctx.fillRect(0,0,1600,1040);
 label('FlyLab',24,38,27,'#edf3fc');label('Physical coding · live demo',130,37,18);
 ctx.fillStyle='#26b5ed';ctx.beginPath();ctx.arc(1532,29,5,0,Math.PI*2);ctx.fill();
 ctx.fillStyle='#080c13';ctx.fillRect(20,62,1180,918);ctx.fillRect(1220,62,360,918);
 fit(brain??world,20,62,1180,918);
 label(brain?'DESK VIEW':'MALECNS · MODELED ACTIVITY',1240,98,15,'#d9e5f4');
 const instrument=brain?world:activity;if(instrument)fit(instrument,1234,116,332,365);
 label('Real anatomy · modeled dynamics',1240,517,15);
 label('Blue: rate   White: recorded spike',1240,544,14,'#8fceee');
 label('ACTUAL CHROMIUM WORKSPACE',1240,610,15,'#d9e5f4');fit(screen,1234,634,332,180);
 label('Screen → circuit → key contact',1240,884,15);label('Contact → browser key event',1240,912,15);
 label(`${(tick*.002).toFixed(3)} s simulation · ${status}`,24,1017,17,'#d9e5f4');
 label('Single-heading benchmark',1240,1017,15);
}
