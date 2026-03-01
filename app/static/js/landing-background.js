import * as THREE from "./vendor/three/three.module.js";

import getStarfield from "./earth/getStarfield.js";
import { getFresnelMat } from "./earth/getFresnelMat.js";

const container = document.getElementById("earth-canvas");

if (!container || !hasWebGLSupport()) {
    document.body.classList.add("no-webgl");
} else {
    initEarthBackground(container);
}

function initEarthBackground(host) {
    const textureBase = (host.dataset.earthTextureBase || "").replace(/\/$/, "");
    if (!textureBase) {
        console.error("[Earth] Missing data-earth-texture-base.");
        document.body.classList.add("no-webgl");
        return;
    }
    const texturePath = (file) => `${textureBase}/${file}`;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(
        75,
        window.innerWidth / window.innerHeight,
        0.1,
        1000
    );
    camera.position.z = 5;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0x00040b, 1);
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.outputColorSpace = THREE.SRGBColorSpace;

    host.innerHTML = "";
    host.appendChild(renderer.domElement);
    renderer.domElement.style.width = "100%";
    renderer.domElement.style.height = "100%";
    renderer.domElement.style.pointerEvents = "none";

    const earthGroup = new THREE.Group();
    earthGroup.rotation.z = (-23.4 * Math.PI) / 180;
    earthGroup.scale.setScalar(1.5);
    scene.add(earthGroup);

    const loader = new THREE.TextureLoader();

    // Match original threejs-earth geometry/orientation behavior.
    const geometry = new THREE.IcosahedronGeometry(1, 12);
    const material = new THREE.MeshPhongMaterial({
        map: loader.load(texturePath("00_earthmap4k.jpg")),
        specularMap: loader.load(texturePath("02_earthspec4k.jpg")),
        bumpMap: loader.load(texturePath("01_earthbump4k.jpg")),
        bumpScale: 0.04,
    });
    if (material.map) material.map.colorSpace = THREE.SRGBColorSpace;
    if (material.specularMap) material.specularMap.colorSpace = THREE.SRGBColorSpace;
    const earthMesh = new THREE.Mesh(geometry, material);
    earthGroup.add(earthMesh);

    const lightsMat = new THREE.MeshBasicMaterial({
        map: loader.load(texturePath("03_earthlights4k.jpg")),
        blending: THREE.AdditiveBlending,
        transparent: true,
    });
    if (lightsMat.map) lightsMat.map.colorSpace = THREE.SRGBColorSpace;
    const lightsMesh = new THREE.Mesh(geometry, lightsMat);
    earthGroup.add(lightsMesh);

    const cloudsMat = new THREE.MeshStandardMaterial({
        map: loader.load(texturePath("04_earthcloudmap.jpg")),
        transparent: true,
        opacity: 0.8,
        blending: THREE.AdditiveBlending,
        alphaMap: loader.load(texturePath("05_earthcloudmaptrans.jpg")),
        depthWrite: false,
    });
    if (cloudsMat.map) cloudsMat.map.colorSpace = THREE.SRGBColorSpace;
    const cloudsMesh = new THREE.Mesh(geometry, cloudsMat);
    cloudsMesh.scale.setScalar(1.003);
    earthGroup.add(cloudsMesh);

    const fresnelMat = getFresnelMat();
    const glowMesh = new THREE.Mesh(geometry, fresnelMat);
    glowMesh.scale.setScalar(1.01);
    earthGroup.add(glowMesh);

    const stars = getStarfield({
        numStars: 2000,
        spriteUrl: texturePath("stars/circle.png"),
    });
    scene.add(stars);

    const sunLight = new THREE.DirectionalLight(0xffffff, 2.0);
    sunLight.position.set(-2, 0.5, 1.5);
    scene.add(sunLight);

    function animate() {
        requestAnimationFrame(animate);

        if (!prefersReducedMotion()) {
            // 3x slower than original threejs-earth speeds.
            earthMesh.rotation.y += 0.0006666667;
            lightsMesh.rotation.y += 0.0006666667;
            cloudsMesh.rotation.y += 0.0007666667;
            glowMesh.rotation.y += 0.0006666667;
            stars.rotation.y -= 0.0002;
        }
        renderer.render(scene, camera);
    }
    animate();

    function handleWindowResize() {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    }
    window.addEventListener("resize", handleWindowResize, false);
}

function prefersReducedMotion() {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function hasWebGLSupport() {
    try {
        const probe = document.createElement("canvas");
        return !!(
            window.WebGLRenderingContext &&
            (probe.getContext("webgl") || probe.getContext("experimental-webgl"))
        );
    } catch {
        return false;
    }
}
