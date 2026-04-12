const likesList = document.getElementById('leaderboardLikes');
const redeemsList = document.getElementById('leaderboardRedeems');

const renderList = (listElement, entries, label) => {
  if (!listElement) return;
  listElement.innerHTML = '';

  if (!entries.length) {
    const empty = document.createElement('li');
    empty.className = 'leaderboard-item';
    empty.textContent = 'No data yet.';
    listElement.appendChild(empty);
    return;
  }

  entries.forEach((entry, index) => {
    const item = document.createElement('li');
    item.className = 'leaderboard-item';

    const rank = document.createElement('div');
    rank.className = 'leaderboard-rank';
    rank.textContent = String(index + 1);

    const avatar = document.createElement('img');
    avatar.className = 'leaderboard-avatar';
    avatar.src = entry.avatar;
    avatar.alt = entry.name;
    avatar.loading = 'lazy';

    const score = document.createElement('div');
    score.className = 'leaderboard-score';
    score.textContent = `${entry.total} ${label}`;

    const nameWrap = document.createElement('div');
    nameWrap.className = 'leaderboard-name';
    nameWrap.textContent = entry.name;

    item.appendChild(rank);
    item.appendChild(avatar);
    item.appendChild(nameWrap);
    item.appendChild(score);

    listElement.appendChild(item);
  });
};

window.EGGHUNT_BASE_PATH = window.EGGHUNT_BASE_PATH || '/egghunt';
const BASE_PATH = window.EGGHUNT_BASE_PATH;
const API_BASE = `${BASE_PATH}/api`;

const loadLeaderboard = async () => {
  if (!likesList || !redeemsList) return;

  try {
    const res = await fetch(`${API_BASE}/leaderboard`);
    if (!res.ok) {
      throw new Error('Failed to load leaderboard');
    }
    const data = await res.json();

    renderList(likesList, data.top_likes || [], 'likes');
    renderList(redeemsList, data.top_redeems || [], 'collected');
  } catch (error) {
    console.error(error);
    renderList(likesList, [], 'likes');
    renderList(redeemsList, [], 'collected');
  }
};

loadLeaderboard();
