let currentUserId = null;

import { loadEgg } from './egg_viewer.js';

const MODEL_PATH = '../assets/models/egg.glb';

function buildGrid(data, gridID) {
  const grid = document.getElementById(gridID);
  grid.innerHTML = '';

  data.forEach((egg) => {
    const card = document.createElement('div');
    card.className = 'egg-container';

    const ext = egg.author_avatar?.startsWith("a_") ? "gif" : "png";

    const avatarUrl = egg.author_avatar
      ? `https://cdn.discordapp.com/avatars/${egg.author_id}/${egg.author_avatar}.${ext}`
      : "https://cdn.discordapp.com/embed/avatars/0.png";

    card.innerHTML = `
      <div class="egg-stage" id="egg-${egg.egg_id}">
      <div class="egg-actions">
          <button class="egg-action egg-qrcode" type="button">VIEW QR CODE</button>
        </div>
      </div>
      <div class="egg-info">
        <div class="egg-name"><b>${egg.name}</b></div>
        <div class="egg-creator">Uploaded by: ${egg.author} <img class="creator-img" src="${avatarUrl}"</div>
    `; //somehow needs to fetch discord image instead of the placeholder 'creator-img'

    grid.appendChild(card);

    card.querySelector('.egg-qrcode').addEventListener('click', (e) => {
      e.stopPropagation();
      const overlay = document.createElement("div");
      overlay.className = "overlay";

      const box = document.createElement("div");
      box.className = "overlay-box overlay-qrcode";

      const qrcodeContainer = document.createElement("div");
      qrcodeContainer.className = "qrcode-container";

      const qrcodeDiv = document.createElement("div");
      qrcodeDiv.id = "qrcode";
      qrcodeDiv.className = "qrcode-display";

      const linkSection = document.createElement("div");
      linkSection.className = "qr-link-section";
      linkSection.innerHTML = `
        <div class="egg-label" style="text-align:center;">${egg.name}</div>
        <div class="qr-link-url">http://localhost:5000/${egg.salted_hash}</div>
        <div class="qr-link-buttons">
          <button class="overlay-btn qr-copy-btn">COPY LINK</button>
          <button class="overlay-btn qr-download-btn">DOWNLOAD QR</button>
        </div>
      `;

      qrcodeContainer.appendChild(qrcodeDiv);
      box.appendChild(qrcodeContainer);
      box.appendChild(linkSection);
      overlay.appendChild(box);
      document.body.appendChild(overlay);

      new QRCode(qrcodeDiv, `http://localhost:5000/${egg.salted_hash}`)

      const copyBtn = linkSection.querySelector('.qr-copy-btn');
      copyBtn.addEventListener('click', async () => {
        const url = `http://localhost:5000/${egg.salted_hash}`;
        try {
          await navigator.clipboard.writeText(url);
          const originalText = copyBtn.textContent;
          copyBtn.textContent = 'COPIED!';
          setTimeout(() => {
            copyBtn.textContent = originalText;
          }, 2000);
        } catch (err) {
          console.error('Failed to copy:', err);
          copyBtn.textContent = 'FAILED!';
          setTimeout(() => {
            copyBtn.textContent = 'COPY LINK';
          }, 2000);
        }
      });
      const downloadBtn = linkSection.querySelector('.qr-download-btn');
      console.log(downloadBtn);

      downloadBtn.addEventListener('click', () => {
        const img = qrcodeDiv.querySelector('img');
        if (!img) return;

        const link = document.createElement('a');
        link.href = img.src;
        link.download = `egg-qr-${egg.egg_id}.png`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      });

      overlay.addEventListener("click", () => overlay.remove());
      box.addEventListener("click", (e) => e.stopPropagation());
    });

    const stageElement = card.querySelector(`.egg-stage`);
    
    // Lazy load 3D model when card becomes visible
    if ('IntersectionObserver' in window) {
      const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            if (!stageElement.querySelector('canvas')) {
              loadEgg(stageElement, egg.texture, { modelPath: MODEL_PATH, repeatNumber: egg.textureSize });
            }
            observer.unobserve(card);
          }
        });
      }, { rootMargin: '100px' });
      observer.observe(card);
    } else {
      loadEgg(stageElement, egg.texture, { modelPath: MODEL_PATH, repeatNumber: egg.textureSize });
    }
  });
}

function showOverlay(id, data) {

  const overlay = document.createElement("div");
  overlay.className = "overlay";

  const box = document.createElement("div");
  box.className = "overlay-box";

  const eggPreview = document.createElement("div");
  eggPreview.className = "overlay-preview";

  const eggInfo = document.createElement("div");
  eggInfo.className = "overlay-info";

  const egg = data.find(e => `egg-${e.egg_id}` === id);

  const isAuthor = currentUserId && egg.author_id === currentUserId;
  
  const actionsHtml = isAuthor
    ? `
      <div class="overlay-actions">
        <button class="overlay-btn overlay-edit" type="button">Modify</button>
        <button class="overlay-btn overlay-delete" type="button">Remove</button>
      </div>
    `
    : '';

  eggInfo.innerHTML = `
  ${actionsHtml}
  <div class="egg-label">Easter Egg</div>
  <h2 class="egg-name"><b>${egg.name}</b></h2>
  <div class="egg-fields">
    <div class="egg-row">
      <span class="egg-key"><b>Creator:</b></span>
      <span class="egg-value">@${egg.author}</span>
    </div>
    <div class="egg-row">
      <span class="egg-key"><b>Redeems:</b></span>
      <span class="egg-redeem-badge">
        ${egg.max_redeems} left
      </span>
    </div>
    <div class="egg-row">
      <span class="egg-key"><b>Hint / Task:</b></span>
      <span class="egg-hint">NOTHINGAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA</span>
    </div>
  </div>
  `;

  setTimeout(() => {
    loadEgg(eggPreview, egg.texture, { modelPath: MODEL_PATH, repeatNumber: egg.textureSize, enableResize: true });
  }, 0);

  box.appendChild(eggPreview);
  box.appendChild(eggInfo);
  overlay.appendChild(box);
  document.body.appendChild(overlay);

  overlay.addEventListener("click", () => overlay.remove());
  box.addEventListener("click", (e) => e.stopPropagation());

  if (isAuthor) {
    const editButton = eggInfo.querySelector('.overlay-edit');
    const deleteButton = eggInfo.querySelector('.overlay-delete');

    editButton?.addEventListener('click', () => {
      window.location.href = `/create-egg?edit=${egg.egg_id}`;
    });

    deleteButton?.addEventListener('click', async () => {
      const confirmed = confirm('Remove this egg?');
      if (!confirmed) return;
      const res = await fetch(`/api/delete_egg/${egg.egg_id}`, { method: 'DELETE' });
      if (res.ok) {
        overlay.remove();
        window.location.reload();
      } else {
        console.error('Failed to delete egg', await res.text());
      }
    });
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  try {
    const [meRes, createdRes, redeemedRes] = await Promise.all([
      fetch('/api/me'),
      fetch('/api/created_eggs'),
      fetch('/api/my_eggs'),
    ]);


    if (meRes.ok) {
      const me = await meRes.json();
      currentUserId = me.id;
    }

    if (!createdRes.ok) {
      console.error("Couldn't fetch created eggs!", await createdRes.text());
      return;
    }
    if (!redeemedRes.ok) {
      console.error("Couldn't fetch redeemed eggs!", await redeemedRes.text());
      return;
    }

    const created = await createdRes.json();
    const redeemed = await redeemedRes.json();

    if (!Array.isArray(created) || !Array.isArray(redeemed)) {
      console.error("Couldn't fetch!", { created, redeemed });
      return;
    }

    buildGrid(created, 'eggGrid-Created');
    buildGrid(redeemed, 'eggGrid-Redeemed');

    document.getElementById("eggGrid-Created").addEventListener("click", (event) => {
      const stage = event.target.closest(".egg-stage");
      if (!stage) return;
      if (stage.dataset.dragged === 'true') {
        stage.dataset.dragged = '';
        return;
      }
      showOverlay(stage.id, created);
    });

    document.getElementById("eggGrid-Redeemed").addEventListener("click", (event) => {
      const stage = event.target.closest(".egg-stage");
      if (!stage) return;
      if (stage.dataset.dragged === 'true') {
        stage.dataset.dragged = '';
        return;
      }
      showOverlay(stage.id, redeemed);
    });
  } catch (err) {
    console.error("Couldn't fetch!", err);
  }
});
