"""Asset-level replacement of the geological specimen and grown bonsai.
Executed within geometry.py's explicit mesh builder. These are authored
procedural assets, not photographs/scans and not signed-distance ray marching.
The fields here are converted to meshes OFFLINE only.
"""
from skimage.measure import marching_cubes
from scipy.interpolate import CubicSpline

def grid_volume(lo, hi, spacing):
    lo=np.array(lo,float);hi=np.array(hi,float)
    shape=np.ceil((hi-lo)/spacing).astype(int)+1
    spacing=(hi-lo)/(shape-1)
    return lo,spacing,np.full(shape,20.,np.float32)

def smooth_min(a,b,k):
    h=np.maximum(k-np.abs(a-b),0.)/k
    return np.minimum(a,b)-h*h*k*.25

def grown_segment(field,lo,step,a,b,r0,r1,blend=.02):
    a=np.asarray(a);b=np.asarray(b);pad=max(r0,r1)+blend*2+.025
    start=np.maximum(0,np.floor((np.minimum(a,b)-pad-lo)/step).astype(int))
    end=np.minimum(field.shape,np.ceil((np.maximum(a,b)+pad-lo)/step).astype(int)+1)
    if np.any(end<=start): return
    sub=tuple(slice(int(i),int(j)) for i,j in zip(start,end))
    coords=np.stack(np.meshgrid(*[lo[k]+np.arange(start[k],end[k])*step[k] for k in range(3)],indexing='ij'),-1).astype('f4')
    pa=coords-a;ba=b-a;t=np.clip((pa*ba).sum(-1)/max(np.dot(ba,ba),1e-9),0,1)
    d=np.linalg.norm(pa-t[...,None]*ba,axis=-1)-(r0+(r1-r0)*t)
    field[sub]=smooth_min(field[sub],d,blend)

def field_mesh(field,lo,spacing,material,uv_function=None):
    p,f,n,_=marching_cubes(field,0,spacing=spacing,gradient_direction='ascent',allow_degenerate=False)
    p=p+lo
    # Field gradient yields the exterior normal independently of MC convention.
    grad=np.gradient(field,*spacing)
    idx=((p-lo)/spacing).T
    n=unit(np.stack([map_coordinates(g,idx,order=1,mode='nearest') for g in grad],-1))
    uv=uv_function(p,n) if uv_function else None
    B.add(p,n,f,material,uv=uv)

def specimen_stone(c,scale,seed,resolution=85):
    """Oblique cleavage planes, fault offsets, chipped seams, and scaled erosion.
    No ellipsoid base: broad fracture planes determine the silhouette first.
    """
    gen=np.random.default_rng(seed)
    lo,step,d=grid_volume([-1.30,-1.25,-1.25],[1.30,1.30,1.25],2.60/resolution)
    p=np.stack(np.meshgrid(*[lo[k]+np.arange(d.shape[k])*step[k] for k in range(3)],indexing='ij'),-1).astype('f4')
    lattice=gen.uniform(-1,1,(37,37,37)).astype('f4')
    def vn(f,offset=0):
        return map_coordinates(lattice,((p*f+15+offset)%35).reshape(-1,3).T,order=1,mode='wrap').reshape(d.shape)
    # Geological foliation determines both shape and later shader coloration.
    bedding=p[...,1]+p[...,0]*.37-p[...,2]*.19
    shift=np.clip(np.sin(bedding*8.7+.3),-.72,.72)*.045
    q=p.copy();q[...,0]+=shift;q[...,2]-=shift*.28
    planes=[([1,.13,.12],.86),([-1,-.11,.24],.82),
            ([.15,.08,1],.76),([-.19,-.03,-1],.72),
            ([.13,1,.12],.91),([-.08,-1,.16],.91),
            ([.82,.62,.35],1.00),([-.55,.83,-.25],.95),
            ([.70,-.43,-.64],1.08),([-.68,.15,.78],.95)]
    d=np.full(p.shape[:-1],-20.,np.float32)
    for normal,offset in planes:
        d=np.maximum(d,np.einsum('...i,i->...',q,unit(normal))-offset)
    # Broad flake losses cut half-spaces into individual strata; no round craters.
    cuts=[(.36,[.76,.08,.65],.51),(-.33,[-.50,.06,.86],.57),(.74,[.22,.12,-.97],.43)]
    for level,normal,depth in cuts:
        wedge=np.maximum(np.abs(bedding-level)-.060,depth-np.einsum('...i,i->...',p,unit(normal)))
        d=np.maximum(d,-wedge)
    # Connected tilted cleavage, locally dislocated rather than evenly spaced rings.
    warp=vn(2.1)*.085
    for level,width,depth in [(-.58,.010,.035),(-.12,.006,.028),(.41,.012,.048),(.70,.008,.032)]:
        seam=np.exp(-((bedding-level+warp)/width)**2)
        d+=seam*depth
    # Fine erosion is subordinate to fracture planes, never the primary form.
    d+=vn(3.7)*.012+vn(11.3,3)*.007+vn(28.9,8)*.003
    pp,ff,_,_=marching_cubes(d,0,spacing=step,allow_degenerate=False)
    raw=pp+lo
    grad=np.gradient(d,*step);sample=(pp/step).T
    nn=unit(np.stack([map_coordinates(g,sample,order=1,mode='nearest') for g in grad],-1)/np.asarray(scale))
    pp=raw*np.asarray(scale)+np.asarray(c)
    B.add(pp,nn,ff,11,ao=1.)

def new_geology():
    B.begin('geological-specimen-eroded-fractures',3);plinth()
    ring(.851,.802,.066,2,(0,.655,0),b=.005,segments=96)
    disk(.803,.025,10,(0,.676,0),b=.002,segments=128)
    specimen_stone([.03,1.22,-.075],[.43,.59,.37],8374,116)
    specimen_stone([-.37,.91,.18],[.23,.27,.22],3412,54)
    specimen_stone([.37,.83,.23],[.21,.16,.20],998,45)
    gen=np.random.default_rng(339)
    for i in range(39):
        a=gen.uniform(0,TAU);rr=gen.uniform(.42,.76);s=gen.uniform(.014,.042)
        mesh=trimesh.creation.icosphere(subdivisions=1)
        pp=mesh.vertices*gen.uniform(.7,1.3,(len(mesh.vertices),1))*[s,s*.67,s*.87]+[rr*np.cos(a),.70,rr*np.sin(a)]
        m=trimesh.Trimesh(pp,mesh.faces,process=False)
        B.add(pp,m.vertex_normals,m.faces,11 if i%9 else 29)
    rod([-.64,.63,-.40],[-.64,1.77,-.40],.009,4,16)
    rod([-.64,1.77,-.40],[-.22,1.77,-.40],.008,4,16)
    screw_thread([-.64,.73,-.40],.018,.13)

def new_forest():
    gen=np.random.default_rng(10493)
    B.begin('grown-bonsai-root-collar-and-branches',6);plinth()
    ring(.833,.713,.10,7,(0,.672,0),b=.006,segments=96)
    ring(.838,.822,.009,4,(0,.723,0),b=.001,segments=96)
    # Soil bed: volumetric humus relief, irregular rooting zone and no lawn-green disk.
    rr,aa=np.meshgrid(np.linspace(0,.719,35),np.linspace(0,TAU,97))
    xx,zz=rr*np.cos(aa),rr*np.sin(aa)
    yy=.721+.037*np.exp(-(rr/.39)**2)+.004*np.sin(xx*49+np.sin(zz*19))*np.sin(zz*40)
    pp=np.stack([xx,yy,zz],-1);da,dr=np.gradient(pp,axis=(0,1));nn=unit(np.cross(da,dr));nn[...,1]=abs(nn[...,1])
    B.add(pp,nn,grid_faces(*rr.shape),30)
    # Old trunk: asymmetrical taper and compound bends, not stacked straight cylinders.
    pts=np.array([[.12,.74,.01],[.065,.91,.035],[-.05,1.08,.07],[-.15,1.29,.025],[-.14,1.48,-.015],[-.055,1.67,.035],[.07,1.88,.025],[.15,2.06,-.045],[.105,2.25,-.07],[.06,2.43,-.005]])
    t=np.linspace(0,1,len(pts));ts=np.linspace(0,1,55)
    trunk=CubicSpline(t,pts,bc_type='natural')(ts)
    radii=np.interp(ts,t,[.162,.136,.113,.091,.077,.062,.047,.034,.019,.003])
    lo,step,field=grid_volume([-.95,.675,-.90],[1.03,2.62,.93],.0125)
    for a,b,r0,r1 in zip(trunk[:-1],trunk[1:],radii[:-1],radii[1:]):grown_segment(field,lo,step,a,b,r0,r1,.04)
    # Root flare with real blended crotches; roots disappear into the substrate.
    for j in range(9):
        a=j*TAU/9+gen.uniform(-.18,.18);length=gen.uniform(.29,.56)
        end=np.array([length*np.cos(a),.713,length*np.sin(a)])
        root=np.array([pts[0]+[0,.10,0],pts[0]*.6+end*.4+[0,.024,0],end])
        tt=np.linspace(0,1,14);curve=CubicSpline([0,.48,1],root)(tt);r=np.linspace(.056,.002,len(curve))
        for p,q,r0,r1 in zip(curve[:-1],curve[1:],r[:-1],r[1:]):grown_segment(field,lo,step,p,q,r0,r1,.026)
    tips=[];small=[]
    # Broadleaf branch hierarchy. Smaller branches alternate along their parent,
    # not repeated radial fans centred on a foliage ball.
    specs=[(.25,2.82,.62),(.38,-.58,.69),(.46,.95,.59),(.54,-2.10,.68),(.64,2.18,.53),(.70,-.28,.50),(.80,1.15,.43),(.85,-2.36,.46),(.93,2.4,.31),(.97,-.25,.25)]
    for idx,(t0,az,length) in enumerate(specs):
        start=CubicSpline(t,pts)(t0);direction=np.array([np.cos(az),.13,np.sin(az)])
        middle=start+direction*length*.47+[0,-.048,0]
        end=start+direction*length+[0,.12+gen.uniform(0,.08),0]
        tt=np.linspace(0,1,14);curve=CubicSpline([0,.48,1],[start,middle,end])(tt)
        rad=np.linspace(.046*(1-t0*.48),.0045,len(curve))
        for p,q,r0,r1 in zip(curve[:-1],curve[1:],rad[:-1],rad[1:]):grown_segment(field,lo,step,p,q,r0,r1,.020)
        for j,t1 in enumerate(np.linspace(.31,.99,6)):
            root=CubicSpline([0,.48,1],[start,middle,end])(t1)
            side=(-1)**j;angle=az+side*gen.uniform(.45,1.15)
            extent=length*(1-t1*.58)*gen.uniform(.32,.68)
            stop=root+np.array([np.cos(angle)*extent,gen.uniform(.03,.16),np.sin(angle)*extent])
            bend=root*.45+stop*.55+[0,-.025,0]
            small.append((np.array([root,bend,stop]),np.array([.008,.004,.001])))
            for k,t2 in enumerate(np.linspace(.25,1.,6)):
                stem=bend*(1-t2)+stop*t2
                an=angle+(-1)**k*gen.uniform(.6,1.3);ext=gen.uniform(.07,.16)
                finish=stem+[np.cos(an)*ext,gen.uniform(.015,.09),np.sin(an)*ext]
                small.append((np.array([stem,(stem+finish)/2,finish]),[.0022,.0014,.0003]))
                for l in range(5):
                    site=stem*(1-(.25+l*.18))+finish*(.25+l*.18)
                    yaw=an+(-1)**l*gen.uniform(.65,1.2)
                    ll=gen.uniform(.040,.065)*(1-.13*t0)
                    tip=site+np.array([np.cos(yaw),gen.uniform(-.05,.45),np.sin(yaw)])*ll*.66
                    tips.append((tip,yaw,gen.uniform(-.50,.68),ll,int(gen.integers(0,9))))
    # Shallow grooves/knots are baked into the trunk silhouette, not random glitter.
    x,y,z=np.meshgrid(*[lo[k]+np.arange(field.shape[k])*step[k] for k in range(3)],indexing='ij')
    ridge=.0018*np.sin(np.arctan2(z+.02,x+.04)*19.+y*2.3)+.0011*np.sin(y*65+x*34+z*17)
    near=abs(field)<.03;field[near]+=ridge[near]
    field_mesh(field,lo,step,12,lambda p,n:np.stack([(np.arctan2(p[:,2],p[:,0])+np.pi)/TAU,(p[:,1]-.69)/2.],1))
    for curve,r in small:tube(curve,r,12,segments=5)
    B.begin('procedural-cupped-leaves-asymmetric-crown',6)
    for site,yaw,pitch,ll,variant in tips:
        u,v=np.meshgrid(np.linspace(0,1,9),[-1.,0.,1.])
        width=np.sin(np.pi*u)**.72*ll*.55*(1+.055*np.sin(u*47+variant))
        width*=1+v*.06*np.sin(u*8+variant)
        pp=np.stack([(u-.35)*ll*2,.0045*(1-v*v)*np.sin(np.pi*u)-.013*u*u+v*.004*np.sin(u*7+variant),v*width*(1+.08*v*np.sin(u*5+variant))],-1)
        dv,du=np.gradient(pp,axis=(0,1));nn=unit(np.cross(dv,du));M=ry(-yaw)@rz(pitch)
        uv=np.stack([(u+variant%3)/3,((v+1)*.5+variant//3)/3],-1)
        ff=grid_faces(*u.shape)
        # Separate front/back normals, no transparent foliage overdraw.
        for side in [1,-1]:B.add(pp,nn*side,ff,13,ao=1.,M=M,C=site,uv=uv)
    B.begin('forest-mineral-substrate-and-litter',6)
    for i in range(180):
        a=gen.uniform(0,TAU);rr=np.sqrt(gen.uniform(.005,.48));size=gen.uniform(.006,.022)
        m=trimesh.creation.icosphere(subdivisions=0)
        pp=m.vertices*[size,size*.55,size*.8]+[rr*np.cos(a),.734,rr*np.sin(a)]
        B.add(pp,m.vertex_normals,m.faces,30 if i%12 else 11)
    # Small moss islands rather than a uniform green lawn.
    for i in range(80):
        a=gen.uniform(0,TAU);rr=gen.uniform(.35,.66);p=np.array([rr*np.cos(a),.738,rr*np.sin(a)])
        for j in range(3):tube([p,p+gen.normal(0,.004,3)+[0,.008,0]],[.0015,.0004],14,segments=3)
