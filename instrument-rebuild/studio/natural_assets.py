"""Seeded geological cleavage and a grown pine specimen, authored from equations.
The trunk/rock implicit fields are meshed once offline. All foliage is geometry.
No photograph, scanner, imported model or image-generation service is involved.
"""

def _grid(lo,hi,step):
    lo=np.asarray(lo,float);hi=np.asarray(hi,float);sh=np.ceil((hi-lo)/step).astype(int)+1
    st=(hi-lo)/(sh-1);return lo,st,np.full(sh,10.,'f4')

def _smin(a,b,k):
    h=np.maximum(k-np.abs(a-b),0)/k;return np.minimum(a,b)-h*h*k*.25

def _branch(field,lo,st,a,b,r0,r1,k=.02):
    a=np.asarray(a);b=np.asarray(b);pad=max(r0,r1)+k*2+.02
    start=np.maximum(0,np.floor((np.minimum(a,b)-pad-lo)/st).astype(int));stop=np.minimum(field.shape,np.ceil((np.maximum(a,b)+pad-lo)/st).astype(int)+1)
    if np.any(stop<=start):return
    ix=tuple(slice(int(a),int(b)) for a,b in zip(start,stop))
    q=np.stack(np.meshgrid(*[lo[j]+np.arange(start[j],stop[j])*st[j] for j in range(3)],indexing='ij'),-1).astype('f4')
    ba=b-a;pa=q-a;t=np.clip((pa*ba).sum(-1)/max(np.dot(ba,ba),1e-12),0,1)
    d=np.linalg.norm(pa-t[...,None]*ba,axis=-1)-(r0+(r1-r0)*t)
    field[ix]=_smin(field[ix],d,k)

def _field_mesh(field,lo,step,mat,uvfn=None):
    p,f,_,_=marching_cubes(field,0,spacing=step,allow_degenerate=False)
    p+=lo;g=np.gradient(field,*step);ix=((p-lo)/step).T
    n=unit(np.stack([map_coordinates(a,ix,order=1,mode='nearest') for a in g],-1))
    B.add(p,n,f,mat,uv=None if uvfn is None else uvfn(p))

def _fractured_specimen(center,scale,seed,res=82):
    gen=np.random.default_rng(seed);lo,st,d=_grid([-1.18,-1.18,-1.18],[1.18,1.18,1.18],2.36/res)
    p=np.stack(np.meshgrid(*[lo[j]+np.arange(d.shape[j])*st[j] for j in range(3)],indexing='ij'),-1).astype('f4')
    # Intersect tectonic planes. Broad faces are preserved; microrelief never
    # determines the large silhouette. Unequal offsets break perfect prisms.
    planes=[([1,.09,.12],.79),([-1,-.19,-.06],.84),([.15,1,.12],.96),([-.14,-1,.2],.96),([.14,.12,1],.69),([-.18,-.15,-1],.69),([.78,.50,.18],.84),([-.78,.42,-.52],.91),([.36,.73,-.69],.87),([-.50,-.72,.53],1.00),([.71,-.37,-.68],.92)]
    d=np.full(p.shape[:-1],-100,'f4')
    for normal,offset in planes:
        n=unit(normal);pl=(p*n).sum(-1)-offset*gen.uniform(.96,1.04)
        d=-_smin(-d,-pl,.014)
    lattice=gen.normal(size=(40,40,40)).astype('f4')
    def ns(f,shift=0):return map_coordinates(lattice,((p*f+18+shift)%38).reshape(-1,3).T,order=1,mode='wrap').reshape(d.shape)
    # Consistent folded bedding; sparse cleavage seams, not periodic rings.
    bedding=p[...,1]*.78+p[...,0]*.43+p[...,2]*.21+.055*ns(1.3)
    for offset,width,depth in [(-.63,.024,.028),(-.34,.012,.019),(-.03,.018,.024),(.26,.013,.015),(.57,.024,.026),(.82,.015,.017)]:
        seam=np.exp(-((bedding-offset)/width)**2);d+=depth*seam*(.7+.3*np.clip(ns(3)+.5,0,1))
    # A torn flake exposes an angular concavity along one side.
    corner=(p[...,0]-.48)*.70+(p[...,2]-.38)*.63+(p[...,1]-.22)*.32
    flake=np.minimum(corner,np.minimum(p[...,1]+.38,.79-p[...,1]));d=np.maximum(d,flake*.34)
    d+=.017*ns(3.1)+.008*ns(10.7,3)+.0026*ns(27.3,7)
    pp,ff,_,_=marching_cubes(d,0,spacing=st,allow_degenerate=False)
    pp=(pp+lo)*np.array(scale)+center
    mesh=trimesh.Trimesh(pp,ff,process=False)
    B.add(pp,mesh.vertex_normals,ff,11)

def make_geology():
    gen=np.random.default_rng(8721);B.begin('scenes-folded-slate-and-kinematic-fixture',3);plinth()
    disk(.82,.042,2,(0,.644,0),b=.006,segments=128)
    ring(.825,.808,.014,33,(0,.671,0),b=.002,segments=128)
    _fractured_specimen([.03,1.265,-.06],[.49,.61,.34],5739,92)
    _fractured_specimen([-.40,.83,.20],[.20,.18,.16],9821,38)
    _fractured_specimen([.39,.79,.25],[.17,.14,.19],1929,34)
    # Connected three-point clamp with polymer contact tips.
    for a in [0,2.13,4.36]:
        x,z=.66*np.cos(a),.66*np.sin(a)
        box([.22,.05,.105],28,(x,.700,z),b=.004,M=ry(-a))
        fastener([x,.735,z],.018,.010)
        rod([x,.716,z],[x*.74,.80,z*.74],.013,28,24)
        disk(.029,.034,16,[x*.74,.80,z*.74],b=.003,segments=24)
    for i in range(22):
        a=gen.uniform(0,TAU);r=gen.uniform(.52,.76);s=gen.uniform(.006,.026)
        m=trimesh.creation.icosphere(subdivisions=0);p=m.vertices*gen.uniform(.8,1.2,(len(m.vertices),1))*[s,s*.44,s*.83]+[r*np.cos(a),.677+s*.22,r*np.sin(a)]
        B.add(p,m.vertex_normals,m.faces,11)
    # Measuring post, clamp and a fine stylus; distinct parts and metal thickness.
    rod([-.65,.635,-.42],[-.65,1.68,-.42],.012,28,32)
    box([.071,.074,.09],2,(-.65,1.60,-.42),b=.004)
    rod([-.65,1.60,-.42],[-.25,1.60,-.42],.008,4,24)
    micrometer([-.65,.76,-.42],np.eye(3))

def make_forest():
    gen=np.random.default_rng(663277);B.begin('forest-grown-pine-roots-and-branches',6);plinth()
    # A restrained bonsai container: unglazed ceramic inside an enamel stand.
    lathe([[0,.625],[.74,.625],[.78,.65],[.80,.71],[.79,.75],[.736,.75],[.72,.69],[0,.69]],26,144)
    ring(.801,.773,.017,26,(0,.735,0),b=.002,segments=144)
    r,a=np.meshgrid(np.linspace(0,.739,29),np.linspace(0,TAU,81))
    x,z=r*np.cos(a),r*np.sin(a);y=.719+.033*np.exp(-(r/.36)**2)+.003*np.sin(x*39)*np.sin(z*43)
    p=np.stack([x,y,z],-1);da,dr=np.gradient(p,axis=(0,1));n=unit(np.cross(da,dr));n[...,1]=abs(n[...,1]);n[:,0]=[0,1,0];B.add(p,n,grid_faces(*r.shape),30)
    # Root-supported tapered old pine; compounded leaning curves imply growth.
    trunk_pts=np.array([[.10,.73,.015],[.035,.91,.026],[-.09,1.10,.035],[-.17,1.30,-.005],[-.15,1.49,-.037],[-.06,1.68,.005],[.05,1.88,-.03],[.10,2.08,-.055],[.055,2.27,-.01]])
    t=np.linspace(0,1,len(trunk_pts));curve=CubicSpline(t,trunk_pts,bc_type='natural');tt=np.linspace(0,1,47);points=curve(tt)
    radii=np.interp(tt,t,[.153,.13,.109,.088,.073,.059,.042,.026,.004])
    lo,st,fld=_grid([-.90,.68,-.87],[.92,2.45,.90],.013)
    for aa,bb,r0,r1 in zip(points[:-1],points[1:],radii[:-1],radii[1:]):_branch(fld,lo,st,aa,bb,r0,r1,.036)
    for i in range(7):
        a=i*TAU/7+gen.uniform(-.2,.2);ext=gen.uniform(.28,.51);end=np.array([ext*np.cos(a),.721,ext*np.sin(a)])
        cs=CubicSpline([0,.45,1],[trunk_pts[0]+[0,.10,0],trunk_pts[0]*.45+end*.55+[0,.023,0],end]);ts=np.linspace(0,1,12);pp=cs(ts);rs=np.linspace(.055,.002,len(pp))
        for aa,bb,r0,r1 in zip(pp[:-1],pp[1:],rs[:-1],rs[1:]):_branch(fld,lo,st,aa,bb,r0,r1,.024)
    # Alternating, unequal branch tiers. There are gaps between the foliage pads
    # and longer low branches; no radial spheres pasted on a central pole.
    specs=[(.23,2.82,.66),(.30,-.35,.61),(.40,-1.55,.53),(.48,1.38,.60),(.57,2.85,.53),(.66,-.10,.49),(.76,-1.46,.45),(.83,1.40,.43),(.92,2.75,.31),(.98,-.20,.27)]
    twigs=[];shoots=[]
    for tier,(t0,az,length) in enumerate(specs):
        start=curve(t0);direction=np.array([np.cos(az),-.07,np.sin(az)])
        middle=start+direction*length*.51+[0,-.048,0];end=start+direction*length+[0,.096,0]
        bc=CubicSpline([0,.5,1],[start,middle,end]);ts=np.linspace(0,1,16);pp=bc(ts);rs=np.linspace(.044*(1-.5*t0),.004,len(pp))
        for aa,bb,r0,r1 in zip(pp[:-1],pp[1:],rs[:-1],rs[1:]):_branch(fld,lo,st,aa,bb,r0,r1,.018)
        for j,t1 in enumerate(np.linspace(.28,.99,8)):
            root=bc(t1);angle=az+(-1)**j*gen.uniform(.48,1.10)
            extent=length*(1-.6*t1)*gen.uniform(.40,.72);stop=root+[np.cos(angle)*extent,gen.uniform(.025,.10),np.sin(angle)*extent]
            mid=root*.45+stop*.55+[0,-.017,0];twigs.append((np.array([root,mid,stop]),[.009,.004,.0011]))
            for k in range(4):
                t2=.35+k*.20;site=mid*(1-t2)+stop*t2
                an=angle+(-1)**k*gen.uniform(.4,1.05);ext=gen.uniform(.065,.12)
                tip=site+[np.cos(an)*ext,gen.uniform(.035,.085),np.sin(an)*ext]
                twigs.append((np.array([site,(site+tip)/2,tip]),[.0024,.0017,.0005]))
                shoots.append((site,tip,an,tier))
    # Bark relief follows the trunk, with restrained broken vertical ridges.
    x,y,z=np.meshgrid(*[lo[j]+np.arange(fld.shape[j])*st[j] for j in range(3)],indexing='ij')
    centers=curve(np.clip((y-.73)/(2.27-.73),0,1));theta=np.arctan2(z-centers[...,2],x-centers[...,0])
    groove=.0016*np.sin(theta*23+y*2)+.0011*np.sin(y*61+x*23)*np.sin(theta*11-y*5)
    near=abs(fld)<.025;fld[near]+=groove[near]
    def trunkuv(p):
        c=curve(np.clip((p[:,1]-.73)/1.54,0,1));theta=(np.arctan2(p[:,2]-c[:,2],p[:,0]-c[:,0])+math.pi)/TAU
        return np.stack([theta,(p[:,1]-.70)/1.9],1)
    _field_mesh(fld,lo,st,12,trunkuv)
    for pp,rr in twigs:tube(pp,rr,12,segments=5)
    B.begin('forest-needle-fascicles-and-terminal-buds',6)
    # Needles grow in fascicles along living terminal shoots, with tapered
    # diamond cross-sections and individual bend/twist. No alpha-card overdraw.
    for start,tip,az,tier in shoots:
        tangent=unit(tip-start);basis=between(tangent)
        for j in range(17):
            f=.16+j*.049;anchor=start*(1-f)+tip*f;phi=j*2.3999632297+gen.uniform(-.3,.3)
            outward=basis[:,0]*np.cos(phi)+basis[:,2]*np.sin(phi)
            direction=unit(tangent*.42+outward*.86+np.array([0,.15,0]));length=gen.uniform(.092,.166)*(1-.025*tier)
            for pair in [-1,1]:
                d=unit(direction+pair*basis[:,0]*.07);perp=unit(np.cross(d,tangent));normal=unit(np.cross(perp,d))
                u=np.linspace(0,1,3);cent=anchor+u[:,None]*d*length+(u*u)[:,None]*np.array([0,-.015,0])
                w=.0034*(1-u)**.65+.00005
                verts=[];norms=[]
                for ii in range(3):
                    for dx,dy in [(1,0),(0,.45),(-1,0),(0,-.45),(1,0)]:
                        verts.append(cent[ii]+(perp*dx+normal*dy)*w[ii]);norms.append(unit(perp*dx+normal*dy))
                uv=np.array([[j/17,ii/2] for ii in range(3) for jj in range(5)])
                B.add(verts,norms,grid_faces(3,5),32,uv=uv)
        # A restrained ochre shoot bud at each terminal.
        rod(tip-tangent*.008,tip+tangent*.019,.0025,12,8)
    B.begin('forest-granular-soil-and-lichen',6)
    for i in range(240):
        a=gen.uniform(0,TAU);rr=np.sqrt(gen.uniform(.014,.53));s=gen.uniform(.006,.019)
        mesh=trimesh.creation.icosphere(subdivisions=0);p=mesh.vertices*[s,s*.55,s*.8]+[rr*np.cos(a),.731,rr*np.sin(a)]
        B.add(p,mesh.vertex_normals,mesh.faces,30 if i%8 else 11)
    for i in range(120):
        a=gen.uniform(0,TAU);rr=gen.uniform(.26,.65);site=np.array([rr*np.cos(a),.735,rr*np.sin(a)]);s=gen.uniform(.01,.026)
        if np.sin(a*3+rr*12)<.12:continue
        mesh=trimesh.creation.icosphere(subdivisions=1);p=mesh.vertices*[s,s*.25,s*.8]+site
        B.add(p,mesh.vertex_normals,mesh.faces,14)
