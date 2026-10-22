vec3 displayTransform(vec3 radiance, vec2 pixel) {
    vec3 x = max(radiance, vec3(0.0))*max(u_exposure, 0.0);
    // A compact filmic shoulder keeps illuminated metal and glass unclipped.
    x = (x*(2.51*x+0.03))/(x*(2.43*x+0.59)+0.14);
    x = pow(clamp(x, 0.0, 1.0), vec3(1.0/2.2));
    vec2 screen = pixel/u_resolution;
    float vignette = 1.0-0.14*dot((screen-0.5)*vec2(1.0,0.8),(screen-0.5)*vec2(1.0,0.8));
    x *= vignette;
    // Stable sub-code-value dither only; no animated noise over typography.
    return max(x+(hash31(vec3(pixel,13.7))-0.5)/1024.0,vec3(0.0));
}

void main() {
    clockTime = u_time;
    chapterPosition = clamp(u_chapter+u_scroll*0.35,0.0,7.0);
    if (u_tour > 0.5) chapterPosition = autoChapter(clockTime);
    pixelFootprint = 1.0/max(u_resolution.y,1.0);
    vec3 radiance = renderWorld(gl_FragCoord.xy);
    if (u_pick > 0.5) {
        fragColor = vec4(radiance,1.0);
        return;
    }
    vec3 color = displayTransform(radiance,gl_FragCoord.xy);
    color = portfolioUI(color,gl_FragCoord.xy,chapterPosition,clockTime);
    fragColor = vec4(clamp(color,0.0,1.0),1.0);
}
