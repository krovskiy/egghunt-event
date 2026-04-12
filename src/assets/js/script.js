import { loadEgg } from './egg_viewer.js';

const MODEL_PATH = './assets/models/egg.glb';
const PAGE_SIZE = 10;
const LOAD_THRESHOLD = 500;

let eggOffset = 0;
let isLoading = false;
let hasMore = true;

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

async function fetchEggs(offset = 0, limit = PAGE_SIZE) {
  const res = await fetch(`/api/list_eggs_by_feedback?offset=${offset}&limit=${limit}`);
  return res.json(); // array of { name, hint, author, texture, max_redeems, egg_id? }
}

async function voteEgg(endpoint, eggId) {
  const res = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ egg_id: eggId }),
  });
  if (res.status === 401) {
    return { ok: false, message: 'You must be logged in to vote.' };
  }
  if (!res.ok) {
    return { ok: false, message: 'Vote failed. Please try again.' };
  }
  return { ok: true };
}

function showVoteToast(message, isError = false) {
  const existingToast = document.querySelector('.toast');
  if (existingToast) existingToast.remove();

  const toast = document.createElement('div');
  toast.className = isError ? 'toast toast-failure' : 'toast';
  toast.setAttribute('role', 'status');
  toast.setAttribute('aria-live', 'polite');
  toast.innerHTML = `
    <svg class="toast-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      ${isError
        ? '<path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12 19 6.41z"></path>'
        : '<path d="M9.2 16.2L4.8 11.8l1.4-1.4 3 3 8-8 1.4 1.4-9.4 9.4z"></path>'}
    </svg>
    <span>${message}</span>
  `;

  document.body.appendChild(toast);
  requestAnimationFrame(() => toast.classList.add('is-visible'));

  setTimeout(() => {
    toast.classList.remove('is-visible');
    setTimeout(() => toast.remove(), 400);
  }, 2000);
}

function updateVoteCount(button, delta = 1) {
  const countSpan = button.querySelector('.vote-count');
  if (!countSpan) return;
  const current = Number(countSpan.dataset.count || 0);
  const next = Math.max(0, current + delta);
  countSpan.dataset.count = String(next);
  countSpan.textContent = String(next);
}

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

const observer = new IntersectionObserver((entries) => {
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

function renderEggs(eggs, append = false) {
  const grid = document.getElementById('eggGrid');
  if (!append) {
    grid.innerHTML = '';
  }

  eggs.forEach((egg) => {
    const card = document.createElement('div');
    card.className = 'egg-container';
    if (egg.redeemed_by_me) {
      card.classList.add('egg-container-redeemed');
    }

    const ext = egg.author_avatar?.startsWith("a_") ? "gif" : "png";

    const avatarUrl = egg.author_avatar
      ? `https://cdn.discordapp.com/avatars/${egg.author_id}/${egg.author_avatar}.${ext}`
      : "https://cdn.discordapp.com/embed/avatars/0.png";

    card.innerHTML = `
      <div class="egg-stage" id="egg-${egg.egg_id}">
        <div class="egg-actions">
          <button class="egg-action egg-like" type="button">
            GOOD <span class="vote-count" data-count="${egg.likes ?? 0}">${egg.likes ?? 0}</span>
          </button>
          <button class="egg-action egg-dislike" type="button">
            BAD <span class="vote-count" data-count="${egg.dislikes ?? 0}">${egg.dislikes ?? 0}</span>
          </button>
        </div>
      </div>
      <div class="egg-info">
        <div class="egg-name"><b></b></div>
        <div class="egg-creator">
          Uploaded by: <span class="egg-author"></span>
          <img class="creator-img" src="${avatarUrl}"/>
        </div>
      </div>
    `;

    const nameEl = card.querySelector('.egg-name b');
    if (nameEl) nameEl.textContent = egg.name ?? '';
    const authorEl = card.querySelector('.egg-author');
    if (authorEl) authorEl.textContent = egg.author ?? '';

    const stage = card.querySelector('.egg-stage');
    stage.dataset.eggId = egg.egg_id;
    stage.dataset.name = egg.name ?? '';
    stage.dataset.author = egg.author ?? '';
    stage.dataset.hint = egg.hint ?? '';
    stage.dataset.reward = egg.reward ?? '';
    stage.dataset.maxRedeems = egg.max_redeems ?? 0;
    stage.dataset.redeems = egg.redeems ?? 0;
    stage.dataset.texture = egg.texture ?? '';
    stage.dataset.textureSize = egg.textureSize ?? 0;

    grid.appendChild(card);
    observer.observe(card);

    const likeButton = card.querySelector('.egg-like');
    const dislikeButton = card.querySelector('.egg-dislike');

    likeButton.addEventListener('click', async (e) => {
      e.stopPropagation();
      const result = await voteEgg('/api/like_egg', egg.egg_id);
      if (!result.ok) {
        showVoteToast(result.message, true);
        return;
      }
      updateVoteCount(likeButton, 1);
      likeButton.disabled = true;
      dislikeButton.disabled = true;
      showVoteToast('Thanks for voting!');
    });

    dislikeButton.addEventListener('click', async (e) => {
      e.stopPropagation();
      const result = await voteEgg('/api/dislike_egg', egg.egg_id);
      if (!result.ok) {
        showVoteToast(result.message, true);
        return;
      }
      updateVoteCount(dislikeButton, 1);
      likeButton.disabled = true;
      dislikeButton.disabled = true;
      showVoteToast('Thanks for voting!');
    });
  });
}

async function loadMore(reset = false) {
  if (isLoading || !hasMore) return;
  isLoading = true;

  if (reset) {
    eggOffset = 0;
    hasMore = true;
  }

  try {
    const eggs = await fetchEggs(eggOffset, PAGE_SIZE);
    if (!Array.isArray(eggs) || eggs.length === 0) {
      if (reset) {
        const grid = document.getElementById('eggGrid');
        grid.innerHTML = '<h2>No eggs to be found... :(</h2>';
      }
      hasMore = false;
      return;
    }

    renderEggs(eggs, !reset);
    eggOffset += eggs.length;
    if (eggs.length < PAGE_SIZE) {
      hasMore = false;
    }
  } catch (error) {
    if (reset) {
      const grid = document.getElementById('eggGrid');
      grid.innerHTML = '<h2>Failed to fetch :(</h2>';
    }
  } finally {
    isLoading = false;
  }
}

let scrollTimeout;
function onScroll() {
  if (scrollTimeout) return;
  scrollTimeout = setTimeout(() => {
    const scrollTop = window.scrollY;
    const windowHeight = window.innerHeight;
    const documentHeight = document.documentElement.scrollHeight;
    if (scrollTop + windowHeight >= documentHeight - LOAD_THRESHOLD) {
      loadMore();
    }
    scrollTimeout = null;
  }, 200);
}

document.getElementById('eggGrid').addEventListener('click', (event) => {
  if (event.target.closest('.egg-actions')) return;
  if (event.target.closest('.egg-action')) return;
  const stage = event.target.closest('.egg-stage');
  if (!stage) return;
  if (stage.dataset.dragged === 'true') {
    stage.dataset.dragged = '';
    return;
  }
  showOverlay(stage);
});

function showOverlay(stage) {
  const egg = {
    egg_id: stage.dataset.eggId,
    name: stage.dataset.name,
    author: stage.dataset.author,
    hint: stage.dataset.hint,
    reward: stage.dataset.reward,
    max_redeems: Number(stage.dataset.maxRedeems || 0),
    redeems: Number(stage.dataset.redeems || 0),
    texture: stage.dataset.texture,
    textureSize: Number(stage.dataset.textureSize || 0),
  };


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

loadMore(true);
window.addEventListener('scroll', onScroll);