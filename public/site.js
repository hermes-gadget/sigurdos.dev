'use strict';

// SPDX-License-Identifier: GPL-3.0-only

// Back-to-top button visibility and action.
const backToTop = document.getElementById('back-to-top');
if (backToTop) {
  window.addEventListener('scroll', () => {
    backToTop.classList.toggle('visible', window.scrollY > 300);
  });
  backToTop.addEventListener('click', () => {
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    window.scrollTo({ top: 0, behavior: reduceMotion ? 'auto' : 'smooth' });
  });
}

// Auto-update version tag + contributors from GitHub.
const GITHUB_TIMEOUT_MS = 8000;
const GITHUB_PROFILE_HOSTS = new Set(['github.com', 'www.github.com']);
const GITHUB_AVATAR_HOSTS = new Set(['avatars.githubusercontent.com']);

async function fetchGitHubJson(url) {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), GITHUB_TIMEOUT_MS);
  try {
    const response = await fetch(url, {
      headers: { Accept: 'application/vnd.github+json' },
      signal: controller.signal,
    });
    if (!response.ok) {
      throw new Error(`GitHub request failed: ${response.status}`);
    }
    return await response.json();
  } finally {
    window.clearTimeout(timeout);
  }
}

function setMetadataMessage(container, message) {
  if (!container) return;
  container.replaceChildren();
  const messageElement = document.createElement('div');
  messageElement.className = 'metadata-message';
  messageElement.textContent = message;
  container.append(messageElement);
}

function validatedHttpsUrl(value, allowedHosts) {
  if (typeof value !== 'string') return null;
  try {
    const url = new URL(value);
    if (url.protocol !== 'https:' || !allowedHosts.has(url.hostname.toLowerCase())) {
      return null;
    }
    return url;
  } catch (error) {
    return null;
  }
}

function createContributorCard(contributor) {
  const login = typeof contributor?.login === 'string' ? contributor.login.trim() : '';
  const profileUrl = validatedHttpsUrl(contributor?.html_url, GITHUB_PROFILE_HOSTS);
  const avatarUrl = validatedHttpsUrl(contributor?.avatar_url, GITHUB_AVATAR_HOSTS);
  const contributions = Number(contributor?.contributions);
  if (
    !login ||
    !profileUrl ||
    !avatarUrl ||
    !Number.isFinite(contributions) ||
    contributions < 0
  ) {
    return null;
  }

  avatarUrl.searchParams.set('s', '48');
  const card = document.createElement('a');
  card.href = profileUrl.href;
  card.target = '_blank';
  card.rel = 'noopener noreferrer';
  card.className = 'contributor';

  const avatar = document.createElement('img');
  avatar.src = avatarUrl.href;
  avatar.alt = login;
  avatar.className = 'contributor__avatar';
  avatar.width = 48;
  avatar.height = 48;
  avatar.loading = 'lazy';

  const name = document.createElement('span');
  name.className = 'contributor__name';
  name.textContent = login;

  const commits = document.createElement('span');
  commits.className = 'contributor__commits';
  const count = Math.floor(contributions);
  commits.textContent = `${count} commit${count === 1 ? '' : 's'}`;

  card.append(avatar, name, commits);
  return card;
}

(async function loadGitHubMetadata() {
  const owner = 'hermes-gadget';
  const repo = 'SigurdOS-tdeck';
  const versionStatus = document.getElementById('version-status');
  try {
    const releases = await fetchGitHubJson(
      `https://api.github.com/repos/${owner}/${repo}/releases?per_page=1`,
    );
    const latestRelease = Array.isArray(releases)
      ? releases.find((release) => typeof release?.tag_name === 'string' && release.tag_name.trim())
      : null;
    if (!latestRelease) {
      throw new Error('GitHub release response had no valid release');
    }
    document.getElementById('version-text').textContent = latestRelease.tag_name;
    if (versionStatus) versionStatus.textContent = '';
  } catch (error) {
    if (versionStatus) {
      versionStatus.textContent = 'Live release data unavailable; showing the verified build fallback.';
    }
  }

  const grid = document.getElementById('contributors-grid');
  try {
    const contributors = await fetchGitHubJson(
      `https://api.github.com/repos/${owner}/${repo}/contributors`,
    );
    if (!Array.isArray(contributors)) {
      throw new Error('GitHub contributor response was not an array');
    }
    const cards = contributors.map(createContributorCard).filter(Boolean);
    if (cards.length) {
      grid.replaceChildren(...cards);
    } else {
      setMetadataMessage(grid, 'Contributor data is currently unavailable.');
    }
  } catch (error) {
    setMetadataMessage(grid, 'Could not load contributor data right now.');
  }
}());

// Hamburger menu toggle.
(function setUpMobileNavigation() {
  const button = document.getElementById('hamburger');
  const navigation = document.getElementById('mobileNav');
  if (!button || !navigation) return;

  const setNavigationState = (isOpen) => {
    button.classList.toggle('active', isOpen);
    navigation.classList.toggle('open', isOpen);
    button.setAttribute('aria-expanded', String(isOpen));
    navigation.setAttribute('aria-hidden', String(!isOpen));
  };

  setNavigationState(false);
  button.addEventListener('click', () => {
    setNavigationState(!navigation.classList.contains('open'));
  });
  navigation.addEventListener('click', (event) => {
    if (event.target.tagName === 'A') {
      setNavigationState(false);
    }
  });
  document.addEventListener('click', (event) => {
    if (!button.contains(event.target) && !navigation.contains(event.target)) {
      setNavigationState(false);
    }
  });
}());

// Interactive map. Leaflet requests only tiles needed for the visible viewport.
(function setUpMapPreview() {
  const mapElement = document.getElementById('tile-map');
  if (!mapElement) return;

  const styleButton = document.getElementById('tile-style-btn');
  const worldBounds = L.latLngBounds(
    [-85.05112878, -180],
    [85.05112878, 180],
  );
  const map = L.map(mapElement, {
    center: [51.5, -0.13],
    zoom: 6,
    minZoom: 3,
    zoomControl: true,
    attributionControl: true,
    maxBounds: worldBounds,
    maxBoundsViscosity: 1,
  });
  const lightLayer = L.tileLayer(
    'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
    {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 18,
      noWrap: true,
    },
  ).addTo(map);
  const darkLayer = L.tileLayer(
    'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
    {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
      maxZoom: 18,
      noWrap: true,
      subdomains: 'abcd',
    },
  );
  let tileStyle = 'light';

  styleButton.addEventListener('click', () => {
    if (tileStyle === 'light') {
      tileStyle = 'dark';
      map.removeLayer(lightLayer);
      map.addLayer(darkLayer);
      styleButton.textContent = '🌙 Dark';
    } else {
      tileStyle = 'light';
      map.removeLayer(darkLayer);
      map.addLayer(lightLayer);
      styleButton.textContent = '☀ Light';
    }
  });
}());
