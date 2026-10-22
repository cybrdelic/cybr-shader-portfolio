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


precision highp sampler2D;
precision highp sampler2DArray;
precision highp usampler2D;
layout(location=0) out vec4 fragColor;
layout(location=1) out vec4 guideColor;
uniform sampler2D u_guide_history;
uniform sampler2D u_history;
uniform sampler2DArray u_surface_color;
uniform sampler2DArray u_surface_normal;
uniform int u_sample;
uniform float u_focus_distance;
uniform float u_physical_focus;
uniform samplerCube u_environment;
vec3 studioEnvironment(vec3 r,float rough){
    // A finite studio's low-level bounced room radiance. Emitters are sampled
    // as real quads below, so they are not counted twice as environment lights.
    float room=.024+.048*smoothstep(-.6,.8,r.y);
    return vec3(room*1.02,room,room*.98);
}
vec2 raySphere(vec3 ro,vec3 rd,vec3 c,float radius){vec3 oc=ro-c;float b=dot(oc,rd),h=b*b-dot(oc,oc)+radius*radius;if(h<0.)return vec2(1e20,-1e20);h=sqrt(h);return vec2(-b-h,-b+h);}
vec2 rayBounds(vec3 ro,vec3 rd,vec3 lo,vec3 hi){vec3 inv=(step(vec3(0),rd)*2.-1.)/max(abs(rd),vec3(1e-8));vec3 a=(lo-ro)*inv,b=(hi-ro)*inv;vec3 n=min(a,b),f=max(a,b);return vec2(max(n.x,max(n.y,n.z)),min(f.x,min(f.y,f.z)));}
// Real triangle intersections for secondary rays. Not a path tracer: terminal
// lighting uses the static irradiance cache plus the studio specular field.
uniform highp sampler2D u_bvh_nodes;
uniform highp usampler2D u_bvh_triangles;
uniform highp sampler2D u_ray_positions;
uniform highp sampler2D u_ray_normals;
uniform highp sampler2D u_ray_attributes;
uniform highp sampler2D u_ray_irradiance;
uniform ivec4 u_bvh_roots;
uniform int u_bvh_width;
uniform bool u_trace_optics;

vec4 traceFetch(sampler2D tex,int i){return texelFetch(tex,ivec2(i%u_bvh_width,i/u_bvh_width),0);}
uvec4 traceTriangle(int i){return texelFetch(u_bvh_triangles,ivec2(i%u_bvh_width,i/u_bvh_width),0);}
vec3 rayRotation(vec3 p,vec3 axis,float a){float c=cos(a),s=sin(a);return p*c+cross(axis,p)*s+axis*dot(axis,p)*(1.-c);}
void rayPartInfo(int part,out vec3 pivot,out vec3 axis,out float angle){
    pivot=vec3(0);axis=vec3(0,1,0);angle=0.;
    if(part==1){vec2 a=moduleAxis(1);pivot=moduleCenter(1)+vec3(0,1.59,0);axis=normalize(vec3(a.x*.943,.334,a.y*.943));angle=.055*sin(u_time*.19);}
    if(part==2){pivot=moduleCenter(2)+vec3(0,1.1,0);angle=u_time*.28;}
    if(part==3){pivot=vec3(0,2.14,0);axis=normalize(vec3(1,.4,.2));angle=.06*sin(u_time*.15);}
}
float traceBox(vec3 lo,vec3 hi,vec3 ro,vec3 inv,float limit){
    vec3 a=(lo-ro)*inv,b=(hi-ro)*inv;
    vec3 nearV=min(a,b),farV=max(a,b);
    float enter=max(nearV.x,max(nearV.y,nearV.z)),leave=min(farV.x,min(farV.y,farV.z));
    return leave>=max(enter,.0004)&&enter<limit?max(enter,0.):1e20;
}
struct RayHit{float t;int triangle;int part;vec2 bary;};
RayHit closestTriangle(vec3 origin,vec3 direction,float maximum){
    RayHit hit;hit.t=maximum;hit.triangle=-1;hit.part=0;hit.bary=vec2(0);
    for(int part=0;part<4;part++){
        int root=u_bvh_roots[part];if(root<0)continue;
        vec3 pivot,axis;float angle;rayPartInfo(part,pivot,axis,angle);
        vec3 ro=pivot+rayRotation(origin-pivot,axis,-angle);
        vec3 rd=rayRotation(direction,axis,-angle);
        vec3 inv=vec3(rd.x<0.?-1.:1.,rd.y<0.?-1.:1.,rd.z<0.?-1.:1.)/max(abs(rd),vec3(1e-9));
        int stack[64];int top=1;stack[0]=root;
        while(top>0){
            int node=stack[--top];vec4 lo=traceFetch(u_bvh_nodes,node*2),hi=traceFetch(u_bvh_nodes,node*2+1);
            if(traceBox(lo.xyz,hi.xyz,ro,inv,hit.t)>hit.t)continue;
            if(hi.w<0.){
                int first=int(lo.w+.5),count=int(-hi.w+.5);
                for(int j=0;j<6;j++){
                    if(j>=count)break;
                    uvec3 ix=traceTriangle(first+j).xyz;
                    vec3 a=traceFetch(u_ray_positions,int(ix.x)).xyz;
                    vec3 b=traceFetch(u_ray_positions,int(ix.y)).xyz;
                    vec3 c=traceFetch(u_ray_positions,int(ix.z)).xyz;
                    vec3 e1=b-a,e2=c-a,h=cross(rd,e2);float det=dot(e1,h);
                    if(abs(det)<1e-11)continue;
                    vec3 s=ro-a;float u=dot(s,h)/det;if(u<0.||u>1.)continue;
                    vec3 q=cross(s,e1);float v=dot(rd,q)/det;if(v<0.||u+v>1.)continue;
                    float t=dot(e2,q)/det;
                    if(t>.0007&&t<hit.t){hit.t=t;hit.triangle=first+j;hit.bary=vec2(u,v);hit.part=part;}
                }
            }else{
                int left=int(lo.w+.5),right=int(hi.w+.5);
                vec4 al=traceFetch(u_bvh_nodes,left*2),ah=traceFetch(u_bvh_nodes,left*2+1);
                vec4 bl=traceFetch(u_bvh_nodes,right*2),bh=traceFetch(u_bvh_nodes,right*2+1);
                float a=traceBox(al.xyz,ah.xyz,ro,inv,hit.t),b=traceBox(bl.xyz,bh.xyz,ro,inv,hit.t);
                if(a<b){if(b<hit.t)stack[top++]=right;if(a<hit.t)stack[top++]=left;}
                else{if(a<hit.t)stack[top++]=left;if(b<hit.t)stack[top++]=right;}
            }
        }
    }
    return hit;
}
vec4 interpolateRayAttribute(sampler2D tex,uvec3 ix,vec3 bary){
    return traceFetch(tex,int(ix.x))*bary.x+traceFetch(tex,int(ix.y))*bary.y+traceFetch(tex,int(ix.z))*bary.z;
}
vec2 raySurfaceUV(vec3 p,vec3 n){vec3 a=abs(n);if(a.y>max(a.x,a.z))return p.xz;if(a.x>a.z)return p.zy;return p.xy;}

const vec4 CORE_PLANES[30]=vec4[30](vec4(-0.9873522000,0.1237805600,-0.0990656600,-0.6010049700),vec4(-0.8319284600,-0.5485686700,-0.0834712700,0.5577709500),vec4(-0.8157243700,0.5726212300,-0.0818454400,-1.6159841100),vec4(-0.7266321100,0.6302380800,-0.2735064000,-1.7641828600),vec4(-0.6945758900,0.1048807600,0.7117333500,-0.5639801200),vec4(-0.6685168500,0.6278884000,0.3985490900,-1.7607171100),vec4(-0.5787897200,-0.5596876300,0.5930870200,0.5847837400),vec4(-0.5777648500,0.5618542300,0.5920368300,-1.5987085000),vec4(-0.5398751900,0.0948854800,-0.8363800100,-0.5443469500),vec4(-0.4507433000,0.5560693900,-0.6982960000,-1.5893779800),vec4(-0.4473083000,-0.5654216900,-0.6929744600,0.5987688100),vec4(-0.2440087000,0.6105585800,-0.7534440800,-1.7349246800),vec4(-0.1076452400,0.6049297000,0.7889693000,-1.7264616900),vec4(-0.0000000000,-1.0000000000,-0.0000000000,1.4800000000),vec4(-0.0000000000,1.0000000000,-0.0000000000,-2.7200000000),vec4(0.1002722400,-0.5889999100,0.8018881400,0.6566782400),vec4(0.1051840800,0.5304447600,0.8411686300,-1.5476510600),vec4(0.1239114600,0.0519293000,0.9909335500,-0.4595610600),vec4(0.2560333600,-0.5956177500,-0.7613714100,0.6730523500),vec4(0.2717365900,0.5226706800,-0.8080684300,-1.5348677800),vec4(0.3184932000,0.0393160900,-0.9471094600,-0.4345398200),vec4(0.4487737100,0.5816488800,-0.6784443500,-1.6910336500),vec4(0.5639678300,0.5767663200,0.5909999100,-1.6835192600),vec4(0.6739423800,-0.6131784900,0.4120847000,0.7167688300),vec4(0.7385337600,0.5006435500,0.4515793500,-1.4983463900),vec4(0.7403530700,-0.6159429200,-0.2692427300,0.7236869700),vec4(0.8155101400,0.4969773800,-0.2965749500,-1.4922255900),vec4(0.8213067600,0.5657810100,-0.0731234800,-1.6665093800),vec4(0.8531426200,0.0046096800,0.5216573900,-0.3653986100),vec4(0.9397833800,-0.0010213600,-0.3417691500,-0.3541401200));
bool coreIntersection(vec3 o,vec3 d,out float enter,out float leave,out vec3 ne,out vec3 nx){
 enter=-1e6;leave=1e6;ne=vec3(0);nx=vec3(0);
 for(int i=0;i<CORE_PLANES.length();i++){vec4 pl=CORE_PLANES[i];float a=dot(pl.xyz,d),b=dot(pl.xyz,o)+pl.w;
 if(abs(a)<.000001){if(b>0.)return false;continue;}float t=-b/a;
 if(a<0.){if(t>enter){enter=t;ne=pl.xyz;}}else if(t<leave){leave=t;nx=pl.xyz;}}
 return leave>max(enter,0.);
}
float glyphFootprint;
const int LABEL_TEXT[288]=int[288](67,89,66,82,32,76,73,71,72,84,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,67,89,66,82,32,71,69,79,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,67,89,66,82,32,83,67,69,78,69,83,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,67,89,66,82,32,69,76,69,77,69,78,84,83,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,67,89,66,82,32,77,65,84,69,82,73,65,76,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,67,89,66,82,32,70,79,82,69,83,84,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,67,89,66,82,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,65,76,69,74,65,78,68,82,79,32,70,73,71,85,69,82,79,65,32,32,32,32,32,32,32,32,32,32,32,32,32,32,71,82,65,80,72,73,67,83,32,32,83,73,77,85,76,65,84,73,79,78,32,32,83,89,83,84,69,77,83,32,32,32);
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



float engraving(vec2 uv,int phrase,float size){
    vec2 p=uv/size;vec2 fp=vec2(glyphFootprint/size);int cell=int(floor(p.x));
    if(cell<0||cell>=32||p.y<-.12||p.y>1.50)return 0.;
    int c=LABEL_TEXT[phrase*32+cell];if(c==32)return 0.;
    vec2 q=vec2(fract(p.x)*.64,p.y/1.35);
    float aa=max(fp.x*.64,fp.y/1.35)*.60;
    return 1.-smoothstep(.043-aa,.043+aa,ufGlyph(q,c));
}

vec2 identityPlateUV(vec3 p){vec3 q=p-vec3(-1.05,.30,4.46);float c=cos(.28),s=sin(.28);q.yz=mat2(c,-s,s,c)*q.yz;return vec2(q.x+1.12,.53-q.z);}
float identityEngraving(vec3 p){vec2 uv=identityPlateUV(p);float text=engraving(uv-vec2(0,.55),6,.40);text=max(text,engraving(uv-vec2(.004,.34),7,.105));text=max(text,engraving(uv-vec2(.004,.17),8,.064));float rule=(1.-smoothstep(.002,.004,abs(uv.y-.486)))*step(0.,uv.x)*step(uv.x,2.22);return max(text,rule*.55);}

float flameDensity(vec3 p){
 float h=p.y;if(h<0.||h>1.02)return 0.;
 vec3 adv=p*vec3(7.0,5.8,7.0)-vec3(0,clockTime*2.45,0);
 vec3 warp=vec3(noise3(adv+17.),noise3(adv+47.),noise3(adv+93.))-.5;
 p+=warp*vec3(.17,.05,.17)*(.30+h);
 float turbulence=noise3(adv*1.9)*.58+noise3(adv*4.0+7.)*.28+noise3(adv*8.1-5.)*.14;
 float density=0.;
 for(int j=0;j<4;j++){
  float k=float(j),hh=.66+.22*sin(k*2.9+clockTime*.52);
  vec2 origin=vec2(sin(k*2.3),cos(k*2.3))*.105;
  origin+=vec2(sin(h*7.-clockTime*1.4+k),cos(h*6.+clockTime*.86-k))*(.008+h*.073);
  float radius=.143*pow(max(0.,1.-h/hh),.68)+.004;
  float boundary=length(p.xz-origin*(1.-h*.4))/radius;
  boundary+=(turbulence-.5)*1.72;
  float sheet=exp(-pow((boundary-.72)*3.0,2.));
  float rupture=smoothstep(.15,.36,turbulence+h*.10);
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
        float density = flameDensity(local);
        float opacity = 1.0 - exp(-density * stride * 1.65);
        float heat = clamp(density * 1.12 + (1.1 - local.y) * 0.25, 0.0, 1.0);
        vec3 temperature = mix(vec3(2.0, 0.09, 0.003), vec3(5.7, 1.26, 0.07), pow(heat, 3.2));
        emission += transmittance * opacity * temperature;
        transmittance *= 1.0 - opacity;
    }
    return color * transmittance + emission;
}

// Quasi-random sample decorrelation, with a separate seed for each native pixel.
uint seed;
uint randomU(){seed=seed*747796405u+2891336453u;uint word=((seed>>((seed>>28u)+4u))^seed)*277803737u;return (word>>22u)^word;}
float randomF(){return float(randomU()>>8u)*(1./16777216.);}
vec2 random2(){return vec2(randomF(),randomF());}
mat3 tangentFrame(vec3 n){vec3 t=normalize(cross(abs(n.y)<.95?vec3(0,1,0):vec3(1,0,0),n));return mat3(t,cross(n,t),n);}
vec3 cosineSample(vec2 u){float r=sqrt(u.x),phi=TAU*u.y;return vec3(r*cos(phi),r*sin(phi),sqrt(max(0.,1.-u.x)));}
vec3 fresnelSchlick(vec3 f0,float c){return f0+(1.-f0)*pow(clamp(1.-c,0.,1.),5.);}
float smithG1(float c,float a2){return 2.*c/max(c+sqrt(a2+(1.-a2)*c*c),1e-8);}
float powerHeuristic(float a,float b){float aa=a*a,bb=b*b;return aa/max(aa+bb,1e-14);}
struct SurfacePT {vec3 base;vec3 n;vec3 tangent;vec3 emission;float metal;float rough;float anisotropy;int id;};
SurfacePT materialAt(RayHit hit,vec3 direction){
 uvec3 ix=traceTriangle(hit.triangle).xyz;vec3 bary=vec3(1.-hit.bary.x-hit.bary.y,hit.bary);
 vec4 pos=interpolateRayAttribute(u_ray_positions,ix,bary),normalAO=interpolateRayAttribute(u_ray_normals,ix,bary),at=interpolateRayAttribute(u_ray_attributes,ix,bary);
 int meta=int(traceFetch(u_ray_positions,int(ix.x)).w+.5),id=meta%32,obj=meta/32;
 vec3 pivot,axis;float angle;rayPartInfo(hit.part,pivot,axis,angle);
 vec3 n=normalize(rayRotation(normalAO.xyz,axis,angle));if(dot(n,direction)>0.)n=-n;
 vec3 q=obj>=1&&obj<=6?moduleLocal(pos.xyz,obj):pos.xyz;
 SurfacePT m;m.base=vec3(.11);m.n=n;m.emission=vec3(0);m.metal=0.;m.rough=.55;m.id=id;m.anisotropy=0.;m.tangent=tangentFrame(n)[0];
 int layer=-1;vec2 uv=raySurfaceUV(q,n);
 if(id==1){layer=7;uv*=.22;m.rough=.8;}
 else if(id==2){m.base=vec3(.026,.030,.033);m.metal=.72;m.rough=.32;}
 else if(id==3){m.base=vec3(.57,.385,.19);m.metal=1.;m.rough=.22;}
 else if(id==4){m.base=vec3(.64,.67,.70);m.metal=1.;m.rough=.245;}
 else if(id==5){layer=5;uv=vec2(q.x*.9+q.z*.5,q.y*.62);}
 else if(id==6){layer=2;uv=vec2(q.x*1.7+q.z*.3,q.y*.58);}
 else if(id==7){m.base=vec3(.70,.682,.638);m.rough=.275;}
 else if(id==8||id==22){layer=6;uv*=2.5;}
 else if(id==9){m.base=vec3(.03,.006,.001);m.emission=vec3(2.,.23,.003);m.rough=.4;}
 else if(id==10){m.base=vec3(.005,.015,.017);m.rough=.075;}
 else if(id==11){layer=3;}
 else if(id==12){layer=4;uv=at.zw*vec2(2.8,3.5);}
 else if(id==13){
  vec2 leafUV=at.zw;float variation=noise3(pos.xyz*7.);float rib=exp(-pow((leafUV.y-.5)/.025,2.));
  float vein=pow(1.-abs(sin((leafUV.x-abs(leafUV.y-.5)*.55)*PI*13.)),18.);
  float edge=smoothstep(.34,.5,abs(leafUV.y-.5));
  m.base=mix(vec3(.023,.056,.009),vec3(.058,.11,.014),variation);
  m.base*=1.+rib*.20+vein*.07-edge*.15;m.rough=.51+edge*.13;
 }
 else if(id==14){m.base=vec3(.025,.040,.010);m.rough=.95;}
 else if(id==15){m.base=vec3(.32,.12,.03);m.emission=vec3(2.2,.6,.08);m.rough=.31;}
 else if(id==16){m.base=vec3(.009,.011,.012);m.rough=.62;}
 else if(id==17){m.base=vec3(.76,.34,.155);m.metal=1.;m.rough=.29;}
 else if(id==26){m.base=vec3(.085,.078,.062);m.rough=.80;}
 else if(id==27){m.base=vec3(.19,.021,.008);m.rough=.48;}
 else if(id==28){m.base=vec3(.59,.62,.65);m.metal=1.;m.rough=.30;}
 else if(id==29){m.base=vec3(.35,.32,.25);m.rough=.46;}
 else if(id==30){m.base=mix(vec3(.018,.010,.006),vec3(.055,.033,.017),noise3(pos.xyz*50.));m.rough=.97;}
 else if(id==18||id==24||id==25){m.base=vec3(.53,.54,.515);m.metal=.55;m.rough=.31;}
 else if(id==19){m.base=vec3(.022,.033,.036);m.rough=.34;}
 else if(id==20){m.base=vec3(.7,.66,.54);m.emission=vec3(1.2,1.07,.85);m.rough=.28;}
 else if(id==21){m.base=vec3(.009,.028,.029);m.rough=.04;}
 else if(id==23){m.base=vec3(.016,.020,.024);m.metal=.25;m.rough=.36;}
 float lod=clamp(log2(max(.0001,hit.t*800./u_resolution.y))+.2,0.,6.);
 if(layer>=0){vec4 t=textureLod(u_surface_color,vec3(uv,float(layer)),lod);m.base=t.rgb;m.rough=t.a;}
 if(id==11){vec3 a=traceFetch(u_ray_positions,int(ix.x)).xyz,b=traceFetch(u_ray_positions,int(ix.y)).xyz,c=traceFetch(u_ray_positions,int(ix.z)).xyz;vec3 fn=normalize(cross(b-a,c-a));if(dot(fn,n)<0.)fn=-fn;m.n=normalize(mix(n,fn,.70));float wet=1.-smoothstep(.7,.86,q.y);m.base*=1.-wet*.38;m.rough=mix(m.rough,.23,wet);}
 if(id==2||id==3||id==4||id==17||id==28){float r=length(q.xz),theta=atan(q.z,q.x)/TAU;uv=abs(n.y)>.65?vec2(theta*4.,r*2.8):vec2(theta*4.,q.y*2.5);vec4 t=textureLod(u_surface_color,vec3(uv,0),lod);m.rough+=(t.a-.26)*.55;vec3 bn=textureLod(u_surface_normal,vec3(uv,0),lod).xyz*2.-1.;m.n=normalize(m.n+tangentFrame(m.n)*vec3(bn.xy*.028,0.));}
 if(id==7){vec4 t=textureLod(u_surface_color,vec3(uv*2.3,1),lod);m.rough+=(t.a-.26)*.4;}
 
 // Surface-specific details retain the identity plaques in the path-traced view.
 glyphFootprint=hit.t/max(u_resolution.y*u_camera_lens.z*max(.12,abs(dot(n,direction))),1.);
 if(id==24||id==25){float text=0.;if(id==24){vec2 euv=vec2(-q.z+.175,q.x-.775);text=engraving(euv,obj-1,.021);}else{text=identityEngraving(pos.xyz);}m.base=mix(m.base,vec3(.010,.015,.017),text);m.metal*=1.-text;}
 if(id==22){float edge=1.-smoothstep(.940,.959,pos.y);m.emission=vec3(.72,.032,.001)*edge*edge;}
 if(id==23){vec2 w=q.xz*125.;float aa=hit.t*125./u_resolution.y;float warp=pow(.5+.5*cos(w.x*PI),2.),weft=pow(.5+.5*cos(w.y*PI),2.);float plaid=mod(floor(w.x)+floor(w.y),2.);float fiber=mix(mix(warp,weft,plaid),.45,smoothstep(.5,1.5,aa));m.base=vec3(.016,.020,.024)*(.35+1.6*fiber);m.rough=.31+.17*(1.-fiber);}
 if(layer>=0&&id!=1){vec3 bn=textureLod(u_surface_normal,vec3(uv,float(layer)),lod).xyz*2.-1.;vec3 localN=n;if(obj>=1&&obj<=6){vec2 a=moduleAxis(obj);localN.xz=vec2(dot(n.xz,a),dot(n.xz,vec2(-a.y,a.x)));}
 vec3 av=abs(localN),t=av.x>max(av.y,av.z)?vec3(0,0,1):vec3(1,0,0),b=av.y>max(av.x,av.z)?vec3(0,0,1):vec3(0,1,0);
 if(id==6){t=normalize(vec3(1.7,0,.3));b=vec3(0,1,0);}if(obj>=1&&obj<=6){vec2 a=moduleAxis(obj);t.xz=vec2(dot(t.xz,vec2(a.x,-a.y)),dot(t.xz,vec2(a.y,a.x)));b.xz=vec2(dot(b.xz,vec2(a.x,-a.y)),dot(b.xz,vec2(a.y,a.x)));}
 t=rayRotation(t,axis,angle);b=rayRotation(b,axis,angle);t-=m.n*dot(t,m.n);b-=m.n*dot(b,m.n);float strength=id==11?.60:id==12?.75:.35;m.n=normalize(m.n*max(bn.z,.2)+(t*bn.x+b*bn.y)*strength);}
 // Machining direction follows the actual turned part rather than screen axes.
 if(id==2||id==3||id==4||id==17||id==28){
  vec3 t=abs(n.y)>.60?normalize(vec3(-q.z,0,q.x)+vec3(1e-7,0,0)):vec3(0,1,0);
  if(obj>=1&&obj<=6){vec2 a=moduleAxis(obj);t.xz=vec2(dot(t.xz,vec2(a.x,-a.y)),dot(t.xz,vec2(a.y,a.x)));}
  t=rayRotation(t,axis,angle);t-=m.n*dot(t,m.n);
  m.tangent=dot(t,t)>1e-5?normalize(t):tangentFrame(m.n)[0];
  m.anisotropy=id==28?.72:id==4?.56:id==3?.42:id==17?.30:.24;
 }
 m.tangent-=m.n*dot(m.tangent,m.n);m.tangent=dot(m.tangent,m.tangent)>1e-8?normalize(m.tangent):tangentFrame(m.n)[0];
 m.rough=clamp(m.rough,.04,.98);return m;
}
// Elliptical Trowbridge-Reitz normal distribution. Evaluation and sampling
// use the same axes; the tangent is attached to the surface, not the camera.
vec2 roughAxes(SurfacePT m){float a=max(.0016,m.rough*m.rough);float aspect=sqrt(max(.1,1.-.9*m.anisotropy));return vec2(a/aspect,a*aspect);}
mat3 surfaceFrame(SurfacePT m){return mat3(m.tangent,normalize(cross(m.n,m.tangent)),m.n);}
float anisotropicG1(vec3 v,vec2 a){float q=dot(v.xy*a,v.xy*a);return 2.*v.z/max(v.z+sqrt(v.z*v.z+q),1e-8);}
vec3 evaluateBSDF(SurfacePT m,vec3 v,vec3 l,out float pdf){
 float nv=dot(m.n,v),nl=dot(m.n,l);pdf=0.;if(nv<=0.)return vec3(0);
 if(m.id==13&&nl<0.){pdf=.28*(-nl)/PI;return m.base*.28/PI;}
 if(nl<=0.)return vec3(0);
 vec3 h=normalize(v+l);float nh=max(dot(m.n,h),0.),vh=max(dot(v,h),1e-6);
 vec2 axes=roughAxes(m);mat3 frame=surfaceFrame(m);
 vec3 hl=transpose(frame)*h,vl=transpose(frame)*v,ll=transpose(frame)*l;
 float den=dot(hl.xy/axes,hl.xy/axes)+hl.z*hl.z;float D=1./(PI*axes.x*axes.y*den*den);
 float G=anisotropicG1(vl,axes)*anisotropicG1(ll,axes);vec3 f0=mix(vec3(.04),m.base,m.metal),F=fresnelSchlick(f0,vh);
 float specProb=mix(.25,1.,m.metal);
 pdf=specProb*(D*nh/(4.*vh))+(1.-specProb)*(nl/PI);
 vec3 result=(1.-F)*m.base*((1.-m.metal)/PI)+F*(D*G/max(4.*nv*nl,1e-8));if(m.id==13){pdf*=.72;result*=.72;}return result;
}
vec3 sampleBSDF(SurfacePT m,vec3 v,out float pdf,out vec3 value){
 mat3 frame=surfaceFrame(m);vec2 u=random2();vec3 l;
 if(m.id==13&&randomF()<.28){l=-(frame*cosineSample(u));value=evaluateBSDF(m,v,l,pdf);return l;}
 if(randomF()<mix(.25,1.,m.metal)){
  vec2 axes=roughAxes(m);float slope=sqrt(u.x/max(1.-u.x,1e-7));
  vec3 h=frame*normalize(vec3(axes.x*slope*cos(TAU*u.y),axes.y*slope*sin(TAU*u.y),1.));
  l=reflect(-v,h);
 }else l=frame*cosineSample(u);
 value=evaluateBSDF(m,v,l,pdf);return l;
}
void areaLight(int index,out vec3 center,out vec3 right,out vec3 up,out vec3 normal,out vec2 size,out vec3 emission){
 if(index==3){center=moduleCenter(4)+vec3(0,.9441,0);right=vec3(1,0,0);up=vec3(0,0,1);normal=vec3(0,1,0);size=vec2(.747);emission=vec3(2.,.23,.003);return;}
 if(index==0){center=vec3(-3.8,7.5,5.4);size=vec2(2.6,1.85);emission=vec3(10.0,9.45,8.70);}
 else if(index==1){center=vec3(5.2,4.5,-2.7);size=vec2(1.6,2.6);emission=vec3(.68,.82,1.05);}
 else{center=vec3(-3.5,3.8,-5.8);size=vec2(.65,2.4);emission=vec3(4.6,4.80,5.10);}
 normal=normalize(vec3(0,1,0)-center);right=normalize(cross(vec3(0,1,0),normal));up=cross(normal,right);
}
float lightProbability(int i){return i==0?.60:i==1?.18:i==2?.14:.08;}
float emitterArea(int i,vec2 size){return i==3?PI*size.x*size.x:4.*size.x*size.y;}
float intersectLights(vec3 ro,vec3 rd,float maxT,out vec3 radiance,out float pdf){
 float closest=maxT;radiance=vec3(0);pdf=0.;
 for(int i=0;i<4;i++){vec3 center,right,up,n,em;vec2 halfSize;areaLight(i,center,right,up,n,halfSize,em);float cosine=dot(n,rd);if(cosine>=-.00001)continue;float t=dot(center-ro,n)/cosine;if(t<=.001||t>=closest)continue;vec3 p=ro+rd*t-center;if(i==3){if(length(vec2(dot(p,right),dot(p,up)))>halfSize.x)continue;}else if(abs(dot(p,right))>halfSize.x||abs(dot(p,up))>halfSize.y)continue;closest=t;radiance=em;pdf=lightProbability(i)*t*t/(emitterArea(i,halfSize)*(-cosine));}
 return closest;
}
vec3 sampleDirect(vec3 p,SurfacePT m,vec3 v){
 float choice=randomF();int i=choice<.60?0:choice<.78?1:choice<.92?2:3;
 vec3 center,right,up,n,em;vec2 size;areaLight(i,center,right,up,n,size,em);
 vec2 u=random2();vec2 st=i==3?sqrt(u.x)*size.x*vec2(cos(TAU*u.y),sin(TAU*u.y)):(u*2.-1.)*size;vec3 point=center+right*st.x+up*st.y;
 vec3 delta=point-p;float d=length(delta);vec3 l=delta/d;
 float nl=dot(m.n,l),cosLight=dot(n,-l);if((m.id!=13&&nl<=0.)||cosLight<=0.)return vec3(0);
 float lightPdf=lightProbability(i)*d*d/(emitterArea(i,size)*cosLight),bsdfPdf;
 vec3 f=evaluateBSDF(m,v,l,bsdfPdf);
 // The analytic glass volumes do not block a straight next-event shadow ray.
 // No refracted caustic connection is claimed by this estimator.
 RayHit shadow=closestTriangle(p+m.n*.0015*(nl>=0.?1.:-1.),l,d-.003);if(shadow.triangle>=0)return vec3(0);
 return em*f*(abs(nl)*powerHeuristic(lightPdf,bsdfPdf)/max(lightPdf,1e-7));
}
struct GlassHit {float t;vec3 n;int id;};
GlassHit glassIntersection(vec3 ro,vec3 rd,float maxT){
 GlassHit g;g.t=maxT;g.n=vec3(0);g.id=0;
 vec2 ax=moduleAxis(1);vec3 axis=normalize(vec3(ax.x*.943,.334,ax.y*.943));vec3 center=moduleCenter(1)+vec3(0,1.59,0),c0=center+axis*1.72,c1=center-axis*1.72;
 vec2 a=raySphere(ro,rd,c0,1.84),b=raySphere(ro,rd,c1,1.84);float enter=max(a.x,b.x),leave=min(a.y,b.y);
 if(leave>max(enter,.0004)){float t=enter>.0004?enter:leave;if(t<g.t){g.t=t;g.id=1;g.n=normalize(ro+rd*t-(enter>.0004?(a.x>b.x?c0:c1):(a.y<b.y?c0:c1)));}}
 vec2 bounds=rayBounds(ro,rd,vec3(-.7,1.4,-.7),vec3(.7,2.8,.7));
 if(bounds.y>max(bounds.x,.0004)&&bounds.x<g.t){float en,ex;vec3 ne,nx;if(coreIntersection(ro,rd,en,ex,ne,nx)&&ex>max(en,.0004)){float t=en>.0004?en:ex;if(t<g.t){g.t=t;g.id=2;g.n=en>.0004?ne:nx;}}}
 return g;
}
vec3 pathRadiance(vec3 origin,vec3 direction,out float firstDistance,out vec3 firstNormal){
 vec3 radiance=vec3(0),throughput=vec3(1);float previousPdf=0.;bool specular=true;int medium=0;
 firstDistance=60.;firstNormal=vec3(0);
 for(int bounce=0;bounce<10;bounce++){
  RayHit hit=closestTriangle(origin,direction,60.);float t=hit.triangle<0?60.:hit.t;
  GlassHit glass=glassIntersection(origin,direction,t);
  vec3 lightRadiance;float lightPdf;float lt=intersectLights(origin,direction,min(t,glass.t),lightRadiance,lightPdf);
  if(bounce>0&&lightPdf>0.){radiance+=throughput*lightRadiance*(specular?1.:powerHeuristic(previousPdf,lightPdf));break;}
  if(glass.id!=0){
   if(bounce==0){firstDistance=glass.t;firstNormal=glass.n;}
   if(medium>0)throughput*=exp(-(medium==1?vec3(.035,.011,.006):vec3(.10,.035,.018))*glass.t);
   vec3 p=origin+direction*glass.t,n=glass.n;bool entering=dot(direction,n)<0.;if(!entering)n=-n;
   float ior=glass.id==1?1.515:1.52,eta=entering?1./ior:ior,ci=max(0.,-dot(direction,n));
   vec3 td=refract(direction,n,eta);float ct=length(td)>.0001?abs(dot(td,n)):0.;
   float etai=entering?1.:ior,etat=entering?ior:1.;
   float rs=(etai*ci-etat*ct)/max(etai*ci+etat*ct,1e-8),rp=(etat*ci-etai*ct)/max(etat*ci+etai*ct,1e-8);
   float F=.5*(rs*rs+rp*rp);
   if(length(td)<.0001||randomF()<F){direction=reflect(direction,n);origin=p+n*.0008;}
   else{direction=td;origin=p-n*.0008;throughput*=eta*eta;medium=entering?glass.id:0;}
   specular=true;continue;
  }
  if(hit.triangle<0){radiance+=throughput*studioEnvironment(direction,0.);break;}
  if(bounce==0)firstDistance=hit.t;
  if(medium>0)throughput*=exp(-(medium==1?vec3(.035,.011,.006):vec3(.10,.035,.018))*hit.t);
  vec3 p=origin+direction*hit.t;SurfacePT m=materialAt(hit,direction);if(bounce==0)firstNormal=m.n;
  radiance+=throughput*(m.emission+sampleDirect(p,m,-direction));
  vec3 f;float pdf;vec3 next=sampleBSDF(m,-direction,pdf,f);float signedCosine=dot(m.n,next),cosine=m.id==13?abs(signedCosine):signedCosine;
  if(pdf<1e-10||cosine<=0.)break;
  throughput*=f*(cosine/pdf);previousPdf=pdf;specular=false;origin=p+m.n*.0015*(signedCosine>=0.?1.:-1.);direction=next;
  if(bounce>2){float survive=clamp(max(throughput.r,max(throughput.g,throughput.b)),.08,.95);if(randomF()>survive)break;throughput/=survive;}
 }
 return radiance;
}
void main(){
 clockTime=u_time;pixelFootprint=1./u_resolution.y;
 uvec2 ip=uvec2(gl_FragCoord.xy);seed=(ip.x*1973u+ip.y*9277u+uint(u_sample)*26699u+911u)^0x9e3779b9u;randomU();
 vec2 jitter=random2()-.5,pixel=gl_FragCoord.xy+jitter;
 vec2 q=(pixel-u_resolution*.5)/u_resolution.y-u_camera_lens.xy;
 vec3 ro=u_camera_origin,rd=normalize(u_camera_forward*u_camera_lens.z+u_camera_right*q.x+u_camera_up*q.y);
 if(u_physical_focus>.5){vec3 focal=ro+rd*(u_focus_distance/max(dot(rd,u_camera_forward),.01));vec2 disk=random2();float rr=sqrt(disk.x)*.023,phi=TAU*disk.y;ro+=(u_camera_right*cos(phi)+u_camera_up*sin(phi))*rr;rd=normalize(focal-ro);}
 float distance;vec3 firstNormal;vec3 c=pathRadiance(ro,rd,distance,firstNormal);
 // Fire remains a translucent emissive volume composite, not simulated fluid dynamics.
 c=integrateFlame(c,ro,rd,distance);
 // Firefly bounding is explicit and conservative; it is not an unbiased renderer.
 c=min(max(c,vec3(0)),vec3(24.));
 vec4 old=texelFetch(u_history,ivec2(gl_FragCoord.xy),0);
 float z=clamp(distance*dot(rd,u_camera_forward)/90.,0.,1.);
 float lum=dot(c,vec3(.2126,.7152,.0722));float moment=lum*lum;
 float w=1./float(u_sample+1);guideColor=vec4(firstNormal*.5+.5,u_sample==0?moment:mix(texelFetch(u_guide_history,ivec2(gl_FragCoord.xy),0).a,moment,w));
 fragColor=u_sample==0?vec4(c,z):mix(old,vec4(c,z),w);
}
