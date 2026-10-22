// CYBR / THE COMPUTATIONAL INSTRUMENT
// Alejandro Figueroa — graphics, simulation, and systems.
// Fresh reconstruction, October 2026. Every visible pixel is procedural GLSL.
// No images, texture samplers, mesh assets, font atlases, or external buffers.
// Scroll or set u_chapter to move through the eight connected chapters.
// Paste this complete source into FragCoord as a GLSL fragment pass.
// FragCoord supplies u_resolution, u_time, u_mouse, u_drag, u_scroll, fragColor.

uniform float u_chapter; //0.0, [0.0, 7.0]
uniform float u_exposure; //1.0, [0.3, 2.0]
uniform float u_quality; //1.0, [0.0, 2.0]
uniform float u_tour; //0.0, [0.0, 1.0]
uniform float u_pick; //0.0, [0.0, 1.0]

const float PI = 3.141592653589793;
const float TAU = 6.283185307179586;
float clockTime;
float chapterPosition;
float pixelFootprint;

float filmEase(float x) {
    x = clamp(x, 0.0, 1.0);
    return x*x*x*(x*(x*6.0-15.0)+10.0);
}

float autoChapter(float seconds) {
    // Four-second chapters, including a deliberate three-quarter-second hold.
    float phase = mod(max(seconds, 0.0), 36.0) / 4.0;
    if (phase < 7.0) {
        float whole = floor(phase);
        return whole + filmEase((fract(phase)-0.26)/0.65);
    }
    if (phase < 8.0) return 7.0;
    return 7.0 * (1.0-filmEase(phase-8.0));
}
