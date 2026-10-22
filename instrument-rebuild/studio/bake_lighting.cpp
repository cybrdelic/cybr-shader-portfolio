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
#ifdef _OPENMP
#include <omp.h>
#endif
struct V{float x,y,z;V operator+(V a)const{return{x+a.x,y+a.y,z+a.z};}V operator-(V a)const{return{x-a.x,y-a.y,z-a.z};}V operator*(float s)const{return{x*s,y*s,z*s};}float operator[](int i)const{return i==0?x:i==1?y:z;}};
float dot(V a,V b){return a.x*b.x+a.y*b.y+a.z*b.z;}V cross(V a,V b){return{a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x};}V norm(V a){return a*(1/std::max(1e-12f,std::sqrt(dot(a,a))));}V vmin(V a,V b){return{std::min(a.x,b.x),std::min(a.y,b.y),std::min(a.z,b.z)};}V vmax(V a,V b){return{std::max(a.x,b.x),std::max(a.y,b.y),std::max(a.z,b.z)};}
struct Tri{V p,e1,e2,lo,hi,c;};struct Node{V lo,hi;int left=-1,right=-1,start=0,count=0;};
std::vector<Tri>T;std::vector<uint32_t>order;std::vector<Node>nodes;
int build(int start,int end){Node n;n.lo={1e10,1e10,1e10};n.hi={-1e10,-1e10,-1e10};V lo=n.lo,hi=n.hi;for(int i=start;i<end;i++){auto&t=T[order[i]];n.lo=vmin(n.lo,t.lo);n.hi=vmax(n.hi,t.hi);lo=vmin(lo,t.c);hi=vmax(hi,t.c);}int idx=nodes.size();nodes.push_back(n);if(end-start<=8){nodes[idx].start=start;nodes[idx].count=end-start;return idx;}V e=hi-lo;int axis=e.x>e.y?(e.x>e.z?0:2):(e.y>e.z?1:2),mid=(start+end)/2;std::nth_element(order.begin()+start,order.begin()+mid,order.begin()+end,[&](int a,int b){return T[a].c[axis]<T[b].c[axis];});int l=build(start,mid),r=build(mid,end);nodes[idx].left=l;nodes[idx].right=r;return idx;}
bool boxHit(const Node&n,V o,V inv,float maxT){float low=0,high=maxT;for(int k=0;k<3;k++){float a=(n.lo[k]-o[k])*inv[k],b=(n.hi[k]-o[k])*inv[k];low=std::max(low,std::min(a,b));high=std::min(high,std::max(a,b));}return high>=low;}
float ray(V o,V d,float distance=1.2f,bool anyHit=false){V inv{1/(std::abs(d.x)<1e-9f?1e-9f:d.x),1/(std::abs(d.y)<1e-9f?1e-9f:d.y),1/(std::abs(d.z)<1e-9f?1e-9f:d.z)};float nearest=distance;int stack[96],top=1;stack[0]=0;while(top){const Node&n=nodes[stack[--top]];if(!boxHit(n,o,inv,nearest))continue;if(n.count){for(int i=0;i<n.count;i++){const auto&t=T[order[n.start+i]];V h=cross(d,t.e2);float det=dot(t.e1,h);if(std::abs(det)<1e-10f)continue;float f=1/det;V s=o-t.p;float u=f*dot(s,h);if(u<0||u>1)continue;V q=cross(s,t.e1);float v=f*dot(d,q);if(v<0||u+v>1)continue;float tt=f*dot(t.e2,q);if(tt>1e-5f&&tt<nearest){nearest=tt;if(anyHit)return nearest;}}}else{stack[top++]=n.left;stack[top++]=n.right;}}return nearest;}
float radical(uint32_t a){a=(a<<16)|(a>>16);a=((a&0x55555555)<<1)|((a&0xaaaaaaaa)>>1);a=((a&0x33333333)<<2)|((a&0xcccccccc)>>2);a=((a&0x0f0f0f0f)<<4)|((a&0xf0f0f0f0)>>4);a=((a&0x00ff00ff)<<8)|((a&0xff00ff00)>>8);return a*2.3283064365386963e-10f;}
uint32_t hash(uint32_t x){x^=x>>16;x*=0x7feb352d;x^=x>>15;x*=0x846ca68b;x^=x>>16;return x;}
int main(int argc,char**argv){if(argc!=3)return 2;std::ifstream in(argv[1],std::ios::binary);if(!in)return 3;std::vector<char>data((std::istreambuf_iterator<char>(in)),{});if(data.size()<16)return 3;uint32_t nv,ni,stride;memcpy(&nv,data.data()+4,4);memcpy(&ni,data.data()+8,4);memcpy(&stride,data.data()+12,4);if(stride!=28||data.size()!=16+size_t(nv)*stride+size_t(ni)*4)return 4;auto pos=[&](uint32_t i){V v;memcpy(&v,data.data()+16+size_t(i)*stride,12);return v;};T.reserve(ni/3);for(uint32_t i=0;i<ni;i+=3){uint32_t ix[3];memcpy(ix,data.data()+16+size_t(nv)*stride+size_t(i)*4,12);V a=pos(ix[0]),b=pos(ix[1]),c=pos(ix[2]);T.push_back({a,b-a,c-a,vmin(a,vmin(b,c)),vmax(a,vmax(b,c)),(a+b+c)*(1.f/3)});}order.resize(T.size());std::iota(order.begin(),order.end(),0);nodes.reserve(T.size()/3);build(0,T.size());std::cout<<"BVH "<<nodes.size()<<" nodes; "<<nv<<" vertices\n"<<std::flush;
constexpr int S=40;auto start=std::chrono::steady_clock::now();
#pragma omp parallel for schedule(dynamic,1024)
for(int64_t i=0;i<static_cast<int64_t>(nv);i++){char*v=data.data()+16+size_t(i)*stride;uint8_t mat=(uint8_t)v[18];int16_t sn[3];memcpy(sn,v+12,6);V n=norm({sn[0]/32767.f,sn[1]/32767.f,sn[2]/32767.f}),p=pos(i),t=norm(cross(std::abs(n.z)<.9f?V{0,0,1}:V{1,0,0},n)),b=cross(n,t);uint32_t seed=hash((int)(p.x*4096))^hash((int)(p.y*4096)+4444)^hash((int)(p.z*4096)+7777);float phase=(seed&65535)*6.283185307f/65536.f,sum=0;V o=p+n*.0016f;for(int j=0;j<S;j++){float r=std::sqrt((j+.5f)/S),phi=6.283185307f*radical(j)+phase;V d=t*(r*std::cos(phi))+b*(r*std::sin(phi))+n*std::sqrt(std::max(0.f,1-r*r));float hit=ray(o,d);if(hit<1.199f)sum+=std::exp(-hit/0.30f);}float ao=std::max(.15f,1-.90f*sum/S),existing=(uint8_t)v[19]/255.f;v[19]=char(std::lround(255*ao*existing));
// Large rectangular studio sources, evaluated with deterministic stratified
// visibility rays. Stored separately from cosine-weighted ambient visibility.
const V lights[2]={{-3.8f,7.5f,5.4f},{5.2f,4.5f,-2.7f}};
const float halfWidth[2]={2.6f,1.6f},halfHeight[2]={1.85f,2.6f};
for(int li=0;li<2;li++){
 V center=lights[li],ln=norm(V{0,1.0f,0}-center),lt=norm(cross(V{0,1,0},ln)),lb=cross(ln,lt);
 int count=li==0?56:24;float visibility=0;
 for(int j=0;j<count;j++){
  float u=(j+.5f)/count,vv=radical(j),cu=std::fmod(u+(seed&255)/256.f,1.f),cv=std::fmod(vv+((seed>>8)&255)/256.f,1.f);
  V sample=center+lt*((cu*2-1)*halfWidth[li])+lb*((cv*2-1)*halfHeight[li]);
  V direction=sample-o;float dist=std::sqrt(dot(direction,direction));direction=direction*(1.f/dist);
  visibility+=ray(o,direction,dist-.005f,true)>=dist-.006f?1.f:0.f;
 }
 v[22+li]=char(std::lround(255*visibility/count));
}
}
std::ofstream out(argv[2],std::ios::binary);out.write(data.data(),data.size());std::cout<<"Baked 40 AO + 56 key + 24 fill directions in "<<std::chrono::duration<float>(std::chrono::steady_clock::now()-start).count()<<" seconds\n";}
