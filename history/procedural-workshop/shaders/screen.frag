#version 300 es
precision highp float;
precision highp int;
const float PI=3.141592653589793;const float TAU=6.283185307179586;
uniform vec2 u_resolution;uniform float u_time;uniform float u_chapter;uniform float u_exposure;
uniform vec3 u_camera_origin,u_camera_forward,u_camera_right,u_camera_up,u_camera_lens;
float clockTime;float pixelFootprint;
mat2 rotation(float a) {
    float c=cos(a), s=sin(a);
    return mat2(c,-s,s,c);
}

float hash31(vec3 p) {
    p=fract(p*0.1031);
    p+=dot(p,p.yzx+33.33);
    return fract((p.x+p.y)*p.z);
}

uniform highp sampler3D u_noise_lattice;
float noise3(vec3 p) {vec3 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);return textureLod(u_noise_lattice,(i+f+.5)/64.,0.).r;}

float fbm3(vec3 p) {
    return noise3(p)*0.57+noise3(p*2.03+7.1)*0.28
         + noise3(p*4.07+13.4)*0.15;
}

vec2 moduleAxis(int id) {
    if (id == 1) return vec2(-0.5, 0.8660254037844386);
    if (id == 2) return vec2(0.5, 0.8660254037844386);
    if (id == 3) return vec2(1.0, 0.0);
    if (id == 4) return vec2(0.5, -0.8660254037844386);
    if (id == 5) return vec2(-0.5, -0.8660254037844386);
    if (id == 6) return vec2(-1.0, 0.0);
    return vec2(1.0, 0.0);
}

vec3 moduleCenter(int objectId) {
    if (objectId < 1 || objectId > 6) return vec3(0.0);
    vec2 axis = moduleAxis(objectId);
    return vec3(axis.x * 3.15, 0.0, axis.y * 3.15);
}

vec3 moduleLocal(vec3 p, int objectId) {
    vec3 q = p - moduleCenter(objectId);
    vec2 axis = moduleAxis(objectId);
    q.xz = vec2(dot(q.xz, axis), dot(q.xz, vec2(-axis.y, axis.x)));
    return q;
}

vec3 moduleWorld(vec3 p, int objectId) {
    vec2 axis = moduleAxis(objectId);
    p.xz = vec2(dot(p.xz, vec2(axis.x, -axis.y)), dot(p.xz, vec2(axis.y, axis.x)));
    return p + moduleCenter(objectId);
}

uniform highp sampler2D u_scene,u_depth;uniform vec4 u_mouse;uniform float u_render_mode,u_playback,u_fps,u_gpu_ms,u_rt_mode,u_interaction;
out vec4 fragColor;
uniform highp samplerCube u_environment;
vec3 studioEnvironment(vec3 r,float rough){vec3 c=textureLod(u_environment,r,rough*9.).rgb;float room=.12+.17*smoothstep(-.6,.8,r.y);return c+vec3(room*1.02,room,room*.98);}
vec3 viewBackground(vec3 r){return mix(vec3(.037,.041,.045),vec3(.023,.026,.030),smoothstep(-.12,.8,r.y));}




vec3 schlick(float cosine, vec3 f0) {
    float grazing = pow(clamp(1.0 - cosine, 0.0, 1.0), 5.0);
    return f0 + (1.0 - f0) * grazing;
}
vec2 raySphere(vec3 ro, vec3 rd, vec3 center, float radius) {
    vec3 oc = ro - center;
    float b = dot(oc, rd);
    float disc = b * b - dot(oc, oc) + radius * radius;
    if (disc < 0.0) return vec2(-1.0);
    float h = sqrt(disc);
    return vec2(-b - h, -b + h);
}

vec2 rayBounds(vec3 ro, vec3 rd, vec3 lo, vec3 hi) {
    vec3 inverseRay = 1.0 / ((step(vec3(0.0), rd) * 2.0 - 1.0) * max(abs(rd), vec3(0.00001)));
    vec3 a = (lo - ro) * inverseRay;
    vec3 b = (hi - ro) * inverseRay;
    vec3 nearT = min(a, b);
    vec3 farT = max(a, b);
    return vec2(max(nearT.x, max(nearT.y, nearT.z)),
                min(farT.x, min(farT.y, farT.z)));
}

uniform highp sampler2DArray u_flame;
vec2 flameSlice(vec3 q,float frame){
    float z=clamp(q.z*31.,0.,31.),iz=floor(z);
    vec2 xy=vec2(clamp(q.x*32.,.5,31.5),clamp(q.y*64.,.5,63.5));
    vec2 a=(vec2(mod(iz,8.)*32.,floor(iz/8.)*64.)+xy)/256.;
    float next=min(iz+1.,31.);vec2 b=(vec2(mod(next,8.)*32.,floor(next/8.)*64.)+xy)/256.;
    return mix(texture(u_flame,vec3(a,frame)).rg,texture(u_flame,vec3(b,frame)).rg,fract(z));
}
vec2 sampledFlame(vec3 p){
    vec3 q=vec3(p.x/.90+.5,(p.y+.125)/2.8,p.z/.90+.5);
    if(any(lessThan(q,vec3(0)))||any(greaterThan(q,vec3(1))))return vec2(0);
    vec3 flow=q*vec3(15.,9.,15.)-vec3(0,clockTime*1.7,0);
    q.xz+=(vec2(noise3(flow),noise3(flow+37.))-.5)*.040;
    float t=mod(clockTime/7.92*48.,48.),i=floor(t);
    return mix(flameSlice(q,i),flameSlice(q,mod(i+1.,48.)),fract(t));
}
float flameDensity(vec3 p){
 float h=p.y;if(h<0.||h>1.02)return 0.;
 vec3 adv=p*vec3(7.0,5.8,7.0)-vec3(0,clockTime*2.45,0);
 vec3 warp=vec3(noise3(adv+17.),noise3(adv+47.),noise3(adv+93.))-.5;
 p+=warp*vec3(.17,.05,.17)*(.30+h);
 float turbulence=noise3(adv*1.7)*.72+noise3(adv*3.6+7.)*.23+noise3(adv*6.1-5.)*.05;
 float density=0.;
 for(int j=0;j<4;j++){
  float k=float(j),hh=.66+.22*sin(k*2.9+clockTime*.52);
  vec2 origin=vec2(sin(k*2.3),cos(k*2.3))*.105;
  origin+=vec2(sin(h*7.-clockTime*1.4+k),cos(h*6.+clockTime*.86-k))*(.008+h*.073);
  float radius=.143*pow(max(0.,1.-h/hh),.68)+.004;
  float boundary=length(p.xz-origin*(1.-h*.4))/radius;
  boundary+=(turbulence-.5)*1.72;
  float sheet=exp(-pow((boundary-.72)*4.2,2.));
  float rupture=smoothstep(.13,.29,turbulence+h*.10);
  density=max(density,sheet*rupture*(1.-smoothstep(hh*.72,hh,h)));
 }
 return density*smoothstep(0.,.025,h)*(1.-smoothstep(.72,1.02,h));
}

vec3 integrateFlame(vec3 color, vec3 ro, vec3 rd, float surfaceT) {
    vec3 center = moduleCenter(4) + vec3(0.0, .96, 0.0);
    vec2 range = rayBounds(ro - center, rd, vec3(-0.50, 0.0, -0.50), vec3(0.50, 1.02, 0.50));
    float start = max(range.x, 0.0);
    float end = min(range.y, surfaceT);
    if (end <= start) return color;
    float flameSamples = 40.0;
    float stride = (end - start) / flameSamples;
    vec3 emission = vec3(0.0);
    float transmittance = 1.0;
    for (int i = 0; i < 40; ++i) {
        if (float(i) >= flameSamples) break;
        float t = start + (float(i) + 0.5) * stride;
        vec3 local = ro + rd * t - center;
        vec2 field=sampledFlame(local);
        // The resolved flow controls intensity/heat; thin sub-grid reaction
        // sheets remain analytic so the coarse volume is not a blurry blob.
        float density = flameDensity(local)*(.72+.55*field.y);
        float opacity = 1.0 - exp(-density * stride * 2.3);
        float heat = clamp(density*.98+(1.1-local.y)*.21+field.x*.23,0.,1.);
        vec3 temperature = mix(vec3(1.8,0.12,0.008),vec3(7.5,3.45,.72),pow(heat,2.3));
        emission += transmittance * opacity * temperature;
        transmittance *= 1.0 - opacity;
    }
    return color * transmittance + emission;
}
// CYBR / analytic typography. All marks are distance fields; no font atlas.
// Logical height: 900. Source rect: [W-124,W-28] x [826,876].
// Navigation: [28,W-28] x [20,70], eight equal cells.
// About links: [28,178] and [194,374] x [106,146] on desktop.
// On portrait, split the width evenly with 16 units between the links.

float ufSegment(vec2 p, vec2 a, vec2 b) {
    vec2 q = p-a, v = b-a;
    return length(q-v*clamp(dot(q,v)/dot(v,v),0.0,1.0));
}

float ufOval(vec2 p, vec2 center, vec2 radii) {
    vec2 q = p-center;
    float k0 = length(q/radii);
    float k1 = length(q/(radii*radii));
    if(k1<0.00001) return min(radii.x,radii.y);
    return abs(k0*(k0-1.0)/k1);
}

float ufArc(vec2 p, vec2 center, vec2 radii, float cutX, float cutY, bool rightOpening) {
    float d = ufOval(p,center,radii);
    float cut = min(rightOpening ? p.x-cutX : cutX-p.x, cutY-abs(p.y-center.y));
    return max(d,cut);
}

// Geometric grotesk: the proportional layout table controls spacing; weight
// is applied separately so the same outlines serve captions and display text.
float ufGlyph(vec2 p, int c) {
    float d=20.0;
    vec2 bl=vec2(0.055,0.035), tl=vec2(0.055,0.965);
    vec2 br=vec2(0.525,0.035), tr=vec2(0.525,0.965);
    vec2 ml=vec2(0.055,0.50), mr=vec2(0.525,0.50);
    if(c==65) { // A
        d=min(ufSegment(p,bl,vec2(0.29,0.965)),ufSegment(p,vec2(0.29,0.965),br));
        d=min(d,ufSegment(p,vec2(0.14,0.37),vec2(0.44,0.37)));
    } else if(c==66) { // B
        d=ufSegment(p,bl,tl);
        float a=max(ufOval(p,vec2(0.24,0.735),vec2(0.26,0.23)),0.24-p.x);
        float b=max(ufOval(p,vec2(0.25,0.27),vec2(0.28,0.235)),0.25-p.x);
        d=min(d,min(a,b));
        d=min(d,min(ufSegment(p,tl,vec2(0.24,0.965)),ufSegment(p,ml,vec2(0.25,0.50))));
        d=min(d,ufSegment(p,bl,vec2(0.25,0.035)));
    } else if(c==67) { // C
        d=ufArc(p,vec2(0.29,0.50),vec2(0.25,0.465),0.40,0.27,true);
    } else if(c==68) { // D
        d=min(ufSegment(p,bl,tl),max(ufOval(p,vec2(0.19,0.50),vec2(0.35,0.465)),0.19-p.x));
        d=min(d,min(ufSegment(p,tl,vec2(0.19,0.965)),ufSegment(p,bl,vec2(0.19,0.035))));
    } else if(c==69) { // E
        d=min(ufSegment(p,bl,tl),min(ufSegment(p,tl,tr),ufSegment(p,bl,br)));
        d=min(d,ufSegment(p,ml,vec2(0.46,0.50)));
    } else if(c==70) { // F
        d=min(ufSegment(p,bl,tl),ufSegment(p,tl,tr));
        d=min(d,ufSegment(p,ml,vec2(0.46,0.50)));
    } else if(c==71) { // G
        d=ufArc(p,vec2(0.29,0.50),vec2(0.25,0.465),0.40,0.27,true);
        d=min(d,ufSegment(p,vec2(0.54,0.48),vec2(0.54,0.16)));
        d=min(d,ufSegment(p,vec2(0.32,0.48),vec2(0.54,0.48)));
    } else if(c==72) { // H
        d=min(ufSegment(p,bl,tl),min(ufSegment(p,br,tr),ufSegment(p,ml,mr)));
    } else if(c==73) { // I
        d=ufSegment(p,vec2(0.29,0.035),vec2(0.29,0.965));
    } else if(c==74) { // J
        d=ufSegment(p,vec2(0.51,0.965),vec2(0.51,0.27));
        d=min(d,max(ufOval(p,vec2(0.28,0.27),vec2(0.23,0.235)),p.y-0.27));
        d=min(d,ufSegment(p,vec2(0.05,0.27),vec2(0.05,0.34)));
    } else if(c==75) { // K
        d=min(ufSegment(p,bl,tl),ufSegment(p,ml,tr));
        d=min(d,ufSegment(p,vec2(0.235,0.68),br));
    } else if(c==76) { // L
        d=min(ufSegment(p,bl,tl),ufSegment(p,bl,br));
    } else if(c==77) { // M
        d=min(ufSegment(p,bl,tl),ufSegment(p,br,tr));
        d=min(d,min(ufSegment(p,tl,vec2(0.29,0.40)),ufSegment(p,vec2(0.29,0.40),tr)));
    } else if(c==78) { // N
        d=min(ufSegment(p,bl,tl),min(ufSegment(p,br,tr),ufSegment(p,tl,br)));
    } else if(c==79) { // O
        d=ufOval(p,vec2(0.29,0.50),vec2(0.25,0.465));
    } else if(c==80 || c==82) { // P / R
        d=min(ufSegment(p,bl,tl),max(ufOval(p,vec2(0.24,0.73),vec2(0.285,0.235)),0.24-p.x));
        d=min(d,min(ufSegment(p,tl,vec2(0.24,0.965)),ufSegment(p,vec2(0.055,0.495),vec2(0.24,0.495))));
        if(c==82) d=min(d,ufSegment(p,vec2(0.26,0.495),br));
    } else if(c==81) { // Q
        d=ufOval(p,vec2(0.29,0.50),vec2(0.25,0.465));
        d=min(d,ufSegment(p,vec2(0.34,0.23),vec2(0.60,-0.045)));
    } else if(c==83) { // S
        float a=max(ufOval(p,vec2(0.29,0.735),vec2(0.25,0.23)),min(p.x-0.29,0.735-p.y));
        float b=max(ufOval(p,vec2(0.29,0.265),vec2(0.25,0.23)),min(0.29-p.x,p.y-0.265));
        d=min(a,b);
        d=min(d,ufSegment(p,vec2(0.29,0.505),vec2(0.29,0.495)));
    } else if(c==84) { // T
        d=min(ufSegment(p,tl,tr),ufSegment(p,vec2(0.29,0.035),vec2(0.29,0.965)));
    } else if(c==85) { // U
        d=min(ufSegment(p,tl,vec2(0.055,0.27)),ufSegment(p,tr,vec2(0.525,0.27)));
        d=min(d,max(ufOval(p,vec2(0.29,0.27),vec2(0.235,0.235)),p.y-0.27));
    } else if(c==86) { // V
        d=min(ufSegment(p,tl,vec2(0.29,0.035)),ufSegment(p,vec2(0.29,0.035),tr));
    } else if(c==87) { // W
        d=min(ufSegment(p,tl,vec2(0.14,0.035)),ufSegment(p,vec2(0.44,0.035),tr));
        d=min(d,min(ufSegment(p,vec2(0.14,0.035),vec2(0.29,0.60)),ufSegment(p,vec2(0.29,0.60),vec2(0.44,0.035))));
    } else if(c==88) { // X
        d=min(ufSegment(p,bl,tr),ufSegment(p,tl,br));
    } else if(c==89) { // Y
        d=min(ufSegment(p,tl,vec2(0.29,0.49)),ufSegment(p,vec2(0.29,0.49),tr));
        d=min(d,ufSegment(p,vec2(0.29,0.49),vec2(0.29,0.035)));
    } else if(c==90) { // Z
        d=min(ufSegment(p,tl,tr),min(ufSegment(p,bl,tr),ufSegment(p,bl,br)));
    } else if(c==48) { // 0
        d=ufOval(p,vec2(0.29,0.50),vec2(0.24,0.465));
        d=min(d,ufSegment(p,vec2(0.12,0.18),vec2(0.46,0.82)));
    } else if(c==49) { // 1
        d=ufSegment(p,vec2(0.31,0.035),vec2(0.31,0.965));
        d=min(d,ufSegment(p,vec2(0.12,0.78),vec2(0.31,0.965)));
    } else if(c==50) { // 2
        d=max(ufOval(p,vec2(0.29,0.74),vec2(0.24,0.225)),0.70-p.y);
        d=min(d,ufSegment(p,vec2(0.52,0.69),vec2(0.055,0.035)));
        d=min(d,ufSegment(p,bl,br));
    } else if(c==51) { // 3
        d=max(ufOval(p,vec2(0.26,0.735),vec2(0.265,0.23)),0.24-p.x);
        d=min(d,max(ufOval(p,vec2(0.26,0.27),vec2(0.265,0.235)),0.24-p.x));
        d=min(d,min(ufSegment(p,vec2(0.08,0.965),vec2(0.26,0.965)),ufSegment(p,vec2(0.24,0.50),vec2(0.33,0.50))));
        d=min(d,ufSegment(p,vec2(0.08,0.035),vec2(0.26,0.035)));
    } else if(c==52) { // 4
        d=min(ufSegment(p,vec2(0.42,0.035),vec2(0.42,0.965)),ufSegment(p,vec2(0.42,0.965),vec2(0.045,0.34)));
        d=min(d,ufSegment(p,vec2(0.045,0.34),vec2(0.55,0.34)));
    } else if(c==53) { // 5
        d=min(ufSegment(p,tl,tr),ufSegment(p,tl,vec2(0.055,0.52)));
        d=min(d,ufSegment(p,vec2(0.055,0.52),vec2(0.26,0.52)));
        d=min(d,max(ufOval(p,vec2(0.26,0.275),vec2(0.265,0.24)),min(0.26-p.x,p.y-0.15)));
    } else if(c==54) { // 6
        d=ufOval(p,vec2(0.29,0.29),vec2(0.24,0.255));
        d=min(d,max(ufOval(p,vec2(0.29,0.55),vec2(0.24,0.415)),min(p.x-0.29,0.83-p.y)));
    } else if(c==55) { // 7
        d=min(ufSegment(p,tl,tr),ufSegment(p,tr,vec2(0.16,0.035)));
    } else if(c==56) { // 8
        d=min(ufOval(p,vec2(0.29,0.735),vec2(0.225,0.23)),ufOval(p,vec2(0.29,0.27),vec2(0.245,0.235)));
    } else if(c==57) { // 9
        d=ufOval(p,vec2(0.29,0.71),vec2(0.24,0.255));
        d=min(d,max(ufOval(p,vec2(0.29,0.45),vec2(0.24,0.415)),min(0.29-p.x,p.y-0.17)));
    } else if(c==46 || c==44 || c==58) { // . , :
        d=length(p-vec2(0.29,0.045))-0.012;
        if(c==44) d=min(d,ufSegment(p,vec2(0.30,0.045),vec2(0.22,-0.12)));
        if(c==58) d=min(d,length(p-vec2(0.29,0.68))-0.012);
    } else if(c==47) { // /
        d=ufSegment(p,vec2(0.085,-0.025),vec2(0.495,1.025));
    } else if(c==45 || c==43 || c==61) { // - + =
        d=ufSegment(p,vec2(0.08,0.50),vec2(0.50,0.50));
        if(c==43) d=min(d,ufSegment(p,vec2(0.29,0.29),vec2(0.29,0.71)));
        if(c==61) d=min(ufSegment(p,vec2(0.08,0.38),vec2(0.50,0.38)),ufSegment(p,vec2(0.08,0.62),vec2(0.50,0.62)));
    } else if(c==62) { // >
        d=min(ufSegment(p,vec2(0.13,0.76),vec2(0.46,0.50)),ufSegment(p,vec2(0.46,0.50),vec2(0.13,0.24)));
    }
    return d;
}


// Each uint packs a proportional x-origin (1/256 em) and an ASCII codepoint.
const uint UF_LAYOUT[1150] = uint[](67u,43353u,86594u,129874u,173056u,65u,43340u,81989u,125258u,166465u,209742u,252996u,296274u,339535u,382752u,404550u,443721u,462663u,505941u,549189u,592466u,635727u,678977u,722176u,83u,43343u,86613u,129874u,173123u,216389u,259584u,84u,43336u,86597u,129824u,151363u,194639u,237901u,283216u,326485u,369748u,412993u,456276u,499529u,518479u,561742u,604993u,648268u,686880u,708425u,727630u,770899u,814164u,857170u,900437u,943693u,988997u,1032270u,1075540u,1118720u,65u,43347u,86611u,129861u,173133u,218178u,261452u,300121u,343296u,76u,38729u,57671u,100936u,144212u,187392u,71u,43333u,86607u,129869u,175173u,218196u,261458u,304729u,347904u,83u,43331u,86597u,129870u,173125u,216403u,259584u,69u,43340u,81989u,125261u,170565u,213838u,257108u,300115u,343296u,77u,45377u,88660u,131909u,175186u,218185u,237377u,280652u,319315u,362496u,70u,39503u,82770u,126021u,169043u,212308u,255488u,65u,43330u,86607u,129877u,173140u,216320u,48u,43313u,86528u,48u,43314u,86528u,48u,43315u,86528u,48u,43316u,86528u,48u,43317u,86528u,48u,43318u,86528u,48u,43319u,86528u,48u,43320u,86528u,47u,33568u,55088u,98360u,141568u,67u,43343u,86596u,129861u,173100u,189984u,211789u,257089u,300100u,343365u,386560u,80u,43336u,86617u,129875u,173129u,192067u,235329u,278604u,317230u,334336u,71u,43346u,86593u,129872u,173128u,216393u,235331u,278611u,321838u,338976u,360531u,403785u,422733u,468053u,511308u,549953u,593236u,636489u,655439u,698702u,741934u,758816u,780627u,823897u,867155u,910420u,953669u,996941u,1042003u,1085230u,1102336u,83u,43337u,62296u,105504u,127319u,172367u,215634u,258892u,297540u,340819u,384046u,401184u,422735u,465998u,509253u,552480u,574275u,617551u,660558u,703822u,747077u,790339u,833620u,876869u,920132u,963360u,985165u,1030209u,1073475u,1116744u,1160009u,1178958u,1222213u,1265454u,1282560u,67u,43353u,86594u,129874u,173088u,194636u,233289u,252487u,295752u,339028u,381952u,76u,38729u,57671u,100936u,144212u,187424u,209236u,252498u,295745u,339022u,382035u,425296u,468559u,511826u,555092u,598272u,79u,43344u,86612u,129865u,148803u,192083u,235308u,252448u,274002u,317253u,360518u,399948u,438597u,481859u,525140u,568393u,587343u,630606u,673824u,695361u,738638u,781892u,825120u,846930u,889925u,933190u,972626u,1015873u,1059139u,1102420u,1145673u,1164623u,1207886u,1251118u,1268224u,70u,39503u,82764u,121420u,160079u,203351u,248352u,270164u,313416u,356677u,399904u,421456u,464705u,507988u,551240u,594464u,616015u,659270u,698656u,720193u,763424u,785234u,828481u,871769u,914990u,931840u,67u,43353u,86594u,129874u,173088u,194631u,237893u,281167u,324352u,80u,43346u,86607u,129859u,173125u,216388u,259669u,302930u,346177u,389452u,428064u,449607u,492869u,536143u,579405u,624709u,667988u,711250u,754521u,797696u,70u,39503u,82770u,126029u,171040u,192833u,236115u,279328u,300865u,344142u,387360u,408901u,452184u,495429u,538691u,581973u,625236u,668481u,711746u,755020u,793669u,836896u,858707u,901977u,945235u,988244u,1031493u,1074765u,1120046u,1137152u,67u,43343u,86606u,129875u,173140u,216402u,259669u,302915u,346196u,389445u,432708u,475936u,497478u,536914u,580175u,623437u,668448u,690258u,733525u,776780u,815429u,858707u,901920u,923457u,966734u,1009988u,1053216u,1074770u,1118021u,1161292u,1199937u,1243220u,1286473u,1305679u,1348686u,1391955u,1435208u,1478473u,1497680u,1540947u,1584174u,1601024u,67u,43353u,86594u,129874u,173088u,194643u,237891u,281157u,324430u,367685u,410963u,454144u,87u,45391u,88658u,131916u,170564u,213792u,235330u,278613u,321865u,340812u,379460u,422729u,441678u,484935u,528128u,76u,38721u,81998u,125252u,168531u,211779u,255041u,298320u,341573u,384851u,428076u,444960u,466771u,510036u,553298u,596565u,639811u,683092u,726101u,769362u,812613u,855891u,899104u,920897u,964174u,1007428u,1050656u,1072193u,1115476u,1158733u,1204047u,1247315u,1290576u,1333832u,1377093u,1420370u,1463365u,1506606u,1523712u,79u,43342u,86597u,129824u,151363u,194639u,237896u,281157u,324434u,367685u,410958u,454228u,497440u,519248u,562258u,605519u,648771u,692037u,735300u,778581u,821842u,865089u,908364u,946976u,968791u,1013839u,1057106u,1100364u,1139012u,1182254u,1199360u,67u,43353u,86594u,129874u,173088u,194629u,237900u,276549u,319821u,365125u,408398u,451668u,494931u,538112u,77u,45377u,88660u,131924u,175173u,218194u,261408u,283209u,302158u,345376u,367181u,412239u,455508u,498761u,517711u,560974u,604160u,70u,39497u,58450u,101701u,144940u,161824u,183639u,228673u,271956u,315205u,358482u,401696u,423489u,466766u,510020u,553248u,574797u,620111u,663372u,702036u,745285u,788558u,831776u,853325u,898625u,941908u,985157u,1028434u,1071689u,1090625u,1133900u,1172526u,1189376u,70u,39497u,58437u,101708u,140356u,183635u,226848u,248386u,291653u,334915u,378191u,421453u,466757u,509984u,531526u,570959u,614226u,657485u,702510u,719616u,67u,43353u,86594u,129874u,173088u,194637u,239937u,283220u,326469u,369746u,413001u,431937u,475212u,513875u,557056u,83u,43349u,86610u,129862u,169025u,212291u,255557u,298784u,320595u,363860u,407125u,450372u,493641u,512581u,555859u,599040u,84u,43336u,86597u,129824u,151379u,194644u,237906u,281173u,324419u,367700u,410965u,454226u,497477u,540704u,562242u,605509u,648776u,692041u,711246u,754500u,797728u,819284u,862536u,905797u,949024u,970579u,1013845u,1057106u,1100358u,1139777u,1183043u,1226309u,1269550u,1286400u,87u,45391u,88655u,131908u,175148u,192032u,213843u,257108u,300111u,343374u,386629u,429868u,447008u,468557u,513861u,557140u,600385u,643660u,682272u,703809u,747086u,790340u,833568u,855363u,898629u,941906u,985153u,1028429u,1073481u,1092675u,1135662u,1152768u,67u,43353u,86594u,129874u,173088u,194630u,234063u,277330u,320581u,363859u,407124u,450304u,76u,38729u,57686u,100937u,119886u,163143u,206368u,228179u,271449u,314707u,357972u,401221u,444493u,489555u,532736u,66u,43346u,86593u,129870u,173123u,216392u,259657u,278606u,321863u,365100u,381984u,403783u,447058u,490319u,533591u,578644u,621896u,665120u,686913u,730190u,773444u,816672u,838223u,881490u,924743u,968001u,1011278u,1054537u,1073475u,1116704u,1138502u,1177679u,1220946u,1264205u,1309486u,1326336u,84u,43336u,86597u,129824u,151363u,194639u,237901u,283216u,326476u,365125u,408408u,451657u,470612u,513881u,557088u,578633u,597838u,641107u,684361u,703300u,746565u,789792u,811347u,854601u,873549u,918864u,962124u,1000773u,1044000u,1065810u,1109077u,1152076u,1190981u,1234003u,1277230u,1294336u,65u,43340u,81989u,125258u,166465u,209742u,252996u,296274u,339535u,382720u,70u,39497u,58439u,101717u,144965u,188242u,231503u,274753u,317952u,83u,43343u,86598u,126036u,169047u,214337u,257618u,300869u,344096u,365637u,408910u,452167u,495433u,514638u,557893u,601157u,644178u,687360u,71u,43346u,86593u,129872u,173128u,216393u,235331u,278611u,321836u,338976u,360531u,403785u,422733u,468053u,511308u,549953u,593236u,636489u,655439u,698702u,741920u,763457u,806734u,849988u,893216u,915027u,958297u,1001555u,1044820u,1088069u,1131341u,1176403u,1219630u,1236736u,67u,43307u,86571u,129824u,151343u,184864u,206420u,249689u,292944u,336197u,379475u,422723u,466002u,509257u,528208u,571476u,614688u,636463u,669728u,691536u,734809u,778068u,821320u,864591u,907854u,951072u,972591u,1006112u,1027655u,1070928u,1114197u,1157376u,71u,43337u,62292u,105544u,148821u,192066u,235264u,88u,43296u,64815u,98336u,119875u,163161u,206402u,249682u,292932u,336197u,379468u,418121u,437315u,480256u,83u,43331u,86610u,129871u,173132u,211788u,250400u,271956u,315215u,358432u,380229u,423512u,466768u,510028u,548687u,591954u,635205u,678400u,83u,43351u,88649u,107600u,150853u,194080u,215636u,258895u,302112u,323909u,367192u,410448u,453708u,492367u,535634u,578629u,621824u,68u,43346u,86593u,129863u,173088u,194644u,237903u,281120u,302927u,346194u,389442u,432713u,451668u,494848u,67u,43340u,81993u,100931u,144203u,187424u,209217u,252448u,273997u,319301u,362563u,405832u,449089u,492366u,535625u,554579u,597837u,642816u,80u,43346u,86607u,129859u,173125u,216388u,259669u,302930u,346177u,389452u,428064u,449863u,493136u,536405u,579616u,601424u,644687u,687954u,731220u,774470u,813647u,856908u,895561u,914511u,957696u,66u,43349u,86601u,105548u,144196u,187465u,206414u,249671u,292896u,314708u,357960u,401221u,444448u,466004u,509263u,552527u,595788u,634451u,677664u,699476u,742472u,785729u,829012u,872224u,894018u,937301u,980553u,999500u,1038148u,1081390u,1098496u,79u,43344u,86597u,129870u,173088u,194643u,237903u,281173u,324434u,367683u,410949u,454144u,67u,43343u,86605u,131920u,175189u,218196u,261441u,304724u,347977u,367183u,410446u,453697u,496716u,535584u,557129u,576078u,619347u,662612u,705874u,749141u,792397u,837701u,880974u,924244u,967456u,988975u,1022496u,1044018u,1087280u,1130546u,1173814u,1217024u,47u,33536u,71u,43340u,82003u,125260u,163840u,78u,42561u,85332u,127817u,170582u,213061u,255488u,55u,42549u,85280u,127824u,170563u,213076u,255488u,53u,42544u,85280u,127824u,170563u,213076u,255488u,76u,42569u,85325u,127817u,170580u,213061u,255556u,298240u,67u,42581u,85331u,127828u,170575u,213069u,255488u,80u,42561u,85333u,127827u,170565u,212992u,80u,42572u,85313u,127833u,170496u);
const ivec2 UF_META[73] = ivec2[](ivec2(0,4),ivec2(5,18),ivec2(24,6),ivec2(31,28),ivec2(60,8),ivec2(69,5),ivec2(75,8),ivec2(84,6),ivec2(91,8),ivec2(100,9),ivec2(110,6),ivec2(117,5),ivec2(123,2),ivec2(126,2),ivec2(129,2),ivec2(132,2),ivec2(135,2),ivec2(138,2),ivec2(141,2),ivec2(144,2),ivec2(147,4),ivec2(152,10),ivec2(163,9),ivec2(173,30),ivec2(204,34),ivec2(239,10),ivec2(250,15),ivec2(266,34),ivec2(301,25),ivec2(327,8),ivec2(336,19),ivec2(356,29),ivec2(386,41),ivec2(428,11),ivec2(440,14),ivec2(455,38),ivec2(494,30),ivec2(525,13),ivec2(539,16),ivec2(556,32),ivec2(589,19),ivec2(609,14),ivec2(624,15),ivec2(640,33),ivec2(674,31),ivec2(706,11),ivec2(718,14),ivec2(733,35),ivec2(769,35),ivec2(805,9),ivec2(815,8),ivec2(824,17),ivec2(842,33),ivec2(876,31),ivec2(908,6),ivec2(915,13),ivec2(929,17),ivec2(947,16),ivec2(964,13),ivec2(978,17),ivec2(996,24),ivec2(1021,30),ivec2(1052,11),ivec2(1064,31),ivec2(1096,1),ivec2(1098,4),ivec2(1103,6),ivec2(1110,6),ivec2(1117,6),ivec2(1124,7),ivec2(1132,6),ivec2(1139,5),ivec2(1145,4));

float ufTextWidth(int phrase, float height, float tracking) {
    if(phrase<0) return (phrase==-1?13.0:phrase==-2?17.0:8.0)*(.65+tracking)*height*1.06;
    ivec2 meta=UF_META[phrase];
    return (float(UF_LAYOUT[meta.x+meta.y]>>8u)/256.0+float(meta.y)*tracking)*height*1.06;
}

// Resolution readout uses the same glyph evaluator, not another font pass.
int ufResolutionCharacter(int index) {
    if(index==5||index==7) return 32;
    if(index==6) return 88;
    int place=index<5?index:index-8;
    float value=index<5?u_resolution.x:u_resolution.y;
    float divisor=pow(10.0,4.0-float(place));
    if(place<4&&value<divisor) return 32;
    return 48+int(mod(floor(value/divisor),10.0));
}
// Runtime telemetry uses the same vector glyphs as the portfolio.
int ufMetricsCharacter(int index) {
    if(index==3||index==7||index==8||index==14)return 32;
    if(index==4)return 70;if(index==5)return 80;if(index==6)return 83;
    if(index==15)return 77;if(index==16)return 83;
    if(index<3) {
        if(u_fps<0.0)return 45;
        float value=floor(clamp(u_fps,0.0,999.0)+.5),divisor=pow(10.0,2.0-float(index));
        if(index<2&&value<divisor)return 32;
        return 48+int(mod(floor(value/divisor),10.0));
    }
    if(u_gpu_ms<0.0)return 45;
    if(index==12)return 46;
    float value=clamp(u_gpu_ms,0.0,999.9),divisor=pow(10.0,11.0-float(index));
    if(index==13)return 48+int(mod(floor(value*10.0),10.0));
    if(index<11&&value<divisor)return 32;
    return 48+int(mod(floor(value/divisor),10.0));
}
int ufModeCharacter(int index) {
    if(u_rt_mode<.5) { // FULL
        return index==0?70:index==1?85:index==2||index==3?76:32;
    }
    if(u_rt_mode>1.5) { // FAST
        return index==0?70:index==1?65:index==2?83:index==3?84:32;
    }
    return index==0?82:index==1?69:index==2?65:index==3?76:
           index==4?84:index==5?73:index==6?77:69;
}
float ufText(vec2 p,vec2 origin,float height,int phrase,float tracking,float weight) {
    vec2 q=(p-origin)/height; q.x/=1.06;
    if(q.y<-.17||q.y>1.12||q.x<-.10) return 0.0;
    int c=32;
    if(phrase<0) {
        float advance=.65+tracking;
        int index=int(floor(q.x/advance));
        int count=phrase==-1?13:phrase==-2?17:8;
        if(index<0||index>=count) return 0.0;
        c=phrase==-1?ufResolutionCharacter(index):phrase==-2?ufMetricsCharacter(index):ufModeCharacter(index);
        q.x-=float(index)*advance;
    } else {
        ivec2 meta=UF_META[phrase];
        float span=float(UF_LAYOUT[meta.x+meta.y]>>8u)/256.0+float(meta.y)*tracking;
        if(q.x>span) return 0.0;
        int lower=0,upper=meta.y;
        for(int k=0;k<7;k++) {
            int middle=(lower+upper)/2;
            float x=float(UF_LAYOUT[meta.x+middle]>>8u)/256.0+float(middle)*tracking;
            if(q.x>=x) lower=middle+1; else upper=middle;
        }
        int index=clamp(lower-1,0,meta.y-1);
        uint word=UF_LAYOUT[meta.x+index];
        c=int(word&255u);
        q.x-=float(word>>8u)/256.0+float(index)*tracking;
    }
    if(c==73)q.x+=.155;
    if(c==46||c==44||c==58)q.x+=.16;
    if(c==47)q.x+=.05;
    float d=ufGlyph(q,c)-weight;
    float aa=.68*900.0/(u_resolution.y*height);
    return 1.0-smoothstep(-aa,aa,d);
}

// Select the text run covering this fragment, then evaluate glyph curves once.
// The layout deliberately has disjoint text rectangles; chapter crossfades
// clear outgoing copy before incoming copy appears. Sharing the glyph call
// avoids huge compiler expansion in WebGL1/ANGLE while preserving the layout.
vec2 ufQueuedOrigin;
float ufQueuedHeight,ufQueuedTracking,ufQueuedWeight,ufQueuedOpacity;
int ufQueuedPhrase;
vec3 ufQueuedInk;
void ufPaint(inout vec3 color,vec2 p,vec2 origin,float height,int phrase,
             float tracking,float weight,vec3 ink,float opacity) {
    if(opacity<.0001)return;
    vec2 q=(p-origin)/height; q.x/=1.06;
    if(q.y<-.17||q.y>1.12||q.x<-.10)return;
    float span=ufTextWidth(phrase,1.0,tracking)/1.06;
    if(q.x>span)return;
    ufQueuedOrigin=origin;ufQueuedHeight=height;ufQueuedPhrase=phrase;
    ufQueuedTracking=tracking;ufQueuedWeight=weight;ufQueuedInk=ink;
    ufQueuedOpacity=opacity;
}

float ufFitted(int phrase,float maxHeight,float width,float tracking) {
    return min(maxHeight,width/max(ufTextWidth(phrase,1.0,tracking),.01));
}

float ufBox(vec2 p,vec2 lower,vec2 upper) {
    vec2 d=abs(p-(lower+upper)*.5)-(upper-lower)*.5;
    return length(max(d,0.0))+min(max(d.x,d.y),0.0);
}

float ufLine(vec2 p,vec2 a,vec2 b,float width) {
    float aa=.65*900.0/u_resolution.y;
    return 1.0-smoothstep(width-aa,width+aa,ufSegment(p,a,b));
}

void ufChapter(inout vec3 color,vec2 p,int chapter,float opacity,float width,bool portrait) {
    if(opacity<.0001)return;
    vec3 paper=vec3(.936,.927,.891),muted=vec3(.66,.69,.685),amber=vec3(.94,.72,.43);
    float x=portrait?28.0:36.0;
    float available=portrait?width-56.0:min(585.0,width*.48);
    float titleHeight=portrait?44.0:59.0;
    float kickerY=portrait?302.0:330.0;
    float titleY=portrait?232.0:247.0;
    float bodyY=portrait?185.0:197.0;
    int title=chapter==0?21:(chapter==7?49:25+(chapter-1)*4);
    int kicker=chapter==0?3:(chapter==7?51:26+(chapter-1)*4);
    int body=chapter==0?23:(chapter==7?52:27+(chapter-1)*4);
    float bodyH=ufFitted(body,portrait?11.6:12.0,available,.025);
    float kickerH=ufFitted(kicker,10.2,available-26.0,.085);
    color=mix(color,amber,ufLine(p,vec2(x,kickerY+4.0),vec2(x+13.0,kickerY+4.0),.65)*opacity);
    ufPaint(color,p,vec2(x+25.0,kickerY),kickerH,kicker,.085,.048,muted,opacity);
    if(chapter==0||chapter==7) {
        titleHeight=ufFitted(title,portrait?42.0:57.0,available,.012);
        float secondY=titleY-61.0;
        ufPaint(color,p,vec2(x-1.0,titleY),titleHeight,title,.012,.060,paper,opacity);
        ufPaint(color,p,vec2(x-1.0,secondY),titleHeight,title+1,.012,.060,paper,opacity);
        bodyY=portrait?145.0:149.0;
        if(chapter==7) {
            ufPaint(color,p,vec2(x,bodyY+10.0),ufFitted(53,10.6,available,.02),53,.02,.045,muted,opacity);
        } else {
            ufPaint(color,p,vec2(x,bodyY+10.0),bodyH,body,.025,.045,paper,opacity);
            ufPaint(color,p,vec2(x,bodyY-12.0),ufFitted(24,10.5,available,.028),24,.028,.043,muted,opacity);
        }
    } else {
        titleHeight=ufFitted(title,titleHeight,available,.012);
        ufPaint(color,p,vec2(x-1.0,titleY),titleHeight,title,.012,.059,paper,opacity);
        ufPaint(color,p,vec2(x,bodyY),bodyH,body,.025,.045,paper,opacity);
        ufPaint(color,p,vec2(x,bodyY-23.0),ufFitted(body+1,portrait?11.1:11.6,available,.025),body+1,.025,.043,muted,opacity);
    }
    if(chapter==7) {
        vec2 mouse=u_mouse.xy*900.0/u_resolution.y;
        for(int i=0;i<2;i++) {
            float loX=i==0?28.0:(portrait?width*.5+8.0:194.0);
            float hiX=i==0?(portrait?width*.5-8.0:178.0):(portrait?width-28.0:374.0);
            vec2 lo=vec2(loX,106.0),hi=vec2(hiX,146.0);
            bool hover=mouse.x>lo.x&&mouse.x<hi.x&&mouse.y>lo.y&&mouse.y<hi.y;
            float aa=.65*900.0/u_resolution.y;
            float edge=ufBox(p,lo,hi);
            float fill=1.0-smoothstep(-aa,aa,edge);
            float stroke=1.0-smoothstep(.4-aa,.4+aa,abs(edge));
            color=mix(color,vec3(.09,.095,.095),fill*.65*opacity);
            color=mix(color,hover?amber:muted,stroke*.45*opacity);
            ufPaint(color,p,lo+vec2(13,14),ufFitted(54+i,10.0,hi.x-lo.x-37.0,.04),54+i,.04,.044,hover?amber:paper,opacity);
            vec2 a=hi-vec2(15,20);
            float arrow=max(ufLine(p,a-vec2(3.3),a+vec2(3.3),.55),
                         max(ufLine(p,a+vec2(-3.0,3.3),a+vec2(3.3),.55),
                             ufLine(p,a+vec2(3.3,-3.0),a+vec2(3.3),.55)));
            color=mix(color,hover?amber:muted,arrow*opacity);
        }
    }
}

vec3 portfolioUI(vec3 sceneColor,vec2 fragCoord,float chapter,float time) {
    vec2 p=fragCoord*900.0/u_resolution.y;
    float width=u_resolution.x*900.0/u_resolution.y;
    bool portrait=width<760.0;
    vec3 color=sceneColor;
    ufQueuedOrigin=vec2(0.0);ufQueuedHeight=1.0;ufQueuedPhrase=0;
    ufQueuedTracking=0.0;ufQueuedWeight=0.0;ufQueuedInk=vec3(0.0);ufQueuedOpacity=0.0;
    vec3 paper=vec3(.936,.927,.891),muted=vec3(.55,.60,.59),amber=vec3(.94,.72,.43);
    vec2 mouse=u_mouse.xy*900.0/u_resolution.y;
    float progress=clamp(chapter,0.0,7.0);
    float side=1.0-smoothstep(portrait?width:width*.38,portrait?width+1.0:width*.69,p.x);
    float bottom=1.0-smoothstep(220.0,portrait?370.0:450.0,p.y);
    color*=1.0-side*bottom*.49*smoothstep(.0,.7,progress);
    float footer=1.0-smoothstep(68.0,101.0,p.y);
    color=mix(color,vec3(.022,.027,.029),footer*.91);
    color*=1.0-smoothstep(808.0,900.0,p.y)*.17;
    color=mix(color,muted,ufLine(p,vec2(28,816),vec2(width-28.0,816),.3)*.21);
    color=mix(color,muted,ufLine(p,vec2(28,78),vec2(width-28.0,78),.3)*.25);
    ufPaint(color,p,vec2(28,844),22.0,0,.025,.052,paper,1.0);
    if(!portrait) {
        color=mix(color,muted,ufLine(p,vec2(108,841),vec2(108,869),.35)*.5);
        ufPaint(color,p,vec2(127,851),10.0,1,.06,.043,muted,1.0);
    }
    bool sourceHover=mouse.x>width-124.0&&mouse.x<width-28.0&&mouse.y>826.0&&mouse.y<876.0;
    ufPaint(color,p,vec2(width-111.0,850),10.5,2,.075,.045,sourceHover?amber:paper,1.0);
    vec2 a=vec2(width-34.0,855.0);
    float arrow=max(ufLine(p,a+vec2(0,5),a-vec2(0,4),.55),
                   max(ufLine(p,a-vec2(0,4),a+vec2(-3.5,0),.55),ufLine(p,a-vec2(0,4),a+vec2(3.5,0),.55)));
    color=mix(color,sourceHover?amber:paper,arrow);
    if(!portrait) {
        int index=int(clamp(floor(progress+.5),0.0,7.0));
        ufPaint(color,p,vec2(width-244.0,850),10.5,12+index,.06,.043,muted,1.0);
        ufPaint(color,p,vec2(width-219.0,850),10.5,20,.06,.043,muted,1.0);
    }
    int current=int(floor(progress)),next=min(current+1,7);
    // Clear the outgoing copy before the next title enters the same position.
    float chapterPhase=fract(progress);
    float outgoingInk=1.0-smoothstep(.12,.44,chapterPhase);
    float incomingInk=smoothstep(.56,.88,chapterPhase);
    if(current!=0||portrait)ufChapter(color,p,current,outgoingInk,width,portrait);
    if(next!=current)ufChapter(color,p,next,incomingInk,width,portrait);
    float cell=(width-56.0)/8.0;
    for(int i=0;i<8;i++) {
        float x=28.0+float(i)*cell;
        float emphasis=max(0.0,1.0-abs(progress-float(i)));
        bool hover=mouse.x>x&&mouse.x<x+cell&&mouse.y>20.0&&mouse.y<70.0;
        vec3 ink=mix(muted,paper,emphasis);
        if(hover)ink=mix(ink,amber,.8);
        float numberX=portrait?x+cell*.5-7.0:x+3.0;
        ufPaint(color,p,vec2(numberX,portrait?39.0:37.0),10.7,12+i,.02,.042,mix(ink,amber,emphasis),1.0);
        if(!portrait) {
            float labelH=ufFitted(4+i,10.0,cell-44.0,.03);
            ufPaint(color,p,vec2(x+30.0,37),labelH,4+i,.03,.043,ink,1.0);
        }
        color=mix(color,amber,ufLine(p,vec2(x,78),vec2(x+cell-9.0,78),.7)*emphasis);
    }
    float hintOpacity=1.0-smoothstep(6.12,6.44,progress);
    if(hintOpacity>.0001) {
        float hintY=107.0;
        ufPaint(color,p,vec2(28,hintY),9.0,portrait?57:56,.04,.042,muted,.9*hintOpacity);
        if(!portrait) {
            ufPaint(color,p,vec2(181,hintY),9.0,58,.04,.042,muted,.85*hintOpacity);
            ufPaint(color,p,vec2(width-ufTextWidth(60,8.4,.03)-28.0,hintY),8.4,60,.03,.041,muted,.8*hintOpacity);
        }
    }
    if(ufQueuedOpacity>.0001)
        color=mix(color,ufQueuedInk,ufText(p,ufQueuedOrigin,ufQueuedHeight,ufQueuedPhrase,
                  ufQueuedTracking,ufQueuedWeight)*ufQueuedOpacity);
    return color;
}

vec3 displayTransform(vec3 radiance, vec2 pixel) {
    vec3 x = max(radiance, vec3(0.0))*max(u_exposure, 0.0);
    // A compact filmic shoulder keeps illuminated metal and glass unclipped.
    x = (x*(2.51*x+0.03))/(x*(2.43*x+0.59)+0.14);
    x = pow(clamp(x, 0.0, 1.0), vec3(1.0/2.2));
    vec2 screen = pixel/u_resolution;
    float vignette = 1.0-0.14*dot((screen-0.5)*vec2(1.0,0.8),(screen-0.5)*vec2(1.0,0.8));
    x *= vignette;
    // Stable sub-code-value dither only; no animated noise over typography.
    return max(x+(hash31(vec3(pixel,13.7))-0.5)/1024.0,vec3(0.0));
}

uniform bool u_linear_hdr;
vec3 decodeHDR(vec4 c){return u_linear_hdr?c.rgb:c.rgb*c.a*16.;}
vec3 scenePixel(vec2 uv){return decodeHDR(texture(u_scene,uv));}
// Edge-adaptive single-pass resolve. Source pixels remain native resolution;
// this is spatial AA, not a lower-resolution framebuffer or a temporal history.
vec3 resolveSurfaceEdges(vec2 uv){
 vec2 p=1./u_resolution;vec3 c=scenePixel(uv);
 vec3 nw=scenePixel(uv+vec2(-1,1)*p),ne=scenePixel(uv+p),sw=scenePixel(uv-p),se=scenePixel(uv+vec2(1,-1)*p);
 vec3 w=vec3(.2126,.7152,.0722);float lc=dot(c,w),lnw=dot(nw,w),lne=dot(ne,w),lsw=dot(sw,w),lse=dot(se,w);
 float lo=min(lc,min(min(lnw,lne),min(lsw,lse))),hi=max(lc,max(max(lnw,lne),max(lsw,lse)));
 if(hi-lo<max(.012,hi*.16))return c;
 vec2 dir=vec2(-((lnw+lne)-(lsw+lse)),(lnw+lsw)-(lne+lse));
 float reduce=max((lnw+lne+lsw+lse)*.03125,.004);
 dir=clamp(dir/(min(abs(dir.x),abs(dir.y))+reduce),vec2(-4.),vec2(4.))*p;
 vec3 a=.5*(scenePixel(uv-dir/6.)+scenePixel(uv+dir/6.));
 vec3 b=.5*a+.25*(scenePixel(uv-dir*.5)+scenePixel(uv+dir*.5));float lb=dot(b,w);
 return lb<lo||lb>hi?a:b;
}
vec2 projectPoint(vec3 p){vec3 q=p-u_camera_origin;float z=max(dot(q,u_camera_forward),.001);vec2 uv=vec2(dot(q,u_camera_right),dot(q,u_camera_up))*u_camera_lens.z/z+u_camera_lens.xy;return uv*vec2(u_resolution.y/u_resolution.x,1)+.5;}
float linearDepth(float d){return .120080053368913/(1.0013342228152102-(d*2.-1.));}
uniform highp sampler2DArray u_surface_color;
// Cached scene-space transmission avoids screen-space self-intersections.
// Seven probes contain actual rendered neighbouring geometry, not an image backdrop.
uniform highp sampler2DArray u_probe_cache;
uniform bool u_have_probes;
vec3 opticalProbe(vec3 d,int objectId,float rough){
 vec3 a=abs(d);vec2 uv;float face;
 if(a.x>=a.y&&a.x>=a.z){face=d.x>0.?0.:1.;uv=vec2(d.x>0.?-d.z:d.z,-d.y)/a.x;}
 else if(a.y>=a.z){face=d.y>0.?2.:3.;uv=vec2(d.x,d.y>0.?d.z:-d.z)/a.y;}
 else{face=d.z>0.?4.:5.;uv=vec2(d.z>0.?d.x:-d.x,-d.y)/a.z;}
 return textureLod(u_probe_cache,vec3(uv*.5+.5,float((objectId-1)*6)+face),rough*8.).rgb;
}
// Analytic solid optics with a scene-local radiance cache. For the optical
// bench, the known platter plane gives a stable current-view transmission term.
// Discontinuous screen-depth marching was rejected after rendered review.
vec3 refractedScene(vec3 o,vec3 d,float approximateDistance,int objectId){
 vec3 origin=moduleCenter(objectId)+vec3(0,objectId==1?1.59:2.14,0);
 float distanceAlong=clamp(approximateDistance,.5,9.);
 if(d.y<-.015){float t=(.235-o.y)/d.y;vec3 hit=o+d*t;if(t>0.&&length(hit.xz)<4.4)distanceAlong=t;}
 vec3 corrected=normalize(o+d*distanceAlong-origin);
 vec3 cached=u_have_probes?opticalProbe(corrected,objectId,.045):studioEnvironment(d,.045);
 if(objectId==1){
   vec3 point=o+d*distanceAlong;vec2 uv=projectPoint(point);
   if(all(greaterThan(uv,vec2(.02)))&&all(lessThan(uv,vec2(.98)))){
     float depth=texture(u_depth,uv).r;
     float sceneZ=linearDepth(depth),pointZ=dot(point-u_camera_origin,u_camera_forward);
     float trust=1.-smoothstep(.15,.55,abs(sceneZ-pointZ));
     cached=mix(cached,scenePixel(uv),trust*.92);
   }
 }
 return cached;
}
const vec4 CORE_PLANES[30]=vec4[30](vec4(-0.9873522000,0.1237805600,-0.0990656600,-0.6010049700),vec4(-0.8319284600,-0.5485686700,-0.0834712700,0.5577709500),vec4(-0.8157243700,0.5726212300,-0.0818454400,-1.6159841100),vec4(-0.7266321100,0.6302380800,-0.2735064000,-1.7641828600),vec4(-0.6945758900,0.1048807600,0.7117333500,-0.5639801200),vec4(-0.6685168500,0.6278884000,0.3985490900,-1.7607171100),vec4(-0.5787897200,-0.5596876300,0.5930870200,0.5847837400),vec4(-0.5777648500,0.5618542300,0.5920368300,-1.5987085000),vec4(-0.5398751900,0.0948854800,-0.8363800100,-0.5443469500),vec4(-0.4507433000,0.5560693900,-0.6982960000,-1.5893779800),vec4(-0.4473083000,-0.5654216900,-0.6929744600,0.5987688100),vec4(-0.2440087000,0.6105585800,-0.7534440800,-1.7349246800),vec4(-0.1076452400,0.6049297000,0.7889693000,-1.7264616900),vec4(-0.0000000000,-1.0000000000,-0.0000000000,1.4800000000),vec4(-0.0000000000,1.0000000000,-0.0000000000,-2.7200000000),vec4(0.1002722400,-0.5889999100,0.8018881400,0.6566782400),vec4(0.1051840800,0.5304447600,0.8411686300,-1.5476510600),vec4(0.1239114600,0.0519293000,0.9909335500,-0.4595610600),vec4(0.2560333600,-0.5956177500,-0.7613714100,0.6730523500),vec4(0.2717365900,0.5226706800,-0.8080684300,-1.5348677800),vec4(0.3184932000,0.0393160900,-0.9471094600,-0.4345398200),vec4(0.4487737100,0.5816488800,-0.6784443500,-1.6910336500),vec4(0.5639678300,0.5767663200,0.5909999100,-1.6835192600),vec4(0.6739423800,-0.6131784900,0.4120847000,0.7167688300),vec4(0.7385337600,0.5006435500,0.4515793500,-1.4983463900),vec4(0.7403530700,-0.6159429200,-0.2692427300,0.7236869700),vec4(0.8155101400,0.4969773800,-0.2965749500,-1.4922255900),vec4(0.8213067600,0.5657810100,-0.0731234800,-1.6665093800),vec4(0.8531426200,0.0046096800,0.5216573900,-0.3653986100),vec4(0.9397833800,-0.0010213600,-0.3417691500,-0.3541401200));
bool coreIntersection(vec3 o,vec3 d,out float enter,out float leave,out vec3 ne,out vec3 nx){
 enter=-1e6;leave=1e6;ne=vec3(0);nx=vec3(0);
 for(int i=0;i<CORE_PLANES.length();i++){vec4 pl=CORE_PLANES[i];float a=dot(pl.xyz,d),b=dot(pl.xyz,o)+pl.w;
 if(abs(a)<.000001){if(b>0.)return false;continue;}float t=-b/a;
 if(a<0.){if(t>enter){enter=t;ne=pl.xyz;}}else if(t<leave){leave=t;nx=pl.xyz;}}
 return leave>max(enter,0.);
}

void main(){clockTime=u_time;pixelFootprint=1./u_resolution.y;vec2 uv=gl_FragCoord.xy/u_resolution;vec2 xy=(gl_FragCoord.xy-.5*u_resolution)/u_resolution.y-u_camera_lens.xy;
 vec3 ro=u_camera_origin,rd=normalize(u_camera_forward*u_camera_lens.z+u_camera_right*xy.x+u_camera_up*xy.y);
 float depth=texture(u_depth,uv).r;float surfaceT=depth<.999999?linearDepth(depth)/max(dot(rd,u_camera_forward),.0001):90.;
 vec3 radiance=depth<.999999?resolveSurfaceEdges(uv):viewBackground(rd);
 // Analytic biconvex optic: intersection of two offset spheres, not a glass ball.
 vec3 lensCenter=moduleCenter(1)+vec3(0,1.59,0);vec2 ax=moduleAxis(1);
 vec3 axis=normalize(vec3(ax.x*.943,.334,ax.y*.943));
 vec3 c0=lensCenter+axis*3.847,c1=lensCenter-axis*3.847;
 vec2 a=raySphere(ro,rd,c0,3.90),b=raySphere(ro,rd,c1,3.90);
 float tEnter=max(a.x,b.x),tExit=min(a.y,b.y),nearest=surfaceT;
 if(tEnter>.001&&tExit>tEnter&&tEnter<surfaceT){
   nearest=tEnter;vec3 point=ro+rd*tEnter;vec3 normal=normalize(point-(a.x>b.x?c0:c1));
   float ior=1.515;vec3 inside=refract(rd,normal,1./ior),ip=point+inside*.001;
   vec2 aa=raySphere(ip,inside,c0,3.90),bb=raySphere(ip,inside,c1,3.90);
   float thickness=min(aa.y,bb.y);vec3 exitPoint=ip+inside*thickness;
   vec3 en=normalize(exitPoint-(aa.y<bb.y?c0:c1));vec3 outgoing=refract(inside,-en,ior);
   if(dot(outgoing,outgoing)<.01)outgoing=reflect(inside,-en);
   float behind=clamp(surfaceT-tEnter-thickness,.05,8.);
   vec3 transmitted=refractedScene(exitPoint+outgoing*.004,outgoing,behind,1);
   float f0=.015;float fresnel=f0+(1.-f0)*pow(1.-max(dot(-rd,normal),0.),5.);
   vec3 reflectance=mix(studioEnvironment(reflect(rd,normal),.025),opticalProbe(reflect(rd,normal),1,.025),.70);
   radiance=transmitted*exp(-vec3(.018,.007,.004)*thickness)*(1.-fresnel)*(1.-f0)+reflectance*vec3(.90,.98,1.08)*fresnel;
 }
 // Planar entry/exit solves the actual cut prism; no spherical replacement.
 vec2 coreBounds=rayBounds(ro,rd,vec3(-.55,1.45,-.55),vec3(.55,2.75,.55));
 if(coreBounds.y>max(coreBounds.x,0.)&&coreBounds.x<nearest){
   float te,tx;vec3 nn,nx;
   if(coreIntersection(ro,rd,te,tx,nn,nx)&&te>.001&&te<nearest){
     vec3 entry=ro+rd*te,inside=refract(rd,nn,1./1.52),ip=entry+inside*.001;
     float en,ex;vec3 n1,n2;coreIntersection(ip,inside,en,ex,n1,n2);
     float pathLength=max(0.,ex);vec3 exitPoint=ip+inside*pathLength;vec3 outRay=refract(inside,-n2,1.52);
     bool tir=dot(outRay,outRay)<.001;
     if(tir){outRay=reflect(inside,-n2);vec3 second=exitPoint+outRay*.001;
       if(coreIntersection(second,outRay,en,ex,n1,n2)){pathLength+=ex;exitPoint=second+outRay*ex;vec3 rr=refract(outRay,-n2,1.52);outRay=dot(rr,rr)<.001?reflect(outRay,-n2):rr;}}
     float behind=clamp(surfaceT-te-pathLength,.10,10.);
     vec3 transmission=refractedScene(exitPoint+outRay*.004,outRay,behind,7);
     float fresnel=.0426+.9574*pow(1.-max(dot(-rd,nn),0.),5.);
     vec3 absorption=exp(-vec3(.10,.035,.018)*pathLength);
     vec3 internalScatter=vec3(.009,.015,.016)*(1.-exp(-pathLength*2.));
     radiance=(transmission*absorption+internalScatter)*(1.-fresnel)*.96+(mix(studioEnvironment(reflect(rd,nn),.05),opticalProbe(reflect(rd,nn),7,.05),.65))*fresnel;
     nearest=te;
   }
 }
 radiance=integrateFlame(radiance,ro,rd,nearest);
 vec3 outputColor=displayTransform(radiance,gl_FragCoord.xy);outputColor=portfolioUI(outputColor,gl_FragCoord.xy,u_chapter,u_time);fragColor=vec4(clamp(outputColor,0.,1.),1.);
}
