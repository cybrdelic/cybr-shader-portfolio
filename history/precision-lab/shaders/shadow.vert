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

layout(location=0)in vec3 a_position;layout(location=1)in vec3 a_normal;layout(location=2)in vec4 a_meta;uniform mat4 u_light_matrix;

vec3 axisRotate(vec3 p,vec3 axis,float a){float c=cos(a),s=sin(a);return p*c+cross(axis,p)*s+axis*dot(axis,p)*(1.-c);}
void transformPart(inout vec3 p,inout vec3 n,float part,float mat){
    if(part>.5&&part<1.5){vec2 ax=moduleAxis(1);vec3 pivot=moduleCenter(1)+vec3(0,1.59,0),axis=normalize(vec3(ax.x*.943,.334,ax.y*.943));float a=.055*sin(u_time*.19);p=pivot+axisRotate(p-pivot,axis,a);n=axisRotate(n,axis,a);}
    else if(part>1.5&&part<2.5){vec3 pivot=moduleCenter(2)+vec3(0,1.1,0);float a=u_time*.28;p=pivot+axisRotate(p-pivot,vec3(0,1,0),a);n=axisRotate(n,vec3(0,1,0),a);}
    else if(part>2.5&&part<3.5){vec3 pivot=vec3(0,2.14,0),axis=normalize(vec3(1,.4,.2));float a=.06*sin(u_time*.15);p=pivot+axisRotate(p-pivot,axis,a);n=axisRotate(n,axis,a);}
    if(mat>9.5&&mat<10.5){vec3 q=moduleLocal(p,3);p.y+=.0015*(sin(q.x*15.+u_time*.67)*sin(q.z*12.-u_time*.42)-sin(q.x*15.)*sin(q.z*12.));}
}

vec4 cameraProject(vec3 p){vec3 q=p-u_camera_origin;float z=dot(q,u_camera_forward);float x=dot(q,u_camera_right),y=dot(q,u_camera_up);float a=u_resolution.x/u_resolution.y;
 return vec4(2.*(u_camera_lens.z*x+u_camera_lens.x*z)/a,2.*(u_camera_lens.z*y+u_camera_lens.y*z),1.0013342228152102*z-.120080053368913, z);}

void main(){vec3 p=a_position,n=a_normal;transformPart(p,n,a_meta.z,a_meta.x);gl_Position=u_light_matrix*vec4(p,1);}
