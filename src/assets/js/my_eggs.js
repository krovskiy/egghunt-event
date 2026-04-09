const userID = "whatever" // TODO: integrate discord instead of hardcode

import { Scene, PerspectiveCamera, WebGLRenderer, AmbientLight, DirectionalLight, TextureLoader, RepeatWrapping, Box3, Vector3 } from 'https://cdn.jsdelivr.net/npm/three@0.182.0/+esm';
import { GLTFLoader } from 'https://cdn.jsdelivr.net/npm/three@0.182.0/examples/jsm/loaders/GLTFLoader.js/+esm';
import { MeshoptDecoder } from 'https://cdn.jsdelivr.net/npm/three@0.182.0/examples/jsm/libs/meshopt_decoder.module.js/+esm';

const MODEL_PATH = '../assets/models/egg.glb';

function loadEgg(container, texturePath) {
  const scene = new Scene();
  const camera = new PerspectiveCamera(55, container.clientWidth / container.clientHeight, 0.1, 100);
  camera.position.set(0, 0, 6);

  const renderer = new WebGLRenderer({ alpha: true, antialias: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.setSize(container.clientWidth, container.clientHeight);
  container.appendChild(renderer.domElement);

  scene.add(new AmbientLight(0xffffff, 1.2));
  const light = new DirectionalLight(0xffffff, 1.0);
  light.position.set(2, 3, 4);
  scene.add(light);

  let model = null;
  let pivot = null;
  let rotationY = 0;
  let isDragging = false;
  let didDrag = false;
  let lastX = 0;
  let dragStartX = 0;
  let lastDragTime = 0;
  const autoRotateDelayMs = 900;
  const autoRotateSpeed = 0.003;

  const loader = new GLTFLoader();
  loader.setMeshoptDecoder(MeshoptDecoder);
  loader.load(MODEL_PATH, (gltf) => {
    model = gltf.scene;
    model.scale.setScalar(4);
    
    // Center the model by calculating bounding box and offsetting position
    const box = new Box3().setFromObject(model);
    const center = new Vector3();
    box.getCenter(center);
    model.position.sub(center);
    
    const textureLoader = new TextureLoader();
    textureLoader.load(texturePath, (texture) => {
      texture.repeat.set(2, 3);
      texture.wrapS = RepeatWrapping;
      texture.wrapT = RepeatWrapping;
      
      model.traverse((child) => {
        if (child.isMesh) {
          child.material.map = texture;
          child.material.needsUpdate = true;
        }
      });
    });
    
    pivot = new Group();
    pivot.add(model);
    scene.add(pivot);
  });

  renderer.domElement.style.cursor = 'grab';
  renderer.domElement.addEventListener('pointerdown', (event) => {
    isDragging = true;
    didDrag = false;
    lastX = event.clientX;
    dragStartX = event.clientX;
    lastDragTime = performance.now();
    renderer.domElement.setPointerCapture(event.pointerId);
    renderer.domElement.style.cursor = 'grabbing';
  });

  renderer.domElement.addEventListener('pointermove', (event) => {
    if (!isDragging || !model) return;
    const deltaX = event.clientX - lastX;
    lastX = event.clientX;
    rotationY += deltaX * 0.01;
    if (Math.abs(event.clientX - dragStartX) > 4) {
      didDrag = true;
    }
    lastDragTime = performance.now();
  });

  renderer.domElement.addEventListener('pointerup', (event) => {
    isDragging = false;
    lastDragTime = performance.now();
    renderer.domElement.releasePointerCapture(event.pointerId);
    renderer.domElement.style.cursor = 'grab';
    if (didDrag) {
      container.dataset.dragged = 'true';
    }
  });

  renderer.domElement.addEventListener('pointerleave', () => {
    isDragging = false;
    lastDragTime = performance.now();
    renderer.domElement.style.cursor = 'grab';
  });

  function animate() {
    requestAnimationFrame(animate);

    if (pivot) {
      if (!isDragging && performance.now() - lastDragTime > autoRotateDelayMs) {
        rotationY += autoRotateSpeed;
      }
      pivot.rotation.y = rotationY;
    }

    camera.lookAt(0, 0, 0);
    
    renderer.render(scene, camera);
  }

  animate();
}

function buildGrid(data) {
  const grid = document.getElementById('eggGrid-Redeemed');
  grid.innerHTML = '';

  data.forEach((egg) => {
    const card = document.createElement('div');
    card.className = 'egg-container';

    card.innerHTML = `
      <div class="egg-stage" id="egg-${egg.egg_id}">
      </div>
      <div class="egg-info">
        <div class="egg-name">${egg.name}</div>
        <div class="egg-creator">${egg.author} <img class="creator-img" src="https://www.gravatar.com/avatar/359e957a7aa4fda8393c1d5340e6c239?s=64&d=identicon&r=PG&f=y&so-version=2"/></div>
      </div>
    `; //somehow needs to fetch discord image instead of the placeholder 'creator-img'

    grid.appendChild(card);

    const stageElement = card.querySelector(`.egg-stage`);
    loadEgg(stageElement, egg.texture); // this needs CHANGED because right now it doesnt do anything
  });
}

function showOverlay(id,data) {
  const overlay = document.createElement("div");
  overlay.className = "overlay";

  const box = document.createElement("div");
  box.className = "overlay-box";

  const eggPreview = document.createElement("div");
  eggPreview.className = "overlay-preview";

  const eggInfo = document.createElement("div");
  eggInfo.className = "overlay-info";

  const egg = data.find(e => `egg-${e.egg_id}` === id);

  eggInfo.innerHTML = `
    <h2>${egg.name}</h2>
    <p>Creator: ${egg.author}</p>
    <p>Redeemable ONLY first who gets it: ${egg.max_redeems}</p>
    <p>Hint: ${egg.hint}</p>
  `;

  setTimeout(() => {
  loadEgg(eggPreview, egg.texture);
    }, 0);

  box.appendChild(eggPreview);
  box.appendChild(eggInfo);
  overlay.appendChild(box);
  document.body.appendChild(overlay);

  overlay.addEventListener("click", () => overlay.remove());
  box.addEventListener("click", (e) => e.stopPropagation());
}

document.addEventListener("DOMContentLoaded", async () => {
    try {
        const res = await fetch(`/api/user/${userID}/my_eggs`)
        const data = await res.json()

        console.log(data)
        buildGrid(data)

        document.getElementById("eggGrid-Redeemed").addEventListener("click", (event) => {
            const stage = event.target.closest(".egg-stage");
            if (!stage) return;
                    showOverlay(stage.id, data); 
                });
            } catch(err){
                console.log("Couldn't fetch!", err)
            }
}
);

document.getElementById("eggGrid-Redeemed").addEventListener("click", (event) => {
  const stage = event.target.closest(".egg-stage");
  if (!stage) return;

  const id = stage.id; 
  console.log("Clicked:", id);

  showOverlay(id);
});