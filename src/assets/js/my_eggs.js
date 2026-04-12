let currentUserId = null;

import { loadEgg } from './egg_viewer.js';

const MODEL_PATH = '../assets/models/egg.glb';

function unloadStage(stageElement) {
  const cleanup = stageElement._cleanup;
  if (typeof cleanup === 'function') {
    cleanup();
  }
  stageElement._cleanup = null;
  delete stageElement.dataset.loading;
  const canvases = stageElement.querySelectorAll('canvas');
  canvases.forEach((canvas) => canvas.remove());
}

const eggObserver = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    const card = entry.target;
    const stageElement = card.querySelector('.egg-stage');
    if (!stageElement) return;

    if (entry.isIntersecting) {
      if (stageElement.dataset.loading === '1') return;
      if (stageElement.querySelector('canvas')) return; // already loaded

      stageElement.dataset.loading = '1';
      const texture = stageElement.dataset.texture || '';
      const textureSize = Number(stageElement.dataset.textureSize || 0);
      stageElement._cleanup = loadEgg(stageElement, texture, {
        modelPath: MODEL_PATH,
        repeatNumber: textureSize,
      });

      setTimeout(() => {
        delete stageElement.dataset.loading;
      }, 0);
    } else {
      unloadStage(stageElement);
    }
  });
}, { rootMargin: '3% 0px' });

function getRedeemClass(remaining, maxRedeems) {
  if (maxRedeems <= 0) return 'redeem-green';
  const ratio = remaining / maxRedeems;
  if (ratio <= 0.2) return 'redeem-red';
  if (ratio <= 0.5) return 'redeem-yellow';
  return 'redeem-green';
}

function formatRedeemBadge(egg) {
  const maxRedeems = Number(egg.max_redeems ?? 0);
  const redeems = Number(egg.redeems ?? 0);
  const remaining = Math.max(0, maxRedeems - redeems);
  const badgeClass = getRedeemClass(remaining, maxRedeems);
  return `
    <span class="egg-redeem-badge ${badgeClass}">
      ${remaining} left
    </span>
  `;
}

function buildGrid(data, gridID) {
  const grid = document.getElementById(gridID);
  grid.innerHTML = '';

  data.forEach((egg) => {
    const card = document.createElement('div');
    card.className = 'egg-container';
    if (gridID === 'eggGrid-Redeemed') {
      card.classList.add('egg-container-redeemed');
    }
    if (gridID === 'eggGrid-Redeemed') {
      card.classList.add('egg-container-redeemed');
    }

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

      const qrTitle = document.createElement("h3");
      qrTitle.style.textAlign = "center";
      qrTitle.style.padding = "20px";
      qrTitle.style.fontSize = "36px";
      qrTitle.innerHTML = "your <mark class=\"mark-brown\">kafeshka</mark> has<br> been stolen!";

      const qrcodeContainer = document.createElement("div");
      qrcodeContainer.className = "qrcode-container";

      const qrcodeDiv = document.createElement("div");
      qrcodeDiv.id = "qrcode";
      qrcodeDiv.className = "qrcode-display";

      const linkSection = document.createElement("div");
      linkSection.className = "qr-link-section";
      linkSection.innerHTML = `
        <div class="egg-label" style="text-align:center;">${egg.name}</div>
        <div class="qr-link-url">http://localhost:5000/redeem_egg/${egg.salted_hash}</div>
        <div class="qr-link-buttons">
          <button class="overlay-btn qr-copy-btn">COPY LINK</button>
          <button class="overlay-btn qr-download-btn">DOWNLOAD QR</button>
        </div>
      `;

      qrcodeContainer.appendChild(qrcodeDiv);
      box.appendChild(qrTitle);
      box.appendChild(qrcodeContainer);
      box.appendChild(linkSection);
      overlay.appendChild(box);
      document.body.appendChild(overlay);

      new QRCode(qrcodeDiv, `http://localhost:5000/redeem_egg/${egg.salted_hash}`)

      const copyBtn = linkSection.querySelector('.qr-copy-btn');
      copyBtn.addEventListener('click', async () => {
        const url = `http://localhost:5000/redeem_egg/${egg.salted_hash}`;
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

        const drawQrWithHeader = () => {
          const fontSize = 28;
          const lineGap = 8;
          const padding = 24;
          const headerHeight = fontSize * 2 + lineGap;

          const qrSize = img.naturalWidth || 256;
          const width = Math.max(qrSize + padding * 2, 420);
          const height = padding + headerHeight + padding + qrSize + padding;

          const canvas = document.createElement('canvas');
          const scale = 2;
          canvas.width = width * scale;
          canvas.height = height * scale;
          const ctx = canvas.getContext('2d');
          if (!ctx) return;

          ctx.scale(scale, scale);

          ctx.fillStyle = '#ffffff';
          ctx.fillRect(0, 0, width, height);

          ctx.fillStyle = '#4a4a4a';
          ctx.font = `700 ${fontSize}px profont, serif`;
          ctx.textBaseline = 'top';

          let textY = padding;
          const leftText = 'your ';
          const highlightText = 'kafeshka';
          const rightText = ' has';
          const secondLine = 'been stolen!';

          const lineWidth =
            ctx.measureText(leftText).width +
            ctx.measureText(highlightText).width +
            ctx.measureText(rightText).width;
          const lineX = (width - lineWidth) / 2;

          ctx.fillStyle = '#4a4a4a';
          ctx.fillText(leftText, lineX, textY);

          const highlightX = lineX + ctx.measureText(leftText).width;
          const gradient = ctx.createLinearGradient(highlightX, textY, highlightX + ctx.measureText(highlightText).width, textY + fontSize);
          gradient.addColorStop(0, 'rgb(255, 255, 33)');
          gradient.addColorStop(0.33, 'rgb(247, 70, 185)');
          gradient.addColorStop(0.66, 'rgb(56, 206, 236)');
          gradient.addColorStop(1, 'rgb(255, 135, 209)');
          ctx.fillStyle = gradient;
          ctx.fillText(highlightText, highlightX, textY);

          ctx.fillStyle = '#4a4a4a';
          ctx.fillText(rightText, highlightX + ctx.measureText(highlightText).width, textY);

          textY += fontSize + lineGap;
          const secondWidth = ctx.measureText(secondLine).width;
          ctx.fillText(secondLine, (width - secondWidth) / 2, textY);

          const qrX = (width - qrSize) / 2;
          const qrY = padding + headerHeight + padding;
          ctx.drawImage(img, qrX, qrY, qrSize, qrSize);

          const link = document.createElement('a');
          link.href = canvas.toDataURL('image/png');
          link.download = `egg-qr-${egg.egg_id}.png`;
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
        };

        if (img.complete) {
          drawQrWithHeader();
        } else {
          img.addEventListener('load', drawQrWithHeader, { once: true });
        }
      });

      overlay.addEventListener("click", () => overlay.remove());
      box.addEventListener("click", (e) => e.stopPropagation());
    });

    const stageElement = card.querySelector(`.egg-stage`);
    
    // Lazy load 3D model when card becomes visible
    if ('IntersectionObserver' in window) {
      const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) {
            const cleanup = stageElement._cleanup;
            if (typeof cleanup === 'function') {
              cleanup();
            }
            stageElement._cleanup = null;
            delete stageElement.dataset.loading;
            stageElement.querySelectorAll('canvas').forEach((canvas) => canvas.remove());
            return;
          }

          if (stageElement.dataset.loading === '1') return;
          if (stageElement.querySelector('canvas')) return; // already loaded

          stageElement.dataset.loading = '1';
          stageElement._cleanup = loadEgg(stageElement, egg.texture, {
            modelPath: MODEL_PATH,
            repeatNumber: egg.textureSize,
          });

          setTimeout(() => {
            delete stageElement.dataset.loading;
          }, 0);
        });
      }, { rootMargin: '3% 0px' });
      observer.observe(card);
    } else {
      stageElement._cleanup = loadEgg(stageElement, egg.texture, {
        modelPath: MODEL_PATH,
        repeatNumber: egg.textureSize,
      });
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
      ${formatRedeemBadge(egg)}
    </div>
    <div class="egg-row">
      <span class="egg-key"><b>Hint / Task:</b></span>
      <span class="egg-hint">${egg.hint}</span>
    </div>
    <div class="egg-row">
      <span class="egg-key"><b>Reward:</b></span>
      <span class="egg-reward">${egg.reward}</span>
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

function showRedeemToast(success = true) {
  const existingToast = document.querySelector('.toast');
  if (existingToast) existingToast.remove();

  const toast = document.createElement('div');
  toast.className = success ? 'toast' : 'toast toast-failure';
  toast.setAttribute('role', 'status');
  toast.setAttribute('aria-live', 'polite');
  
  if (success) {
    toast.innerHTML = `
      <svg class="toast-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
        <path d="M9.2 16.2L4.8 11.8l1.4-1.4 3 3 8-8 1.4 1.4-9.4 9.4z"></path>
      </svg>
      <span>Egg redeemed successfully!</span>
    `;
  } else {
    toast.innerHTML = `
      <svg class="toast-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
        <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12 19 6.41z"></path>
      </svg>
      <span>Failed to redeem egg. Please try again.</span>
    `;
  }

  document.body.appendChild(toast);
  requestAnimationFrame(() => toast.classList.add('is-visible'));

  setTimeout(() => {
    toast.classList.remove('is-visible');
    setTimeout(() => {
      toast.remove();
    }, 400);
  }, 2400);
}

document.addEventListener("DOMContentLoaded", async () => {
  // Check for query parameters from redemption redirect
  const params = new URLSearchParams(window.location.search);
  if (params.has('redeemed')) {
    showRedeemToast(true);
    // Clean up URL
    window.history.replaceState({}, document.title, window.location.pathname);
  } else if (params.has('error')) {
    const errorType = params.get('error');
    const errorMessages = {
      'invalid_egg': 'This egg could not be found.',
      'redeem_failed': 'This egg has already been redeemed or is no longer available.',
      'must_create': 'Create at least one egg before redeeming.',
    };
    const message = errorMessages[errorType] || 'An error occurred while redeeming the egg.';
    const toast = document.querySelector('.toast');
    if (toast) toast.remove();
    const newToast = document.createElement('div');
    newToast.className = 'toast toast-failure';
    newToast.innerHTML = `
      <svg class="toast-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
        <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12 19 6.41z"></path>
      </svg>
      <span>${message}</span>
    `;
    document.body.appendChild(newToast);
    requestAnimationFrame(() => newToast.classList.add('is-visible'));
    setTimeout(() => {
      newToast.classList.remove('is-visible');
      setTimeout(() => newToast.remove(), 400);
    }, 2400);
    // Clean up URL
    window.history.replaceState({}, document.title, window.location.pathname);
  }

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
