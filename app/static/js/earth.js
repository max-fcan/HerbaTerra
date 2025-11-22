'use strict';

import * as THREE from './vendor/three/three.module.js';
import { OrbitControls } from './vendor/three/OrbitControls.js';

const degToRad = deg => (deg * Math.PI) / 180;

function getFresnelMat({ rimHex = 0x0088ff, facingHex = 0x000000 } = {}) {
  const uniforms = {
    color1: { value: new THREE.Color(rimHex) },
    color2: { value: new THREE.Color(facingHex) },
    fresnelBias: { value: 0.1 },
    fresnelScale: { value: 1.0 },
    fresnelPower: { value: 4.0 },
  };

  const vs = `
    uniform float fresnelBias;
    uniform float fresnelScale;
    uniform float fresnelPower;

    varying float vReflectionFactor;

    void main() {
      vec4 mvPosition = modelViewMatrix * vec4( position, 1.0 );
      vec4 worldPosition = modelMatrix * vec4( position, 1.0 );

      vec3 worldNormal = normalize( mat3( modelMatrix[0].xyz, modelMatrix[1].xyz, modelMatrix[2].xyz ) * normal );
      vec3 I = worldPosition.xyz - cameraPosition;

      vReflectionFactor = fresnelBias + fresnelScale * pow( 1.0 + dot( normalize( I ), worldNormal ), fresnelPower );

      gl_Position = projectionMatrix * mvPosition;
    }
  `;

  const fs = `
    uniform vec3 color1;
    uniform vec3 color2;

    varying float vReflectionFactor;

    void main() {
      float f = clamp( vReflectionFactor, 0.0, 1.0 );
      gl_FragColor = vec4(mix(color2, color1, vec3(f)), f);
    }
  `;

  return new THREE.ShaderMaterial({
    uniforms,
    vertexShader: vs,
    fragmentShader: fs,
    transparent: true,
    blending: THREE.AdditiveBlending,
  });
}

function getStarfield(numStars, spriteUrl) {
  const verts = [];
  const colors = [];

  const randomSpherePoint = () => {
    const radius = Math.random() * 25 + 25;
    const u = Math.random();
    const v = Math.random();
    const theta = 2 * Math.PI * u;
    const phi = Math.acos(2 * v - 1);
    const x = radius * Math.sin(phi) * Math.cos(theta);
    const y = radius * Math.sin(phi) * Math.sin(theta);
    const z = radius * Math.cos(phi);
    return new THREE.Vector3(x, y, z);
  };

  for (let i = 0; i < numStars; i += 1) {
    const pos = randomSpherePoint();
    const col = new THREE.Color().setHSL(0.6, 0.2, Math.random());
    verts.push(pos.x, pos.y, pos.z);
    colors.push(col.r, col.g, col.b);
  }

  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(verts, 3));
  geo.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));

  const mat = new THREE.PointsMaterial({
    size: 0.2,
    vertexColors: true,
    map: spriteUrl ? new THREE.TextureLoader().load(spriteUrl) : null,
    transparent: true,
    depthWrite: false,
  });

  return new THREE.Points(geo, mat);
}

function initEarthBackground(container) {
  const textureBase = (container.dataset.earthTextureBase || '').replace(/\/$/, '');
  const texturePath = file => `${textureBase}/${file}`;

  if (!textureBase) {
    console.warn('[Earth] Missing data-earth-texture-base attribute.');
    return;
  }

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(
    55,
    window.innerWidth / window.innerHeight,
    0.1,
    1000
  );
  camera.position.z = 4.5;

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  if ('outputColorSpace' in renderer) {
    renderer.outputColorSpace = THREE.SRGBColorSpace;
  } else {
    renderer.outputEncoding = THREE.sRGBEncoding;
  }

  container.innerHTML = '';
  renderer.domElement.style.width = '100%';
  renderer.domElement.style.height = '100%';
  renderer.domElement.style.pointerEvents = 'none';
  container.appendChild(renderer.domElement);

  const earthGroup = new THREE.Group();
  earthGroup.rotation.z = -degToRad(23.4);
  scene.add(earthGroup);

  const manager = new THREE.LoadingManager();
  manager.onError = url => console.error('[Earth] Texture failed to load:', url);
  const loader = new THREE.TextureLoader(manager);
  const geoDetail = 12;
  const geometry = new THREE.IcosahedronGeometry(1, geoDetail);

  const baseMat = new THREE.MeshPhongMaterial({
    map: loader.load(texturePath('00_earthmap1k.jpg')),
    specularMap: loader.load(texturePath('02_earthspec1k.jpg')),
    bumpMap: loader.load(texturePath('01_earthbump1k.jpg')),
    bumpScale: 0.04,
  });
  [baseMat.map, baseMat.specularMap, baseMat.bumpMap].forEach(tex => {
    if (!tex) return;
    if ('colorSpace' in tex) tex.colorSpace = THREE.SRGBColorSpace;
    else tex.encoding = THREE.sRGBEncoding;
  });
  const earthMesh = new THREE.Mesh(geometry, baseMat);
  earthGroup.add(earthMesh);

  const lightsMat = new THREE.MeshBasicMaterial({
    map: loader.load(texturePath('03_earthlights1k.jpg')),
    blending: THREE.AdditiveBlending,
    transparent: true,
  });
  if (lightsMat.map) {
    if ('colorSpace' in lightsMat.map) lightsMat.map.colorSpace = THREE.SRGBColorSpace;
    else lightsMat.map.encoding = THREE.sRGBEncoding;
  }
  const lightsMesh = new THREE.Mesh(geometry, lightsMat);
  earthGroup.add(lightsMesh);

  const cloudsMat = new THREE.MeshStandardMaterial({
    map: loader.load(texturePath('04_earthcloudmap.jpg')),
    transparent: true,
    opacity: 0.65,
    blending: THREE.AdditiveBlending,
    alphaMap: loader.load(texturePath('05_earthcloudmaptrans.jpg')),
  });
  ['map', 'alphaMap'].forEach(key => {
    const tex = cloudsMat[key];
    if (!tex) return;
    if ('colorSpace' in tex) tex.colorSpace = THREE.SRGBColorSpace;
    else tex.encoding = THREE.sRGBEncoding;
  });
  const cloudsMesh = new THREE.Mesh(geometry, cloudsMat);
  cloudsMesh.scale.setScalar(1.003);
  earthGroup.add(cloudsMesh);

  const fresnelMat = getFresnelMat();
  const glowMesh = new THREE.Mesh(geometry, fresnelMat);
  glowMesh.scale.setScalar(1.01);
  earthGroup.add(glowMesh);

  const stars = getStarfield(1500, texturePath('stars/circle.png'));
  scene.add(stars);

  const sunLight = new THREE.DirectionalLight(0xffffff, 2.2);
  sunLight.position.set(-2, 0.5, 1.5);
  scene.add(sunLight);

  const ambientLight = new THREE.AmbientLight(0x1d2635, 0.6);
  scene.add(ambientLight);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enablePan = false;
  controls.enableZoom = false;
  controls.enableRotate = false;
  controls.enableDamping = true;

  const handleResize = () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  };
  window.addEventListener('resize', handleResize);

  function animate() {
    earthMesh.rotation.y += 0.0018;
    lightsMesh.rotation.y += 0.0018;
    cloudsMesh.rotation.y += 0.0021;
    glowMesh.rotation.y += 0.0018;
    stars.rotation.y -= 0.0002;
    controls.update();
    renderer.render(scene, camera);
    requestAnimationFrame(animate);
  }

  animate();
}

document.addEventListener('DOMContentLoaded', () => {
  const container = document.querySelector('#earth-canvas');
  if (!container) return;
  initEarthBackground(container);
});
