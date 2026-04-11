let currentUserId = null;

import { loadEgg } from './egg_viewer.js';

const MODEL_PATH = '../assets/models/egg.glb';

function buildGrid(data, gridID) {
  const grid = document.getElementById(gridID);
  grid.innerHTML = '';

  data.forEach((egg) => {
    const card = document.createElement('div');
    card.className = 'egg-container';

    const ext = egg.user_avatar?.startsWith("a_") ? "gif" : "png";

    const avatarUrl = egg.user_avatar
      ? `https://cdn.discordapp.com/avatars/${egg.user_id}/${egg.user_avatar}.${ext}`
      : "https://cdn.discordapp.com/embed/avatars/0.png";

    card.innerHTML = `
      <div class="egg-stage" id="egg-${egg.egg_id}">
      </div>
      <div class="egg-info">
        <div class="egg-name"><b>${egg.name}</b></div>
        <div class="egg-creator">Uploaded by: ${egg.author} <img class="creator-img" src="${avatarUrl}"</div>
    `; //somehow needs to fetch discord image instead of the placeholder 'creator-img'

    grid.appendChild(card);

    const stageElement = card.querySelector(`.egg-stage`);
    loadEgg(stageElement, egg.texture, { modelPath: MODEL_PATH, repeatNumber: egg.textureSize }); // this needs CHANGED because right now it doesnt do anything
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

  const isAuthor = currentUserId && egg.author === currentUserId;
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
