// Build a binned-SAH hierarchy for real secondary-ray intersections.
// Vertex attributes are shared with the raster mesh. Four roots preserve
// independently moving parts. The leaf index order never changes the mesh.
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <numeric>
#include <stdexcept>
#include <vector>
#include <limits>
struct V {float x,y,z; float operator[](int i)const{return i==0?x:i==1?y:z;} V operator+(V b)const{return{x+b.x,y+b.y,z+b.z};}V operator-(V b)const{return{x-b.x,y-b.y,z-b.z};}V operator*(float s)const{return{x*s,y*s,z*s};}};
V mn(V a,V b){return{std::min(a.x,b.x),std::min(a.y,b.y),std::min(a.z,b.z)};}
V mx(V a,V b){return{std::max(a.x,b.x),std::max(a.y,b.y),std::max(a.z,b.z)};}
struct Bounds{V lo={1e20f,1e20f,1e20f},hi={-1e20f,-1e20f,-1e20f};void add(V v){lo=mn(lo,v);hi=mx(hi,v);}void add(const Bounds& b){lo=mn(lo,b.lo);hi=mx(hi,b.hi);}float area()const{V s=hi-lo;return std::max(0.f,2*(s.x*s.y+s.x*s.z+s.y*s.z));}};
struct Tri{std::array<uint32_t,4> indices;Bounds b;V c;};
struct Node{Bounds b;int left=-1,right=-1,start=0,count=0;};
std::vector<Tri> tris;std::vector<uint32_t> order;std::vector<Node> nodes;int maxDepth=0;
int build(uint32_t first,uint32_t end,int depth){
 maxDepth=std::max(maxDepth,depth);Node n;Bounds cent;
 for(uint32_t j=first;j<end;j++){auto&t=tris[order[j]];n.b.add(t.b);cent.add(t.c);}
 int idx=int(nodes.size());nodes.push_back(n);uint32_t count=end-first;
 if(count<=6){nodes[idx].start=first;nodes[idx].count=count;return idx;}
 constexpr int B=12;float cost=std::numeric_limits<float>::infinity();int bestAxis=-1,bestSplit=-1;
 for(int a=0;a<3;a++){
  float extent=cent.hi[a]-cent.lo[a];if(extent<1e-8f)continue;
  struct Bin{Bounds b;uint32_t count=0;};Bin bins[B];
  for(uint32_t j=first;j<end;j++){auto&t=tris[order[j]];int k=std::min(B-1,int((t.c[a]-cent.lo[a])/extent*B));bins[k].b.add(t.b);bins[k].count++;}
  Bounds lb[B],rb[B];uint32_t ln[B]={},rn[B]={};Bounds l,r;uint32_t lc=0,rc=0;
  for(int j=0;j<B;j++){if(bins[j].count)l.add(bins[j].b);lc+=bins[j].count;lb[j]=l;ln[j]=lc;int k=B-1-j;if(bins[k].count)r.add(bins[k].b);rc+=bins[k].count;rb[k]=r;rn[k]=rc;}
  for(int j=0;j<B-1;j++){if(!ln[j]||!rn[j+1])continue;float c=lb[j].area()*ln[j]+rb[j+1].area()*rn[j+1];if(c<cost){cost=c;bestAxis=a;bestSplit=j;}}
 }
 uint32_t mid=first;
 if(bestAxis>=0){float threshold=cent.lo[bestAxis]+(cent.hi[bestAxis]-cent.lo[bestAxis])*(bestSplit+1)/12.f;
  mid=std::partition(order.begin()+first,order.begin()+end,[&](uint32_t i){return tris[i].c[bestAxis]<threshold;})-order.begin();}
 if(mid<=first||mid>=end){V e=cent.hi-cent.lo;int a=e.x>e.y?(e.x>e.z?0:2):(e.y>e.z?1:2);mid=first+count/2;std::nth_element(order.begin()+first,order.begin()+mid,order.begin()+end,[&](uint32_t i,uint32_t j){return tris[i].c[a]<tris[j].c[a];});}
 int left=build(first,mid,depth+1),right=build(mid,end,depth+1);nodes[idx].left=left;nodes[idx].right=right;return idx;
}
int main(int argc,char**argv){try{
 if(argc!=3)throw std::runtime_error("Usage: build_optical_bvh mesh.bin output.bin");
 std::ifstream in(argv[1],std::ios::binary);std::vector<uint8_t> data((std::istreambuf_iterator<char>(in)),{});if(data.size()<16)throw std::runtime_error("Missing or truncated mesh");
 uint32_t nv,ni,stride;memcpy(&nv,data.data()+4,4);memcpy(&ni,data.data()+8,4);memcpy(&stride,data.data()+12,4);if(stride!=28||data.size()!=16+size_t(nv)*stride+size_t(ni)*4)throw std::runtime_error("Invalid mesh format");
 auto pos=[&](uint32_t i){V p;memcpy(&p,data.data()+16+size_t(i)*28,12);return p;};
 std::array<std::vector<uint32_t>,4> parts;
 for(uint32_t i=0;i<ni;i+=3){Tri t;memcpy(t.indices.data(),data.data()+16+size_t(nv)*28+size_t(i)*4,12);auto v=data.data()+16+size_t(t.indices[0])*28;int material=v[18],part=v[20],object=v[21];if(material==21&&object==7)continue;part=std::min(part,3);
  V a=pos(t.indices[0]),b=pos(t.indices[1]),c=pos(t.indices[2]);t.b.add(a);t.b.add(b);t.b.add(c);t.b.lo=t.b.lo-V{.000005f,.000005f,.000005f};t.b.hi=t.b.hi+V{.000005f,.000005f,.000005f};t.c=(a+b+c)*(1.f/3);t.indices[3]=part;parts[part].push_back(tris.size());tris.push_back(t);}
 std::array<int32_t,4> roots;nodes.reserve(tris.size()/2);order.reserve(tris.size());
 for(int p=0;p<4;p++){uint32_t first=order.size();order.insert(order.end(),parts[p].begin(),parts[p].end());roots[p]=parts[p].empty()?-1:build(first,order.size(),0);}
 if(maxDepth>=60)throw std::runtime_error("BVH exceeds shader stack capacity");
 std::ofstream out(argv[2],std::ios::binary);uint32_t header[8]={0x33564243,uint32_t(nodes.size()),uint32_t(order.size()),uint32_t(nv),uint32_t(roots[0]),uint32_t(roots[1]),uint32_t(roots[2]),uint32_t(roots[3])};out.write((char*)header,sizeof(header));
 for(auto&n:nodes){float row[8]={n.b.lo.x,n.b.lo.y,n.b.lo.z,float(n.count?n.start:n.left),n.b.hi.x,n.b.hi.y,n.b.hi.z,float(n.count?-n.count:n.right)};out.write((char*)row,32);}
 for(uint32_t i:order)out.write((char*)tris[i].indices.data(),16);
 std::cout<<"{\"nodes\":"<<nodes.size()<<",\"triangles\":"<<order.size()<<",\"vertices\":"<<nv<<",\"maxDepth\":"<<maxDepth<<",\"roots\":["<<roots[0]<<","<<roots[1]<<","<<roots[2]<<","<<roots[3]<<"]}"<<std::endl;
}catch(const std::exception&e){std::cerr<<e.what()<<std::endl;return 1;}return 0;}
