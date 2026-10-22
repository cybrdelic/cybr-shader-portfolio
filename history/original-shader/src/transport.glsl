// Light transport and photography. All radiance remains linear until main().
// One real reflected scene ray and two analytic glass interfaces are evaluated.
// Rough secondary transport uses the studio environment as a filtered tail.

vec2 raySphere(vec3 ro, vec3 rd, vec3 center, float radius) {
    vec3 oc = ro - center;
    float b = dot(oc, rd);
    float disc = b * b - dot(oc, oc) + radius * radius;
    if (disc < 0.0) return vec2(-1.0);
    float h = sqrt(disc);
    return vec2(-b - h, -b + h);
}

vec2 rayBounds(vec3 ro, vec3 rd, vec3 lo, vec3 hi) {
    vec3 inverseRay = 1.0 / ((step(vec3(0.0), rd) * 2.0 - 1.0) * max(abs(rd), vec3(0.00001)));
    vec3 a = (lo - ro) * inverseRay;
    vec3 b = (hi - ro) * inverseRay;
    vec3 nearT = min(a, b);
    vec3 farT = max(a, b);
    return vec2(max(nearT.x, max(nearT.y, nearT.z)),
                min(farT.x, min(farT.y, farT.z)));
}

vec3 traceScene(vec3 ro, vec3 rd, float maximum, int stepBudget) {
    // The infinite floor is analytically intersected. The expensive mechanism
    // only occupies this conservative finite box.
    float floorT = rd.y < -0.00001 ? (-0.18 - ro.y) / rd.y : maximum;
    bool floorVisible = floorT > 0.001 && floorT < maximum;
    float limit = floorVisible ? floorT : maximum;
    vec2 box = rayBounds(ro, rd, vec3(-4.85, -0.17, -4.85), vec3(4.85, 3.55, 4.85));
    if (box.x < box.y && box.y > 0.0 && box.x < limit) {
        float t = max(0.004, box.x);
        float endT = min(limit, box.y);
        for (int i = 0; i < 152; ++i) {
            if (i >= stepBudget || t > endT) break;
            vec3 h = mapScene(ro + rd * t);
            float epsilon = 0.00065 + 0.000045 * t;
            if (h.x < epsilon) return vec3(t, h.y, h.z);
            // Geometry bounds and displaced surfaces are conservative. The
            // safety multiplier also protects near-tangent radial filigree.
            t += max(h.x * 0.84, 0.0006);
        }
    }
    if (floorVisible) return vec3(floorT, 1.0, 0.0);
    return vec3(maximum, -1.0, 0.0);
}

vec3 worldNormal(vec3 p, float travel, float materialId) {
    if (materialId < 1.5) return vec3(0.0, 1.0, 0.0);
    float stepSize = 0.0007 + 0.000035 * travel;
    vec2 e = vec2(1.0, -1.0) * stepSize;
    return normalize(e.xyy * mapScene(p + e.xyy).x +
                     e.yyx * mapScene(p + e.yyx).x +
                     e.yxy * mapScene(p + e.yxy).x +
                     e.xxx * mapScene(p + e.xxx).x);
}

float contactOcclusion(vec3 p, vec3 n) {
    float occlusion = 0.0;
    float attenuation = 1.0;
    for (int i = 0; i < 4; ++i) {
        float h = 0.018 + float(i) * 0.080;
        vec3 sampleHit = mapScene(p + n * h);
        // Proxy bounds are conservative advances, never real occluding matter.
        if (fract(sampleHit.y) < 0.06) {
            occlusion += max(0.0, h - sampleHit.x) * attenuation;
        }
        attenuation *= 0.59;
    }
    return clamp(1.0 - occlusion * 2.3, 0.18, 1.0);
}

float penumbra(vec3 p, vec3 direction, float distanceToLight) {
    float visibility = 1.0;
    float t = 0.024;
    for (int i = 0; i < 28; ++i) {
        if (t >= distanceToLight || p.y + direction.y * t > 3.6) break;
        vec3 sampleHit = mapScene(p + direction * t);
        float h = sampleHit.x;
        if (h < 0.0009) return 0.0;
        if (fract(sampleHit.y) < 0.06) {
            visibility = min(visibility, 9.0 * h / max(0.005, t));
        }
        t += clamp(h * 0.9, 0.018, 0.43);
    }
    return clamp(visibility, 0.0, 1.0);
}

float studioPanel(vec3 ray, vec3 facing, vec2 extent, float roughness) {
    vec3 normal = normalize(facing);
    vec3 horizontal = normalize(cross(vec3(0.0, 1.0, 0.0), normal));
    vec3 vertical = cross(normal, horizontal);
    float front = dot(ray, normal);
    vec2 point = vec2(dot(ray, horizontal), dot(ray, vertical)) / max(front, 0.001);
    vec2 edge = abs(point) - extent;
    float blur = 0.008 + roughness * roughness * 0.60;
    return (1.0 - smoothstep(-blur, blur, max(edge.x, edge.y))) * step(0.0, front);
}

vec3 studioEnvironment(vec3 ray, float roughness) {
    float sky = clamp(ray.y * 0.5 + 0.5, 0.0, 1.0);
    vec3 result = mix(vec3(0.022, 0.027, 0.033), vec3(0.24, 0.27, 0.30), pow(sky, 1.7));
    result += vec3(5.3, 4.7, 3.8) * studioPanel(ray, vec3(-0.7, 1.0, 0.8), vec2(0.44, 0.68), roughness);
    result += vec3(1.9, 2.5, 3.0) * studioPanel(ray, vec3(1.0, 0.4, 0.3), vec2(0.085, 0.90), roughness);
    result += vec3(2.4, 2.55, 2.7) * studioPanel(ray, vec3(0.2, 1.0, -0.55), vec2(0.72, 0.12), roughness);
    result += vec3(2.3, 1.25, 0.52) * studioPanel(ray, vec3(-0.9, 0.25, -0.8), vec2(0.045, 0.62), roughness);
    return result;
}

vec3 viewBackground(vec3 ray) {
    float up = smoothstep(-0.10, 0.65, ray.y);
    return mix(vec3(0.038, 0.048, 0.055), vec3(0.011, 0.020, 0.029), up);
}

vec3 schlick(float cosine, vec3 f0) {
    float grazing = pow(clamp(1.0 - cosine, 0.0, 1.0), 5.0);
    return f0 + (1.0 - f0) * grazing;
}

vec3 evaluateBRDF(Surface surface, vec3 n, vec3 v, vec3 l, vec3 incident) {
    float nl = max(dot(n, l), 0.0);
    float nv = max(dot(n, v), 0.0005);
    vec3 h = normalize(v + l);
    float nh = max(dot(n, h), 0.0);
    float vh = max(dot(v, h), 0.0);
    float alpha = max(surface.rough * surface.rough, 0.022);
    float alpha2 = alpha * alpha;
    float denominator = nh * nh * (alpha2 - 1.0) + 1.0;
    float distribution = alpha2 / max(PI * denominator * denominator, 0.00001);
    float k = (surface.rough + 1.0) * (surface.rough + 1.0) * 0.125;
    float geometry = (nl / max(nl * (1.0 - k) + k, 0.0005)) *
                     (nv / max(nv * (1.0 - k) + k, 0.0005));
    vec3 f = schlick(vh, mix(vec3(0.04), surface.base, surface.metal));
    vec3 specular = f * distribution * geometry / max(4.0 * nl * nv, 0.0005);
    vec3 diffuse = (1.0 - f) * (1.0 - surface.metal) * surface.base / PI;
    return (diffuse + specular) * nl * incident;
}

vec3 baseLighting(vec3 p, vec3 n, vec3 ray, Surface surface, float ao, bool detailed) {
    vec3 view = -ray;
    vec3 keyVector = vec3(-4.5, 8.5, 6.5) - p;
    float keyLength = length(keyVector);
    vec3 key = keyVector / keyLength;
    vec3 rim = normalize(vec3(4.0, 5.0, -5.0) - p);
    vec3 fill = normalize(vec3(-7.0, 3.0, -2.0) - p);
    float shadow = detailed ? penumbra(p + n * 0.006, key, keyLength) : 0.85;
    vec3 result = evaluateBRDF(surface, n, view, key, vec3(5.9, 5.25, 4.25) * shadow);
    result += evaluateBRDF(surface, n, view, rim, vec3(1.65, 2.12, 2.65));
    result += evaluateBRDF(surface, n, view, fill, vec3(0.72, 0.60, 0.46));
    vec3 f = schlick(max(dot(n, view), 0.0), mix(vec3(0.04), surface.base, surface.metal));
    vec3 ambient = mix(vec3(0.12, 0.14, 0.16), vec3(0.36, 0.39, 0.42), n.y * 0.5 + 0.5);
    result += (1.0 - f) * surface.base * (1.0 - surface.metal) * ambient * ao;

    // Restrained hot-matter irradiance onto neighbouring basin hardware.
    vec3 hotVector = moduleCenter(4) + vec3(0.0, 1.12, 0.0) - p;
    float hotDistance2 = dot(hotVector, hotVector);
    vec3 hotDirection = hotVector * inversesqrt(max(hotDistance2, 0.0001));
    result += surface.base * vec3(0.55, 0.075, 0.009) * max(dot(n, hotDirection), 0.0) /
              (0.6 + hotDistance2 * 4.0);

    return result + surface.emission;
}

vec3 secondaryRadiance(vec3 ro, vec3 rd, float roughness) {
    vec3 env = studioEnvironment(rd, roughness);
    vec3 hit = traceScene(ro, rd, 34.0, 78);
    if (hit.y < 0.0) return env;
    vec3 p = ro + rd * hit.x;
    vec3 n = worldNormal(p, hit.x, hit.y);
    Surface surface = surfaceAt(p, n, hit.y);
    vec3 result = baseLighting(p, n, rd, surface, 0.84, false);
    vec3 f = schlick(max(dot(n, -rd), 0.0), mix(vec3(0.04), surface.base, surface.metal));
    result += studioEnvironment(reflect(rd, n), surface.rough) * f * (1.0 - 0.48 * surface.rough);
    // A high-roughness lobe integrates unresolved rays into the analytic studio.
    return mix(result, env, smoothstep(0.10, 0.48, roughness) * 0.94);
}

vec3 shadeOpaque(vec3 ro, vec3 rd, vec3 hit) {
    vec3 p = ro + rd * hit.x;
    vec3 gn = worldNormal(p, hit.x, hit.y);
    vec3 n = detailNormal(p, gn, hit.y);
    Surface surface = surfaceAt(p, gn, hit.y);
    float ao = contactOcclusion(p + gn * 0.003, gn);
    vec3 result = baseLighting(p, n, rd, surface, ao, true);
    vec3 f = schlick(max(dot(n, -rd), 0.0), mix(vec3(0.04), surface.base, surface.metal));
    vec3 reflected = studioEnvironment(reflect(rd, n), surface.rough);
    bool worldReflection = u_quality > 0.35 &&
        (surface.metal > 0.55 || surface.rough < 0.28 || (hit.y < 1.5 && dot(n, -rd) < 0.63));
    if (worldReflection) {
        reflected = secondaryRadiance(p + gn * 0.009, reflect(rd, n), surface.rough);
    }
    result += reflected * f * ao * (1.0 - surface.rough * 0.48);

    // Light reaching the rear of small foliage gently tints its thin tissue.
    if (hit.y > 12.5 && hit.y < 13.5) {
        float transmission = pow(max(dot(rd, normalize(vec3(-0.55, 0.85, 0.65))), 0.0), 2.0);
        result += surface.base * vec3(0.65, 0.95, 0.32) * transmission * 0.65;
    }
    float fog = 1.0 - exp(-hit.x * hit.x * (hit.y < 1.5 ? 0.0014 : 0.00010));
    return mix(result, viewBackground(rd), fog);
}

vec3 shadeDielectric(vec3 ro, vec3 rd, float entryT, vec4 sphere, int glassId) {
    float ior = glassId == 0 ? 1.49 : 1.46;
    vec3 p = ro + rd * entryT;
    vec3 entryNormal = normalize(p - sphere.xyz);
    vec3 internalRay = refract(rd, entryNormal, 1.0 / ior);
    vec3 internalOrigin = p + internalRay * 0.002;
    vec2 boundary = raySphere(internalOrigin, internalRay, sphere.xyz, sphere.w);
    float interiorLength = max(0.0, boundary.y);
    vec3 exitPoint = internalOrigin + internalRay * interiorLength;
    vec3 exitNormal = normalize(exitPoint - sphere.xyz);
    vec3 transmittedRay = refract(internalRay, -exitNormal, ior);
    if (dot(transmittedRay, transmittedRay) < 0.01) {
        transmittedRay = reflect(internalRay, -exitNormal);
    }

    vec3 through = secondaryRadiance(exitPoint + transmittedRay * 0.007, transmittedRay, 0.025);
    // Opaque mechanical parts located within the crystal remain correctly
    // visible through its front interface rather than disappearing.
    vec3 interiorHit = traceScene(internalOrigin, internalRay, max(0.001, interiorLength - 0.004), 64);
    if (interiorHit.y >= 0.0) {
        vec3 q = internalOrigin + internalRay * interiorHit.x;
        vec3 qn = worldNormal(q, interiorHit.x, interiorHit.y);
        Surface m = surfaceAt(q, qn, interiorHit.y);
        through = baseLighting(q, qn, internalRay, m, 0.86, false);
        through += studioEnvironment(reflect(internalRay, qn), m.rough) *
                   schlick(max(dot(qn, -internalRay), 0.0), mix(vec3(0.04), m.base, m.metal));
        interiorLength = interiorHit.x;
    }

    vec3 absorption = glassId == 0 ? vec3(0.105, 0.034, 0.017) : vec3(0.065, 0.024, 0.012);
    through *= exp(-absorption * interiorLength);
    vec3 reflected = secondaryRadiance(p + entryNormal * 0.007, reflect(rd, entryNormal), 0.025);
    float cosine = max(dot(-rd, entryNormal), 0.0);
    float f0 = pow((ior - 1.0) / (ior + 1.0), 2.0);
    float fresnel = f0 + (1.0 - f0) * pow(1.0 - cosine, 5.0);
    float exitFresnel = f0 + (1.0 - f0) * pow(1.0 - max(dot(internalRay, exitNormal), 0.0), 5.0);

    // Small spectral separation only changes transmitted illumination. It is
    // not a screen-space rainbow fringe or an additive emissive glass hack.
    vec3 redRay = refract(internalRay, -exitNormal, ior - 0.006);
    vec3 blueRay = refract(internalRay, -exitNormal, ior + 0.009);
    vec3 dispersion = vec3(studioEnvironment(redRay, 0.02).r,
                           studioEnvironment(transmittedRay, 0.02).g,
                           studioEnvironment(blueRay, 0.02).b);
    through = mix(through, dispersion * exp(-absorption * interiorLength), 0.025);
    return through * (1.0 - fresnel) * (1.0 - exitFresnel) + reflected * fresnel;
}

float flameDensity(vec3 localPoint) {
    float height = localPoint.y;
    float taper = max(0.035, 0.35 * (1.0 - height / 1.35));
    vec2 axis = vec2(0.10 * sin(height * 3.0 - clockTime * 1.4),
                     0.07 * sin(height * 4.3 - clockTime * 1.0)) * height;
    vec3 advected = localPoint * vec3(5.0, 3.1, 5.0) - vec3(0.0, clockTime * 1.35, 0.0);
    float turbulence = noise3(advected) * 0.63 + noise3(advected * 2.03) * 0.37;
    float radial = length(localPoint.xz - axis);
    float body = 1.0 - smoothstep(taper * 0.38, taper * 1.5, radial);
    float envelope = smoothstep(0.0, 0.12, height) * (1.0 - smoothstep(0.65, 1.35, height));
    return max(0.0, body * envelope * (turbulence * 1.7 - 0.35));
}

vec3 integrateFlame(vec3 color, vec3 ro, vec3 rd, float surfaceT) {
    vec3 center = moduleCenter(4) + vec3(0.0, 1.20, 0.0);
    vec2 range = rayBounds(ro - center, rd, vec3(-0.57, 0.0, -0.57), vec3(0.57, 1.40, 0.57));
    float start = max(range.x, 0.0);
    float end = min(range.y, surfaceT);
    if (end <= start) return color;
    float stride = (end - start) / 16.0;
    vec3 emission = vec3(0.0);
    float transmittance = 1.0;
    for (int i = 0; i < 16; ++i) {
        float t = start + (float(i) + 0.5) * stride;
        vec3 local = ro + rd * t - center;
        float density = flameDensity(local);
        float opacity = 1.0 - exp(-density * stride * 2.3);
        float heat = clamp(density * 1.45 + (1.1 - local.y) * 0.25, 0.0, 1.0);
        vec3 temperature = mix(vec3(4.7, 0.28, 0.008), vec3(9.0, 4.6, 1.0), pow(heat, 2.0));
        emission += transmittance * opacity * temperature;
        transmittance *= 1.0 - opacity * 0.30;
    }
    return color * transmittance + emission;
}

vec3 cameraTarget(int chapter) {
    chapter = clamp(chapter, 0, 7);
    if (chapter == 0) return vec3(0.0, 0.90, 0.0);
    if (chapter == 7) return vec3(0.0, 1.05, 0.0);
    float h = chapter == 1 ? 1.62 :
              chapter == 2 ? 1.55 :
              chapter == 3 ? 1.05 :
              chapter == 4 ? 1.24 :
              chapter == 5 ? 1.25 : 1.62;
    return moduleCenter(chapter) + vec3(0.0, h, 0.0);
}

vec3 cameraEye(int chapter) {
    chapter = clamp(chapter, 0, 7);
    if (chapter == 0) return vec3(9.8, 8.3, 12.0);
    if (chapter == 7) return vec3(-9.0, 7.0, 11.0);
    vec3 center = moduleCenter(chapter);
    vec3 radial = normalize(vec3(center.x, 0.0, center.z));
    vec3 tangent = vec3(-radial.z, 0.0, radial.x);
    float distance = chapter == 3 ? 4.8 : chapter == 6 ? 4.8 : 4.65;
    float side = chapter == 1 ? 0.9 : chapter == 3 ? 1.8 : chapter == 5 ? 1.55 : 0.55;
    float altitude = chapter == 3 ? 4.15 : chapter == 4 ? 3.65 : 3.35;
    return center + radial * distance + tangent * side + vec3(0.0, altitude, 0.0);
}

vec3 cameraSpline(vec3 a, vec3 b, vec3 c, vec3 d, float t) {
    return 0.5 * ((2.0 * b) + (-a + c) * t +
                  (2.0 * a - 5.0 * b + 4.0 * c - d) * t * t +
                  (-a + 3.0 * b - 3.0 * c + d) * t * t * t);
}

void cameraRay(vec2 coord, out vec3 ro, out vec3 rd) {
    float position = clamp(chapterPosition, 0.0, 7.0);
    int chapter = int(floor(position));
    float fraction = fract(position);
    vec3 target = cameraSpline(cameraTarget(chapter - 1), cameraTarget(chapter),
                               cameraTarget(chapter + 1), cameraTarget(chapter + 2), fraction);
    vec3 eye = cameraSpline(cameraEye(chapter - 1), cameraEye(chapter),
                            cameraEye(chapter + 1), cameraEye(chapter + 2), fraction);
    vec3 offset = eye - target;
    vec2 orbit = clamp(u_drag / max(u_resolution, vec2(1.0)), vec2(-0.9), vec2(0.9));
    offset.xz = rotation(orbit.x * 1.65 + 0.018 * sin(clockTime * 0.37)) * offset.xz;
    offset.y += orbit.y * 3.0 + 0.035 * sin(clockTime * 0.29);
    float aspect = u_resolution.x / u_resolution.y;
    bool portrait = aspect < 0.85;
    float wide = 1.0 - smoothstep(0.0, 0.8, min(position, 7.0 - position));
    if (portrait) offset *= mix(1.48, 1.85, wide);
    ro = target + offset;
    vec3 forward = normalize(target - ro);
    vec3 right = normalize(cross(forward, vec3(0.0, 1.0, 0.0)));
    vec3 up = cross(right, forward);
    vec2 uv = (coord - 0.5 * u_resolution) / u_resolution.y;
    uv.x -= portrait ? 0.0 : 0.085 * aspect;
    uv.y -= portrait ? 0.085 : 0.055;
    float lens = portrait ? 1.43 : mix(1.65, 1.38, wide);
    rd = normalize(forward * lens + right * uv.x + up * uv.y);
}

float pickObject(vec2 coord) {
    vec3 ro, rd;
    cameraRay(coord, ro, rd);
    vec3 hit = traceScene(ro, rd, 55.0, 144);
    float nearest = hit.x;
    float objectId = hit.z;
    for (int i = 0; i < 2; ++i) {
        vec4 sphere = glassSphere(i);
        vec2 intersection = raySphere(ro, rd, sphere.xyz, sphere.w);
        if (intersection.x > 0.0 && intersection.x < nearest) {
            nearest = intersection.x;
            objectId = i == 0 ? 1.0 : 7.0;
        }
    }
    return objectId;
}

vec3 renderWorld(vec2 coord) {
    vec3 ro, rd;
    cameraRay(coord, ro, rd);
    int primaryBudget = u_quality < 0.5 ? 102 : 144;
    vec3 hit = traceScene(ro, rd, 60.0, primaryBudget);
    int glassId = -1;
    float nearest = hit.x;
    vec4 selectedSphere = vec4(0.0);
    for (int i = 0; i < 2; ++i) {
        vec4 sphere = glassSphere(i);
        vec2 intersection = raySphere(ro, rd, sphere.xyz, sphere.w);
        if (intersection.x > 0.0 && intersection.x < nearest) {
            nearest = intersection.x;
            glassId = i;
            selectedSphere = sphere;
        }
    }
    // Share the complete primary trace with display rendering. A separate
    // picking branch in main would duplicate the scene at every inlined call.
    if (u_pick > 0.5) {
        float objectId = glassId >= 0 ? (glassId == 0 ? 1.0 : 7.0) : hit.z;
        return vec3(objectId / 255.0, 0.0, 0.0);
    }
    vec3 color;
    if (glassId >= 0) color = shadeDielectric(ro, rd, nearest, selectedSphere, glassId);
    else if (hit.y >= 0.0) color = shadeOpaque(ro, rd, hit);
    else color = viewBackground(rd);
    color = integrateFlame(color, ro, rd, nearest);
    return max(color, vec3(0.0));
}
