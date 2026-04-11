import { loadEgg } from './egg_viewer.js';

const submit = document.getElementById("sbmitBtn")
const textureInput = document.getElementById("eggTexture")
const textureStatus = document.getElementById("textureStatus")
const textureRepeatInput = document.querySelector(".eggTextureNumber")

const MODEL_PATH = '../assets/models/egg.glb';

const stageElement = document.getElementById('createEggPreview');
let currentTextureUrl = null;
let repeatNumber = Number(textureRepeatInput?.value ?? 1);
const editId = document.body?.dataset?.editId || null;

const reloadPreview = (textureUrl) => {
  if (!stageElement) return;
  stageElement.innerHTML = '';
  loadEgg(stageElement, textureUrl, {
    modelPath: MODEL_PATH,
    enableResize: true,
    onError: (error) => console.error('Failed to load egg model:', error),
    repeatNumber: repeatNumber,
  });
};

if (stageElement) {
  reloadPreview("");
}

const applyEditEgg = (egg) => {
  const eggName = document.getElementById("eggName");
  const eggHint = document.getElementById("eggHint");
  const eggMaxRedeems = document.getElementById("eggMaxRedeems");
  const eggReward = document.getElementById("eggReward");

  if (eggName) eggName.value = egg.name ?? "";
  if (eggHint) eggHint.value = egg.hint ?? "";
  if (eggMaxRedeems) eggMaxRedeems.value = egg.max_redeems ?? "";
  if (eggReward) eggReward.value = egg.reward ?? "";

  repeatNumber = Number(egg.textureSize ?? 1);
  if (textureRepeatInput) {
    textureRepeatInput.value = String(repeatNumber);
  }

  if (egg.texture) {
    currentTextureUrl = `/${egg.texture}`;
    reloadPreview(currentTextureUrl);
  }
};

const loadEditEgg = async () => {
  if (!editId) return;
  try {
    const res = await fetch(`/api/egg/${editId}`);
    if (!res.ok) {
      console.error("Couldn't load egg for edit", await res.text());
      return;
    }
    const egg = await res.json();
    applyEditEgg(egg);
  } catch (error) {
    console.error("Couldn't load egg for edit", error);
  }
};

loadEditEgg();

if (textureRepeatInput) {
  textureRepeatInput.addEventListener('input', () => {
    repeatNumber = Number(textureRepeatInput.value || 1);
    reloadPreview(currentTextureUrl ?? "");
  });
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
    const repeatValue = Number(textureRepeatInput?.value ?? 1);

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
      const isEdit = Boolean(editId);
      const url = isEdit ? `/api/update_egg/${editId}` : "/api/create_egg";
      const method = isEdit ? "PUT" : "POST";

      const payload = {
        "user_id": "whatever", //THIS IS HARDCODED
        "name": eggName.value,
        "hint": eggHint.value,
        "max_redeems": eggMaxRedeems.value,
        "texture": textureBase64,
        "textureSize": repeatValue,
      };

      const res = await fetch(url, {
        method,
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload),
      });

      const contentType = res.headers.get('content-type') || '';
      const body = contentType.includes('application/json')
        ? await res.json()
        : await res.text();

      if (!res.ok) {
        console.error("Failed to fetch", body);
        return;
      }

      console.log(body);
    } catch(err) {
      console.log("Failed to fetch", err)
    }
})

