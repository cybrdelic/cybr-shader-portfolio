"""Procedural instrument redesign. No imported mesh, photo, scan or generated image.
Executed in geometry.py's shared mesh-builder namespace. Dimensions in scene units.
The assembly is a designed visual exhibit; it is not a manufacturing certification.
"""
import trimesh
from scipy.spatial import ConvexHull, Voronoi
from scipy.interpolate import CubicSpline
from skimage.measure import marching_cubes

def fastener(c,r=.018,h=.010,M=None):
    # A turned head, recessed hex and a bearing washer, not a raised silver dot.
    ring(r*1.22,r*.88,h*.30,28,np.asarray(c)-((M@np.array([0,h*.4,0])) if M is not None else [0,h*.4,0]),b=.001,segments=28,M=M)
    bolt(c,r,h,M)

def plinth():
    disk(1.025,.110,2,(0,.35,0),b=.010,segments=144)
    disk(.997,.165,7,(0,.480,0),b=.012,segments=144)
    ring(.999,.982,.015,2,(0,.568,0),b=.002,segments=144)
    disk(.945,.026,2,(0,.588,0),b=.004,segments=144)
    for a in np.linspace(0,TAU,8,endpoint=False):fastener([.975*np.cos(a),.579,.975*np.sin(a)],.016,.008)
    for a in [0,TAU/3,2*TAU/3]:disk(.085,.045,16,(.72*np.cos(a),.276,.72*np.sin(a)),b=.005,segments=24)
    box([.40,.011,.14],24,(.80,.615,0),b=.002,M=ry(math.pi/2))
    for z in [-.176,.176]:fastener([.8,.624,z],.009,.005)
    # Rear circular connector and strain-relieved lead.
    for zz in [-.18,.18]:
        M=rz(math.pi/2);c=np.array([-.992,.47,zz]);disk(.043,.052,28,c,b=.002,segments=6,M=M)
        ring(.035,.020,.065,2,c+[-.03,0,0],b=.002,segments=24,M=M)
        t=np.linspace(0,1,15);p=np.stack([-1.02-.14*np.sin(t*math.pi*.5),.47-.17*t,np.full_like(t,zz)],1)
        tube(p,.014,16,segments=6)

def knurled_knob(c,r=.06,h=.08,M=None):
    c=np.asarray(c);disk(r,h,2,c,b=.005,segments=64,M=M)
    # Broad recessed knurl rhythm; tips remain dielectric black, not chrome.
    for a in np.linspace(0,TAU,24,endpoint=False):
        p=np.array([r*.985*np.cos(a),0,r*.985*np.sin(a)])
        disk(.0025,h*.68,2,c+(M@p if M is not None else p),b=.0006,segments=6,M=M)
    ring(r*.89,r*.83,.006,28,c+(M@[0,h*.49,0] if M is not None else [0,h*.49,0]),b=.001,segments=48,M=M)

def micrometer(c,M=None):
    c=np.asarray(c);M=np.eye(3) if M is None else M
    disk(.032,.21,4,c,b=.002,M=M,segments=48)
    disk(.052,.085,28,c+M@[0,.055,0],b=.002,M=M,segments=64)
    knurled_knob(c+M@[0,.139,0],.064,.08,M)
    for j in range(8):ring(.053,.051,.002,2,c+M@[0,.018+j*.009,0],b=.0002,M=M,segments=40)

def hoop_tube(radius,height,r,mat,M=None,C=(0,0,0),start=0,end=TAU):
    t=np.linspace(start,end,max(16,int(abs(end-start)*24)))
    p=np.stack([radius*np.cos(t),np.full_like(t,height),radius*np.sin(t)],1)
    if M is not None:p=p@M.T
    tube(p+np.asarray(C),r,mat,segments=8)

# ---------- shared chassis: broad readable forms, restrained metal accents ----------
B.begin('chassis-cast-enamel-and-machined-rim',0)
disk(4.45,.14,2,(0,.01,0),b=.022,segments=256)
disk(4.41,.154,7,(0,.158,0),b=.010,segments=256)
ring(4.418,4.369,.022,33,(0,.222,0),b=.003,segments=256)
disk(4.367,.016,7,(0,.239,0),b=.003,segments=256)
# Recessed perimeter fasteners are sized like hardware, not scenery.
for a in np.linspace(0,TAU,24,endpoint=False):fastener([4.24*np.cos(a),.254,4.24*np.sin(a)],.019,.010)
for a in np.linspace(0,TAU,6,endpoint=False):
    c=np.array([np.cos(a),0,np.sin(a)]);side=np.array([-np.sin(a),0,np.cos(a)])
    disk(.18,.12,16,c*3.60+[0,-.11,0],b=.013,segments=32)
    # Connected loom routed under the exhibits; no intersecting ornamental beams.
    for sg in [-1,1]:
        t=np.linspace(0,1,18);p=np.stack([t,t,t],1)*0
        for j,u in enumerate(t):p[j]=c*(.92+1.36*u)+side*(.11*sg+.04*np.sin(u*math.pi))+[0,.268+.045*np.sin(u*math.pi),0]
        tube(p,.012,16,segments=8)
    for rr in [1.2,1.82]:
        box([.08,.027,.28],2,c*rr+[0,.289,0],b=.004,M=ry(-a));fastener(c*rr+side*.105+[0,.308,0],.012,.006)
    # Joined mounting brackets, not floating ears.
    box([.20,.055,.22],2,c*4.04+[0,.252,0],b=.008,M=ry(-a));fastener(c*4.04+[0,.285,0],.021,.01)
# Original foreground identity plate retained, but thinner and less glossy.
plateC=np.array([-1.05,.30,4.46]);plateM=rx(.28)
box([2.68,.050,1.34],2,plateC-plateM@[0,.025,0],b=.008,M=plateM)
box([2.60,.021,1.27],25,plateC,b=.003,M=plateM)
for xx in [-1.18,1.18]:
    for zz in [-.54,.54]:fastener(plateC+plateM@[xx,.015,zz],.013,.007,plateM)
    support=plateC+plateM@[xx,-.08,-.50];box([.08,.21,.17],2,support,b=.004)

# ---------- LIGHT: a kinematic optical mount, lenses and micrometers ----------
B.begin('light-kinematic-lens-mount',1);plinth()
C=np.array([0,1.59,0]);M=rz(-1.23)@rx(.06)
# Three broad feet ground the mount on the optical bench.
box([.55,.075,.63],28,(-.06,.66,0),b=.007)
for x,z in [(-.23,-.24),(-.23,.24),(.15,0)]:fastener([x,.707,z],.024,.014)
for z in [-.235,.235]:
    box([.15,.33,.13],2,(-.06,.84,z),b=.012)
    rod([-.06,.85,z],[-.06,1.09,z],.034,4,40)
box([.25,.08,.65],28,(-.06,1.04,0),b=.007)
ring(.860,.741,.132,2,C,b=.008,M=M,segments=192)
ring(.861,.841,.011,28,C+M@[0,.073,0],b=.0015,M=M,segments=192)
ring(.751,.663,.058,2,C+M@[0,.005,0],b=.004,M=M,segments=192)
# A single polished retaining shoulder and black light baffle.
ring(.683,.657,.012,28,C+M@[0,.040,0],b=.0015,M=M,segments=192)
ring(.667,.650,.008,2,C+M@[0,.049,0],b=.001,M=M,segments=192)
for a in np.linspace(0,TAU,8,endpoint=False):fastener(C+M@[.802*np.cos(a),.076,.802*np.sin(a)],.017,.010,M)
for side in [-1,1]:
    p=C+M@[side*.871,0,0];disk(.073,.094,28,p,b=.004,M=M@rz(math.pi/2),segments=64)
    micrometer(p+M@[side*.12,0,0],M@rz(-side*math.pi/2))
# Laser-engraved fine angle marks on the front black rim, not bright mesh rings.
for i,a in enumerate(np.linspace(0,TAU,72,endpoint=False)):
    p=C+M@[.820*np.cos(a),.080,.820*np.sin(a)]
    box([.015 if i%6==0 else .006,.0008,.0018],18,p,b=.0001,M=M@ry(-a))
# Compact collimator on telescoping post, with a thick matte lens tube.
for c,angle in [([.48,.82,-.42],-.47),([-.47,.79,.37],.5)]:
    disk(.095,.035,2,[c[0],.637,c[2]],b=.004,segments=48)
    rod([c[0],.64,c[2]],c,.023,28,40)
    m=rz(angle);ring(.117,.078,.19,2,c,b=.004,M=m,segments=72)
    ring(.119,.106,.010,28,np.asarray(c)+m@[0,.10,0],b=.001,M=m,segments=72)
    disk(.077,.006,21,np.asarray(c)+m@[0,.097,0],b=.001,M=m,segments=72)

# ---------- GEOMETRY: motor/compressor cutaway with continuous blade airfoils ----------
B.begin('geometry-compressor-stator-housing',2);plinth()
disk(.80,.113,2,(0,.688,0),b=.009,segments=160)
ring(.808,.735,.022,28,(0,.752,0),b=.003,segments=160)
# Open casing sections reveal windings while retaining a continuous end bell.
ring(.799,.711,.068,7,(0,.805,0),b=.007,segments=160)
ring(.799,.713,.065,7,(0,1.101,0),b=.007,segments=160)
for a in np.linspace(0,TAU,9,endpoint=False):
    x,z=.749*np.cos(a),.749*np.sin(a)
    box([.11,.245,.09],2,(x,.946,z),b=.006,M=ry(-a))
    # Separate copper turns around a rectangular stator tooth.
    path=np.array([[-.058,-.036],[-.047,-.048],[.047,-.048],[.058,-.036],[.058,.036],[.047,.048],[-.047,.048],[-.058,.036],[-.058,-.036]])
    for j in range(9):
        pp=np.stack([path[:,0],np.full(len(path),.854+j*.022),path[:,1]],1)@ry(-a).T+[x,0,z]
        tube(pp,.0055,17,segments=6)
# Four substantial casing ribs, smoothly beveled and enamelled like ARX joints.
for a in np.linspace(.15,TAU+.15,4,endpoint=False):
    x,z=.785*np.cos(a),.785*np.sin(a)
    box([.15,.43,.105],7,(x,.966,z),b=.016,M=ry(-a))
    fastener([x,1.19,z],.027,.016)
# Real curved rotor blades with thickness, closed perimeter, and coherent normals.
B.begin('geometry-rotor-airfoils',2,2)
for idx in range(19):
    a=idx*TAU/19
    r,c=np.meshgrid(np.linspace(.23,.694,17),np.linspace(0,1,11))
    rr=(r-.23)/.464;chord=.125+.105*rr
    angle=a+.42*rr+(c-.5)*chord/r
    camber=.028*np.sin(c*math.pi)*(1-.4*rr)
    y=1.135+.16*rr+.13*(c-.5)*(1-.36*rr)+camber
    thickness=.024*(.2969*np.sqrt(c)-.126*c-.3516*c*c+.2843*c**3-.1015*c**4)*5*(.95-.35*rr)
    faces=grid_faces(*r.shape)
    for sg in [-1,1]:
        pp=np.stack([r*np.cos(angle),y+sg*thickness,r*np.sin(angle)],-1)
        dv,du=np.gradient(pp,axis=(0,1));nn=unit(np.cross(dv,du))*sg
        B.add(pp,nn,faces,4,part=2)
    # Thin tip seal closes the outer blade rather than exposing paper surfaces.
    outer=r.shape[1]-1
    for idx2 in [0,outer]:
        top=np.stack([r[:,idx2]*np.cos(angle[:,idx2]),y[:,idx2]+thickness[:,idx2],r[:,idx2]*np.sin(angle[:,idx2])],1)
        bot=top.copy();bot[:,1]-=2*thickness[:,idx2]
        p=np.stack([top,bot],0);n=unit(p-[0,1.2,0]);B.add(p,n,grid_faces(2,len(top)),4,part=2)
# Smooth revolved spinner instead of a stacked cone.
profile=[[0,1.02],[.223,1.02],[.223,1.135],[.212,1.205],[.184,1.269],[.139,1.326],[.082,1.364],[.04,1.377],[0,1.379]]
lathe(profile,28,144,part=2)
B.begin('geometry-bearing-frame-and-adjuster',2)
ring(.832,.750,.068,7,(0,1.283,0),b=.008,segments=192)
ring(.833,.818,.012,28,(0,1.324,0),b=.0015,segments=192)
# Three solid bridges with machined ends, forming a supported bearing seat.
for a in [.20,.20+TAU/3,.20+2*TAU/3]:
    box([.55,.052,.09],28,(.48*np.cos(a),1.47,.48*np.sin(a)),b=.009,M=ry(-a))
    box([.11,.17,.10],7,(.748*np.cos(a),1.40,.748*np.sin(a)),b=.008,M=ry(-a))
    fastener([.742*np.cos(a),1.51,.742*np.sin(a)],.020,.011)
ring(.214,.115,.091,2,(0,1.477,0),b=.005,segments=96)
ring(.183,.109,.028,4,(0,1.534,0),b=.004,segments=96)
disk(.104,.059,28,(0,1.55,0),b=.005,segments=96)
fastener([0,1.590,0],.034,.014)
for a in np.linspace(0,TAU,8,endpoint=False):fastener([.79*np.cos(a),1.333,.79*np.sin(a)],.018,.010)

# ---------- natural exhibits are authored with shared coherent fields ----------
exec((Path(__file__).parent/'natural_assets.py').read_text(),globals())
make_geology()

# ---------- ELEMENTS: heat-darkened refractory cup, fractured sintered crust ----------
B.begin('elements-refractory-crucible',4);plinth()
# Outer shell is a thermal housing with enamel supports and a refractory insert.
lathe([[.66,.65],[.79,.65],[.825,.70],[.825,.88],[.80,.96],[.755,.995],[.703,.995],[.68,.94],[.66,.78],[.66,.65]],26,160)
ring(.829,.808,.025,28,(0,.686,0),b=.003,segments=144)
ring(.835,.795,.032,2,(0,.923,0),b=.004,segments=144)
# Exposed pale refractory edge with heat discoloration handled by the surface shader.
ring(.780,.709,.043,31,(0,.980,0),b=.006,segments=160)
disk(.71,.025,9,(0,.921,0),b=.003,segments=144)
# Unequal cellular plates have displaced domed tops, thick fissure walls and holes.
gen=np.random.default_rng(314151)
sites=gen.uniform(-.9,.9,(95,2));sites=sites[np.linalg.norm(sites,axis=1)<.67]
bound=np.stack([np.cos(np.linspace(0,TAU,48,endpoint=False)),np.sin(np.linspace(0,TAU,48,endpoint=False))],1)*.95
vor=Voronoi(np.r_[sites,bound])
for i in range(len(sites)):
    ids=vor.regions[vor.point_region[i]]
    if -1 in ids or len(ids)<3:continue
    poly=vor.vertices[ids]
    # Clip boundary cells against the crucible instead of deleting them. This
    # gives a mostly solid sintered crust with narrow hot cracks, not orange liquid
    # surrounding disconnected black polygon tiles.
    for angle in np.linspace(0,TAU,64,endpoint=False):
        normal=np.array([np.cos(angle),np.sin(angle)]);clipped=[]
        for pa,pb in zip(poly,np.roll(poly,-1,axis=0)):
            da=np.dot(pa,normal)-.701;db=np.dot(pb,normal)-.701
            if da<=0:clipped.append(pa)
            if (da<=0)!=(db<=0):clipped.append(pa+(pb-pa)*da/(da-db))
        poly=np.asarray(clipped)
        if len(poly)<3:break
    if len(poly)<3:continue
    # In x/z, clockwise boundary order produces outward (+Y) top normals.
    # scipy Voronoi cell order is not guaranteed; never trust implicit winding.
    signed=np.sum(poly[:,0]*np.roll(poly[:,1],-1)-poly[:,1]*np.roll(poly[:,0],-1))
    if signed>0:poly=poly[::-1].copy()
    c=poly.mean(0);poly=c+(poly-c)*gen.uniform(.935,.975);n=len(poly)
    top=.949+gen.uniform(0,.040);rough=gen.uniform(-.012,.012,n)
    # Ring + inner ring + central apex, allowing warped plates rather than flat polygons.
    pp=np.r_[np.c_[poly[:,0],top+rough,poly[:,1]],np.c_[c[0]+(poly[:,0]-c[0])*.64,top+rough*.6+.010,c[1]+(poly[:,1]-c[1])*.64],[[c[0],top+.017,c[1]]],np.c_[poly[:,0]*.992,np.full(n,.923),poly[:,1]*.992]]
    ff=[]
    for k in range(n):
        j=(k+1)%n;ff += [[k,j,n+j],[k,n+j,n+k],[n+k,n+j,2*n],[k,2*n+1+k,2*n+1+j],[k,2*n+1+j,j]]
    mesh=trimesh.Trimesh(pp,ff,process=False);B.add(pp,mesh.vertex_normals,mesh.faces,22)
# Three retaining feet, thermocouple, and strain-relieved supply wires.
for a in [.25,2.34,4.43]:
    x,z=.837*np.cos(a),.837*np.sin(a)
    box([.105,.32,.075],28,(x,.78,z),b=.006,M=ry(-a));fastener([x,.951,z],.018,.01)
    disk(.041,.036,7,[x,.656,z],b=.003,segments=24)
tube([[-.60,.64,-.39],[-.60,1.10,-.39],[-.50,1.21,-.34],[-.26,1.18,-.21]],.011,4,segments=12)
box([.11,.08,.10],2,(-.60,.68,-.39),b=.006)
for j in range(3):
    t=np.linspace(0,1,20);p=np.stack([-.79-.11*np.sin(t*math.pi),.74-.12*t,-.22-.33*t+j*.022],1);tube(p,.008,16 if j else 27,segments=6)

# ---------- MATERIALS: sectioned samples with finishing/manufacturing contrast ----------
B.begin('materials-sectioned-physical-coupons',5);plinth()
box([1.13,.046,.72],2,(0,.637,0),b=.006)
# Keep samples separated so their thickness, grain and cleanly cut edges read.
box([.38,1.19,.17],6,(-.31,1.257,-.22),b=.0025,M=rz(-.045))
box([.40,.94,.145],5,(.18,1.135,-.20),b=.002,M=rz(.055))
box([.22,.61,.10],7,(.50,.976,-.19),b=.008,M=rz(.065))
for x in [-.31,.18,.50]:
    box([.27,.065,.24],28,(x,.697,-.20),b=.004)
    fastener([x,.735,-.11],.017,.01)
# Solid turned coupon with circular tool-feed highlights, polished rim and dark bore.
lathe([[.101,.67],[.19,.67],[.198,.68],[.198,.91],[.186,.925],[.111,.925],[.102,.915],[.101,.67]],28,128,C=(.33,0,.29))
ring(.203,.193,.010,4,(.33,.724,.29),b=.002,segments=128)
# Woven carbon sample draped over a rod; smooth large curvature plus fine weave.
u,v=np.meshgrid(np.linspace(-.25,.25,25),np.linspace(0,1,38))
y=.69+.28*np.sin(v*math.pi*.92);z=.32-.60*v
p=np.stack([u-.25,y,z],-1);dv,du=np.gradient(p,axis=(0,1));n=unit(np.cross(du,dv))
for sg in [1,-1]:B.add(p+[0,sg*.001,0],n*sg,grid_faces(*u.shape),23)
rod([-.54,.90,-.27],[.03,.90,-.27],.013,4,24)
box([.29,.10,.24],6,(-.30,.737,.31),b=.002,M=ry(.1))

make_forest()

# ---------- CENTRAL METROLOGY: bearings, tie rods, gimbals and restrained shell ----------
B.begin('central-bearing-cartridge',7)
disk(1.005,.11,2,(0,.32,0),b=.012,segments=192)
ring(.994,.972,.015,33,(0,.381,0),b=.002,segments=192)
disk(.947,.22,7,(0,.502,0),b=.012,segments=192)
ring(.951,.919,.022,33,(0,.622,0),b=.003,segments=192)
# Recessed drive ring: actual edge teeth, not a chrome castle around the center.
disk(.84,.215,2,(0,.748,0),b=.006,segments=160)
for a in np.linspace(0,TAU,48,endpoint=False):box([.046,.135,.024],2,(.849*np.cos(a),.743,.849*np.sin(a)),b=.002,M=ry(-a))
ring(.864,.815,.023,33,(0,.850,0),b=.003,segments=192)
disk(.78,.07,3,(0,.903,0),b=.005,segments=160)
disk(.717,.25,7,(0,1.060,0),b=.012,segments=192)
ring(.739,.712,.020,33,(0,1.195,0),b=.003,segments=192)
disk(.74,.062,7,(0,1.240,0),b=.006,segments=160)
for a in np.linspace(0,TAU,10,endpoint=False):fastener([.913*np.cos(a),.632,.913*np.sin(a)],.018,.01)
B.begin('central-structural-tie-rods',7)
for a in np.linspace(.18,TAU+.18,4,endpoint=False):
    ca,sa=np.cos(a),np.sin(a);p0=np.array([ca*.716,1.28,sa*.716]);p1=np.array([ca*.77,2.91,sa*.77])
    rod(p0,p1,.021,33,48)
    disk(.051,.12,2,p0+[0,.030,0],b=.004,segments=48)
    disk(.043,.048,4,p0+[0,.109,0],b=.003,segments=40)
    fastener([ca*.77,3.048,sa*.77],.023,.014)
B.begin('central-enamel-top-cap',7)
ring(.849,.289,.12,7,(0,2.975,0),b=.009,segments=224)
ring(.851,.828,.013,2,(0,3.044,0),b=.002,segments=192)
disk(.315,.039,2,(0,3.063,0),b=.006,segments=160)
for a in np.linspace(0,TAU,6,endpoint=False):fastener([.25*np.cos(a),3.088,.25*np.sin(a)],.013,.008)
# Sparse, flush top ventilation -- no high contrast stippled chrome.
# Upper cap is continuous enamel; no decorative ventilation marks.
B.begin('central-calibrated-gimbals',7,3)
for rad,M,mat in [(.65,rx(.62)@rz(-.36),3),(.73,rx(-.62)@rz(.83),28)]:
    ring(rad,rad-.029,.036,mat,(0,2.14,0),b=.004,M=M,segments=192,part=3)
    for a in np.linspace(0,TAU,36,endpoint=False):box([.010,.001,.002],2,np.array([0,2.14,0])+M@[rad*np.cos(a),.021,rad*np.sin(a)],b=.0002,M=M@ry(-a),part=3)
B.begin('central-cut-optical-core',7)
N=7;verts=[]
for y,r,phase in [(1.48,.30,.10),(1.63,.42,.10),(2.38,.37,.10),(2.72,.12,.36)]:
    for a in np.linspace(0,TAU,N,endpoint=False)+phase:verts.append([np.cos(a)*r,y,np.sin(a)*r])
verts=np.array(verts);verts[:,0]+=.065*(verts[:,1]-2.)
hull=ConvexHull(verts)
for f in hull.simplices:
    pp=verts[f];nn=unit(np.cross(pp[1]-pp[0],pp[2]-pp[0]));nn=nn if np.dot(nn,pp.mean(0)-[0,2,0])>0 else -nn
    B.add(pp,[nn]*3,[[0,1,2]],21)
for a in [0,TAU/3,2*TAU/3]:box([.09,.18,.07],28,(.32*np.cos(a),1.43,.32*np.sin(a)),b=.004,M=ry(-a))
B.begin('central-micrometer-carriage',7)
box([.30,.20,.20],2,(.55,1.04,.44),b=.012)
micrometer([.76,1.04,.44],rz(-math.pi/2))
# Ground plane for actual baked contact shadows.
B.begin('studio-cyclorama',0)
axis=np.unique(np.r_[-60,-30,-15,np.linspace(-11,11,160),15,30,60]);xx,zz=np.meshgrid(axis,axis)
p=np.stack([xx,np.full_like(xx,-.18),zz],-1);n=np.zeros_like(p);n[:,:,1]=1
B.add(p,n,grid_faces(*xx.shape),1)
B.write()
