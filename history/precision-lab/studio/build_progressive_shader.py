"""Assemble a WebGL2 progressive, multi-bounce surface path tracer.
The visibility hierarchy is the same one used by the live optical renderer.
No rendered scene image is used as a texture or a background.
"""
from pathlib import Path
R=Path(__file__).resolve().parent.parent
common=(R/'shaders/scene.vert').read_text().split('layout(location=0)')[0]
optical=(R/'shaders/screen.frag').read_text()
planes=optical[optical.index('const vec4 CORE_PLANES'):optical.index('void main(){',optical.index('const vec4 CORE_PLANES'))]
# Strip functions after the core clipper, if future files append helpers.
start=planes.index('bool coreIntersection');brace=planes.index('{',start);depth=1;end=brace+1
while depth:
 if planes[end]=='{':depth+=1
 if planes[end]=='}':depth-=1
 end+=1
planes=planes[:end]
bvh=(R/'shaders/optical-bvh.glsl').read_text()
bvh=bvh[:bvh.index('float rayArea')]
flame=optical[optical.index('float flameDensity'):optical.index('// CYBR / analytic typography')]
surfaceSource=(R/'shaders/scene.frag').read_text()
glyph=surfaceSource[surfaceSource.index('const int LABEL_TEXT'):surfaceSource.index('Surface surfaceAt')]
glyph='float glyphFootprint;\n'+glyph.replace('vec2 fp=fwidth(p);','vec2 fp=vec2(glyphFootprint/size);')
src=common+'''
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
'''+bvh+'\n'+planes+'\n'+glyph+'\n'+flame+'\n'+(R/'shaders/progressive-body.glsl').read_text()
(R/'shaders/progressive.frag').write_text(src)
print('Progressive shader',len(src),'bytes')
