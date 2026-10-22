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
