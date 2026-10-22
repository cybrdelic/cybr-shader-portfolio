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
float rayArea(vec3 p,vec3 n,vec3 center,vec2 halfSize){
    vec3 delta=center-p;float d=length(delta);vec3 l=delta/max(d,.001);vec3 ln=normalize(vec3(0,1,0)-center);
    float omega=4.*atan(halfSize.x*halfSize.y/(d*sqrt(d*d+dot(halfSize,halfSize))));
    return omega*max(dot(-l,ln),0.)*max(dot(n,l),0.);
}
vec2 rayBRDF(float r,float nv){vec4 a=r*vec4(-1.,-.0275,-.572,.022)+vec4(1.,.0425,1.04,-.04);float b=min(a.x*a.x,exp2(-9.28*nv))*a.x+a.y;return vec2(-1.04,1.04)*b+a.zw;}
vec3 traceIncidentRadiance(vec3 origin,vec3 direction,float rough){
    RayHit hit=closestTriangle(origin,direction,60.);
    if(hit.triangle<0)return studioEnvironment(direction,rough);
    uvec3 ix=traceTriangle(hit.triangle).xyz;vec3 bary=vec3(1.-hit.bary.x-hit.bary.y,hit.bary);
    vec4 pos=interpolateRayAttribute(u_ray_positions,ix,bary);
    int meta=int(traceFetch(u_ray_positions,int(ix.x)).w+.5),id=meta%32,objectId=meta/32;
    vec4 normalAO=interpolateRayAttribute(u_ray_normals,ix,bary);
    vec4 attr=interpolateRayAttribute(u_ray_attributes,ix,bary);
    vec3 bounce=interpolateRayAttribute(u_ray_irradiance,ix,bary).rgb;
    vec3 pivot,axis;float angle;rayPartInfo(hit.part,pivot,axis,angle);
    vec3 p=origin+direction*hit.t,n=normalize(rayRotation(normalAO.xyz,axis,angle));
    if(dot(n,direction)>0.)n=-n;
    vec3 q=objectId>=1&&objectId<=6?moduleLocal(pos.xyz,objectId):pos.xyz;
    vec3 base=vec3(.11),emit=vec3(0);float metal=0.,r=.55;int layer=-1;vec2 uv=raySurfaceUV(q,n);
    if(id==1){layer=7;uv*=.22;r=.8;}
    else if(id==2){base=vec3(.018,.023,.026);metal=.16;r=.32;}
    else if(id==3){base=vec3(.64,.44,.24);metal=1.;r=.22;}
    else if(id==4){base=vec3(.62,.66,.69);metal=1.;r=.245;}
    else if(id==5){layer=5;uv=vec2(q.x*.9+q.z*.5,q.y*.62);}
    else if(id==6){layer=2;uv=vec2(q.x*1.7+q.z*.3,q.y*.58);}
    else if(id==7){base=vec3(.65,.65,.62);r=.275;}
    else if(id==8||id==22){layer=6;uv*=2.5;}
    else if(id==9){base=vec3(.03,.006,0);emit=vec3(1.65,.14,.001);r=.4;}
    else if(id==10){base=vec3(.005,.015,.017);r=.075;}
    else if(id==11){layer=3;}
    else if(id==12){layer=4;uv=attr.zw*vec2(2.8,3.5);}
    else if(id==13){base=vec3(.034,.085,.008);r=.39;}
    else if(id==14){base=vec3(.025,.040,.010);r=.95;}
    else if(id==16){base=vec3(.009,.011,.012);r=.62;}
    else if(id==17){base=vec3(.75,.38,.20);metal=1.;r=.29;}
    else if(id==18||id==24||id==25){base=vec3(.53,.54,.515);metal=.7;r=.31;}
    else if(id==19){base=vec3(.022,.033,.036);r=.34;}
    if(layer>=0){vec4 t=textureLod(u_surface_color,vec3(uv,float(layer)),clamp(1.+rough*6.+hit.t*.15,1.,6.));base=t.rgb;r=t.a;}
    float nv=max(dot(n,-direction),.001);vec3 f0=mix(vec3(.04),base,metal);
    vec3 fresnel=f0+(1.-f0)*pow(1.-nv,5.);
    float key=rayArea(p,n,vec3(-3.8,7.5,5.4),vec2(3.2,2.2))*attr.x;
    float fill=rayArea(p,n,vec3(5.2,4.5,-2.7),vec2(1.6,2.6))*attr.y;
    vec3 irradiance=bounce*.62+vec3(6.0,5.72,5.28)*key+vec3(1.05,1.18,1.37)*fill;
    vec2 brdf=rayBRDF(r,nv);float ao=clamp(normalAO.w,.05,1.);
    float specAO=clamp(pow(nv+ao,exp2(-16.*r-1.))-1.+ao,0.,1.);
    vec3 diffuse=irradiance*base*(1.-metal)/PI*(1.-fresnel);
    vec3 spec=studioEnvironment(reflect(direction,n),max(r,rough))*(f0*brdf.x+brdf.y)*specAO;
    return max(vec3(0),diffuse+spec+emit);
}
