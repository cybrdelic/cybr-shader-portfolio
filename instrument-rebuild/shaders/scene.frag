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


in vec3 v_irradiance;
in vec2 v_uv;
in vec3 v_world,v_normal;in vec2 v_lighting;in float v_ao;flat in float v_material;flat in float v_object;
uniform mat4 u_light_matrix;uniform highp sampler2DShadow u_shadow;uniform float u_shadow_texel;uniform highp sampler2D u_shadow_raw;
out vec4 fragColor;
float lavaFissures(vec3 p) {
    vec2 q=p.xz*5.4;
    q+=vec2(noise3(p*3.0+clockTime*0.035),noise3(p*3.0+17.0))*1.8;
    vec2 cell=floor(q),f=fract(q);
    float nearest=8.0,second=8.0;
    for(int j=-1;j<=1;j++)for(int i=-1;i<=1;i++) {
        vec2 g=vec2(i,j),site=g+0.03+0.94*vec2(hash31(vec3(cell+g,3)),hash31(vec3(cell+g,21)))-f;
        float d=dot(site,site);
        if(d<nearest){second=nearest;nearest=d;}else second=min(second,d);
    }
    return sqrt(second)-sqrt(nearest);
}
// Material response is in linear scene-referred units. Fine structure changes
// roughness at submillimetre-equivalent scale, not the overall silhouette.
struct Surface { vec3 base; float rough; float metal; vec3 emission; };
float filteredNoise(vec3 q) {
    float footprint=max(length(dFdx(q)),length(dFdy(q)));
    return mix(noise3(q),.5,smoothstep(.45,1.7,footprint));
}

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
    vec2 p=uv/size;vec2 fp=fwidth(p);int cell=int(floor(p.x));
    if(cell<0||cell>=32||p.y<-.12||p.y>1.50)return 0.;
    int c=LABEL_TEXT[phrase*32+cell];if(c==32)return 0.;
    vec2 q=vec2(fract(p.x)*.64,p.y/1.35);
    float aa=max(fp.x*.64,fp.y/1.35)*.60;
    return 1.-smoothstep(.043-aa,.043+aa,ufGlyph(q,c));
}

vec2 identityPlateUV(vec3 p){vec3 q=p-vec3(-1.05,.30,4.46);float c=cos(.28),s=sin(.28);q.yz=mat2(c,-s,s,c)*q.yz;return vec2(q.x+1.12,.53-q.z);}
float identityEngraving(vec3 p){vec2 uv=identityPlateUV(p);float text=engraving(uv-vec2(0,.55),6,.40);text=max(text,engraving(uv-vec2(.004,.34),7,.105));text=max(text,engraving(uv-vec2(.004,.17),8,.064));float rule=(1.-smoothstep(.002,.004,abs(uv.y-.486)))*step(0.,uv.x)*step(uv.x,2.22);return max(text,rule*.55);}
Surface surfaceAt(vec3 p,vec3 n,float materialId) {
    Surface m; m.base=vec3(.12);m.rough=.4;m.metal=0.;m.emission=vec3(0);
    int id=int(materialId+.5);
    float broad=filteredNoise(p*3.1);
    if(id==1){m.base=vec3(.065,.070,.074)*( .98+.04*broad);m.rough=.78;}
    else if(id==2){m.base=vec3(.012,.016,.021);m.rough=.335;m.metal=0.;}
    else if(id==3){m.base=vec3(.68,.37,.13)*(.985+.025*broad);m.rough=.31;m.metal=1.;}
    else if(id==4){m.base=vec3(.56,.59,.62);m.rough=.29;m.metal=1.;}
    else if(id==5){
        vec3 q=moduleLocal(p,5)-vec3(.30,1.15,.22);q.xz=rotation(.08)*q.xz;
        float flow=q.x*3.7+q.y*1.6+q.z*1.7+fbm3(q*3.3)*2.2;
        float vein=pow(1.-abs(sin(flow*3.)),25.);
        float hair=pow(1.-abs(sin(flow*13.+fbm3(q*12.)*.8)),60.);
        float cloud=fbm3(q*9.);
        m.base=mix(vec3(.48,.50,.49),vec3(.70,.682,.638),cloud);
        m.base=mix(m.base,vec3(.17,.19,.20),vein*.55+hair*.14);
        m.rough=.235+.035*filteredNoise(q*32.);
    }else if(id==6){
        vec3 q=moduleLocal(p,5)-vec3(-.06,1.39,-.29);q.xz=rotation(-.10)*q.xz;
        vec2 fiber=q.xz+vec2(1.23,.29);
        fiber+=vec2(noise3(q*vec3(5.,.65,5.)),noise3(q*vec3(5.,.65,5.)+31.))*.030;
        // Branch-knot distortion changes ring spacing and longitudinal grain together.
        float knot=exp(-pow((q.y-.27)/.17,2.)-pow((q.z+.11)/.11,2.));
        fiber.x+=.042*knot*sin(q.y*18.);fiber.y+=.014*knot;
        float growth=length(fiber*vec2(.92,1.))*137.;
        growth+=noise3(vec3(growth*.13,3.7,8.1))*1.5;
        float phase=fract(growth);float late=smoothstep(.70,.91,phase)*(1.-smoothstep(.92,.99,phase));
        float ringFilter=1.-smoothstep(.16,.8,fwidth(growth));late=mix(.19,late,ringFilter);
        float pore=pow(filteredNoise(q*vec3(300.,16.,300.)),6.);
        float fiberTone=filteredNoise(q*vec3(80.,1.5,80.));
        float body=filteredNoise(q*vec3(6.,.7,6.));
        m.base=mix(vec3(.052,.022,.008),vec3(.145,.065,.023),body);
        m.base*=.86+.22*fiberTone-.35*late-.75*pore;
        m.rough=.34+.08*late+.13*pore;
    }else if(id==7){m.base=vec3(.70,.682,.638);m.rough=.275;}
    else if(id==8){float g=fbm3(p*16.);m.base=mix(vec3(.028,.031,.032),vec3(.068,.071,.070),g);m.rough=.83;}
    else if(id==9){
        vec3 q=moduleLocal(p,4);float hot=clamp(.18+1.15*noise3(q*11.+vec3(0,clockTime*.25,0))+.2*noise3(q*37.),0.,1.);
        m.base=vec3(.045,.008,.001);m.rough=.38;
        m.emission=mix(vec3(.18,.004,.0002),vec3(1.70,.115,.002),hot);
    }else if(id==10){m.base=vec3(.012,.055,.057);m.rough=.06;m.metal=0.;}
    else if(id==11){
        vec3 q=moduleLocal(p,3);float strata=q.y*67.+q.x*14.+noise3(q*4.)*3.;
        float lamina=.5+.5*sin(strata),grain=filteredNoise(q*95.);
        float mineral=fbm3(q*13.);m.base=mix(vec3(.085,.094,.092),vec3(.23,.224,.193),mineral);
        m.base*=.83+.18*lamina+.14*grain;
        float vein=pow(1.-abs(sin(q.y*30.+q.x*13.+fbm3(q*5.)*2.)),20.);
        m.base=mix(m.base,vec3(.32,.30,.245),vein*.34);
        float wet=1.-smoothstep(.68,.83,q.y);m.base*=1.-wet*.43;m.rough=mix(.84,.28,wet);
    }else if(id==12){
        vec3 q=moduleLocal(p,6);float around=v_uv.x*TAU;
        float rib=sin(around*19.+noise3(vec3(v_uv.x*8.,v_uv.y*13.,7.))*3.4);
        float rift=pow(max(0.,1.-abs(rib)),8.);
        float scales=filteredNoise(vec3(v_uv*vec2(55,130),3.));
        float weather=filteredNoise(q*24.);
        m.base=mix(vec3(.063,.045,.027),vec3(.19,.155,.108),weather);
        m.base*=.74+.42*scales-.43*rift;
        m.rough=.89+.08*rift;
    }else if(id==13){
        vec2 uv=v_uv;float leaf=noise3(p*16.);
        float mid=exp(-pow((uv.y-.5)/.016,2.));
        float veins=pow(1.-abs(sin((uv.x-abs(uv.y-.5)*.52)*PI*13.)),20.);
        float edge=smoothstep(.30,.5,abs(uv.y-.5));
        float body=filteredNoise(vec3(uv*vec2(41,22),7.));
        m.base=mix(vec3(.020,.067,.007),vec3(.074,.165,.025),leaf)*(.88+.22*body);
        m.base=mix(m.base,m.base*vec3(1.45,1.18,.85),(mid*.65+veins*.20)*(1.-edge));
        m.base*=1.-edge*.18;m.rough=.39+.12*body;
    }
    else if(id==14){m.base=mix(vec3(.012,.022,.006),vec3(.043,.065,.016),filteredNoise(p*86.));m.rough=.95;}
    else if(id==15){m.base=vec3(.32,.12,.03);m.emission=vec3(2.2,.6,.08);m.rough=.31;}
    else if(id==16){m.base=vec3(.009,.011,.012);m.rough=.62;}
    else if(id==17){m.base=vec3(.76,.34,.155);m.rough=.29;m.metal=1.;}
    else if(id==18){m.base=vec3(.63,.65,.65);m.rough=.31;m.metal=1.;}
    else if(id==19){m.base=vec3(.022,.033,.036);m.rough=.34;m.metal=0.;}
    else if(id==20){m.base=vec3(.7,.66,.54);m.emission=vec3(1.2,1.07,.85);m.rough=.28;}
    else if(id==21){m.base=vec3(.011,.028,.032);m.rough=.065;m.metal=0.;}
    else if(id==22){float grain=fbm3(p*38.);m.base=mix(vec3(.008,.009,.009),vec3(.030,.026,.021),grain);m.rough=.86;
        float edge=1.-smoothstep(.940,.959,p.y);m.emission=vec3(.72,.032,.001)*edge*edge;}
    else if(id==23){vec3 q=moduleLocal(p,5);vec2 w=q.xz*125.;float aa=length(fwidth(w));
        float warp=pow(.5+.5*cos(w.x*PI),2.),weft=pow(.5+.5*cos(w.y*PI),2.);
        float plaid=mod(floor(w.x)+floor(w.y),2.);float fiber=mix(warp,weft,plaid);fiber=mix(fiber,.45,smoothstep(.5,1.5,aa));
        m.base=vec3(.016,.020,.024)*(.35+1.6*fiber);m.rough=.31+.17*(1.-fiber);m.metal=.25;}
    else if(id==26){m.base=vec3(.105,.081,.060);m.rough=.78;}
    else if(id==31){vec3 q=moduleLocal(p,4);float burnt=smoothstep(.78,.95,q.y)*(.5+.5*filteredNoise(q*18.));m.base=mix(vec3(.43,.385,.30),vec3(.052,.040,.032),burnt);m.rough=.86;}
    else if(id==32){vec3 q=moduleLocal(p,6);float variation=noise3(q*23.);m.base=mix(vec3(.028,.065,.022),vec3(.10,.20,.055),variation);m.rough=.48;m.metal=0.;}
    else if(id==33){m.base=vec3(.36,.39,.42);m.rough=.48;m.metal=1.;}
    else if(id==27){m.base=vec3(.19,.021,.008);m.rough=.48;}
    else if(id==28){m.base=vec3(.66,.69,.72);m.metal=1.;m.rough=.335;}
    else if(id==29){m.base=vec3(.35,.32,.25);m.rough=.46;}
    else if(id==30){m.base=mix(vec3(.018,.010,.006),vec3(.055,.033,.017),filteredNoise(p*50.));m.rough=.97;}
    else if(id==24||id==25){m.base=vec3(.58,.575,.535);m.rough=.36;m.metal=0.;
        float text=0.;
        if(id==24){vec3 q=moduleLocal(p,int(v_object+.5));vec2 uv=vec2(-q.z+.175,q.x-.775);text=engraving(uv,int(v_object+.5)-1,.021);}
        else {text=identityEngraving(p);}
        m.base=mix(m.base,vec3(.010,.015,.017),text);m.metal*=1.-text;}

    return m;
}

uniform highp sampler2DArray u_surface_color;
uniform highp sampler2DArray u_surface_normal;
in vec3 v_rest;

struct Detail {vec3 base; vec3 n; float rough; float ao;};
vec3 perturbNormal(vec3 n,vec3 p,vec2 uv,vec3 normalValue,float amount){
    // Cotangent frame keeps world geometry and surface UV handedness consistent.
    vec3 dp1=dFdx(p),dp2=dFdy(p);vec2 duv1=dFdx(uv),duv2=dFdy(uv);
    vec3 dp2perp=cross(dp2,n),dp1perp=cross(n,dp1);
    vec3 t=dp2perp*duv1.x+dp1perp*duv2.x;
    vec3 b=dp2perp*duv1.y+dp1perp*duv2.y;
    float inv=inversesqrt(max(max(dot(t,t),dot(b,b)),1e-16));
    vec3 sampled=normalValue*2.-1.;sampled.xy*=amount;
    return normalize(t*inv*sampled.x+b*inv*sampled.y+n*max(.1,sampled.z));
}
vec2 projectSurface(vec3 p,vec3 n){
    vec3 a=abs(n);
    if(a.y>=max(a.x,a.z))return p.xz;
    if(a.x>a.z)return vec2(p.z,p.y);
    return p.xy;
}
Detail physicalDetail(vec3 p,vec3 n,Surface m){
    int id=int(v_material+.5),objectId=int(v_object+.5);
    vec3 q=objectId>=1&&objectId<=6?moduleLocal(v_rest,objectId):v_rest;
    vec3 localNormal=n;
    if(objectId>=1&&objectId<=6){vec2 a=moduleAxis(objectId);localNormal.xz=vec2(dot(n.xz,a),dot(n.xz,vec2(-a.y,a.x)));}
    Detail d;d.base=m.base;d.n=n;d.rough=m.rough;d.ao=1.;
    int layer=-1;vec2 uv=projectSurface(q,localNormal);float bump=.7;
    if(id==1){layer=-1;}
    if(id==2||id==3||id==4||id==17||id==18||id==28){
        layer=0;
        // All revolved parts share concentric lathe-tool marks on end faces.
        float radius=length(q.xz);float theta=atan(q.z,q.x)/TAU;
        uv=abs(localNormal.y)>.65?vec2(theta*4.,radius*2.8):vec2(theta*4.,q.y*2.5);
        bump=.012;
    }
    if(id==7){layer=1;uv*=2.3;bump=.045;}
    if(id==6){layer=2;uv=vec2(q.x*1.3+q.z*.7,q.y*.42);bump=.28;}
    if(id==11){layer=3;uv*=1.0;bump=.55;}
    if(id==12){layer=4;uv=v_uv*vec2(1.7,2.7);bump=.35;}
    if(id==5){layer=5;uv=vec2(q.x*.9+q.z*.5,q.y*.62);bump=.32;}
    if(id==8||id==22){layer=6;uv*=2.5;bump=.85;}
    if(layer>=0){
        vec4 a=texture(u_surface_color,vec3(uv,float(layer)));
        vec4 b=texture(u_surface_normal,vec3(uv,float(layer)));
        d.n=perturbNormal(n,p,uv,b.rgb,bump);d.ao=b.a;
        if(id==2||id==3||id==4||id==17||id==18||id==28){
            d.base=m.base*(.98+.025*(a.r/.68));
            d.rough=m.rough+(a.a-.32)*.24;
            // Handled metal has low-frequency oil variation, not uniform glitter.
            d.rough+=.009*sin(q.x*6.2+q.y*8.1)*sin(q.z*9.7+q.y*2.6);
        }else if(id==7){d.base=vec3(.64,.620,.580)*(a.rgb/.78);d.rough=.295+(a.a-.26)*.22;}
        else {d.base=a.rgb;d.rough=a.a;}
        if(id==11){float wet=1.-smoothstep(.7,.86,q.y);d.base*=1.-wet*.38;d.rough=mix(d.rough,.23,wet);}
    }
    if(id==11){
        vec3 w=pow(abs(localNormal),vec3(5.));w/=max(dot(w,vec3(1)),.0001);
        vec4 ax=texture(u_surface_color,vec3(q.zy*2.4,3.)),ay=texture(u_surface_color,vec3(q.xz*2.4,3.)),az=texture(u_surface_color,vec3(q.xy*2.4,3.));
        vec4 al=ax*w.x+ay*w.y+az*w.z;
        float layer=q.y*.78+q.x*.43+q.z*.21+.025*noise3(q*5.7);
        float mineral=noise3(vec3(layer*41.,q.x*8.,q.z*9.));
        float grain=filteredNoise(q*185.);
        vec3 slate=mix(vec3(.083,.092,.100),vec3(.20,.205,.196),mineral);
        float quartz=pow(clamp(1.-abs(noise3(vec3(layer*17.,q.x*3.,q.z*3.))-.49)*24.,0.,1.),6.);
        slate=mix(slate,vec3(.39,.38,.33),quartz*.42);
        float oxide=pow(max(noise3(q*6.5)-.52,0.)*2.3,2.);
        d.base=mix(slate,vec3(.16,.080,.035),clamp(oxide*.55,0.,.26))*(.88+.20*grain);
        d.rough=.72+.17*(1.-grain);d.ao=mix(1.,d.ao,.55);
    }
    if(id==6 && abs(localNormal.y)>.72){
        vec2 end=q.xz-vec2(-.31,-.22);float warped=length(end*vec2(1.,1.22)+.006*sin(end.yx*33.));
        float ring=sin(warped*330.+noise3(q*12.)*1.5),grain=filteredNoise(q*175.);
        d.base=mix(vec3(.065,.027,.011),vec3(.19,.10,.044),.48+.25*ring+.17*grain);d.rough=.47;
    }
    // Flow directions on the liquid surface; no noisy faceted 'plastic' water.
    if(id==10){vec2 uv=q.xz;float r=length(uv-vec2(.08,.05));
        vec2 grad=normalize(uv-vec2(.08,.05))*.012*sin(r*37.-clockTime*1.4);
        grad+=.006*vec2(sin(q.z*34.+clockTime*.7),sin(q.x*29.-clockTime*.9));
        d.n=normalize(n+vec3(grad.x,0,grad.y));d.base=vec3(.005,.015,.017);d.rough=.075;
    }
    if(id==13){
        vec2 uv=v_uv;
        vec4 al=texture(u_surface_color,vec3(uv,7.));
        vec4 nm=texture(u_surface_normal,vec3(uv,7.));
        d.base=al.rgb;d.rough=al.a;d.n=perturbNormal(n,p,uv,nm.rgb,.62);d.ao=nm.a;
    }
    d.rough=clamp(d.rough,.055,.95);return d;
}
uniform highp samplerCube u_environment;
uniform vec3 u_irradiance[9];
vec3 irradiance(vec3 n){
    return max(vec3(0),u_irradiance[0]*.2820947918+
    u_irradiance[1]*(.4886025119*n.y)+u_irradiance[2]*(.4886025119*n.z)+u_irradiance[3]*(.4886025119*n.x)+
    u_irradiance[4]*(1.092548431*n.x*n.y)+u_irradiance[5]*(1.092548431*n.y*n.z)+
    u_irradiance[6]*(.3153915653*(3.*n.z*n.z-1.))+u_irradiance[7]*(1.092548431*n.x*n.z)+
    u_irradiance[8]*(.5462742153*(n.x*n.x-n.y*n.y)));
}

uniform highp sampler2DArray u_probe_cache;
uniform bool u_have_probes;
vec4 probeReflection(vec3 d,float rough){
    vec3 origin=moduleCenter(int(v_object+.5))+vec3(0,v_object<1.5?1.59:1.35,0);
    if(v_object>6.5||v_object<.5)origin=vec3(0,2.14,0);
    vec3 bmin=vec3(-5.,-.18,-5.),bmax=vec3(5.,7.,5.);
    vec3 inv=sign(d)/max(abs(d),vec3(.0001));
    vec3 exitT=max((bmin-v_world)*inv,(bmax-v_world)*inv);
    float hit=min(exitT.x,min(exitT.y,exitT.z));
    if(hit>0.)d=normalize(v_world+d*hit-origin);
    vec3 a=abs(d);vec2 uv;float face;
    if(a.x>=a.y&&a.x>=a.z){face=d.x>0.?0.:1.;uv=vec2(d.x>0.?-d.z:d.z,-d.y)/a.x;}
    else if(a.y>=a.z){face=d.y>0.?2.:3.;uv=vec2(d.x,d.y>0.?d.z:-d.z)/a.y;}
    else{face=d.z>0.?4.:5.;uv=vec2(d.z>0.?d.x:-d.x,-d.y)/a.z;}
    int objectId=int(v_object+.5);int layer=objectId>=1&&objectId<=6?objectId-1:6;
    return textureLod(u_probe_cache,vec3(uv*.5+.5,float(layer*6)+face),rough*8.);
}

vec3 studioEnvironment(vec3 r,float rough){vec3 c=textureLod(u_environment,r,rough*9.).rgb;float room=.022+.040*smoothstep(-.6,.8,r.y);return c+vec3(room*1.02,room,room*.98);}
vec3 viewBackground(vec3 r){return mix(vec3(.020,.025,.030),vec3(.009,.014,.020),smoothstep(-.12,.8,r.y));}
vec3 schlick(float c,vec3 f0){return f0+(1.-f0)*pow(clamp(1.-c,0.,1.),5.);}
vec2 envBRDF(float rough,float nv){vec4 r=rough*vec4(-1.,-.0275,-.572,.022)+vec4(1.,.0425,1.04,-.04);float a=min(r.x*r.x,exp2(-9.28*nv))*r.x+r.y;return vec2(-1.04,1.04)*a+r.zw;}

float shadowVisibility(vec3 p,vec3 n){
 vec4 q=u_light_matrix*vec4(p+n*.0018,1);vec3 uv=q.xyz/q.w*.5+.5;
 if(any(lessThan(uv,vec3(0)))||any(greaterThan(uv,vec3(1))))return 1.;
 float bias=.00022+.00035*(1.-max(dot(n,normalize(vec3(-4.5,7.9,6.5))),0.));
 const vec2 taps[12]=vec2[](vec2(-.326,-.406),vec2(-.840,-.074),vec2(-.696,.457),vec2(-.203,.621),vec2(.962,-.195),vec2(.473,-.480),vec2(.519,.767),vec2(.185,-.893),vec2(.507,.064),vec2(.896,.412),vec2(-.322,-.933),vec2(-.792,-.598));
 float blockers=0.,sum=0.;
 for(int i=0;i<6;i++){float z=texture(u_shadow_raw,uv.xy+taps[i]*.017).r;if(z<uv.z-bias){sum+=z;blockers+=1.;}}
 if(blockers==0.)return 1.;
 float penumbra=clamp((uv.z-sum/blockers)*.62,.00085,.028);
 float lit=0.;for(int i=0;i<12;i++)lit+=texture(u_shadow,vec3(uv.xy+taps[i]*penumbra,uv.z-bias));
 return lit/12.;
}
uniform bool u_linear_hdr;
vec4 encodeHDR(vec3 c){if(u_linear_hdr)return vec4(c,1.);c=clamp(c/16.,0.,1.);float m=max(max(c.r,c.g),max(c.b,1./255.));m=ceil(m*255.)/255.;return vec4(c/m,m);}

// Solid-angle area-light approximation with independently baked visibility.
float areaIrradiance(vec3 p,vec3 n,vec3 center,vec2 halfSize){
 vec3 delta=center-p;float d=length(delta);vec3 l=delta/max(d,.001);
 vec3 ln=normalize(vec3(0,1,0)-center);float emit=max(dot(-l,ln),0.);
 float omega=4.*atan(halfSize.x*halfSize.y/(d*sqrt(d*d+dot(halfSize,halfSize))));
 return omega*emit*max(dot(n,l),0.);
}

// Stable anisotropic reflection broadening in the tangent direction. The
// roughness-squared distribution is filtered offline in the radiance maps.
// Mathematical GGX lobe fit generated by studio/fit_area_lights.py.
// Polygon integration is constant work per light; no shadow rays or path history.
uniform highp sampler2DArray u_area_lut;
float polygonIntegral(vec3 P,vec3 N,vec3 V,mat3 Mi,vec3 center,vec2 halfSize){
    vec3 ln=normalize(vec3(0,1,0)-center);
    if(dot(ln,P-center)<=0.)return 0.;
    vec3 lu=normalize(cross(vec3(0,1,0),ln));vec3 lv=cross(ln,lu);
    vec3 T=V-N*dot(V,N);T=dot(T,T)<1e-7?normalize(cross(N,abs(N.y)<.9?vec3(0,1,0):vec3(1,0,0))):normalize(T);
    vec3 B=cross(N,T);mat3 transform=Mi*transpose(mat3(T,B,N));
    vec3 corners[4];corners[0]=transform*(center-lu*halfSize.x-lv*halfSize.y-P);
    corners[1]=transform*(center+lu*halfSize.x-lv*halfSize.y-P);
    corners[2]=transform*(center+lu*halfSize.x+lv*halfSize.y-P);
    corners[3]=transform*(center-lu*halfSize.x+lv*halfSize.y-P);
    // Exact clipping to the lobe's positive hemisphere before spherical integration.
    vec3 clipped[8];int count=0;
    for(int i=0;i<4;i++){
      vec3 a=corners[i],b=corners[(i+1)%4];bool ia=a.z>0.,ib=b.z>0.;
      if(ia)clipped[count++]=a;
      if(ia!=ib)clipped[count++]=mix(a,b,-a.z/(b.z-a.z));
    }
    if(count<3)return 0.;
    for(int i=0;i<8;i++){if(i>=count)break;clipped[i]=normalize(clipped[i]);}
    float sum=0.;for(int i=0;i<8;i++){
      if(i>=count)break;vec3 a=clipped[i],b=clipped[(i+1)%count];float d=clamp(dot(a,b),-.999999,.999999);
      sum+=cross(a,b).z*acos(d)*inversesqrt(max(1.-d*d,1e-8));
    }
    return abs(sum)/(2.*PI);
}
vec3 areaSurface(vec3 p,vec3 n,vec3 v,vec3 base,vec3 f0,float metal,float rough,vec3 center,vec2 size,vec3 radiance,float visibility){
    float nv=max(dot(n,v),.035);vec2 uv=vec2(clamp((rough-.10)/.85,0.,1.),sqrt(1.-nv));uv=uv*(31./32.)+vec2(.5/32.);
    vec4 a=texture(u_area_lut,vec3(uv,0.)),b=texture(u_area_lut,vec3(uv,1.));
    mat3 invM=mat3(a.x,0.,a.w,0.,a.z,0.,a.y,0.,b.x);
    float specular=polygonIntegral(p,n,v,invM,center,size);
    float diffuse=polygonIntegral(p,n,v,mat3(1.),center,size);
    vec3 specScale=f0*b.y+(1.-f0)*b.z;
    // Schlick's hemispherical average prevents direct diffuse/specular double counting.
    vec3 diffScale=base*(1.-metal)*(1.-f0)*(.96);
    return radiance*visibility*(specScale*specular+diffScale*diffuse);
}

vec3 roomFill(vec3 r){return mix(vec3(.018,.022,.028),vec3(.042,.047,.055),.5+.5*r.y);}
void main(){
    clockTime=u_time;pixelFootprint=1./u_resolution.y;
    if(v_material>20.5&&v_material<21.5&&v_object>6.5)discard;
    vec3 p=v_world,gn=normalize(v_normal),v=normalize(u_camera_origin-p);
    if(dot(gn,v)<0.)gn=-gn;
    if(v_material>10.5&&v_material<11.5){vec3 face=normalize(cross(dFdx(p),dFdy(p)));if(dot(face,gn)<0.)face=-face;gn=normalize(mix(gn,face,.05));}
    Surface m=surfaceAt(p,gn,v_material);
    Detail d=physicalDetail(p,gn,m);vec3 n=d.n;m.base=d.base;m.rough=d.rough;
    vec3 dx=dFdx(n),dy=dFdy(n);
    float variance=.12*(dot(dx,dx)+dot(dy,dy));
    m.rough=sqrt(clamp(m.rough*m.rough+min(variance,.12),.004,1.));
    float nv=max(dot(n,v),.001),ao=clamp(v_ao*d.ao,.02,1.);
    vec3 f0=mix(vec3(.04),m.base,m.metal),f=schlick(nv,f0);
    vec3 f0Physical=f0;
    if(v_material>1.5&&v_material<2.5)f0Physical=vec3(.047,.049,.052);
    vec3 result=areaSurface(p,n,v,m.base,f0Physical,m.metal,m.rough,vec3(-3.8,7.5,5.4),vec2(2.6,1.85),vec3(9.0,8.65,8.05),v_lighting.x);
    result+=areaSurface(p,n,v,m.base,f0Physical,m.metal,m.rough,vec3(5.2,4.5,-2.7),vec2(1.6,2.6),vec3(2.2,2.50,2.90),v_lighting.y);
    vec3 diffuse=m.base*(1.-m.metal)*(1.-f)*(v_irradiance*.74/PI+vec3(.012,.014,.017)*ao);
    vec3 reflection=reflect(-v,n),ambientSpec=roomFill(reflection);
    if(u_have_probes){vec4 capture=probeReflection(reflection,m.rough);ambientSpec=mix(ambientSpec,capture.rgb,clamp(capture.a,0.,1.)*.52);}
    vec2 dfg=envBRDF(m.rough,nv);
    float specAO=clamp(pow(nv+ao,exp2(-16.*m.rough-1.))-1.+ao,0.,1.);
    result+=diffuse+ambientSpec*(f0Physical*dfg.x+dfg.y)*specAO+m.emission;
    if((v_material>12.5&&v_material<13.5)||(v_material>31.5&&v_material<32.5)){
        float back=areaIrradiance(p,-n,vec3(-3.8,7.5,5.4),vec2(2.6,1.85));
        result+=m.base*vec3(3.7,4.8,2.0)*back*(.25+.75*ao);
    }
    if(v_material>9.5&&v_material<10.5)result+=vec3(.004,.009,.008)*(1.-f)*ao;
    vec3 hot=moduleCenter(4)+vec3(0,1.10,0)-p;
    result+=m.base*(1.-m.metal)*vec3(.48,.038,.001)*max(dot(n,normalize(hot)),0.)/(.3+dot(hot,hot)*7.);
    // A subtle room haze applies only to the sweep, not a grey overlay on metals.
    float distanceToCamera=length(p-u_camera_origin);
    float fog=1.-exp(-distanceToCamera*distanceToCamera*(v_material<1.5?.00010:0.));
    result=mix(result,viewBackground(-v),fog);
    fragColor=encodeHDR(max(result,vec3(0)));
}
