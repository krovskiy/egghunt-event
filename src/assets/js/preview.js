import { Scene, PerspectiveCamera, WebGLRenderer, AmbientLight, DirectionalLight, TextureLoader, RepeatWrapping, Box3, Vector3, Group } from 'https://cdn.jsdelivr.net/npm/three@0.182.0/+esm';
import { GLTFLoader } from 'https://cdn.jsdelivr.net/npm/three@0.182.0/examples/jsm/loaders/GLTFLoader.js/+esm';
import { MeshoptDecoder } from 'https://cdn.jsdelivr.net/npm/three@0.182.0/examples/jsm/libs/meshopt_decoder.module.js/+esm';

const submit = document.getElementById("sbmitBtn")
const textureInput = document.getElementById("eggTexture")
const textureStatus = document.getElementById("textureStatus")

const MODEL_PATH = '../assets/models/egg.glb';


function loadEgg(container, texturePath) {
  const scene = new Scene();
  const camera = new PerspectiveCamera(55, container.clientWidth / container.clientHeight, 0.1, 100);
  camera.position.set(0, 0, 6);

  const renderer = new WebGLRenderer({ alpha: true, antialias: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.setSize(container.clientWidth, container.clientHeight);
  container.appendChild(renderer.domElement);

  const resize = () => {
    const width = container.clientWidth;
    const height = container.clientHeight;
    if (width === 0 || height === 0) return;
    renderer.setSize(width, height);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  };

  requestAnimationFrame(resize);
  window.addEventListener('resize', resize);

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
    const resolvedTexture = texturePath;
    textureLoader.load(resolvedTexture, (texture) => {
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
  }, undefined, (error) => {
    console.error('Failed to load egg model:', error);
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

const stageElement = document.getElementById('createEggPreview');
let currentTextureUrl = null;

const reloadPreview = (textureUrl) => {
  if (!stageElement) return;
  stageElement.innerHTML = '';
  loadEgg(stageElement, textureUrl);
};

if (stageElement) {
  loadEgg(stageElement, "");
}

if (textureInput && textureStatus) {
  const fileLabel = textureInput.closest('.file-input');

  const updateStatus = (file) => {
    textureStatus.textContent = file ? `Selected: ${file.name}` : 'No image selected';
  };

  textureInput.addEventListener('change', (event) => {
    const file = event.target.files && event.target.files[0];
    updateStatus(file);
    if (file) {
      if (currentTextureUrl) URL.revokeObjectURL(currentTextureUrl);
      currentTextureUrl = URL.createObjectURL(file);
      reloadPreview(currentTextureUrl);
    }
  });

  if (fileLabel) {
    fileLabel.addEventListener('dragover', (event) => {
      event.preventDefault();
      fileLabel.classList.add('dragover');
    });

    fileLabel.addEventListener('dragleave', () => {
      fileLabel.classList.remove('dragover');
    });

    fileLabel.addEventListener('drop', (event) => {
      event.preventDefault();
      fileLabel.classList.remove('dragover');
      const file = event.dataTransfer.files && event.dataTransfer.files[0];
      if (file) {
        const dt = new DataTransfer();
        dt.items.add(file);
        textureInput.files = dt.files;
        updateStatus(file);
        if (currentTextureUrl) URL.revokeObjectURL(currentTextureUrl);
        currentTextureUrl = URL.createObjectURL(file);
        reloadPreview(currentTextureUrl);
      }
    });
  }
}

submit.addEventListener("click", async (e)=>{
    e.preventDefault()
    let eggName = document.getElementById("eggName")
    let eggHint = document.getElementById("eggHint")
    let eggMaxRedeems = document.getElementById("eggMaxRedeems")

    let file = null;
    if (textureInput && textureInput.files && textureInput.files.length > 0) {
      file = textureInput.files[0];
    }

    const toBase64 = (inputFile) => {
        return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = () => reject(reader.error);
        reader.readAsDataURL(inputFile);
        });
    };

    try {
    const textureBase64 = file ? await toBase64(file) : null;
        const res = await fetch("/api/create_egg", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                "user_id": "whatever",
                "name": eggName.value,
                "hint": eggHint.value,
                "max_redeems": eggMaxRedeems.value,
                "texture": textureBase64
            })
        })
        const data = await res.json()
        console.log(data)
    } catch(err) {
        console.log("Failed to fetch", err)
    }
})