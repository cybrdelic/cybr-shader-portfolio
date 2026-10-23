// Common math, BVH layout/traversal and sample sequence for the two native bakers.
// Each standalone baker has one translation unit and retains its own ray/transport policy.
#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <vector>
struct V{float x,y,z;V operator+(V a)const{return{x+a.x,y+a.y,z+a.z};}V operator-(V a)const{return{x-a.x,y-a.y,z-a.z};}V operator*(float s)const{return{x*s,y*s,z*s};}float operator[](int i)const{return i==0?x:i==1?y:z;}};
float dot(V a,V b){return a.x*b.x+a.y*b.y+a.z*b.z;}V cross(V a,V b){return{a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x};}V norm(V a){return a*(1/std::max(1e-12f,std::sqrt(dot(a,a))));}V vmin(V a,V b){return{std::min(a.x,b.x),std::min(a.y,b.y),std::min(a.z,b.z)};}V vmax(V a,V b){return{std::max(a.x,b.x),std::max(a.y,b.y),std::max(a.z,b.z)};}
struct Tri{V p,e1,e2,lo,hi,c;};struct Node{V lo,hi;int left=-1,right=-1,start=0,count=0;};
std::vector<Tri>T;std::vector<uint32_t>order;std::vector<Node>nodes;
int build(int start,int end){Node n;n.lo={1e10,1e10,1e10};n.hi={-1e10,-1e10,-1e10};V lo=n.lo,hi=n.hi;for(int i=start;i<end;i++){auto&t=T[order[i]];n.lo=vmin(n.lo,t.lo);n.hi=vmax(n.hi,t.hi);lo=vmin(lo,t.c);hi=vmax(hi,t.c);}int idx=nodes.size();nodes.push_back(n);if(end-start<=8){nodes[idx].start=start;nodes[idx].count=end-start;return idx;}V e=hi-lo;int axis=e.x>e.y?(e.x>e.z?0:2):(e.y>e.z?1:2),mid=(start+end)/2;std::nth_element(order.begin()+start,order.begin()+mid,order.begin()+end,[&](int a,int b){return T[a].c[axis]<T[b].c[axis];});int l=build(start,mid),r=build(mid,end);nodes[idx].left=l;nodes[idx].right=r;return idx;}
bool boxHit(const Node&n,V o,V inv,float maxT){float low=0,high=maxT;for(int k=0;k<3;k++){float a=(n.lo[k]-o[k])*inv[k],b=(n.hi[k]-o[k])*inv[k];low=std::max(low,std::min(a,b));high=std::min(high,std::max(a,b));}return high>=low;}
float radical(uint32_t a){a=(a<<16)|(a>>16);a=((a&0x55555555)<<1)|((a&0xaaaaaaaa)>>1);a=((a&0x33333333)<<2)|((a&0xcccccccc)>>2);a=((a&0x0f0f0f0f)<<4)|((a&0xf0f0f0f0)>>4);a=((a&0x00ff00ff)<<8)|((a&0xff00ff00)>>8);return a*2.3283064365386963e-10f;}
uint32_t hash(uint32_t x){x^=x>>16;x*=0x7feb352d;x^=x>>15;x*=0x846ca68b;x^=x>>16;return x;}
