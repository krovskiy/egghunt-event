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

const showSuccessToast = (isEdit = false) => {
  const existingToast = document.querySelector('.toast');
  if (existingToast) existingToast.remove();

  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.setAttribute('role', 'status');
  toast.setAttribute('aria-live', 'polite');
  const action = isEdit ? 'edited' : 'created';
  toast.innerHTML = `
    <svg class="toast-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path d="M9.2 16.2L4.8 11.8l1.4-1.4 3 3 8-8 1.4 1.4-9.4 9.4z"></path>
    </svg>
    <span>Succesful! The Egg has been ${action}</span>
  `;

  document.body.appendChild(toast);
  requestAnimationFrame(() => toast.classList.add('is-visible'));

  setTimeout(() => {
    toast.classList.remove('is-visible');
    setTimeout(() => {
      toast.remove();
      window.location.reload();
    }, 400);
  }, 2400);
};

const showFailureToast = (message = 'Failed to create egg. Please try again.') => {
  const existingToast = document.querySelector('.toast');
  if (existingToast) existingToast.remove();

  const toast = document.createElement('div');
  toast.className = 'toast toast-failure';
  toast.setAttribute('role', 'status');
  toast.setAttribute('aria-live', 'polite');
  toast.innerHTML = `
    <svg class="toast-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12 19 6.41z"></path>
    </svg>
    <span>${message}</span>
  `;

  document.body.appendChild(toast);
  requestAnimationFrame(() => toast.classList.add('is-visible'));

  setTimeout(() => {
    toast.classList.remove('is-visible');
    setTimeout(() => {
      toast.remove();
    }, 400);
  }, 2400);
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
      if (!textureBase64){
        showFailureToast('Error: You must add a texture!')
        throw Error('Missing texture');
      }

      if (eggName.value == "" || eggHint.value == "" || eggMaxRedeems == ""){
        showFailureToast('Error: One of the fields is empty!')
        throw Error('No value in field');
      }

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
      showSuccessToast(isEdit);
    } catch(err) {
      console.log("Failed to fetch", err)
    }
})

