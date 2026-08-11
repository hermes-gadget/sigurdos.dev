'use strict';

// Back-to-top button visibility and action.
const backToTop = document.getElementById('back-to-top');
if (backToTop) {
  window.addEventListener('scroll', () => {
    backToTop.classList.toggle('visible', window.scrollY > 300);
  });
  backToTop.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
}

// Auto-update version tag + contributors from GitHub.
(async function loadGitHubMetadata() {
  const owner = 'hermes-gadget';
  const repo = 'SigurdOS-tdeck';
  try {
    const releaseResponse = await fetch(
      `https://api.github.com/repos/${owner}/${repo}/releases?per_page=1`,
    );
    const releases = await releaseResponse.json();
    if (releases && releases[0]) {
      document.getElementById('version-text').textContent = releases[0].tag_name;
    }
  } catch (error) {
    // Keep the build-time release fallback in the page.
  }

  try {
    const contributorResponse = await fetch(
      `https://api.github.com/repos/${owner}/${repo}/contributors`,
    );
    const contributors = await contributorResponse.json();
    const grid = document.getElementById('contributors-grid');
    if (contributors && contributors.length) {
      grid.innerHTML = contributors.map((contributor) => `
        <a href="${contributor.html_url}" target="_blank" class="contributor">
          <img src="${contributor.avatar_url}&s=48" alt="${contributor.login}" class="contributor__avatar" width="48" height="48" loading="lazy">
          <span class="contributor__name">${contributor.login}</span>
          <span class="contributor__commits">${contributor.contributions} commit${contributor.contributions !== 1 ? 's' : ''}</span>
        </a>
      `).join('');
    } else {
      grid.innerHTML = '<div style="color:var(--text-muted);font-size:14px;">No contributors yet</div>';
    }
  } catch (error) {
    document.getElementById('contributors-grid').innerHTML =
      '<div style="color:var(--text-muted);font-size:14px;">Could not load contributors</div>';
  }
}());

// Hamburger menu toggle.
(function setUpMobileNavigation() {
  const button = document.getElementById('hamburger');
  const navigation = document.getElementById('mobileNav');
  if (!button || !navigation) return;

  button.addEventListener('click', () => {
    button.classList.toggle('active');
    navigation.classList.toggle('open');
  });
  navigation.addEventListener('click', (event) => {
    if (event.target.tagName === 'A') {
      button.classList.remove('active');
      navigation.classList.remove('open');
    }
  });
  document.addEventListener('click', (event) => {
    if (!button.contains(event.target) && !navigation.contains(event.target)) {
      button.classList.remove('active');
      navigation.classList.remove('open');
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
      styleButton.innerHTML = '&#x1F319; Dark';
    } else {
      tileStyle = 'light';
      map.removeLayer(darkLayer);
      map.addLayer(lightLayer);
      styleButton.innerHTML = '&#x2600; Light';
    }
  });
}());
