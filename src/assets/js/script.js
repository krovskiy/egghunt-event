import { loadEgg } from './egg_viewer.js';

const MODEL_PATH = './assets/models/egg.glb';

async function fetchEggs() {
  const res = await fetch('/api/list_eggs');
  return res.json(); // array of { name, hint, author, texture, max_redeems, egg_id? }
}

async function voteEgg(endpoint, eggId) {
  const res = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ egg_id: eggId }),
  });
  if (res.status === 401) {
    alert('You must be logged in to vote.');
  }
}

async function buildGrid() {
  const eggs = await fetchEggs();
  const grid = document.getElementById('eggGrid');
  grid.innerHTML = '';

  // Store eggs by their index so we can look them up on click, REPLACE WITH ANOTHER FIELD IN TABLE
  grid._eggs = eggs;

  eggs.forEach((egg, index) => {
    const card = document.createElement('div');
    card.className = 'egg-container';

    const ext = egg.user_avatar?.startsWith("a_") ? "gif" : "png";

    const avatarUrl = egg.user_avatar
      ? `https://cdn.discordapp.com/avatars/${egg.user_id}/${egg.user_avatar}.${ext}`
      : "https://cdn.discordapp.com/embed/avatars/0.png";

    card.innerHTML = `
      <div class="egg-stage" id="egg-${index}">
        <div class="egg-actions">
          <button class="egg-action egg-like" type="button">GOOD</button>
          <button class="egg-action egg-dislike" type="button">BAD</button>
        </div>
      </div>
      <div class="egg-info">
        <div class="egg-name">${egg.name}</div>
        <div class="egg-creator">
          Uploaded by: ${egg.author}
          <img class="creator-img" src="${avatarUrl}"/>
        </div>
      </div>
    `;

    grid.appendChild(card);

    const stageElement = card.querySelector('.egg-stage');
    loadEgg(stageElement, egg.texture, { modelPath: MODEL_PATH, repeatNumber: egg.textureSize });

    card.querySelector('.egg-like').addEventListener('click', (e) => {
      e.stopPropagation();
      voteEgg('/api/like_egg', egg.egg_id);
    });

    card.querySelector('.egg-dislike').addEventListener('click', (e) => {
      e.stopPropagation();
      voteEgg('/api/dislike_egg', egg.egg_id);
    });
  });
}

document.getElementById('eggGrid').addEventListener('click', (event) => {
  if (event.target.closest('.egg-action')) return;
  const stage = event.target.closest('.egg-stage');
  if (!stage) return;
  if (stage.dataset.dragged === 'true') {
    stage.dataset.dragged = '';
    return;
  }
  showOverlay(stage.id);
});

function showOverlay(id) {
  const index = parseInt(id.replace('egg-', ''), 10);
  const egg = document.getElementById('eggGrid')._eggs[index];
  if (!egg) return;


  const overlay = document.createElement('div');
  overlay.className = 'overlay';

  const box = document.createElement('div');
  box.className = 'overlay-box';

  const eggPreview = document.createElement('div');
  eggPreview.className = 'overlay-preview';

  const eggInfo = document.createElement('div');
  eggInfo.className = 'overlay-info';

  eggInfo.innerHTML = `
  <div class="egg-label">Easter Egg</div>
  <h2 class="egg-name">${egg.name}</h2>
  <div class="egg-fields">
    <div class="egg-row">
      <span class="egg-key">Creator:</span>
      <span class="egg-value">@${egg.author}</span>
    </div>
    <div class="egg-row">
      <span class="egg-key">Redeems:</span>
      <span class="egg-redeem-badge">
        ${egg.max_redeems} left
      </span>
    </div>
    <div class="egg-row">
      <span class="egg-key">Hint / Task:</span>
      <span class="egg-hint">NOTHINGAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA</span>
    </div>
  </div>
`;

  setTimeout(
    () => loadEgg(eggPreview, egg.texture, { modelPath: MODEL_PATH, repeatNumber: egg.textureSize, enableResize: true }),
    0
  );

  box.appendChild(eggPreview);
  box.appendChild(eggInfo);
  overlay.appendChild(box);
  document.body.appendChild(overlay);

  overlay.addEventListener('click', () => overlay.remove());
  box.addEventListener('click', (e) => e.stopPropagation());
}

buildGrid();