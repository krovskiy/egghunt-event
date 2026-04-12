import { loadEgg } from './egg_viewer.js';

const submit = document.getElementById("sbmitBtn")
const textureInput = document.getElementById("eggTexture")
const textureStatus = document.getElementById("textureStatus")
const textureRepeatInput = document.querySelector(".eggTextureNumber")

const BASE_PATH = '/egghunt';
const API_BASE = `${BASE_PATH}/api`;
const MODEL_PATH = `${BASE_PATH}/assets/models/egg.glb`;
const MAX_NAME_LEN = 60;
const MAX_HINT_LEN = 280;
const MAX_REWARD_LEN = 140;
const MAX_REDEEMS = 99;

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
      window.location.href = `${BASE_PATH}/create-egg`;
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

const updateTextureStatus = (message, isError = false) => {
  if (textureStatus) {
    textureStatus.textContent = message;
    textureStatus.style.color = isError ? '#c00' : '#060';
  }
};

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
    const texturePath = egg.texture.startsWith('/') ? egg.texture : `/${egg.texture}`;
    currentTextureUrl = `${BASE_PATH}${texturePath}`;
    console.log('Loading texture from server:', currentTextureUrl);
    reloadPreview(currentTextureUrl);
   
    updateTextureStatus(`Loaded: ${egg.texture.split('/').pop()}`);
  }
};

const loadEditEgg = async () => {
  if (!editId) return;
  try {
    const res = await fetch(`${API_BASE}/egg/${editId}`);
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
  const MAX_FILE_SIZE = 8 * 1024 * 1024; // 8 MB
  const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'];

  const validateFile = (file) => {
    if (!file) return null;
    
    if (!ALLOWED_TYPES.includes(file.type)) {
      return 'Only image files (JPEG, PNG, WebP, GIF) are allowed.';
    }
    
    if (file.size > MAX_FILE_SIZE) {
      return `File size must be less than 8 MB. Current: ${(file.size / 1024 / 1024).toFixed(2)} MB`;
    }
    
    return null;
  };

  const updateStatus = (file, error = null) => {
    if (error) {
      textureStatus.textContent = error;
      textureStatus.style.color = '#c00';
    } else if (file) {
      textureStatus.textContent = `Selected: ${file.name}`;
      textureStatus.style.color = '#060';
    } else {
      textureStatus.textContent = 'No image selected';
      textureStatus.style.color = '#666';
    }
  };

  textureInput.addEventListener('change', (event) => {
    const file = event.target.files && event.target.files[0];
    const error = file ? validateFile(file) : null;

    if (error) {
      updateStatus(null, error);
      textureInput.value = '';
      return;
    }

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
        const error = validateFile(file);
        if (error) {
          updateStatus(null, error);
          return;
        }
        
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

const compressImage = (inputFile) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const img = new Image();
      img.onload = () => {
        const canvas = document.createElement('canvas');
        const maxWidth = 1024;
        const maxHeight = 1024;
        let width = img.width;
        let height = img.height;

        if (width > height) {
          if (width > maxWidth) {
            height = (height * maxWidth) / width;
            width = maxWidth;
          }
        } else {
          if (height > maxHeight) {
            width = (width * maxHeight) / height;
            height = maxHeight;
          }
        }

        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0, width, height);
        
        canvas.toBlob((blob) => {
          const compressedFile = new File([blob], inputFile.name, { type: 'image/jpeg' });
          resolve(compressedFile);
        }, 'image/jpeg', 0.85);
      };
      img.onerror = () => reject(new Error('Failed to load image'));
      img.src = e.target.result;
    };
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(inputFile);
  });
};

const toBase64 = (inputFile) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(inputFile);
  });
};

submit.addEventListener("click", async (e)=>{
  e.preventDefault();
  
  let eggName = document.getElementById("eggName");
  let eggHint = document.getElementById("eggHint");
  let eggMaxRedeems = document.getElementById("eggMaxRedeems");
  let eggReward = document.getElementById("eggReward");
  const repeatValue = Number(textureRepeatInput?.value ?? 1);

  let file = null;
  if (textureInput && textureInput.files && textureInput.files.length > 0) {
    file = textureInput.files[0];
  }

  try {
    const isEdit = Boolean(editId);
    
    // For new eggs, texture is required. For edits, texture is optional.
    if (!file && !isEdit) {
      showFailureToast('Error: You must add a texture!');
      return;
    }

    const nameValue = eggName.value.trim();
    const hintValue = eggHint.value.trim();
    const rewardValue = eggReward.value.trim();
    const maxRedeemsValue = Number(eggMaxRedeems.value);

    if (!nameValue || !hintValue || !eggMaxRedeems.value) {
      showFailureToast('Error: One of the fields is empty!');
      return;
    }

    if (nameValue.length > MAX_NAME_LEN) {
      showFailureToast(`Error: Name is too long (max ${MAX_NAME_LEN} chars).`);
      return;
    }

    if (hintValue.length > MAX_HINT_LEN) {
      showFailureToast(`Error: Hint is too long (max ${MAX_HINT_LEN} chars).`);
      return;
    }

    if (rewardValue.length > MAX_REWARD_LEN) {
      showFailureToast(`Error: Reward is too long (max ${MAX_REWARD_LEN} chars).`);
      return;
    }

    if (nameValue.includes('<') || nameValue.includes('>') || hintValue.includes('<') || hintValue.includes('>') || rewardValue.includes('<') || rewardValue.includes('>')) {
      showFailureToast('Error: Text fields contain invalid characters.');
      return;
    }

    if (!Number.isFinite(maxRedeemsValue) || maxRedeemsValue < 1 || maxRedeemsValue > MAX_REDEEMS) {
      showFailureToast(`Error: Max redeems must be between 1 and ${MAX_REDEEMS}.`);
      return;
    }

    let textureBase64 = null;
    if (file) {
      const compressedFile = await compressImage(file);
      textureBase64 = await toBase64(compressedFile);
    }

    const url = isEdit ? `${API_BASE}/update_egg/${editId}` : `${API_BASE}/create_egg`;
    const method = isEdit ? "PUT" : "POST";

    const payload = {
      "name": nameValue,
      "hint": hintValue,
      "max_redeems": maxRedeemsValue,
      "textureSize": repeatValue,
      "reward": rewardValue
    };

    if (textureBase64) {
      payload.texture = textureBase64;
    }

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
      const message = typeof body === 'object' && body && body.error
        ? `Error: ${body.error}`
        : 'Error: Failed to create egg. Please try again.';
      showFailureToast(message);
      return;
    }

    console.log(body);
    showSuccessToast(isEdit);
  } catch(err) {
    console.error("Failed to process egg", err);
    showFailureToast('Error: ' + (err.message || 'Failed to create egg'));
  }
});

