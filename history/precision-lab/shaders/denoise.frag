#version 300 es
precision highp float;
precision highp int;
uniform sampler2D u_input;
uniform sampler2D u_reference;
uniform sampler2D u_guide;
uniform vec2 u_resolution;
uniform float u_samples;
uniform int u_step;
out vec4 fragColor;
float luminance(vec3 c){return dot(c,vec3(.2126,.7152,.0722));}
vec3 normalOf(vec3 c){vec3 n=c*2.-1.;return n/max(length(n),1e-5);}
void main(){
 ivec2 p=ivec2(gl_FragCoord.xy),hi=ivec2(u_resolution)-1;
 vec4 center=texelFetch(u_input,p,0),reference=texelFetch(u_reference,p,0),g=texelFetch(u_guide,p,0);
 vec3 n=normalOf(g.rgb);float lum=luminance(reference.rgb);
 float var=max(0.,g.a-lum*lum)/max(1.,u_samples);
 // A-trous spatial reconstruction is explicitly biased. Depth and normals
 // prevent crossing silhouettes; luminance variance limits texture smoothing.
 float sigma2=max(.00008,6.*var+.0018*lum*lum);
 float depthScale=max(.00012,reference.a*float(u_step)*2.0/u_resolution.y);
 vec3 sum=vec3(0);float weight=0.;
 for(int y=-1;y<=1;y++)for(int x=-1;x<=1;x++){
  ivec2 q=clamp(p+ivec2(x,y)*u_step,ivec2(0),hi);
  vec4 c=texelFetch(u_input,q,0),r=texelFetch(u_reference,q,0),ng=texelFetch(u_guide,q,0);
  vec3 nn=normalOf(ng.rgb);float l=luminance(r.rgb),v=max(0.,ng.a-l*l)/max(1.,u_samples);
  float wn=pow(max(0.,dot(n,nn)),48.);
  if(dot(n,n)<.01&&dot(nn,nn)<.01)wn=1.;
  float wz=exp(-abs(reference.a-r.a)/depthScale);
  float wc=exp(-pow(l-lum,2.)/(sigma2+6.*v));
  float spatial=(x==0?2.:1.)*(y==0?2.:1.);
  float w=spatial*wn*wz*wc;if(x==0&&y==0)w=4.;
  sum+=c.rgb*w;weight+=w;
 }
 fragColor=vec4(sum/max(weight,1e-6),center.a);
}
