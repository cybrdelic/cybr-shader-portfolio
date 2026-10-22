#!/usr/bin/env python3
"""Render all portfolio chapters with the same shader and make a QA contact sheet."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import time
import numpy as np
from PIL import Image, ImageDraw
from native_render import NativeRenderer, atomic_png

ROOT = Path(__file__).resolve().parents[1]
NAMES = ['Assembly','Light','Geometry','Scenes','Elements','Materials','Forest','About']

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--shader',type=Path,default=ROOT/'dist/cybr-computational-instrument.frag')
    ap.add_argument('--output',type=Path,default=ROOT/'qa/chapters')
    ap.add_argument('--width',type=int,default=800)
    ap.add_argument('--height',type=int,default=500)
    ap.add_argument('--quality',type=float,default=1)
    ap.add_argument('--chapters',default='0,1,2,3,4,5,6,7')
    args=ap.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    renderer=NativeRenderer(args.shader)
    frames=[]; records=[]
    for number in [int(x) for x in args.chapters.split(',')]:
        start=time.monotonic()
        frame=renderer.render(args.width,args.height,time=2.5+number*2.0,chapter=number,quality=args.quality)
        path=args.output/f'chapter-{number}.png'
        atomic_png(path,frame)
        record={'chapter':number,'name':NAMES[number],'seconds':round(time.monotonic()-start,3),
                'path':str(path),'sha256':hashlib.sha256(frame.tobytes()).hexdigest(),
                'mean_rgb':np.mean(frame,axis=(0,1)).round(2).tolist(),'width':args.width,'height':args.height}
        print(json.dumps(record),flush=True)
        records.append(record);frames.append((number,frame))
    columns=4 if len(frames)>4 else len(frames)
    tilew=480 if args.width>=args.height else 270
    tileh=round(tilew*args.height/args.width)
    sheet=Image.new('RGB',(columns*tilew,((len(frames)+columns-1)//columns)*(tileh+28)),(14,16,18))
    draw=ImageDraw.Draw(sheet)
    for j,(number,frame) in enumerate(frames):
        x=(j%columns)*tilew;y=(j//columns)*(tileh+28)
        shot=Image.fromarray(frame).resize((tilew,tileh),Image.Resampling.LANCZOS)
        sheet.paste(shot,(x,y));draw.text((x+10,y+tileh+7),f'{number+1:02d}  {NAMES[number]}',fill=(220,221,216))
    sheet.save(args.output/'contact.png')
    (args.output/'report.json').write_text(json.dumps({'source_sha256':renderer.source_hash,'renderer':renderer.renderer_name,'frames':records},indent=2)+'\n')
    renderer.close()

if __name__=='__main__':main()
