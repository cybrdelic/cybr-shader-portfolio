# These definitions are executed with the explicit surface builder from geometry.py.
# All dimensions are scene units; 1 scene unit represents approximately 100 mm.
# Seeded and deterministic, using physical parts rather than imported models.
import trimesh
from scipy.spatial import Voronoi, ConvexHull

# Geometry sampling supports area-light irradiance baked at vertices.
def plinth():
    # Cast black base, exposed turned aluminium collar, thin enamel top flange.
    disk(1.025,.102,2,(0,.349,0),b=.009,segments=112)
    disk(.982,.157,7,(0,.477,0),b=.006,segments=112)
    # Single enamel skirt, not five subpixel decorative grooves.
    ring(1.006,.935,.036,7,(0,.559,0),b=.005,segments=112)
    ring(1.008,.994,.010,4,(0,.581,0),b=.001,segments=112)
    disk(.935,.028,2,(0,.591,0),b=.004,segments=112)
    ring(.939,.925,.006,3,(0,.609,0),b=.0007,segments=112)
    for a in np.linspace(0,TAU,10,endpoint=False):
        bolt([.971*math.cos(a),.585,.971*math.sin(a)],.021,.010)
    for a in [0,TAU/3,2*TAU/3]:
        disk(.071,.027,16,(.72*math.cos(a),.286,.72*math.sin(a)),b=.004,segments=20)
    # Dowel-located little identification plate; two sunk screws.
    box([.40,.012,.14],24,(.80,.620,0),b=.0015,M=ry(math.pi/2))
    for dz in [-.18,.18]: bolt([.80,.628,dz],.010,.004)
    # Coupled rear connectors and an insulating cable gland.
    for zz in [-.24,.24]:
        c=np.array([-.95,.493,zz]);M=rz(math.pi/2)
        disk(.056,.068,4,c,b=.002,segments=6,M=M)
        ring(.046,.028,.090,2,c+[-.035,0,0],b=.002,segments=32,M=M)
        for k in range(4):ring(.046,.036,.003,4,c+[-.025-k*.011,0,0],b=.0005,segments=28,M=M)
        t=np.linspace(0,1,18);points=np.stack([-.99-.18*t,.49-.19*t+.05*np.sin(t*math.pi),np.full_like(t,zz)],1)
        tube(points,.018,16,segments=8)


def grooved_knob(c,r=.065,h=.085,mat=2,M=None):
    disk(r,h,mat,c,b=.005,segments=48,M=M)
    ring(r*1.01,r*.90,.009,4,np.asarray(c)+(np.array([0,h*.25,0]) if M is None else M@np.array([0,h*.25,0])),b=.001,segments=48,M=M)
    for a in np.linspace(0,TAU,24,endpoint=False):
        p=np.array([r*.99*math.cos(a),0,r*.99*math.sin(a)])
        p=np.asarray(c)+(p if M is None else M@p)
        disk(.0028,h*.7,4,p,b=.0007,segments=6,M=M)


def screw_thread(c,r=.035,h=.20,mat=4,M=None):
    disk(r*.82,h,mat,c,b=.001,segments=24,M=M)
    turns=max(3,int(h/.012));u=np.linspace(0,turns*TAU,turns*12)
    p=np.stack([r*np.cos(u),h*(u/(turns*TAU)-.5),r*np.sin(u)],1)
    if M is not None:p=p@M.T
    tube(p+np.asarray(c),.0022,mat,segments=4)


def face_plate(c,size=(.83,.021,.32),mat=24,M=None):
    box(size,mat,c,b=.003,M=M)
    # Two countersunk side screws rather than oversized cartoon dots.
    for x in [-size[0]*.44,size[0]*.44]:
        q=np.array([x,size[1]*.62,0]);bolt(np.asarray(c)+(q if M is None else M@q),.014,.007,M)

B.begin('atelier-chassis',0)
disk(4.46,.115,2,(0,.016,0),b=.012,segments=192)
ring(4.462,4.415,.014,4,(0,.08,0),b=.002,segments=192)
disk(4.395,.141,28,(0,.16,0),b=.008,segments=224)
disk(4.355,.013,7,(0,.235,0),b=.002,segments=224)
ring(4.407,4.350,.028,4,(0,.229,0),b=.003,segments=224)
ring(4.396,4.388,.007,2,(0,.239,0),b=.001,segments=192)
# Rather than broad black radial cuts, there are flush fine instrument seams.
for a in np.linspace(0,TAU,6,endpoint=False):
    c=np.array([math.cos(a),0,math.sin(a)])
    box([2.35,.003,.004],2,c*2.77+[0,.232,0],b=.0005,M=ry(-a))
    # Separate conduit visible where the two module assemblies meet.
    for sign in [-1,1]:
        side=np.array([-math.sin(a),0,math.cos(a)])*.070*sign
        tube([c*.85+side+[0,.25,0],c*1.15+side+[0,.275,0],c*1.65+side+[0,.275,0],c*2.25+side+[0,.27,0]],.010,16,segments=8)
    disk(.175,.12,16,c*3.60+[0,-.103,0],b=.012,segments=32)
for a in np.linspace(0,TAU,32,endpoint=False):bolt([4.24*math.cos(a),.240,4.24*math.sin(a)],.023,.012)
# Interrupted ventilation around the anodised instrument bed.
for a in np.linspace(0,TAU,144,endpoint=False):
    if abs(math.sin(a*3.))<.23: continue
    box([.045,.053,.015],4,(4.452*math.cos(a),.009,4.452*math.sin(a)),b=.0018,M=ry(-a+math.pi/2))
for r in [4.368,4.374,4.381]:ring(r+.0012,r,.0012,2,(0,.245,0),b=.0002,segments=224)
# Six inboard mounting lugs. The layers are mechanically joined, not floating.
for a in np.linspace(0,TAU,6,endpoint=False):
    ca,sa=math.cos(a),math.sin(a)
    for dr in [-.22,.22]:
        box([.16,.06,.19],2,((4.1+dr)*ca,.25,(4.1+dr)*sa),b=.009,M=ry(-a))
        bolt([(4.1+dr)*ca,.288,(4.1+dr)*sa],.022,.011)
# Fine inner concentric scribe marks define the platter scale.
for rr in [4.12,4.16]:ring(rr+.0018,rr,.002,4,(0,.233,0),b=.0003,segments=192)
# A physical engraved identity plate matching the original foreground brief.
plateC=np.array([-1.05,.30,4.46]);plateM=rx(.28)
box([2.68,.065,1.34],2,plateC-plateM@[0,.025,0],b=.012,M=plateM)
box([2.60,.035,1.27],25,plateC,b=.006,M=plateM)
for xx in [-1.18,1.18]:
    for zz in [-.54,.54]:bolt(plateC+plateM@[xx,.023,zz],.018,.007,plateM)
    support=plateC+plateM@[xx,-.09,-.52]
    box([.10,.22,.16],2,support,b=.006)
    bolt([support[0],.245,support[2]-.10],.022,.010)


# LIGHT: an actual optical bench with gimbal, lens rim and paired collimators.
B.begin('light-optomechanics',1);plinth()
optCenter=np.array([0,1.59,0]);optM=rz(-1.23)@rx(.06)
for z in [-.28,.28]:
    rod([-.10,.63,z],[-.10,.95,z],.035,4,24)
    disk(.078,.026,2,[-.10,.636,z],b=.003,segments=32)
    box([.21,.055,.78],2,(-.10,.93,0),b=.005)
ring(.868,.754,.148,2,optCenter,.007,optM,segments=128)
ring(.872,.848,.016,4,optCenter+optM@[0,.082,0],.002,optM,segments=128)
ring(.770,.742,.026,3,optCenter+optM@[0,.078,0],.002,optM,segments=128)
for a in np.linspace(0,TAU,16,endpoint=False):bolt(optCenter+optM@[.813*math.cos(a),.083,.813*math.sin(a)],.016,.010,optM)
# Interior gimbal with real side pivots and graduated rings.
innerM=optM@rx(.32)
ring(.718,.677,.052,4,optCenter,.004,innerM,segments=112,part=1)
ring(.682,.658,.018,2,optCenter,.002,innerM,segments=112,part=1)
for side in [-1,1]:
    c=optCenter+optM@[side*.861,0,0]
    disk(.068,.105,4,c,b=.004,M=optM@rz(math.pi/2),segments=40)
    grooved_knob(c+optM@[side*.083,0,0],.051,.05,M=optM@rz(math.pi/2))
for a in np.linspace(0,TAU,96,endpoint=False):
    pos=optCenter+optM@[.828*math.cos(a),.092,.828*math.sin(a)]
    box([.014 if int(a/TAU*96)%8==0 else .007,.001,.0024],18,pos,b=.0002,M=optM@ry(-a))
# Matte stepped light baffles, retaining wire and fine threaded objective rim.
for offset in [-.061,-.042,-.023,.025,.044,.062]:
    ring(.754,.729,.005,2,optCenter+optM@[0,offset,0],.0006,optM,segments=144)
for a in np.linspace(0,TAU,60,endpoint=False):
    q=optCenter+optM@[.861*math.cos(a),0,.861*math.sin(a)]
    disk(.0035,.115,2,q,b=.0007,segments=6,M=optM)
# Lower gimbal axle and 0.5-mm knurled fine focus drive.
rod([-.12,.76,0],[.18,.76,0],.033,4,24)
grooved_knob([.19,.76,0],.083,.105,M=rz(math.pi/2))
# Three adjustment stages, with non-overlapping sleeves and telescopic posts.
for c,angle in [([.47,.76,.38],-.62),([-.48,.79,-.35],.7)]:
    disk(.11,.04,2,[c[0],.63,c[2]],b=.004,segments=40)
    rod([c[0],.63,c[2]],c,.025,4,24)
    ring(.126,.079,.20,2,c,b=.004,M=rz(angle),segments=64)
    ring(.129,.117,.010,4,np.asarray(c)+rz(angle)@[0,.105,0],b=.001,M=rz(angle),segments=64)
    disk(.078,.006,21,np.asarray(c)+rz(angle)@[0,.102,0],b=.001,M=rz(angle),segments=48)
face_plate((.50,.632,-.51),(.42,.014,.18),24,ry(.35))

# GEO: vertical shaft, open radial rotor, stator blades and tangible bearing support.
B.begin('geometry-axial-machine',2);plinth()
disk(.77,.15,2,(0,.703,0),b=.009,segments=128)
ring(.785,.74,.021,4,(0,.773,0),b=.003,segments=128)
# Lower rim, outer mounting columns and exposed copper windings.
ring(.79,.69,.028,3,(0,.791,0),b=.002,segments=128)
for a in np.linspace(0,TAU,12,endpoint=False):
    x,z=.728*math.cos(a),.728*math.sin(a)
    box([.095,.21,.080],2,(x,.90,z),b=.006,M=ry(-a))
    for j in range(7):
        # Winding geometry visible between separate housing cheeks.
        local=np.array([[-.057,-.038],[-.050,-.048],[.050,-.048],[.057,-.038],[.057,.038],[.050,.048],[-.050,.048],[-.057,.038],[-.057,-.038]])
        points=np.stack([local[:,0],np.full(len(local),.825+j*.023),local[:,1]],1)
        points=points@ry(-a).T+np.array([x,0,z])
        tube(points,.0053,17,segments=6)
ring(.79,.72,.033,4,(0,1.035,0),b=.003,segments=128)
ring(.756,.677,.080,2,(0,1.09,0),b=.004,segments=128)
# Bottom diffuser blades are unpainted nickel alloy, not identical flat wedges.
for idx in range(31):
    a=idx*TAU/31
    radius,chord=np.meshgrid(np.linspace(.235,.672,10),np.linspace(-1,1,6))
    rr=(radius-.235)/(.672-.235);ang=a+.24*rr+.046*chord
    yy=1.08+.12*rr+.05*chord+.022*(1-chord*chord)
    for side in [-1,1]:
        pp=np.stack([radius*np.cos(ang),yy+side*.004*np.sqrt(np.maximum(0,1-chord**2)),radius*np.sin(ang)],-1)
        dv,du=np.gradient(pp,axis=(0,1));nn=unit(np.cross(du,dv))*side
        B.add(pp,nn,grid_faces(*radius.shape),4,ao=.95,part=2)
lathe([[0,.82],[.18,.82],[.21,1.02],[.21,1.17],[.18,1.25],[.12,1.31],[.10,1.42],[0,1.42]],4,96,part=2)
ring(.215,.19,.025,2,(0,1.17,0),b=.003,segments=96,part=2)
# Transparent architecture without a plastic dome: steel posts and machined top annulus.
for a in np.linspace(0,TAU,5,endpoint=False):
    x,z=.736*math.cos(a),.736*math.sin(a)
    rod([x,.64,z],[x,1.39,z],.022,4,24)
    screw_thread([x,1.40,z],.027,.07)
    disk(.045,.026,2,[x,1.444,z],b=.002,segments=6)
ring(.819,.728,.041,28,(0,1.37,0),b=.002,segments=144)
for aa in [0,TAU/3,2*TAU/3]:
    box([.53,.030,.066],28,(.48*math.cos(aa),1.39,.48*math.sin(aa)),b=.005,M=ry(-aa))
    bolt([.70*math.cos(aa),1.412,.70*math.sin(aa)],.015,.008)
ring(.824,.804,.014,4,(0,1.416,0),b=.002,segments=128)
for a in np.linspace(0,TAU,10,endpoint=False):bolt([.76*math.cos(a),1.419,.76*math.sin(a)],.023,.011)
# Top bearing tower, separated steel races and central axial fastener.
disk(.21,.064,2,(0,1.44,0),b=.004,segments=80)
disk(.22,.035,4,(0,1.481,0),b=.003,segments=96)
ring(.187,.15,.040,3,(0,1.514,0),b=.003,segments=80)
disk(.168,.059,4,(0,1.55,0),b=.005,segments=80)
bolt([0,1.586,0],.050,.020)
face_plate((.69,.634,-.27),(.40,.014,.18),24,ry(.35))

# Additional bearing race, ball pockets and an exposed worm-drive assembly.
B.begin('precision-rotor-bearing',2)
for a in np.linspace(0,TAU,16,endpoint=False):
    # The rolling elements sit between two metal races.
    torus(.026,.011,4,(.255*math.cos(a),1.449,.255*math.sin(a)),segments=12,steps=8)
ring(.292,.274,.018,2,(0,1.446,0),b=.001,segments=96)
ring(.294,.286,.010,4,(0,1.460,0),b=.001,segments=96)
for x in [-.39,.39]:
    box([.12,.21,.16],2,(x,.82,-.59),b=.008)
rod([-.48,.82,-.59],[.48,.82,-.59],.035,4,24)
screw_thread([0,.82,-.59],.064,.55,3,M=rz(math.pi/2))
grooved_knob([.49,.82,-.59],.095,.085,M=rz(math.pi/2))

# SCENES: tilted stratified outcrop, secondary fractures, talus and a dark water margin.
exec((Path(__file__).parent/'rebuild_organics.py').read_text(),globals())
new_geology()
'''REMOVED_OLD_STONE
B.begin('scenes-geological-outcrop',3);plinth()
ring(.851,.802,.066,2,(0,.655,0),b=.005,segments=96)
disk(.803,.025,10,(0,.676,0),b=.002,segments=128)
def fractured_rock(c,scale,seed):
    gen=np.random.default_rng(seed)
    # Intersecting broad fracture planes determine the silhouette. Fine relief
    # is continuous along shared edges, not a stack of separate horizontal disks.
    ring=np.array([[-.88,-.68],[-.94,.24],[-.37,.87],[.48,.94],[.96,.22],[.68,-.68]])
    pts=[]
    for y,fac,offset in [(-1.,.93,[-.11,.02]),(.04,1.,[0,0]),(1.,.67,[.18,-.10])]:
        xy=ring*fac*gen.uniform(.89,1.08,(6,1))+np.array(offset)
        for x,z in xy:pts.append([x,y+gen.uniform(-.14,.14),z])
    hull=ConvexHull(np.asarray(pts));points=np.asarray(pts)
    lattice=gen.normal(size=(48,48,48))
    def noise(p,freq):
        return map_coordinates(lattice,((p*freq+23.4)%47).T,order=1,mode='wrap')
    for face in hull.simplices:
        abc=points[face];baseN=unit(np.cross(abc[1]-abc[0],abc[2]-abc[0]))
        if np.dot(baseN,abc.mean(0))<0:abc=abc[[0,2,1]]
        # Shared barycentric subdivision retains razor-thin cleavage edges.
        n=25;vv=[];ids={}
        for i in range(n+1):
            for j in range(n+1-i):
                ids[i,j]=len(vv);vv.append(abc[0]*(1-(i+j)/n)+abc[1]*(i/n)+abc[2]*(j/n))
        vv=np.asarray(vv);r=unit(vv)
        relief=.024*noise(vv,2.0)+.009*noise(vv,8.3)+.003*noise(vv,23.0)
        lam=vv[:,1]*29.+vv[:,0]*6.4+vv[:,2]*3.1+.32*noise(vv,2.4)
        fissure=np.exp(-((np.sin(lam*math.pi))/.13)**2)
        relief-=fissure*.016
        vv=(vv+r*relief[:,None])*np.array(scale)+np.array(c)
        ff=[]
        for i in range(n):
            for j in range(n-i):
                ff.append([ids[i,j],ids[i+1,j],ids[i,j+1]])
                if j<n-i-1:ff.append([ids[i+1,j],ids[i+1,j+1],ids[i,j+1]])
        mesh=trimesh.Trimesh(vertices=vv,faces=ff,process=False)
        B.add(vv,mesh.vertex_normals,mesh.faces,11,ao=.97)
fractured_rock((.05,1.31,-.08),(.37,.61,.29),5021)
fractured_rock((-.31,.94,.14),(.24,.24,.22),5022)
fractured_rock((.30,.84,.22),(.24,.14,.19),5023)
for i in range(52):
    a=rng.uniform(0,TAU);r=rng.uniform(.41,.76);sc=rng.uniform(.014,.056,3)
    rock=trimesh.creation.icosphere(subdivisions=1,radius=1)
    pp=rock.vertices*sc*(.86+rng.random((len(rock.vertices),1))*.3)+[r*math.cos(a),.694+sc[1],r*math.sin(a)]
    B.add(pp,rock.vertex_normals,rock.faces,11 if i%7 else 29)
rod([-.64,.63,-.40],[-.64,1.77,-.40],.012,4,16)
rod([-.64,1.77,-.40],[-.22,1.77,-.40],.010,4,16)
screw_thread([-.64,.73,-.40],.023,.13)

REMOVED_OLD_STONE'''
# ELEMENTS: thick ceramic crucible, coarse cooled plates over actual molten gaps.
B.begin('elements-crucible',4);plinth()
disk(.82,.29,26,(0,.78,0),b=.006,segments=128)
ring(.838,.803,.027,4,(0,.66,0),b=.003,segments=112)
ring(.835,.75,.041,2,(0,.94,0),b=.005,segments=112)
ring(.797,.749,.014,4,(0,.969,0),b=.002,segments=112)
disk(.748,.022,9,(0,.933,0),b=.002,segments=128)
# Voronoi plate topology, with finite-width channels and beveled sidewalls.
sites=rng.uniform(-.72,.72,(120,2));sites=sites[np.linalg.norm(sites,axis=1)<.70]
boundary=np.stack([np.cos(np.linspace(0,TAU,40,endpoint=False)),np.sin(np.linspace(0,TAU,40,endpoint=False))],1)*.99
def clip_crust(poly,radius=.746):
    # Convex polygon clipping fills edge cells; there is no exposed orange annulus.
    for angle in np.linspace(0,TAU,64,endpoint=False):
        normal=np.array([math.cos(angle),math.sin(angle)]);clipped=[]
        for aa,bb in zip(poly,np.roll(poly,-1,axis=0)):
            da=float(aa@normal-radius);db=float(bb@normal-radius)
            if da<=0:clipped.append(aa)
            if (da<=0)!=(db<=0):clipped.append(aa+(bb-aa)*da/(da-db))
        poly=np.asarray(clipped)
        if len(poly)<3:return poly
    return poly
vor=Voronoi(np.r_[sites,boundary])
for i in range(len(sites)):
    region=vor.regions[vor.point_region[i]]
    if -1 in region or len(region)<3:continue
    poly=clip_crust(vor.vertices[region])
    if len(poly)<3:continue
    center=poly.mean(axis=0);poly=center+(poly-center)*rng.uniform(.953,.984)
    top=.958+rng.uniform(0,.019);bottom=.940
    # Convex polygons as bevelled prisms, with separate normal domains.
    for a,b in zip(poly,np.roll(poly,-1,axis=0)):
        pp=np.array([[center[0],top,center[1]],[a[0],top,a[1]],[b[0],top,b[1]]])
        B.add(pp,[[0,1,0]]*3,[[0,1,2]],22)
        e=b-a;nn=unit([e[1],.2,-e[0]])
        B.add([[a[0],top,a[1]],[b[0],top,b[1]],[b[0],bottom,b[1]],[a[0],bottom,a[1]]],[nn]*4,[[0,1,2],[0,2,3]],22)
for a in np.linspace(0,TAU,18,endpoint=False):
    x,z=.797*math.cos(a),.797*math.sin(a)
    bolt([x,.982,z],.016,.009)
    rod([x,.69,z],[x,.91,z],.010,4,12)
# Thermocouple and metal thermowell; one purposeful probe, not decorative fences.
tube([[-.57,.63,-.42],[-.57,1.22,-.42],[-.44,1.30,-.35],[-.21,1.24,-.24]],.013,4,segments=12)
box([.12,.075,.10],2,(-.57,.68,-.42),b=.005)

# Insulating standoffs, thermocouple feedthroughs and a wound heater jacket.
B.begin('thermal-physical-hardware',4)
for a in [.25,2.34,4.43]:
    x,z=.86*math.cos(a),.86*math.sin(a)
    box([.11,.34,.08],28,(x,.79,z),b=.005,M=ry(-a))
    bolt([x,.972,z],.021,.011)
    disk(.044,.045,7,[x,.67,z],b=.002,segments=24)
for j in range(9):ring(.824,.817,.007,2,(0,.685+j*.027,0),b=.0008,segments=96)
# Explicit cable bundle remains connected to the module base.
t=np.linspace(0,1,18)
for i in range(3):
    pts=np.stack([-.79-.10*np.sin(t*math.pi),.75-.12*t,-.23-.31*t+i*.025],1)
    tube(pts,.008,27 if i==0 else 16,segments=8)

# MATERIALS: a specimen rack, metal coupons and a draped physical woven swatch.
B.begin('materials-study-rack',5);plinth()
box([1.12,.052,.70],2,(0,.645,0),b=.004)
box([.42,1.23,.15],6,(-.30,1.29,-.22),b=.003,M=rz(-.055))
box([.40,.92,.16],5,(.17,1.135,-.18),b=.004,M=rz(.045))
box([.21,.65,.12],7,(.49,.998,-.15),b=.003,M=rz(.07))
# Milled steel sample with genuine small through holes along its upper edge.
ring(.174,.112,.28,4,(.31,.82,.30),b=.004,segments=80)
for y in [.71,.74,.89,.92]:ring(.176,.167,.004,2,(.31,y,.30),b=.0006,segments=80)
# Carbon weave is a bent sheet, not a plastic-coloured block.
u,v=np.meshgrid(np.linspace(-.30,.30,32),np.linspace(0,1,45))
y=.690+.33*np.sin(v*math.pi*.90);z=.31-.62*v
pp=np.stack([u-.27,y,z],-1);dv,du=np.gradient(pp,axis=(0,1));nn=unit(np.cross(du,dv))
for side in [-1,1]:B.add(pp+[0,side*.001,0],nn*side,grid_faces(*u.shape),23)
rod([-.57,.90,-.27],[.03,.90,-.27],.014,4,16)
# End-grain cut piece stands proud of the wood specimen.
box([.30,.10,.24],6,(-.30,.74,.29),b=.003,M=ry(.1))

# FOREST: twisted root flare and actual hierarchical branch/twig/leaf geometry.
new_forest()

# CENTER: precise cage, threaded tie rods, concentric gear bed and cut mineral prism.
B.begin('central-metrology-instrument',7)
disk(1.005,.11,2,(0,.32,0),b=.009,segments=128)
ring(.987,.94,.020,4,(0,.379,0),b=.002,segments=128)
disk(.928,.21,28,(0,.50,0),b=.006,segments=144)
ring(.932,.903,.021,4,(0,.607,0),b=.002,segments=128)
disk(.84,.24,2,(0,.755,0),b=.005,segments=128)
# Slender external gear teeth, not broad blocky castle crenellations.
for i,a in enumerate(np.linspace(0,TAU,64,endpoint=False)):
    box([.055,.19,.035],4,(.851*math.cos(a),.744,.851*math.sin(a)),b=.002,M=ry(-a))
ring(.872,.811,.029,3,(0,.648,0),b=.003,segments=128)
ring(.864,.800,.029,4,(0,.851,0),b=.003,segments=128)
disk(.766,.09,3,(0,.912,0),b=.005,segments=128)
disk(.705,.22,7,(0,1.065,0),b=.006,segments=144)
# Coated cylindrical housing: no ornamental silver stripes.
ring(.742,.702,.024,4,(0,1.183,0),b=.003,segments=128)
disk(.736,.071,7,(0,1.225,0),b=.005,segments=128)
# Cap has a mild machined profile with a distinct rim rather than an inflated puck.
ring(.846,.286,.100,28,(0,2.982,0),b=.006,segments=160)
ring(.850,.835,.014,4,(0,3.040,0),b=.002,segments=160)
ring(.821,.365,.009,7,(0,3.036,0),b=.002,segments=160)
ring(.848,.814,.018,4,(0,2.913,0),b=.002,segments=160)
disk(.315,.037,2,(0,3.066,0),b=.004,segments=96)
ring(.319,.296,.008,4,(0,3.088,0),b=.001,segments=96)
for a in np.linspace(0,TAU,6,endpoint=False):
    ca,sa=math.cos(a),math.sin(a);p0=np.array([ca*.735,1.27,sa*.735]);p1=np.array([ca*.79,2.91,sa*.79])
    rod(p0,p1,.027,4,32)
    screw_thread(p0+[0,.05,0],.021,.11)
    disk(.038,.033,2,p0+[0,.13,0],b=.002,segments=6)
    disk(.045,.075,4,p0+[0,.014,0],b=.003,segments=32)
    bolt([ca*.78,3.056,sa*.78],.020,.012)
# Double gimbal: irregular crossing angles and real calibration notches.
for rad,M,mat,part in [(.65,rx(.62)@rz(-.36),3,3),(.73,rx(-.62)@rz(.83),4,3)]:
    ring(rad,rad-.027,.033,mat,(0,2.14,0),b=.003,M=M,segments=128,part=part)
    for a in np.linspace(0,TAU,72,endpoint=False):
        pos=np.array([0,2.14,0])+M@[rad*math.cos(a),.019,rad*math.sin(a)]
        box([.012,.002,.003],2,pos,b=.0003,M=M@ry(-a),part=part)
# Faceted optically dark quartz core, a physical cut polyhedron with planar faces.
N=7;verts=[]
for y,r,phase in [(1.48,.30,.10),(1.63,.42,.10),(2.38,.37,.10),(2.72,.12,.36)]:
    for a in np.linspace(0,TAU,N,endpoint=False)+phase:verts.append([math.cos(a)*r,y,math.sin(a)*r])
verts=np.array(verts);verts[:,0]+=.065*(verts[:,1]-2.)
hull=ConvexHull(verts)
for f in hull.simplices:
    pp=verts[f];nn=unit(np.cross(pp[1]-pp[0],pp[2]-pp[0]));center=pp.mean(0)-[0,2.0,0]
    if np.dot(nn,center)<0:nn=-nn
    B.add(pp,[nn]*3,[[0,1,2]],21)
# Lower prism holder grips the specimen at three small beveled contacts.
for a in [0,TAU/3,2*TAU/3]:
    box([.09,.18,.07],4,(.32*math.cos(a),1.43,.32*math.sin(a)),b=.003,M=ry(-a))
for a in np.linspace(0,TAU,12,endpoint=False):bolt([.925*math.cos(a),.617,.925*math.sin(a)],.021,.010)

B.begin('central-calibration-hardware',7)
# Micrometer fine-adjuster at the front, with knurled drum and physical grooves.
M=rz(math.pi/2)
box([.31,.21,.20],2,(.55,1.03,.45),b=.010)
rod([.44,1.04,.45],[.95,1.04,.45],.033,4,24)
screw_thread([.72,1.04,.45],.042,.24,4,M=M)
grooved_knob([.94,1.04,.45],.095,.15,2,M)
# Fine service collar texture is shading, not subpixel stacked geometry.
# Top vents and individually visible low-profile screwheads.
for a in np.linspace(0,TAU,48,endpoint=False):
    if int(a/TAU*48)%8==0:continue
    q=np.array([.55*math.cos(a),3.043,.55*math.sin(a)])
    box([.12,.0012,.008],2,q,b=.0005,M=ry(-a))
# Bearing and motor cap have a useful-looking perimeter, not a giant black dot.
for a in np.linspace(0,TAU,8,endpoint=False):bolt([.245*math.cos(a),3.089,.245*math.sin(a)],.017,.008)

# A tessellated photographic sweep receives offline area-light shadows.
B.begin('area-lit-studio-sweep',0)
axis=np.unique(np.r_[-60,-30,-15,np.linspace(-11,11,180),15,30,60]);xx,zz=np.meshgrid(axis,axis)
pp=np.stack([xx,np.full_like(xx,-.18),zz],-1);nn=np.zeros_like(pp);nn[:,:,1]=1
B.add(pp,nn,grid_faces(*xx.shape),1)
B.write()
