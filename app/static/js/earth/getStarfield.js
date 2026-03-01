import * as THREE from "../vendor/three/three.module.js";

export default function getStarfield({ numStars = 2000, spriteUrl }) {
    const verts = [];
    const colors = [];

    function randomSpherePoint() {
        const radius = Math.random() * 25 + 25;
        const u = Math.random();
        const v = Math.random();
        const theta = 2 * Math.PI * u;
        const phi = Math.acos(2 * v - 1);
        const x = radius * Math.sin(phi) * Math.cos(theta);
        const y = radius * Math.sin(phi) * Math.sin(theta);
        const z = radius * Math.cos(phi);
        return new THREE.Vector3(x, y, z);
    }

    for (let i = 0; i < numStars; i += 1) {
        const pos = randomSpherePoint();
        const col = new THREE.Color().setHSL(0.6, 0.2, Math.random());
        verts.push(pos.x, pos.y, pos.z);
        colors.push(col.r, col.g, col.b);
    }

    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.Float32BufferAttribute(verts, 3));
    geo.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));

    const mat = new THREE.PointsMaterial({
        size: 0.2,
        vertexColors: true,
        map: spriteUrl ? new THREE.TextureLoader().load(spriteUrl) : null,
        transparent: true,
        depthWrite: false,
    });

    return new THREE.Points(geo, mat);
}
