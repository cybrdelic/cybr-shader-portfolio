// Offline, deterministic cosine-hemisphere visibility bake. Approximate static
// ambient occlusion only; it is not a global-illumination solution.
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <numeric>
#include <vector>
#include <chrono>
#include <omp.h>
struct V{float x,y,z;V operator+(V a)const{return{x+a.x,y+a.y,z+a.z};}V operator-(V a)const{return{x-a.x,y-a.y,z-a.z};}V operator*(float s)const{return{x*s,y*s,z*s};}float operator[](int i)const{return i==0?x:i==1?y:z;}};
float dot(V a,V b){return a.x*b.x+a.y*b.y+a.z*b.z;}V cross(V a,V b){return{a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x};}V norm(V a){return a*(1/std::max(1e-12f,std::sqrt(dot(a,a))));}V vmin(V a,V b){return{std::min(a.x,b.x),std::min(a.y,b.y),std::min(a.z,b.z)};}V vmax(V a,V b){return{std::max(a.x,b.x),std::max(a.y,b.y),std::max(a.z,b.z)};}
struct Tri{V p,e1,e2,lo,hi,c;};struct Node{V lo,hi;int left=-1,right=-1,start=0,count=0;};
std::vector<Tri>T;std::vector<uint32_t>order;std::vector<Node>nodes;
int build(int start,int end){Node n;n.lo={1e10,1e10,1e10};n.hi={-1e10,-1e10,-1e10};V lo=n.lo,hi=n.hi;for(int i=start;i<end;i++){auto&t=T[order[i]];n.lo=vmin(n.lo,t.lo);n.hi=vmax(n.hi,t.hi);lo=vmin(lo,t.c);hi=vmax(hi,t.c);}int idx=nodes.size();nodes.push_back(n);if(end-start<=8){nodes[idx].start=start;nodes[idx].count=end-start;return idx;}V e=hi-lo;int axis=e.x>e.y?(e.x>e.z?0:2):(e.y>e.z?1:2),mid=(start+end)/2;std::nth_element(order.begin()+start,order.begin()+mid,order.begin()+end,[&](int a,int b){return T[a].c[axis]<T[b].c[axis];});int l=build(start,mid),r=build(mid,end);nodes[idx].left=l;nodes[idx].right=r;return idx;}
bool boxHit(const Node&n,V o,V inv,float maxT){float low=0,high=maxT;for(int k=0;k<3;k++){float a=(n.lo[k]-o[k])*inv[k],b=(n.hi[k]-o[k])*inv[k];low=std::max(low,std::min(a,b));high=std::min(high,std::max(a,b));}return high>=low;}
float ray(V o,V d,float distance=1.2f,bool anyHit=false){V inv{1/(std::abs(d.x)<1e-9f?1e-9f:d.x),1/(std::abs(d.y)<1e-9f?1e-9f:d.y),1/(std::abs(d.z)<1e-9f?1e-9f:d.z)};float nearest=distance;int stack[96],top=1;stack[0]=0;while(top){const Node&n=nodes[stack[--top]];if(!boxHit(n,o,inv,nearest))continue;if(n.count){for(int i=0;i<n.count;i++){const auto&t=T[order[n.start+i]];V h=cross(d,t.e2);float det=dot(t.e1,h);if(std::abs(det)<1e-10f)continue;float f=1/det;V s=o-t.p;float u=f*dot(s,h);if(u<0||u>1)continue;V q=cross(s,t.e1);float v=f*dot(d,q);if(v<0||u+v>1)continue;float tt=f*dot(t.e2,q);if(tt>1e-5f&&tt<nearest){nearest=tt;if(anyHit)return nearest;}}}else{stack[top++]=n.left;stack[top++]=n.right;}}return nearest;}
float radical(uint32_t a){a=(a<<16)|(a>>16);a=((a&0x55555555)<<1)|((a&0xaaaaaaaa)>>1);a=((a&0x33333333)<<2)|((a&0xcccccccc)>>2);a=((a&0x0f0f0f0f)<<4)|((a&0xf0f0f0f0)>>4);a=((a&0x00ff00ff)<<8)|((a&0xff00ff00)>>8);return a*2.3283064365386963e-10f;}
uint32_t hash(uint32_t x){x^=x>>16;x*=0x7feb352d;x^=x>>15;x*=0x846ca68b;x^=x>>16;return x;}

struct Vertex{V p,n;float ao,key,fill;int mat;};
std::vector<Vertex>vertices;std::vector<std::array<uint32_t,3>>triangleVertices;
struct Hit{int index=-1;float t=60,u=0,v=0;};
Hit nearestHit(V o,V d){Hit hit;V inv{1/(std::abs(d.x)<1e-9f?1e-9f:d.x),1/(std::abs(d.y)<1e-9f?1e-9f:d.y),1/(std::abs(d.z)<1e-9f?1e-9f:d.z)};int stack[96],top=1;stack[0]=0;
while(top){auto&node=nodes[stack[--top]];if(!boxHit(node,o,inv,hit.t))continue;
if(node.count){for(int j=0;j<node.count;j++){int id=order[node.start+j];if(vertices[triangleVertices[id][0]].mat==21)continue;auto&t=T[id];V h=cross(d,t.e2);float det=dot(t.e1,h);if(std::abs(det)<1e-10f)continue;float f=1/det;V s=o-t.p;float u=f*dot(s,h);if(u<0||u>1)continue;V q=cross(s,t.e1);float v=f*dot(d,q);if(v<0||u+v>1)continue;float tt=f*dot(t.e2,q);if(tt>.0001f&&tt<hit.t)hit={id,tt,u,v};}}
else{stack[top++]=node.left;stack[top++]=node.right;}}return hit;}
V times(V a,V b){return{a.x*b.x,a.y*b.y,a.z*b.z};}
V ambient(V d){float y=std::clamp(d.y*.5f+.5f,0.f,1.f),x=.030f+.060f*std::pow(y,1.3f);return{.92f*x,.98f*x,1.06f*x};}
float solidAngle(V p,V n,V center,float w,float h){V delta=center-p;float d=std::sqrt(dot(delta,delta));V l=delta*(1/d),ln=norm(V{0,1,0}-center);return 4*std::atan(w*h/(d*std::sqrt(d*d+w*w+h*h)))*std::max(dot(l,n),0.f)*std::max(dot(l*(-1),ln),0.f);}
V materialColor(int mat){switch(mat){case 1:return{.028,.032,.035};case 2:return{.065,.073,.080};case 3:return{.64,.395,.175};case 4:return{.69,.72,.75};case 5:return{.55,.56,.53};case 6:return{.10,.048,.019};case 7:return{.66,.646,.610};case 8:return{.045,.048,.047};case 9:return{.045,.008,.001};case 10:return{.012,.055,.057};case 11:return{.155,.158,.139};case 12:return{.12,.091,.061};case 13:return{.045,.118,.016};case 14:return{.024,.046,.010};case 16:return{.009,.011,.012};case 17:return{.75,.38,.2};case 18:return{.63,.65,.65};case 19:return{.022,.033,.036};case 22:return{.018,.016,.012};case 23:return{.016,.020,.024};case 26:return{.085,.078,.062};case 27:return{.19,.021,.008};case 28:return{.59,.62,.65};case 29:return{.35,.32,.25};case 30:return{.032,.019,.009};default:return{.53,.54,.515};}}
V reflectedRoom(V d){V result=ambient(d);const V facing[3]={{-3.8f,6.5f,5.4f},{5.2f,3.5f,-2.7f},{-2,4,-5}};const V color[3]={{7.5,7.1,6.6},{1.65,1.95,2.4},{2,2.1,2.2}};float w[3]={.37,.25,.065},h[3]={.255,.40,.55};for(int i=0;i<3;i++){V n=norm(facing[i]),u=norm(cross(V{0,1,0},n)),v=cross(n,u);float front=dot(d,n);if(front<=0)continue;float x=dot(d,u)/front,y=dot(d,v)/front,e=std::max(std::abs(x)-w[i],std::abs(y)-h[i]);float a=std::clamp((.045f-e)/.09f,0.f,1.f);a=a*a*(3-2*a);result=result+color[i]*(a*.93f);}return result;}
V outgoing(const Hit&hit,V d){auto ix=triangleVertices[hit.index];float w=1-hit.u-hit.v;auto&a=vertices[ix[0]];auto&b=vertices[ix[1]];auto&c=vertices[ix[2]];V p=a.p*w+b.p*hit.u+c.p*hit.v,n=norm(a.n*w+b.n*hit.u+c.n*hit.v);if(dot(n,d)>0)n=n*(-1);float ao=a.ao*w+b.ao*hit.u+c.ao*hit.v,key=a.key*w+b.key*hit.u+c.key*hit.v,fill=a.fill*w+b.fill*hit.u+c.fill*hit.v;int m=a.mat;V albedo=materialColor(m);
if(m==2||m==3||m==4||m==17||m==18||m==28){V reflected=d-n*(2*dot(d,n));return times(reflectedRoom(reflected),albedo)*std::max(.25f,ao);}
float ek=solidAngle(p,n,{-3.8,7.5,5.4},2.6,1.85)*key,ef=solidAngle(p,n,{5.2,4.5,-2.7},1.6,2.6)*fill;
if(m==13)ek+=solidAngle(p,n*(-1),{-3.8,7.5,5.4},2.6,1.85)*key*.45f;
V total=ambient(n)*(3.14159265f*ao)+V{10.0,9.45,8.70}*ek+V{.68,.82,1.05}*ef;
V value=times(total,albedo)*(1/3.14159265f);if(m==9)value=value+V{1.45,.12,.002};return value;}
int main(int argc,char**argv){if(argc!=3)return 2;std::ifstream in(argv[1],std::ios::binary);std::vector<char>data((std::istreambuf_iterator<char>(in)),{});if(data.size()<16)return 3;uint32_t nv,ni,stride;memcpy(&nv,data.data()+4,4);memcpy(&ni,data.data()+8,4);memcpy(&stride,data.data()+12,4);if(stride!=28||data.size()!=16+size_t(nv)*stride+size_t(ni)*4)return 4;vertices.resize(nv);for(uint32_t i=0;i<nv;i++){char*v=data.data()+16+size_t(i)*stride;auto&o=vertices[i];memcpy(&o.p,v,12);int16_t n[3];memcpy(n,v+12,6);o.n=norm({n[0]/32767.f,n[1]/32767.f,n[2]/32767.f});o.mat=(uint8_t)v[18];o.ao=(uint8_t)v[19]/255.f;o.key=(uint8_t)v[22]/255.f;o.fill=(uint8_t)v[23]/255.f;}
T.reserve(ni/3);triangleVertices.reserve(ni/3);for(uint32_t i=0;i<ni;i+=3){uint32_t ix[3];memcpy(ix,data.data()+16+size_t(nv)*stride+size_t(i)*4,12);V a=vertices[ix[0]].p,b=vertices[ix[1]].p,c=vertices[ix[2]].p;T.push_back({a,b-a,c-a,vmin(a,vmin(b,c)),vmax(a,vmax(b,c)),(a+b+c)*(1.f/3)});triangleVertices.push_back({ix[0],ix[1],ix[2]});}order.resize(T.size());std::iota(order.begin(),order.end(),0);nodes.reserve(T.size()/3);build(0,T.size());std::cout<<"Irradiance BVH ready: "<<nv<<" vertices\n"<<std::flush;std::vector<V>indirect(nv);constexpr int S=80;auto start=std::chrono::steady_clock::now();
#pragma omp parallel for schedule(dynamic,512)
for(uint32_t i=0;i<nv;i++){auto&vert=vertices[i];V n=vert.n,p=vert.p,t=norm(cross(std::abs(n.z)<.9f?V{0,0,1}:V{1,0,0},n)),b=cross(n,t);uint32_t seed=hash(int(p.x*4096))^hash(int(p.y*4096)+4444)^hash(int(p.z*4096)+7777);float phase=(seed&65535)*6.283185307f/65536.f;V sum{0,0,0},o=p+n*.002f;for(int j=0;j<S;j++){float r=std::sqrt((j+.5f)/S),phi=6.283185307f*radical(j)+phase;V d=t*(r*std::cos(phi))+b*(r*std::sin(phi))+n*std::sqrt(std::max(0.f,1-r*r));Hit h=nearestHit(o,d);V c=h.index<0?ambient(d):outgoing(h,d);sum=sum+c;}indirect[i]=sum*(3.14159265f/S);}
std::ofstream out(argv[2],std::ios::binary);out.write((char*)indirect.data(),indirect.size()*sizeof(V));std::cout<<"Baked 80 cosine-weighted indirect transport samples per vertex in "<<std::chrono::duration<float>(std::chrono::steady_clock::now()-start).count()<<" seconds\n";}
