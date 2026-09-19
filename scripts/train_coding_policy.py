"""Run after capturing curriculum in ?view=coding → Training → Capture & train."""
import argparse,json
from hawking_fly.coding.training import train
p=argparse.ArgumentParser();p.add_argument('--seed',type=int,default=37);p.add_argument('--epochs',type=int,default=900);p.add_argument('--resume',action='store_true');a=p.parse_args()
print(json.dumps(train(a.seed,a.epochs,a.resume),indent=2))
