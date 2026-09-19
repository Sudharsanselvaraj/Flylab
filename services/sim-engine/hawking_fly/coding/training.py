"""Offline, supervised imitation from real browser captures. Never an inference oracle."""
import hashlib,itertools,json,time
import numpy as np
from .core import ART,VERSION,Reservoir,graph,split,teacher,digest

def compose(a,b):
    return np.concatenate([np.asarray(a).reshape(24,16,3),np.asarray(b).reshape(24,16,3)],axis=1).reshape(-1).tolist()

def train(seed=37,epochs=900,resume=False,cancelled=None):
    import torch
    if not 1<=epochs<=10000:raise ValueError("epochs must be between 1 and 10000")
    torch.set_num_threads(2);torch.manual_seed(seed);np.random.seed(seed)
    data=json.loads((ART/'captures.json').read_text());g=graph();reservoir=Reservoir(g)
    pages={tuple(p['state']):p['pixels'] for p in data['pages']}
    required=set(itertools.product(range(5),repeat=3))
    if set(pages)!=required:raise ValueError('All 125 browser-rendered curriculum states required')
    dataset_sha=digest(data);run_id=f'{VERSION}-{seed}-{dataset_sha[:12]}'
    for folder in ('trained_policy','training_manifest','metrics','checkpoints'):(ART/folder).mkdir(exist_ok=True)
    status=ART/'metrics/status.json'
    def report(**kw):status.write_text(json.dumps({'run_id':run_id,**kw}))
    report(state='encoding',progress=0)
    cache=ART/'checkpoints/features.npz'
    if cache.exists():
        with np.load(cache,allow_pickle=False) as c:
            valid=str(c['dataset_sha'])==dataset_sha and str(c['graph_sha'])==g['sha256']
            if valid:X=c['X'];Y=c['Y'];S=c['S']
    else:valid=False
    if not valid:
        X=[];Y=[];S=[]
        for ti,target in enumerate(itertools.product(range(2,5),repeat=3)):
            if cancelled and cancelled():raise InterruptedError('Training cancelled')
            for current,pixels in pages.items():
                observation=compose(pages[target],pixels)
                x,_=reservoir.encode(observation)
                X.append(x);Y.append(teacher(target,current));S.append(split(target))
            report(state='encoding',progress=(ti+1)/27)
        X=np.array(X);Y=np.array(Y);S=np.array(S)
        np.savez_compressed(cache,X=X,Y=Y,S=S,dataset_sha=dataset_sha,graph_sha=g['sha256'])
    mask=S=='train';mean=X[mask].mean(0);scale=np.maximum(X[mask].std(0),.01)
    x=torch.tensor((X-mean)/scale,dtype=torch.float32);y=torch.tensor(Y,dtype=torch.long)
    net=torch.nn.Sequential(torch.nn.Linear(X.shape[1],48),torch.nn.Tanh(),torch.nn.Linear(48,13))
    opt=torch.optim.Adam(net.parameters(),lr=.005,weight_decay=1e-5)
    start=0;history=[];best=float('inf');best_state=None
    checkpoint=ART/'checkpoints/optimizer.pt'
    if resume:
        ck=torch.load(checkpoint,weights_only=True)
        if ck['run_id']!=run_id:raise ValueError('Resume dataset/seed mismatch')
        net.load_state_dict(ck['model']);opt.load_state_dict(ck['optimizer']);start=ck['epoch'];history=ck['history'];best=ck.get('best_loss',float('inf'));best_state=ck.get('best_model')
    trainmask=torch.tensor(mask);valmask=torch.tensor(S=='validation')
    for epoch in range(start,start+epochs):
        if cancelled and cancelled():raise InterruptedError('Training cancelled')
        opt.zero_grad();logits=net(x[trainmask]);loss=torch.nn.functional.cross_entropy(logits,y[trainmask]);loss.backward();opt.step()
        if epoch%20==0 or epoch==start+epochs-1:
            with torch.no_grad():
                val_loss=float(torch.nn.functional.cross_entropy(net(x[valmask]),y[valmask]))
                accuracy=float((net(x[trainmask]).argmax(1)==y[trainmask]).float().mean())
            row={'epoch':epoch+1,'train_loss':float(loss.detach()),'validation_loss':val_loss,'train_action_accuracy':accuracy};history.append(row)
            if val_loss<best:best=val_loss;best_state={k:v.detach().clone() for k,v in net.state_dict().items()}
            report(state='optimizing',**row)
        if (epoch+1)%100==0:
            torch.save({'run_id':run_id,'epoch':epoch+1,'model':net.state_dict(),'optimizer':opt.state_dict(),'history':history,'best_loss':best,'best_model':best_state},checkpoint)
    torch.save({'run_id':run_id,'epoch':start+epochs,'model':net.state_dict(),'optimizer':opt.state_dict(),'history':history,'best_loss':best,'best_model':best_state},checkpoint)
    net.load_state_dict(best_state)
    weights={k:v.detach().numpy() for k,v in net.state_dict().items()}
    out=ART/'trained_policy/policy.npz'
    np.savez_compressed(out,mean=mean,scale=scale,w1=weights['0.weight'].T,b1=weights['0.bias'],w2=weights['2.weight'].T,b2=weights['2.bias'],graph_sha=g['sha256'],version=VERSION)
    with torch.no_grad():pred=net(x).argmax(1).numpy()
    accuracies={s:float((pred[S==s]==Y[S==s]).mean()) for s in ('train','validation','test')}
    manifest={'version':VERSION,'run_id':run_id,'seed':seed,'epochs':start+epochs,'method':'Supervised imitation; privileged offline correction oracle. No RL claim.','optimizer':'Adam lr=.005 weight_decay=.00001','hidden_units':48,'trainable_parameters':sum(p.numel() for p in net.parameters()),'graph_sha256':g['sha256'],'capture_sha256':dataset_sha,'checkpoint_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'selection':'Lowest validation cross entropy among evaluated epochs','split':{s:[list(t) for t in itertools.product(range(2,5),repeat=3) if split(t)==s] for s in ('train','validation','test')},'offline_action_accuracy':accuracies,'browser_rollout_verified':False,'scope':'Fixed layout, three elements, three colours. Held-out target palette compositions; not unseen syntax or layouts.','dynamics_validated':False,'flyvis_to_malecns_mapping_verified':False,'capture_renderer':data.get('renderer'),'created_unix':time.time()}
    (ART/'training_manifest/manifest.json').write_text(json.dumps(manifest,indent=2));(ART/'metrics/history.json').write_text(json.dumps(history,indent=2))
    report(state='trained',manifest=manifest)
    return manifest
