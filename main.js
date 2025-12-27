import * as THREE from "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js";
import { PointerLockControls } from "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/controls/PointerLockControls.js";

const scene = new THREE.Scene();
scene.fog = new THREE.Fog(0x0f1116, 10, 48);

const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 200);
camera.position.set(0, 6, 16);

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
document.body.appendChild(renderer.domElement);

const ambient = new THREE.AmbientLight(0x88a0ff, 0.5);
scene.add(ambient);

const keyLight = new THREE.DirectionalLight(0x88ccff, 0.6);
keyLight.position.set(8, 12, 4);
scene.add(keyLight);

const fillLight = new THREE.DirectionalLight(0x55ffb0, 0.35);
fillLight.position.set(-10, 6, -6);
scene.add(fillLight);

const gridHelper = new THREE.GridHelper(80, 40, 0x335050, 0x1a2525);
scene.add(gridHelper);

const floorGeo = new THREE.PlaneGeometry(80, 80);
const floorMat = new THREE.MeshStandardMaterial({ color: 0x16211f, roughness: 0.8, metalness: 0.2 });
const floor = new THREE.Mesh(floorGeo, floorMat);
floor.rotation.x = -Math.PI / 2;
floor.position.y = -0.1;
scene.add(floor);

const hubGeo = new THREE.CylinderGeometry(1.4, 1.8, 1.2, 32, 1, false);
const hubMat = new THREE.MeshStandardMaterial({ color: 0x7fffd0, emissive: 0x25624a, metalness: 0.6 });
const hub = new THREE.Mesh(hubGeo, hubMat);
hub.position.set(-10, 0.6, -8);
scene.add(hub);

const resourceMat = new THREE.MeshStandardMaterial({ color: 0xe0a070, emissive: 0x332218, metalness: 0.3 });
const nodeMat = new THREE.MeshStandardMaterial({ color: 0x4ed8a2, emissive: 0x164030, metalness: 0.7 });

const resources = [];
for (let i = 0; i < 22; i += 1) {
  const mesh = new THREE.Mesh(new THREE.SphereGeometry(0.4, 16, 12), resourceMat);
  mesh.position.set((Math.random() - 0.5) * 40, 0.4, (Math.random() - 0.5) * 40);
  scene.add(mesh);
  resources.push({ mesh, amount: Math.random() * 1.0 + 0.2 });
}

const nodes = [];

const npcMat = new THREE.MeshStandardMaterial({ color: 0xffc456, emissive: 0x5a2d10 });
const npcGeo = new THREE.CapsuleGeometry(0.5, 1.2, 6, 10);

const npcNames = ["Эхо", "Люм", "Код", "Нова", "Сфера"];
const npcs = npcNames.map((name, index) => {
  const mesh = new THREE.Mesh(npcGeo, npcMat);
  mesh.position.set(-12 + index * 3.2, 1.2, -3 + index);
  scene.add(mesh);
  return {
    name,
    mesh,
    energy: 100,
    knowledge: 0,
    inventory: 0,
    target: new THREE.Vector3(),
    role: "скиталец",
  };
});

const controls = new PointerLockControls(camera, renderer.domElement);
scene.add(controls.getObject());

const move = { forward: false, backward: false, left: false, right: false };

window.addEventListener("click", () => {
  controls.lock();
});

window.addEventListener("keydown", (event) => {
  if (event.code === "KeyW") move.forward = true;
  if (event.code === "KeyS") move.backward = true;
  if (event.code === "KeyA") move.left = true;
  if (event.code === "KeyD") move.right = true;
});

window.addEventListener("keyup", (event) => {
  if (event.code === "KeyW") move.forward = false;
  if (event.code === "KeyS") move.backward = false;
  if (event.code === "KeyA") move.left = false;
  if (event.code === "KeyD") move.right = false;
});

const clock = new THREE.Clock();
let dayTimer = 0;
let dayCount = 1;

function chooseResourceTarget(npc) {
  let best = null;
  let bestScore = -Infinity;
  resources.forEach((res) => {
    const dist = npc.mesh.position.distanceTo(res.mesh.position);
    const score = res.amount - dist * 0.01;
    if (score > bestScore) {
      bestScore = score;
      best = res;
    }
  });
  if (best) npc.target.copy(best.mesh.position);
}

function chooseBuildTarget(npc) {
  npc.target.set((Math.random() - 0.5) * 26, 0.4, (Math.random() - 0.5) * 26);
}

function updateNpc(npc, dt) {
  npc.energy = Math.max(0, npc.energy - dt * 4.5);
  npc.knowledge = Math.min(100, npc.knowledge + dt * 0.6);

  if (npc.energy < 35) {
    npc.role = "отдых";
    npc.target.copy(hub.position);
  } else if (npc.inventory >= 3) {
    npc.role = "строитель";
    if (npc.mesh.position.distanceTo(npc.target) < 0.6) {
      const node = new THREE.Mesh(new THREE.BoxGeometry(1, 1.6, 1), nodeMat);
      node.position.copy(npc.mesh.position);
      node.position.y = 0.8;
      scene.add(node);
      nodes.push(node);
      npc.inventory -= 3;
      npc.knowledge = Math.min(100, npc.knowledge + 12);
      chooseBuildTarget(npc);
    }
  } else {
    npc.role = "сборщик";
    chooseResourceTarget(npc);
  }

  const direction = npc.target.clone().sub(npc.mesh.position);
  if (direction.lengthSq() > 0.01) {
    direction.normalize();
    npc.mesh.position.addScaledVector(direction, dt * 3.2);
    npc.mesh.rotation.y = Math.atan2(direction.x, direction.z);
  }

  if (npc.role === "сборщик") {
    resources.forEach((res) => {
      if (npc.mesh.position.distanceTo(res.mesh.position) < 0.7 && res.amount > 0.2) {
        res.amount = Math.max(0, res.amount - 0.4);
        npc.inventory += 1;
      }
    });
  }

  if (npc.role === "отдых" && npc.mesh.position.distanceTo(hub.position) < 1.2) {
    npc.energy = Math.min(100, npc.energy + dt * 40);
  }
}

function updateResources(dt) {
  resources.forEach((res) => {
    res.amount = Math.min(1.4, res.amount + dt * 0.15);
    res.mesh.scale.setScalar(0.6 + res.amount * 0.5);
  });
}

function updatePlayer(dt) {
  const speed = 6.0;
  if (!controls.isLocked) return;
  const direction = new THREE.Vector3();
  if (move.forward) direction.z -= 1;
  if (move.backward) direction.z += 1;
  if (move.left) direction.x -= 1;
  if (move.right) direction.x += 1;
  if (direction.lengthSq() > 0) {
    direction.normalize();
    const moveVector = direction.applyQuaternion(camera.quaternion);
    controls.getObject().position.addScaledVector(moveVector, speed * dt);
    controls.getObject().position.y = 3.5;
  }
}

function animate() {
  requestAnimationFrame(animate);
  const dt = clock.getDelta();

  dayTimer += dt;
  if (dayTimer > 45) {
    dayTimer = 0;
    dayCount += 1;
  }

  updatePlayer(dt);
  updateResources(dt);
  npcs.forEach((npc) => updateNpc(npc, dt));

  document.getElementById("nodes").textContent = nodes.length.toString();
  document.getElementById("day").textContent = dayCount.toString();

  renderer.render(scene, camera);
}

window.addEventListener("resize", () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

animate();
