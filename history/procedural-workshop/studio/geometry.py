"""Precision parametric mechanisms for CYBR's studio material revision.
All surfaces below are generated from dimensions, profiles and seeded procedures.
No image-derived geometry. Vertex normals follow those surfaces directly.
"""
from pathlib import Path
import numpy as np, math, json, gzip, struct, hashlib
from scipy.ndimage import gaussian_filter, map_coordinates
R=Path(__file__).resolve().parent.parent
TAU=math.tau
rng=np.random.default_rng(270219)
DT=np.dtype([('p','<f4',(3,)),('n','<i2',(3,)),('m','u1',(4,)),('pad','u1',(2,)),('uv','<i2',(2,))])
AXES=np.array([[1,0],[-.5,math.sqrt(3)/2],[.5,math.sqrt(3)/2],[1,0],[.5,-math.sqrt(3)/2],[-.5,-math.sqrt(3)/2],[-1,0]])

def unit(v):
 v=np.asarray(v,float);return v/np.maximum(np.linalg.norm(v,axis=-1,keepdims=True),1e-12)
def rx(a):
 c,s=math.cos(a),math.sin(a);return np.array([[1,0,0],[0,c,-s],[0,s,c]])
def ry(a):
 c,s=math.cos(a),math.sin(a);return np.array([[c,0,s],[0,1,0],[-s,0,c]])
def rz(a):
 c,s=math.cos(a),math.sin(a);return np.array([[c,-s,0],[s,c,0],[0,0,1]])
def between(y):
 y=unit(y);x=unit(np.cross([0,0,1] if abs(y[2])<.9 else [1,0,0],y));z=np.cross(x,y);return np.stack([x,y,z],1)

class Builder:
 def __init__(self):self.v=[];self.f=[];self.groups=[];self.offset=0;self.count=0;self.obj=0;self.part=0;self.start=0;self.vstart=0
 def begin(self,name,obj,part=0):
  self.end();self.name=name;self.obj=obj;self.part=part;self.start=self.count;self.vstart=self.offset
 def end(self):
  if hasattr(self,'name'):
   self.groups.append(dict(name=self.name,object=self.obj,part=self.part,indexStart=self.start,indexCount=self.count-self.start,vertices=self.offset-self.vstart,triangles=(self.count-self.start)//3));del self.name
 def add(self,p,n,f,mat,ao=1.,M=None,C=(0,0,0),part=None,world=False,uv=None):
  p=np.asarray(p,dtype=float).reshape(-1,3);n=unit(np.asarray(n,dtype=float).reshape(-1,3));f=np.asarray(f,dtype=np.uint32).reshape(-1,3)
  if M is not None:p=p@M.T;n=n@M.T
  p+=np.asarray(C)
  if 1<=self.obj<=6 and not world:
   a,b=AXES[self.obj];T=np.array([[a,0,-b],[0,1,0],[b,0,a]]);p=p@T.T+np.array([a*3.15,0,b*3.15]);n=n@T.T
  # Correct winding locally to match analytic surface normals.
  if len(f):
   cross=np.cross(p[f[:,1]]-p[f[:,0]],p[f[:,2]]-p[f[:,0]]);nn=n[f].sum(axis=1);flip=(cross*nn).sum(axis=1)<0
   tmp=f[flip,1].copy();f[flip,1]=f[flip,2];f[flip,2]=tmp
   good=np.linalg.norm(cross,axis=1)>1e-12;f=f[good]
  a=np.zeros(len(p),DT);a['p']=p;a['n']=np.round(n*32767).astype(np.int16);a['m'][:,0]=mat;a['m'][:,1]=np.round(np.clip(ao,0,1)*255).astype(np.uint8);a['m'][:,2]=self.part if part is None else part;a['m'][:,3]=self.obj;a['pad'][:]=255
  
  if uv is not None:a['uv']=np.round(np.clip(np.asarray(uv).reshape(-1,2),-1,1)*32767).astype(np.int16)
  self.v.append(a);self.f.append(f.ravel()+self.offset);self.offset+=len(p);self.count+=f.size
 def write(self):
  self.end();v=np.concatenate(self.v);f=np.concatenate(self.f).astype('<u4')
  v['p']=np.round(v['p'],6)
  unique,first,inverse=np.unique(v,return_index=True,return_inverse=True)
  v=unique;f=inverse[f].astype('<u4')
  for g in self.groups:g['vertices']=len(np.unique(f[g['indexStart']:g['indexStart']+g['indexCount']]))
  payload=struct.pack('<4sIII',b'CYB2',len(v),len(f),28)+v.tobytes()+f.tobytes();compressed=gzip.compress(payload,compresslevel=9,mtime=0)
  (R/'geometry/mesh.bin').write_bytes(payload);(R/'geometry/mesh.bin.gz').write_bytes(compressed)
  info=dict(format='CYB2',vertices=len(v),triangles=len(f)//3,stride=28,uncompressedBytes=len(payload),compressedBytes=len(compressed),sha256=hashlib.sha256(payload).hexdigest(),groups=self.groups,source='Entirely procedural: cleavage-plane schist, rooted asymmetric broadleaf tree, closed airfoil impeller, spherical bearing balls, dimensioned mechanical housings. No scans, photographs, generated imagery, or imported models.')
  (R/'geometry/packed.json').write_text(json.dumps(info,indent=2));print(json.dumps(info,indent=2))
B=Builder()

def grid_faces(rows,cols):
 a=(np.arange(rows-1)[:,None]*cols+np.arange(cols-1)[None,:]).ravel();return np.concatenate([np.stack([a,a+cols,a+cols+1],1),np.stack([a,a+cols+1,a+1],1)])

def lathe(profile,mat,segments=72,M=None,C=(0,0,0),ao=1.,part=None):
 """Revolve a cross section; vertices duplicated at profile changes preserve
 deliberate machined corners, while rounded profile arcs interpolate normals."""
 segments=segments if segments<12 else max(12,int(math.ceil(segments*(.62 if segments>=80 else .45)/4))*4)
 source=np.array(profile,float);refined=[]
 for i in range(len(source)-1):
  a,b=source[i],source[i+1];steps=max(1,int(np.ceil(abs(b[0]-a[0])/.09))) if abs(b[1]-a[1])<1e-6 else max(1,int(np.ceil(abs(b[1]-a[1])/.12)))
  refined.extend([a+(b-a)*t/steps for t in range(steps)])
 refined.append(source[-1]);P=np.array(refined,float);ang=np.linspace(0,TAU,segments+1);co,si=np.cos(ang),np.sin(ang)
 for i in range(len(P)-1):
  r0,y0=P[i];r1,y1=P[i+1];dr,dy=r1-r0,y1-y0
  if abs(dr)+abs(dy)<1e-9:continue
  norm=unit([dy,-dr])
  # Profiles carry tangent-correct smooth normals when both neighbouring
  # slopes belong to a rounded bevel, but retain hard planes at large turns.
  ns=[]
  closed=np.linalg.norm(P[0]-P[-1])<1e-8
  for k in [i,i+1]:
   before=P[k]-P[k-1] if k>0 else (P[-1]-P[-2] if closed else P[1]-P[0])
   after=P[k+1]-P[k] if k<len(P)-1 else (P[1]-P[0] if closed else before)
   previous=unit([before[1],-before[0]]);following=unit([after[1],-after[0]])
   ns.append(unit(previous+following) if np.dot(previous,following)>.70 else norm)
  p=np.concatenate([np.stack([co*r0,np.full_like(co,y0),si*r0],1),np.stack([co*r1,np.full_like(co,y1),si*r1],1)])
  n=np.concatenate([np.stack([co*ns[0][0],np.full_like(co,ns[0][1]),si*ns[0][0]],1),np.stack([co*ns[1][0],np.full_like(co,ns[1][1]),si*ns[1][0]],1)])
  B.add(p,n,grid_faces(2,segments+1),mat,ao,M,C,part)

def rounded_profile(r0,r1,y0,y1,b):
 # Rounded rectangular ring section, CCW in radial/height coordinates.
 b=min(b,(r1-r0)*.49,(y1-y0)*.49);p=[]
 for cx,cy,start in [(r1-b,y0+b,-90),(r1-b,y1-b,0),(r0+b,y1-b,90),(r0+b,y0+b,180)]:
  for a in np.linspace(math.radians(start),math.radians(start+90),4):p.append([cx+b*math.cos(a),cy+b*math.sin(a)])
 p.append(p[0]);return p

def ring(ro,ri,h,mat,C=(0,0,0),b=.009,M=None,segments=72,part=None,ao=1.):lathe(rounded_profile(ri,ro,-h/2,h/2,b),mat,segments,M,C,ao,part)
def disk(r,h,mat,C=(0,0,0),b=.008,M=None,segments=72,part=None,ao=1.):
 b=min(b,h*.49,r*.2);p=[[0,-h/2],[r-b,-h/2]]
 for a in np.linspace(-math.pi/2,0,4):p.append([r-b+b*math.cos(a),-h/2+b+b*math.sin(a)])
 for a in np.linspace(0,math.pi/2,4):p.append([r-b+b*math.cos(a),h/2-b+b*math.sin(a)])
 p+=[[0,h/2]];lathe(p,mat,segments,M,C,ao,part)

def box(size,mat,C=(0,0,0),b=.008,M=None,ao=1.,part=None):
 # Spherically rounded cuboid from six projected cube-face patches.
 half=np.asarray(size)/2;b=min(b,float(half.min())*.49);core=half-b
 for axis in range(3):
  axes=[i for i in range(3) if i!=axis]
  for sign in [-1,1]:
   a,c=axes
   def samples(h):
    e=min(b*2,h*.9);return np.unique(np.r_[-h,-h+e*.33,-h+e,h-e,h-e*.33,h])
   u,v=np.meshgrid(samples(half[a]),samples(half[c]));p=np.zeros((u.size,3));p[:,axis]=half[axis]*sign;p[:,a]=u.ravel();p[:,c]=v.ravel();cl=np.clip(p,-core,core);n=unit(p-cl);p=cl+n*b
   B.add(p,n,grid_faces(*u.shape),mat,ao,M,C,part=part)

def tube(points,radii,mat,segments=10,ao=1.,part=None):
 points=np.array(points,float);radii=np.broadcast_to(radii,(len(points),));p=[];n=[];angles=np.linspace(0,TAU,segments+1)
 for i,(q,r) in enumerate(zip(points,radii)):
  tangent=unit(points[min(i+1,len(points)-1)]-points[max(0,i-1)]);basis=between(tangent);rad=basis[:,0,None]*np.cos(angles)+basis[:,2,None]*np.sin(angles)
  p.extend(q+rad.T*r);n.extend(rad.T)
 distance=np.r_[0,np.cumsum(np.linalg.norm(np.diff(points,axis=0),axis=1))]
 uu,vv=np.meshgrid(np.linspace(0,1,segments+1),np.minimum(distance*1.4,.999))
 B.add(p,n,grid_faces(len(points),segments+1),mat,ao,part=part,uv=np.stack([uu,vv],-1))

def rod(a,b,r,mat,segments=32):
 a,b=np.array(a),np.array(b);disk(r,np.linalg.norm(b-a),mat,(a+b)/2,min(r*.2,.005),between(b-a),segments)

def bolt(C,r=.03,h=.015,M=None):
 # Head, visible annular shoulder, hexagonal socket wall and recessed bottom.
 C=np.asarray(C);ring(r,r*.46,h,4,C,b=min(h*.25,.003),segments=16,M=M)
 disk(r*.455,.003,2,C+(np.array([0,-h*.34,0]) if M is None else M@np.array([0,-h*.34,0])),b=.0005,segments=6,M=M)
 # A six-sided wall produces a real socket silhouette rather than a painted dot.
 ring(r*.47,r*.37,h*.7,2,C,b=.0004,segments=6,M=M)

def torus(Radius,r,mat,C=(0,0,0),M=None,segments=72,steps=8,part=None):
 segments=max(8,int(math.ceil(segments*.50/4))*4);steps=min(steps,6)
 u,v=np.meshgrid(np.linspace(0,TAU,segments+1),np.linspace(0,TAU,steps+1));n=np.stack([np.cos(v)*np.cos(u),np.sin(v),np.cos(v)*np.sin(u)],-1);p=n*r+np.stack([Radius*np.cos(u),np.zeros_like(u),Radius*np.sin(u)],-1)
 B.add(p,n,grid_faces(*u.shape),mat,M=M,C=C,part=part)

def base():
 disk(1.025,.11,2,(0,.35,0),b=.012);disk(.994,.19,7,(0,.488,0),b=.012)
 ring(1.001,.982,.018,4,(0,.401,0),b=.003);ring(1.003,.971,.018,4,(0,.58,0),b=.003)
 disk(.932,.027,2,(0,.598,0),b=.005);ring(.94,.908,.013,3,(0,.609,0),b=.003)
 for a in np.linspace(0,TAU,8,endpoint=False):bolt([.965*math.cos(a),.594,.965*math.sin(a)],.022,.012)
 # Elastomer isolation beneath each housing.
 for a in [0,TAU/3,2*TAU/3]:disk(.085,.026,16,(.72*math.cos(a),.287,.72*math.sin(a)),b=.004,segments=24)
 box([.38,.028,.13],18,(.82,.635,0),b=.005,M=ry(math.pi/2))


# The exhibit definitions are kept separate for review and independent revisions.
exec((Path(__file__).parent/'exhibits.py').read_text(), globals())
