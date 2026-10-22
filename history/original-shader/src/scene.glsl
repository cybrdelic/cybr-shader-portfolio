// CYBR / COMPUTATIONAL INSTRUMENT
// Six mechanisms, one connected chassis. Every surface is an analytic field.
// Material ids: 1 floor, 2 anodized alloy, 3 bronze, 4 silver, 5 marble,
// 6 walnut, 7 ivory ceramic, 8 basalt, 9 lava, 10 water, 11 sandstone,
// 12 bark, 13 leaves, 14 moss, 15 warm emitter, 16 carbon, 17 copper,
// 18 maker plate, 19 blue enamel, 20 pale emitter.

mat2 rotation(float a) {
    float c=cos(a), s=sin(a);
    return mat2(c,-s,s,c);
}
float hash31(vec3 p) {
    p=fract(p*0.1031);
    p+=dot(p,p.yzx+33.33);
    return fract((p.x+p.y)*p.z);
}
float noise3(vec3 p) {
    vec3 i=floor(p), f=fract(p);
    f=f*f*(3.0-2.0*f);
    float a=mix(hash31(i),hash31(i+vec3(1,0,0)),f.x);
    float b=mix(hash31(i+vec3(0,1,0)),hash31(i+vec3(1,1,0)),f.x);
    float c=mix(hash31(i+vec3(0,0,1)),hash31(i+vec3(1,0,1)),f.x);
    float d=mix(hash31(i+vec3(0,1,1)),hash31(i+vec3(1,1,1)),f.x);
    return mix(mix(a,b,f.y),mix(c,d,f.y),f.z);
}
float fbm3(vec3 p) {
    return noise3(p)*0.57+noise3(p*2.03+7.1)*0.28
         + noise3(p*4.07+13.4)*0.15;
}
float sdBox(vec3 p,vec3 b) {
    vec3 q=abs(p)-b;
    return length(max(q,0.0))+min(max(q.x,max(q.y,q.z)),0.0);
}
float sdRoundBox(vec3 p,vec3 b,float r) { return sdBox(p,b)-r; }
float sdCylinder(vec3 p,vec2 rh) {
    vec2 d=abs(vec2(length(p.xz),p.y))-rh;
    return min(max(d.x,d.y),0.0)+length(max(d,0.0));
}
float sdTorus(vec3 p,vec2 t) { return length(vec2(length(p.xz)-t.x,p.y))-t.y; }
float sdBand(vec3 p,float radius,float width,float height,float bevel) {
    vec2 q=abs(vec2(length(p.xz)-radius,p.y))-vec2(width,height);
    return min(max(q.x,q.y),0.0)+length(max(q,0.0))-bevel;
}
float sdCapsule(vec3 p,vec3 a,vec3 b,float radius) {
    vec3 pa=p-a, ba=b-a;
    return length(pa-ba*clamp(dot(pa,ba)/dot(ba,ba),0.0,1.0))-radius;
}
float taperedBranch(vec3 p,vec3 a,vec3 b,float ra,float rb) {
    vec3 ba=b-a;
    float t=clamp(dot(p-a,ba)/dot(ba,ba),0.0,1.0);
    return (length(p-a-ba*t)-mix(ra,rb,t))*0.88;
}
float sdEllipsoid(vec3 p,vec3 r) {
    float k0=length(p/r),k1=length(p/(r*r));
    if(k0<0.0001)return -min(r.x,min(r.y,r.z));
    return k0*(k0-1.0)/max(k1,0.00001);
}
float smoothUnion(float a,float b,float k) {
    float h=clamp(0.5+0.5*(b-a)/k,0.0,1.0);
    return mix(b,a,h)-k*h*(1.0-h);
}
vec3 closerScene(vec3 a,vec3 b) { return a.x<b.x?a:b; }
vec3 polarFold(vec3 p,float count) {
    float a=atan(p.z,p.x),stepA=TAU/count;
    p.xz=rotation(floor((a+0.5*stepA)/stepA)*stepA)*p.xz;
    return p;
}
vec3 moduleCenter(int objectId) {
    if(objectId<1||objectId>6)return vec3(0.0);
    float a=PI+float(objectId-1)*TAU/6.0;
    return vec3(cos(a)*3.15,0.0,sin(a)*3.15);
}
vec3 moduleLocal(vec3 p,int objectId) {
    vec3 q=p-moduleCenter(objectId);
    q.xz=rotation(PI+float(objectId-1)*TAU/6.0)*q.xz;
    return q;
}
vec3 moduleWorld(vec3 p,int objectId) {
    p.xz=rotation(-(PI+float(objectId-1)*TAU/6.0))*p.xz;
    return p+moduleCenter(objectId);
}

// All bolts have a sunk hexagonal socket. They share a radial fold, so sixty
// fasteners are nearly as cheap as one and retain physical silhouettes.
float socketBolt(vec3 p,float radius,float halfHeight) {
    float head=sdCylinder(p,vec2(radius,halfHeight))-0.003;
    vec2 h=abs(p.xz);
    float hex=max(dot(h,normalize(vec2(1.0,1.7320508))),h.x);
    float socket=max(hex-radius*0.43,abs(p.y-halfHeight)-halfHeight*0.7);
    return max(head,-socket);
}
vec3 chassis(vec3 p) {
    // Raised graphite table with a continuous precision-machined annulus.
    float ring=max(sdCylinder(p-vec3(0,0.06,0),vec2(4.43,0.15)),
                  -sdCylinder(p-vec3(0,0.06,0),vec2(1.89,0.40)))-0.035;
    vec3 d=vec3(ring,2,0);
    d=closerScene(d,vec3(sdCylinder(p-vec3(0,0.08,0),vec2(0.99,0.17))-0.025,2,0));
    d=closerScene(d,vec3(sdCylinder(p-vec3(0,0.28,0),vec2(0.64,0.09))-0.018,3,0));
    d=closerScene(d,vec3(sdBand(p-vec3(0,0.235,0),4.39,0.052,0.018,0.010),3,0));
    d=closerScene(d,vec3(sdBand(p-vec3(0,0.265,0),4.13,0.026,0.017,0.007),4,0));
    d=closerScene(d,vec3(sdBand(p-vec3(0,0.26,0),2.03,0.105,0.022,0.012),3,0));
    d=closerScene(d,vec3(sdBand(p-vec3(0,0.255,0),2.24,0.020,0.018,0.007),4,0));

    // Uninterrupted machined track with recessed radial ruling.
    vec3 ruling=polarFold(p,96.0)-vec3(4.25,0.26,0);
    float tick=sdRoundBox(ruling,vec3(0.054,0.002,0.006),0.002);
    d=closerScene(d,vec3(tick,3,0));
    vec3 fastener=polarFold(p,24.0)-vec3(4.30,0.276,0);
    d=closerScene(d,vec3(socketBolt(fastener,0.036,0.015),4,0));

    vec3 beam=polarFold(p,6.0);
    d=closerScene(d,vec3(sdRoundBox(beam-vec3(1.75,0.35,0),vec3(1.25,0.045,0.12),0.024),3,0));
    d=closerScene(d,vec3(sdRoundBox(beam-vec3(1.75,0.412,0),vec3(1.21,0.014,0.050),0.008),2,0));
    // Paired conduit runs are continuous from the optical core to each module.
    vec3 cable=beam; cable.z=abs(cable.z)-0.19;
    d=closerScene(d,vec3(sdCapsule(cable,vec3(0.80,0.315,0),vec3(2.52,0.315,0),0.023),16,0));
    vec3 clip=cable;clip.x=mod(clip.x+0.13,0.26)-0.13;
    float cableClip=max(sdBand(vec3(clip.y-0.315,clip.x,clip.z),0.028,0.009,0.014,0.003),
                        max(0.89-beam.x,beam.x-2.44));
    d=closerScene(d,vec3(cableClip,4,0));

    // Six low isolation feet visible beneath the chassis edge.
    vec3 foot=polarFold(p,6.0)-vec3(3.80,-0.095,0);
    d=closerScene(d,vec3(sdCylinder(foot,vec2(0.23,0.071))-0.018,16,0));
    return d;
}

vec3 moduleBase(vec3 p,int objectId) {
    float id=float(objectId);
    vec3 d=vec3(sdCylinder(p-vec3(0,0.39,0),vec2(1.03,0.10))-0.025,2,id);
    d=closerScene(d,vec3(sdBand(p-vec3(0,0.51,0),0.955,0.035,0.026,0.012),3,id));
    d=closerScene(d,vec3(sdCylinder(p-vec3(0,0.512,0),vec2(0.88,0.024))-0.014,2,id));
    vec3 bolt=polarFold(p,8.0)-vec3(0.96,0.55,0);
    d=closerScene(d,vec3(socketBolt(bolt,0.028,0.014),4,id));
    // Each mechanism has its own small enamel index plaque.
    vec3 plaque=p-vec3(0.91,0.61,0);
    plaque.xz=rotation(PI*0.5)*plaque.xz;
    d=closerScene(d,vec3(sdRoundBox(plaque,vec3(0.23,0.040,0.055),0.012),19,id));
    return d;
}

vec3 opticsModule(vec3 p) {
    vec3 d=moduleBase(p,1);
    p.xz=rotation(PI*0.5)*p.xz;
    vec3 q=p-vec3(0,1.67,0);
    vec3 a=q; a.xy=rotation(0.24)*a.xy; a.yz=rotation(1.13)*a.yz;
    d=closerScene(d,vec3(sdBand(a,0.88,0.042,0.085,0.014),3,1));
    d=closerScene(d,vec3(sdBand(a,0.975,0.018,0.036,0.008),4,1));
    // Inner gimbal tilts slowly, while the outer precision frame remains fixed.
    vec3 b=q; b.xy=rotation(-0.36)*b.xy;
    b.yz=rotation(0.53+0.09*sin(clockTime*0.18))*b.yz;
    d=closerScene(d,vec3(sdBand(b,0.738,0.025,0.054,0.011),4,1));
    vec3 bolts=polarFold(a,12.0)-vec3(0.88,0.103,0);
    d=closerScene(d,vec3(socketBolt(bolts,0.026,0.018),2,1));
    vec3 pivot=a; pivot.x=abs(pivot.x)-0.88;
    d=closerScene(d,vec3(sdCylinder(pivot.yxz,vec2(0.083,0.10))-0.012,4,1));
    d=closerScene(d,vec3(sdCapsule(p,vec3(-0.12,0.57,0),vec3(-0.12,0.99,0),0.065),3,1));
    d=closerScene(d,vec3(sdCylinder(p-vec3(-0.12,0.60,0),vec2(0.20,0.04))-0.014,4,1));
    // A beam splitter and a collimator occupy real machined posts.
    vec3 mirror=p-vec3(0.53,0.82,0.39);
    mirror.xy=rotation(-0.24)*mirror.xy;
    d=closerScene(d,vec3(sdCylinder(mirror,vec2(0.19,0.035))-0.009,4,1));
    d=closerScene(d,vec3(sdCylinder(p-vec3(0.53,0.65,0.39),vec2(0.034,0.12))-0.007,3,1));
    vec3 barrel=p-vec3(-0.52,0.79,-0.42);barrel.yz=rotation(PI*0.5)*barrel.yz;
    d=closerScene(d,vec3(sdCylinder(barrel,vec2(0.105,0.21))-0.008,2,1));
    d=closerScene(d,vec3(sdBand(barrel,0.106,0.008,0.15,0.003),3,1));
    return d;
}

vec3 rotorModule(vec3 p) {
    vec3 d=moduleBase(p,2);
    p.xz=rotation(PI*0.5)*p.xz;
    vec3 q=p-vec3(0,1.55,0);
    q.yz=rotation(1.28)*q.yz;
    q.xz=rotation(clockTime*0.33)*q.xz;
    // Thirty swept vanes bridge a hub and two distinct structural rings.
    float body=max(sdCylinder(q,vec2(0.88,0.16)),-sdCylinder(q,vec2(0.70,0.40)));
    d=closerScene(d,vec3(body-0.015,3,2));
    d=closerScene(d,vec3(sdBand(q,0.91,0.028,0.235,0.012),4,2));
    d=closerScene(d,vec3(sdBand(q,0.68,0.027,0.23,0.008),2,2));
    vec3 vane=polarFold(q,30.0)-vec3(0.52,0,0);
    vane.xz=rotation(0.43)*vane.xz;
    d=closerScene(d,vec3(sdRoundBox(vane,vec3(0.207,0.205,0.018),0.010),4,2));
    d=closerScene(d,vec3(sdCylinder(q,vec2(0.27,0.28))-0.022,3,2));
    d=closerScene(d,vec3(sdCylinder(q-vec3(0,0.30,0),vec2(0.12,0.19))-0.017,4,2));
    float bevel=sdCylinder(q-vec3(0,0.51,0),vec2(0.085,0.032))-0.012;
    d=closerScene(d,vec3(bevel,2,2));
    vec3 radialBolt=polarFold(q,10.0)-vec3(0.81,0.19,0);
    d=closerScene(d,vec3(socketBolt(radialBolt,0.024,0.018),2,2));
    // Side yoke and a skew cross brace establish believable load paths.
    vec3 leg=p;leg.z=abs(leg.z)-0.43;
    d=closerScene(d,vec3(sdCapsule(leg,vec3(-0.27,0.61,0),vec3(-0.27,1.36,0),0.065),2,2));
    d=closerScene(d,vec3(sdCapsule(p,vec3(-0.27,0.64,-0.43),vec3(0.30,0.64,0.43),0.044),3,2));
    return d;
}

float archField(vec3 p,float radius,float thickness,float depth) {
    // Vertical arch in the x/y plane, cropped above its spring line.
    float ring=abs(length(p.xy)-radius)-thickness;
    return max(max(ring,abs(p.z)-depth),-p.y);
}
vec3 landscapeModule(vec3 p) {
    vec3 d=moduleBase(p,3);
    p.xz=rotation(PI*0.5)*p.xz;
    vec3 basin=p-vec3(0,0.64,0);
    d=closerScene(d,vec3(sdBand(basin,0.78,0.10,0.095,0.026),11,3));
    // The water is an actual, gently moving surface, not a painted texture.
    float ripple=sin(p.x*15.0+clockTime*0.67)*sin(p.z*12.0-clockTime*0.42)*0.004;
    float water=max(abs(p.y-0.685-ripple)-0.022,length(p.xz)-0.74);
    d=closerScene(d,vec3(water*0.85,10,3));
    vec3 land=p-vec3(-0.30,0.75,-0.12);
    float dune=sdEllipsoid(land,vec3(0.52,0.12,0.64));
    dune+=(noise3(land*15.0)-0.5)*0.012;
    d=closerScene(d,vec3(dune*0.8,11,3));
    // A three-arch ruin makes a recognizable landscape silhouette.
    vec3 a=p-vec3(-0.05,1.23,-0.24);
    a.xz=rotation(-0.18)*a.xz;
    float arc=archField(a,0.47,0.10,0.115);
    vec3 posts=a;posts.x=abs(posts.x)-0.47;
    arc=min(arc,sdRoundBox(posts-vec3(0,-0.27,0),vec3(0.095,0.27,0.115),0.012));
    d=closerScene(d,vec3(arc,11,3));
    vec3 small=p-vec3(0.33,0.98,0.37);small.xz=rotation(0.38)*small.xz;
    float smallArch=archField(small,0.25,0.060,0.075);
    vec3 smallPosts=small;smallPosts.x=abs(smallPosts.x)-0.25;
    smallArch=min(smallArch,sdRoundBox(smallPosts-vec3(0,-0.12,0),vec3(0.06,0.12,0.075),0.009));
    d=closerScene(d,vec3(smallArch,11,3));
    // Weathered stepping stones are separated by reflective water channels.
    vec3 stones=p;stones.z=mod(stones.z+0.11,0.22)-0.11;
    float stone=max(sdRoundBox(stones-vec3(0.47,0.714,0),vec3(0.13,0.022,0.067),0.018),abs(p.z)-0.59);
    d=closerScene(d,vec3(stone,8,3));
    return d;
}

vec3 elementsModule(vec3 p) {
    vec3 d=moduleBase(p,4);
    p.xz=rotation(PI*0.5)*p.xz;
    vec3 q=p-vec3(0,0.98,0);
    float shell=max(sdCylinder(q,vec2(0.77,0.32)),-sdCylinder(q-vec3(0,0.11,0),vec2(0.64,0.34)));
    d=closerScene(d,vec3(shell-0.025,8,4));
    d=closerScene(d,vec3(sdBand(q-vec3(0,0.19,0),0.80,0.027,0.033,0.012),3,4));
    d=closerScene(d,vec3(sdBand(q-vec3(0,-0.20,0),0.80,0.035,0.038,0.012),3,4));
    vec3 ribs=polarFold(q,12.0)-vec3(0.77,0,0);
    d=closerScene(d,vec3(sdRoundBox(ribs,vec3(0.037,0.28,0.035),0.012),2,4));
    float h=0.012*sin(p.x*11.0+clockTime*0.21)*sin(p.z*9.0-clockTime*0.17);
    float molten=max(abs(p.y-1.17-h)-0.033,length(p.xz)-0.635);
    d=closerScene(d,vec3(molten*0.7,9,4));
    // Three cooling stones break the surface; only cracks emit light.
    vec3 stone=p-vec3(-0.25,1.23,-0.19);stone.xz=rotation(0.3)*stone.xz;
    float c=sdEllipsoid(stone,vec3(0.25,0.075,0.19));
    c=min(c,sdEllipsoid(p-vec3(0.29,1.235,0.10),vec3(0.17,0.06,0.24)));
    c=min(c,sdEllipsoid(p-vec3(-0.04,1.22,0.35),vec3(0.17,0.065,0.13)));
    d=closerScene(d,vec3(c,8,4));
    vec3 hoop=p-vec3(0,1.65,0);hoop.yz=rotation(1.37)*hoop.yz;
    d=closerScene(d,vec3(sdBand(hoop,0.96,0.016,0.025,0.006),3,4));
    return d;
}

vec3 materialsModule(vec3 p) {
    vec3 d=moduleBase(p,5);
    p.xz=rotation(PI*0.5)*p.xz;
    // Six independent specimens: marble, walnut, ceramic, bronze, carbon,
    // and satin enamel. Asymmetric heights read as curated physical samples.
    vec3 q=p-vec3(-0.40,1.12,-0.29);q.xz=rotation(-0.17)*q.xz;
    d=closerScene(d,vec3(sdRoundBox(q,vec3(0.21,0.57,0.18),0.038),5,5));
    q=p-vec3(0.10,1.34,-0.27);q.xz=rotation(0.10)*q.xz;
    d=closerScene(d,vec3(sdRoundBox(q,vec3(0.19,0.79,0.17),0.035),6,5));
    q=p-vec3(0.56,1.03,-0.13);q.xz=rotation(0.36)*q.xz;
    d=closerScene(d,vec3(sdRoundBox(q,vec3(0.15,0.49,0.17),0.042),7,5));
    d=closerScene(d,vec3(length(p-vec3(-0.48,0.79,0.39))-0.24,3,5));
    q=p-vec3(0.04,0.84,0.40);q.xz=rotation(-0.20)*q.xz;
    d=closerScene(d,vec3(sdRoundBox(q,vec3(0.20,0.29,0.18),0.022),16,5));
    d=closerScene(d,vec3(length(p-vec3(0.55,0.77,0.37))-0.22,19,5));
    return d;
}

float foliageCluster(vec3 p,vec3 center,vec3 radii,float seed) {
    vec3 q=p-center;
    float outer=sdEllipsoid(q,radii);
    if(outer>0.055)return outer;
    // Whole, thin, pointed blades replace the overlapping equal ellipsoids
    // that previously formed a tiled shell. Each layer has an independent
    // offset; individual centers, lengths, widths, yaw and pitch also vary.
    // Four neighbouring x/z cells preserve leaves across repeat boundaries.
    const float horizontalPitch=0.092;
    const float verticalPitch=0.080;
    float layer=floor(q.y/verticalPitch);
    vec2 stagger=(vec2(hash31(vec3(layer,seed,7.0)),
                       hash31(vec3(layer,seed,29.0)))-0.5)*0.074;
    vec2 grid=(q.xz+stagger)/horizontalPitch;
    vec2 base=floor(grid-0.5);
    float leaflet=100.0;
    for(int iz=0;iz<2;iz++)for(int ix=0;ix<2;ix++) {
        vec3 cell=vec3(base.x+float(ix),layer,base.y+float(iz));
        float h0=hash31(cell+vec3(seed,2.7,19.1));
        float h1=hash31(cell+vec3(11.7,seed,3.4));
        float h2=hash31(cell+vec3(7.3,25.1,seed));
        vec3 site=(cell+0.5)*vec3(horizontalPitch,verticalPitch,horizontalPitch);
        site.xz-=stagger;
        site+=vec3((h0-0.5)*0.054,(h2-0.5)*0.012,(h1-0.5)*0.054);
        vec3 leaf=q-site;
        leaf.xz=rotation(h0*TAU+seed)*leaf.xz;
        leaf.xy=rotation((h2-0.5)*1.10)*leaf.xy;
        float leafLength=0.029+0.012*h1;
        float leafWidth=leafLength*(0.32+0.16*h2);
        // Intersection of two circles makes a lenticular blade with pointed
        // tips, unlike a flattened oval. A shallow fold produces a midrib.
        float radius=(leafLength*leafLength+leafWidth*leafWidth)/(2.0*leafWidth);
        float outline=length(vec2(leaf.x,abs(leaf.z)+radius-leafWidth))-radius;
        float fold=0.003*pow(leaf.x/leafLength,2.0)+0.0015*abs(leaf.z/leafWidth);
        float blade=max(outline,abs(leaf.y+fold)-(0.0018+0.0010*h0));
        leaflet=min(leaflet,blade);
    }
    // Every blade stays at least0.0055 inside its y-layer. The positive
    // boundary cap safely crosses into the next layer without creating a
    // false plane;0.018 also bounds the reach of omitted horizontal cells.
    float layerBoundary=min(fract(q.y/verticalPitch),1.0-fract(q.y/verticalPitch))*verticalPitch;
    leaflet=min(leaflet,min(0.018,layerBoundary+0.0055));
    return max(outer,leaflet)*0.62;
}
vec3 forestModule(vec3 p) {
    vec3 d=moduleBase(p,6);
    p.xz=rotation(PI*0.5)*p.xz;
    vec3 bowl=p-vec3(0,0.73,0);
    float pot=max(sdCylinder(bowl,vec2(0.70,0.13)),-sdCylinder(bowl-vec3(0,0.07,0),vec2(0.60,0.12)));
    d=closerScene(d,vec3(pot-0.018,7,6));
    d=closerScene(d,vec3(sdBand(bowl-vec3(0,0.105,0),0.685,0.025,0.035,0.009),3,6));
    float soil=max(abs(p.y-0.82)-0.025,length(p.xz)-0.60);
    d=closerScene(d,vec3(soil,14,6));
    // Tapered, connected trunk and branches: there is a tree under the canopy.
    float trunk=taperedBranch(p,vec3(0,0.80,0),vec3(-0.18,1.26,0.06),0.12,0.095);
    trunk=smoothUnion(trunk,taperedBranch(p,vec3(-0.18,1.26,0.06),vec3(0.08,1.76,-0.03),0.095,0.060),0.045);
    trunk=smoothUnion(trunk,taperedBranch(p,vec3(0.08,1.76,-0.03),vec3(-0.10,2.25,0.05),0.060,0.027),0.035);
    trunk=min(trunk,taperedBranch(p,vec3(-0.12,1.42,0.04),vec3(-0.60,1.73,0.17),0.067,0.025));
    trunk=min(trunk,taperedBranch(p,vec3(0.05,1.75,-0.03),vec3(0.58,1.97,-0.18),0.050,0.020));
    trunk=min(trunk,taperedBranch(p,vec3(-0.01,1.99,0.00),vec3(-0.34,2.13,-0.35),0.038,0.014));
    trunk=min(trunk,taperedBranch(p,vec3(-0.13,1.42,0.04),vec3(0.26,1.61,0.43),0.048,0.019));
    trunk=min(trunk,taperedBranch(p,vec3(-0.15,1.56,0.07),vec3(-0.54,1.58,-0.32),0.039,0.013));
    trunk+=(noise3(p*vec3(48.0,5.0,48.0))-0.5)*0.008;
    d=closerScene(d,vec3(trunk*0.85,12,6));
    float leaves=foliageCluster(p,vec3(-0.62,1.82,0.18),vec3(0.40,0.22,0.34),6.0);
    leaves=min(leaves,foliageCluster(p,vec3(0.57,2.05,-0.18),vec3(0.38,0.25,0.32),13.0));
    leaves=min(leaves,foliageCluster(p,vec3(-0.11,2.38,0.04),vec3(0.43,0.29,0.34),21.0));
    leaves=min(leaves,foliageCluster(p,vec3(-0.38,2.19,-0.33),vec3(0.28,0.20,0.27),31.0));
    leaves=min(leaves,foliageCluster(p,vec3(0.30,1.70,0.43),vec3(0.34,0.21,0.28),44.0));
    leaves=min(leaves,foliageCluster(p,vec3(-0.55,1.67,-0.33),vec3(0.30,0.17,0.26),51.0));
    d=closerScene(d,vec3(leaves,13,6));
    // Exposed radial roots anchor the bonsai instead of floating above soil.
    vec3 root=polarFold(p-vec3(0,0.86,0),5.0);
    d=closerScene(d,vec3(taperedBranch(root,vec3(0,0,0),vec3(0.40,-0.035,0),0.065,0.014),12,6));
    return d;
}

vec3 coreInstrument(vec3 p) {
    vec3 d=vec3(sdCylinder(p-vec3(0,0.48,0),vec2(0.83,0.13))-0.025,3,7);
    d=closerScene(d,vec3(sdCylinder(p-vec3(0,0.74,0),vec2(0.62,0.14))-0.022,2,7));
    d=closerScene(d,vec3(sdBand(p-vec3(0,0.88,0),0.61,0.035,0.025,0.01),4,7));
    // An axial optical stack with warm ring illumination and a glass crown.
    d=closerScene(d,vec3(sdCylinder(p-vec3(0,1.25,0),vec2(0.38,0.40))-0.022,2,7));
    vec3 fins=p;fins.y=mod(fins.y-0.97,0.095)-0.0475;
    float fin=max(sdCylinder(fins,vec2(0.48,0.017))-0.007,max(0.92-p.y,p.y-1.54));
    d=closerScene(d,vec3(fin,3,7));
    d=closerScene(d,vec3(sdCylinder(p-vec3(0,1.68,0),vec2(0.62,0.087))-0.025,4,7));
    d=closerScene(d,vec3(sdBand(p-vec3(0,1.80,0),0.53,0.025,0.018,0.006),20,7));
    vec3 guard=p-vec3(0,2.32,0);guard.yz=rotation(0.55)*guard.yz;
    guard.xy=rotation(0.15*sin(clockTime*0.15))*guard.xy;
    d=closerScene(d,vec3(sdBand(guard,0.63,0.031,0.047,0.011),3,7));
    vec3 spar=polarFold(p,3.0);
    d=closerScene(d,vec3(sdCapsule(spar,vec3(0.53,1.70,0),vec3(0.53,2.72,0),0.030),4,7));
    d=closerScene(d,vec3(sdBand(p-vec3(0,2.76,0),0.54,0.041,0.038,0.009),2,7));
    vec3 coreBolts=polarFold(p,12.0)-vec3(0.73,0.64,0);
    d=closerScene(d,vec3(socketBolt(coreBolts,0.030,0.016),4,7));
    // An octagonal mechanical aperture under the glass crown.
    vec3 iris=p-vec3(0,1.82,0);iris.xz=rotation(clockTime*0.07)*iris.xz;
    iris=polarFold(iris,9.0)-vec3(0.28,0,0);iris.xz=rotation(0.55)*iris.xz;
    d=closerScene(d,vec3(sdRoundBox(iris,vec3(0.19,0.014,0.07),0.008),3,7));
    return d;
}

vec3 makerPlate(vec3 p) {
    vec3 q=p-vec3(0,0.42,3.96);
    q.xy=rotation(0.0)*q.xy;
    q.yz=rotation(-0.20)*q.yz;
    vec3 d=vec3(sdRoundBox(q,vec3(0.62,0.025,0.19),0.027),18,8);
    vec3 rivet=q;rivet.x=abs(rivet.x)-0.52;rivet.z=abs(rivet.z)-0.115;
    d=closerScene(d,vec3(socketBolt(rivet-vec3(0,0.04,0),0.025,0.010),4,8));
    return d;
}

vec4 glassSphere(int i) {
    if(i==0)return vec4(moduleCenter(1)+vec3(0,1.67,0),0.64);
    return vec4(0,2.32,0,0.44);
}

vec3 mapScene(vec3 p) {
    // Bounding distances are conservative advances only. Geometry is always
    // evaluated inside a 0.055 margin, preventing boxes from becoming surfaces.
    vec3 d=vec3(p.y+0.18,1,0);
    float allBound=sdBox(p-vec3(0,1.35,0),vec3(4.60,1.55,4.60));
    if(allBound>0.10)return closerScene(d,vec3(allBound,2.125,0));
    float chassisBound=sdCylinder(p-vec3(0,0.16,0),vec2(4.55,0.35));
    if(chassisBound<d.x) {
        d=closerScene(d,chassisBound>0.06?vec3(chassisBound,2.125,0):chassis(p));
    }
    float coreBound=sdCylinder(p-vec3(0,1.60,0),vec2(0.94,1.28));
    if(coreBound<d.x)d=closerScene(d,coreBound>0.06?vec3(coreBound,2.125,7):coreInstrument(p));
    float plateBound=sdBox(p-vec3(0,0.45,3.96),vec3(0.70,0.14,0.25));
    if(plateBound<d.x)d=closerScene(d,plateBound>0.06?vec3(plateBound,18.125,8):makerPlate(p));
    // The module cylinders are disjoint (3.15 between centers, diameter2.18).
    // Select the nearest bound with cheap distances, then evaluate exactly one
    // complex mechanism. The second bound remains a conservative advance in
    // empty parts of the nearest cylinder. This avoids six inlined copies of
    // the whole mechanism dispatch inside every transport/normal/shadow path.
    float bestBound=100.0,secondBound=100.0;
    int nearestModule=1;
    for(int i=1;i<=6;i++) {
        vec3 q=p-moduleCenter(i)-vec3(0,1.47,0);
        float bound=sdCylinder(q,vec2(1.09,1.20));
        if(bound<bestBound){secondBound=bestBound;bestBound=bound;nearestModule=i;}
        else secondBound=min(secondBound,bound);
    }
    d=closerScene(d,vec3(secondBound,2.125,0));
    if(bestBound<d.x) {
        if(bestBound>0.055)d=closerScene(d,vec3(bestBound,2.125,float(nearestModule)));
        else {
            vec3 q=moduleLocal(p,nearestModule),object;
            if(nearestModule==1)object=opticsModule(q);
            else if(nearestModule==2)object=rotorModule(q);
            else if(nearestModule==3)object=landscapeModule(q);
            else if(nearestModule==4)object=elementsModule(q);
            else if(nearestModule==5)object=materialsModule(q);
            else object=forestModule(q);
            d=closerScene(d,object);
        }
    }
    return d;
}

struct Surface {vec3 base;float rough;float metal;vec3 emission;};

float lavaFissures(vec3 p) {
    vec2 q=p.xz*8.5;
    q+=vec2(noise3(p*3.0+clockTime*0.035),noise3(p*3.0+17.0))*0.7;
    vec2 cell=floor(q),f=fract(q);
    float nearest=8.0,second=8.0;
    for(int j=-1;j<=1;j++)for(int i=-1;i<=1;i++) {
        vec2 g=vec2(i,j),site=g+0.22+0.56*vec2(hash31(vec3(cell+g,3)),hash31(vec3(cell+g,21)))-f;
        float d=dot(site,site);
        if(d<nearest){second=nearest;nearest=d;}else second=min(second,d);
    }
    return sqrt(second)-sqrt(nearest);
}

Surface surfaceAt(vec3 p,vec3 n,float materialId) {
    Surface m;m.base=vec3(0.12);m.rough=0.4;m.metal=0.0;m.emission=vec3(0);
    int id=int(materialId+0.5);
    if(id==1) {
        float broad=noise3(p*1.6),fine=noise3(p*9.0);
        m.base=mix(vec3(0.030,0.038,0.043),vec3(0.040,0.047,0.051),broad);
        m.rough=0.50+0.030*fine;
    } else if(id==2) {
        m.base=vec3(0.029,0.038,0.043)*(0.97+0.06*noise3(p*11.0));
        m.rough=0.365+0.020*noise3(p*7.0);m.metal=0.66;
    } else if(id==3) {
        float brushed=noise3(p*vec3(38.0,1.8,38.0));
        m.base=mix(vec3(0.47,0.30,0.145),vec3(0.56,0.39,0.205),noise3(p*2.7));
        m.rough=0.30+0.025*brushed;m.metal=0.94;
    } else if(id==4) {
        m.base=vec3(0.61,0.66,0.68);m.rough=0.25+0.022*noise3(p*18.0);m.metal=1.0;
    } else if(id==5) {
        vec3 q=moduleLocal(p,5);
        q.xz=rotation(PI*0.5)*q.xz;
        float flow=q.y*2.9+q.x*3.6+q.z*2.1+fbm3(q*3.2)*1.6;
        float vein=pow(1.0-abs(sin(flow)),25.0);
        m.base=mix(vec3(0.70,0.715,0.655),vec3(0.11,0.15,0.16),vein*0.68);
        m.base*=0.96+0.08*noise3(q*24.0);m.rough=0.24;
    } else if(id==6) {
        vec3 q=moduleLocal(p,5);
        q.xz=rotation(PI*0.5)*q.xz;
        q-=vec3(0.10,1.34,-0.27);
        q.xz=rotation(0.10)*q.xz;
        float radius=length((q.xz+vec2(1.3,0.4))*vec2(0.75,1.0));
        float warp=noise3(q*vec3(4,0.7,4))*0.025;
        float grain=pow(0.5+0.5*sin((radius+warp)*115.0),6.0);
        float body=noise3(q*vec3(7,0.75,7));
        m.base=mix(vec3(0.070,0.026,0.010),vec3(0.26,0.125,0.049),body);
        m.base*=0.97-0.17*grain;m.rough=0.37+0.06*grain;
    } else if(id==7) {
        m.base=vec3(0.70,0.69,0.60)*(0.98+0.035*noise3(p*18.0));m.rough=0.22;
    } else if(id==8) {
        float grain=noise3(p*35.0);
        m.base=mix(vec3(0.022,0.026,0.028),vec3(0.055,0.058,0.057),grain);m.rough=0.73;
    } else if(id==9) {
        vec3 q=moduleLocal(p,4);
        q.xz=rotation(PI*0.5)*q.xz;
        float fissure=lavaFissures(q);
        float crack=1.0-smoothstep(0.018,0.10,fissure);
        float hot=1.0-smoothstep(0.0,0.027,fissure);
        m.base=vec3(0.040,0.024,0.016);m.rough=0.61;
        m.emission=vec3(4.8,0.55,0.018)*crack+vec3(3.5,1.12,0.08)*hot;
    } else if(id==10) {
        m.base=vec3(0.022,0.15,0.145);m.rough=0.075;m.metal=0.38;
    } else if(id==11) {
        float grain=fbm3(p*12.0);
        m.base=mix(vec3(0.25,0.14,0.072),vec3(0.60,0.40,0.22),grain);m.rough=0.81;
    } else if(id==12) {
        vec3 q=moduleLocal(p,6);
        q.xz=rotation(PI*0.5)*q.xz;
        float stripe=noise3(q*vec3(37.0,3.1,37.0));
        stripe=0.65*stripe+0.35*noise3(q*vec3(11.0,1.8,11.0));
        m.base=mix(vec3(0.060,0.029,0.012),vec3(0.135,0.075,0.029),stripe);m.rough=0.85;
    } else if(id==13) {
        // Continuous pigmentation avoids cutting one physical leaflet into
        // unrelated bright/dark tiles with a second world-space voxel grid.
        float leaf=fbm3(p*7.0);
        m.base=mix(vec3(0.023,0.069,0.009),vec3(0.077,0.165,0.023),leaf);
        m.rough=0.60;
    } else if(id==14) {
        m.base=mix(vec3(0.022,0.033,0.008),vec3(0.083,0.13,0.023),noise3(p*43.0));m.rough=0.91;
    } else if(id==15) {
        m.base=vec3(0.46,0.21,0.07);m.emission=vec3(3.5,1.1,0.19);m.rough=0.3;
    } else if(id==16) {
        float warp=0.5+0.5*sin(p.x*150.0)*sin(p.z*150.0);
        float weaveFilter=1.0/(1.0+max(pixelFootprint,0.0)*150.0*8.0);
        warp=mix(0.5,warp,weaveFilter);
        m.base=mix(vec3(0.016,0.022,0.024),vec3(0.029,0.037,0.040),warp);
        m.rough=0.44;m.metal=0.22;
    } else if(id==17) {
        m.base=vec3(0.65,0.27,0.12);m.rough=0.25;m.metal=1.0;
    } else if(id==18) {
        m.base=vec3(0.36,0.25,0.13);m.rough=0.28;m.metal=0.92;
    } else if(id==19) {
        m.base=vec3(0.015,0.07,0.095);m.rough=0.21;m.metal=0.20;
    } else if(id==20) {
        m.base=vec3(0.65,0.58,0.39);m.emission=vec3(2.0,1.65,0.92);m.rough=0.22;
    }
    return m;
}

vec3 detailNormal(vec3 p,vec3 n,float materialId) {
    int id=int(materialId+0.5);
    if(id==4||id==7||id==15||id==18||id==19||id==20)return n;
    float frequency=id==1?9.0:(id==11?39.0:(id==8?45.0:32.0));
    float amount=id==11?0.11:(id==8?0.095:(id==12?0.12:0.018));
    if(id==1)amount=0.006;
    if(id==2){frequency=26.0;amount=0.003;}
    if(id==3){frequency=38.0;amount=0.003;}
    if(id==10){frequency=13.0;amount=0.030;}
    if(id==13)return n;
    vec3 tangent=normalize(cross(n,abs(n.y)<0.9?vec3(0,1,0):vec3(1,0,0)));
    vec3 bitangent=cross(n,tangent);
    vec3 q=p*frequency;
    if(id==10)q+=vec3(clockTime*0.2,0,-clockTime*0.15);
    float base=noise3(q);
    float stepSize=0.11;
    vec2 gradient=vec2(noise3(q+tangent*stepSize)-base,noise3(q+bitangent*stepSize)-base)/stepSize;
    float filterWeight=1.0/(1.0+max(pixelFootprint,0.0)*frequency*2.0);
    return normalize(n-(tangent*gradient.x+bitangent*gradient.y)*amount*filterWeight);
}
