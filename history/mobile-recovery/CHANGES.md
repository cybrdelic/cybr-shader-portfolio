# Scope of this repair

The user's report identified WebGL2 on ANGLE/Qualcomm Adreno 830, 1440 × 2654 rendered pixels, a lost context, one completed frame and three submitted frames. The old application automatically entered a ten-interaction progressive rendering path and requested large native-resolution accumulation/reconstruction targets. Live mode also eagerly loaded the scene-ray hierarchy.

This package removes those workloads from the mobile artifact rather than increasing their step budgets or silently lowering the native canvas resolution. No additional geometry was added. The original geometry, material caches and baked irradiance are preserved with hash checks.

The original visual-quality request remains unresolved. This repair is separately scoped to startup, GPU allocations, workload bounds, rendering on demand and recovery controls. No visual score or physical-device frame-rate guarantee is asserted.

See README.md for exact changes and tradeoffs. See verification/asset-audit.json for HDR cache encoding differences and verification/allocation-audit.json for the source-derived payload audit.
