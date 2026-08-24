/**
 * XON Music — Premium Discord Music Bot & Dashboard Controller
 * Client ID: 1539145323048599625
 */

document.addEventListener('DOMContentLoaded', () => {
  const CLIENT_ID = '1539145323048599625';
  const BOT_INVITE_URL = `https://discord.com/oauth2/authorize?client_id=${CLIENT_ID}&permissions=8&scope=bot%20applications.commands`;

  // Update invite buttons dynamically
  document.querySelectorAll('#navInviteBtn, #heroInviteBtn, .cta-buttons a').forEach(btn => {
    btn.href = BOT_INVITE_URL;
  });

  // State Management
  let isPlaying = true;
  let isLooping = false;
  let currentVolume = 100;
  let currentUser = JSON.parse(localStorage.getItem('xonmusic_user') || 'null');
  let userGuilds = JSON.parse(localStorage.getItem('xonmusic_guilds') || '[]');
  let activeDJRole = localStorage.getItem('xonmusic_dj_role') || 'DJ';

  // Elements
  const discordLoginBtn = document.getElementById('discordLoginBtn');
  const loginBtnText = document.getElementById('loginBtnText');
  const authModal = document.getElementById('authModal');
  const modalCloseBtn = document.getElementById('modalCloseBtn');
  const btnProceedDiscordAuth = document.getElementById('btnProceedDiscordAuth');
  const btnPromptDiscordLogin = document.getElementById('btnPromptDiscordLogin');

  const serversLoggedOutBanner = document.getElementById('serversLoggedOutBanner');
  const serversLoggedInGrid = document.getElementById('serversLoggedInGrid');

  const customDJRoleInput = document.getElementById('customDJRoleInput');
  const btnSaveDJRole = document.getElementById('btnSaveDJRole');
  const roleStatusText = document.getElementById('roleStatusText');

  const mockupPlayBtn = document.getElementById('mockupPlayBtn');
  const mockupSkipBtn = document.getElementById('mockupSkipBtn');
  const mockupLoopBtn = document.getElementById('mockupLoopBtn');
  const mockupVolBtn = document.getElementById('mockupVolBtn');
  const mockupTitle = document.getElementById('mockupTitle');
  const mockupArtist = document.getElementById('mockupArtist');
  const mockupImg = document.getElementById('mockupImg');
  const equalizerBars = document.querySelectorAll('.equalizer-bar-group .bar');

  const webSearchInput = document.getElementById('webSearchInput');
  const webSearchBtn = document.getElementById('webSearchBtn');
  const tagPills = document.querySelectorAll('.tag-pill');
  const webVolumeRange = document.getElementById('webVolumeRange');
  const volValueDisplay = document.getElementById('volValueDisplay');
  const consoleLogs = document.getElementById('consoleLogs');
  const queueListContainer = document.getElementById('queueListContainer');
  const queueCountBadge = document.getElementById('queueCountBadge');
  const clearQueueBtn = document.getElementById('clearQueueBtn');
  const shuffleQueueBtn = document.getElementById('shuffleQueueBtn');

  const cmdFilterBtns = document.querySelectorAll('.cmd-filter-btn');
  const commandsTableRows = document.querySelectorAll('#commandsTableBody tr');
  const copyCmdBtns = document.querySelectorAll('.btn-copy-cmd');

  // Track Queue
  const sampleTracks = [
    {
      title: "Luis Fonsi - Despacito ft. Daddy Yankee",
      artist: "Latin Pop • 48kHz HD Audio",
      duration: "03:50",
      image: "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=600&auto=format&fit=crop&q=80",
      requester: "@Gamer"
    },
    {
      title: "Imagine Dragons - Believer",
      artist: "Rock/Electronic • Lossless",
      duration: "03:24",
      image: "https://images.unsplash.com/photo-1614613535308-eb5fbd3d2c17?w=600&auto=format&fit=crop&q=80",
      requester: "@Alex"
    },
    {
      title: "Ed Sheeran - Shape of You",
      artist: "Pop Acoustic • Stereo 48kHz",
      duration: "03:54",
      image: "https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=600&auto=format&fit=crop&q=80",
      requester: "@NeonRider"
    }
  ];

  let queue = [...sampleTracks];

  // Toast Notifications
  function showToast(message, icon = "fa-check-circle text-success") {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = 'toast-msg';
    toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 3200);
  }

  function appendConsoleLog(message, isInfo = false) {
    if (!consoleLogs) return;
    const now = new Date();
    const timeStr = `[${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}]`;
    const p = document.createElement('p');
    p.className = isInfo ? 'log-line text-info' : 'log-line';
    p.innerHTML = `<span class="log-time">${timeStr}</span> ${message}`;
    consoleLogs.appendChild(p);
    consoleLogs.scrollTop = consoleLogs.scrollHeight;
  }

  // Official Real Discord OAuth2 Login Redirect Helper
  function redirectToDiscordOAuth() {
    const currentOrigin = window.location.origin;
    const redirectUri = encodeURIComponent(currentOrigin);
    const discordAuthUrl = `https://discord.com/oauth2/authorize?client_id=${CLIENT_ID}&response_type=token&scope=identify%20guilds&redirect_uri=${redirectUri}`;
    
    showToast('Redirecting to official Discord Authorization...', 'fa-brands fa-discord');
    setTimeout(() => {
      window.location.href = discordAuthUrl;
    }, 400);
  }

  // Handle Return from Discord OAuth2 (Parse access_token hash)
  async function checkDiscordOAuthRedirect() {
    const hash = window.location.hash;
    if (hash && hash.includes('access_token=')) {
      const params = new URLSearchParams(hash.substring(1));
      const accessToken = params.get('access_token');

      if (accessToken) {
        try {
          // 1. Fetch real user profile from Discord API
          const userRes = await fetch('https://discord.com/api/users/@me', {
            headers: { Authorization: `Bearer ${accessToken}` }
          });
          if (userRes.ok) {
            const userData = await userRes.json();
            const avatarUrl = userData.avatar
              ? `https://cdn.discordapp.com/avatars/${userData.id}/${userData.avatar}.png`
              : `https://cdn.discordapp.com/embed/avatars/${(parseInt(userData.discriminator || 0) % 5)}.png`;

            currentUser = {
              username: userData.global_name || userData.username,
              id: userData.id,
              avatar: avatarUrl
            };
            localStorage.setItem('xonmusic_user', JSON.stringify(currentUser));
          }

          // 2. Fetch user's real Discord servers/guilds
          const guildsRes = await fetch('https://discord.com/api/users/@me/guilds', {
            headers: { Authorization: `Bearer ${accessToken}` }
          });
          if (guildsRes.ok) {
            const guildsData = await guildsRes.json();
            userGuilds = guildsData.map(g => ({
              id: g.id,
              name: g.name,
              icon: g.icon ? `https://cdn.discordapp.com/icons/${g.id}/${g.icon}.png` : null,
              owner: g.owner,
              canManage: (parseInt(g.permissions) & 0x20) === 0x20 || (parseInt(g.permissions) & 0x8) === 0x8 || g.owner
            }));
            localStorage.setItem('xonmusic_guilds', JSON.stringify(userGuilds));
          }

          window.history.replaceState(null, null, window.location.pathname);
          updateAuthUI();
          renderServersDashboard();
          showToast(`Welcome, @${currentUser.username}! Logged in with Discord.`, 'fa-user-check text-success');
          appendConsoleLog(`Real Discord OAuth session established for <b>@${currentUser.username}</b>.`, true);
        } catch (err) {
          console.error("Discord OAuth fetch error:", err);
          showToast("Failed to authenticate with Discord.", "fa-circle-xmark text-danger");
        }
      }
    }
  }

  // Render Server Cards — auto load from bot API (no login required)
  async function renderServersDashboard() {
    if (!serversLoggedOutBanner || !serversLoggedInGrid) return;

    // Always show bot's servers grid, hide login banner
    serversLoggedOutBanner.style.display = 'none';
    serversLoggedInGrid.style.display = 'grid';

    // Show loading skeleton first
    serversLoggedInGrid.innerHTML = `
      <div class="server-card glass-panel" style="opacity:0.5; animation: pulse 1.2s infinite alternate;">
        <div class="server-card-top"><div class="server-avatar-placeholder" style="background:rgba(255,255,255,0.05)"></div><div style="flex:1"><div style="height:14px;background:rgba(255,255,255,0.07);border-radius:6px;margin-bottom:8px"></div><div style="height:10px;background:rgba(255,255,255,0.05);border-radius:6px;width:60%"></div></div></div>
      </div>
      <div class="server-card glass-panel" style="opacity:0.5; animation: pulse 1.4s infinite alternate;">
        <div class="server-card-top"><div class="server-avatar-placeholder" style="background:rgba(255,255,255,0.05)"></div><div style="flex:1"><div style="height:14px;background:rgba(255,255,255,0.07);border-radius:6px;margin-bottom:8px"></div><div style="height:10px;background:rgba(255,255,255,0.05);border-radius:6px;width:60%"></div></div></div>
      </div>
    `;

    // Fetch bot's own servers
    let botGuilds = [];
    try {
      const res = await fetch('/api/guilds');
      if (res.ok) {
        const data = await res.json();
        botGuilds = data.guilds || [];
      }
    } catch (e) {
      console.warn('Could not fetch bot guilds:', e);
    }

    serversLoggedInGrid.innerHTML = '';

    if (botGuilds.length === 0) {
      serversLoggedInGrid.innerHTML = `
        <div class="glass-panel text-center" style="grid-column: 1 / -1; padding: 40px;">
          <i class="fa-solid fa-server text-purple" style="font-size: 2rem; margin-bottom: 12px;"></i>
          <h3>Bot Not Connected</h3>
          <p style="color: var(--text-secondary); margin-bottom: 20px;">Bot abhi kisi server mein nahi hai ya deploy nahi hua.</p>
          <a href="${BOT_INVITE_URL}" target="_blank" class="btn btn-primary btn-sm"><i class="fa-solid fa-plus"></i> Add to Your Server</a>
        </div>
      `;
      return;
    }

    botGuilds.forEach(guild => {
      const inviteGuildUrl = `https://discord.com/oauth2/authorize?client_id=${CLIENT_ID}&permissions=8&scope=bot%20applications.commands&guild_id=${guild.id}`;
      const card = document.createElement('div');
      card.className = 'server-card glass-panel';

      const avatarHtml = guild.icon
        ? `<img src="${guild.icon}" class="server-avatar" alt="icon" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'"><div class="server-avatar-placeholder" style="display:none">${guild.name.charAt(0).toUpperCase()}</div>`
        : `<div class="server-avatar-placeholder">${guild.name.charAt(0).toUpperCase()}</div>`;

      card.innerHTML = `
        <div class="server-card-top">
          ${avatarHtml}
          <div class="server-meta">
            <h4>${guild.name}</h4>
            <span class="server-perm-badge"><i class="fa-solid fa-users"></i> ${guild.member_count?.toLocaleString() || '?'} members</span>
          </div>
        </div>

        <div class="server-card-bot-status">
          <span><i class="fa-solid fa-compact-disc text-purple"></i> Music Engine:</span>
          <strong class="text-success"><i class="fa-solid fa-circle-check"></i> Active</strong>
        </div>

        <div class="server-actions">
          <a href="${inviteGuildUrl}" target="_blank" class="btn btn-secondary btn-sm" style="flex: 1;">
            <i class="fa-solid fa-plus"></i> Add / Reinvite
          </a>
          <button class="btn btn-primary btn-sm btn-manage-music" data-guild="${guild.name}" style="flex: 1;">
            <i class="fa-solid fa-play"></i> Web Player
          </button>
        </div>
      `;
      serversLoggedInGrid.appendChild(card);
    });

    // Add footer note
    const note = document.createElement('div');
    note.style.cssText = 'grid-column: 1 / -1; text-align: center; padding: 12px; color: var(--text-muted); font-size: 13px;';
    note.innerHTML = `<i class="fa-solid fa-compact-disc text-purple"></i> <strong>${botGuilds.length}</strong> servers mein XON Music active hai`;
    serversLoggedInGrid.appendChild(note);

    document.querySelectorAll('.btn-manage-music').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const gName = e.currentTarget.dataset.guild;
        showToast(`Connected Web Player to ${gName}!`, 'fa-sliders text-purple');
        appendConsoleLog(`Web Remote Controller active for server: <b>${gName}</b> (DJ Role: <code>@${activeDJRole}</code>)`);
        document.getElementById('player').scrollIntoView({ behavior: 'smooth' });
      });
    });
  }


  // DJ Role Settings
  if (customDJRoleInput) {
    customDJRoleInput.value = activeDJRole;
  }
  if (roleStatusText) {
    roleStatusText.innerHTML = `✅ Active DJ Role: <strong>@${activeDJRole}</strong> (Members with this role can manage playback)`;
  }

  if (btnSaveDJRole && customDJRoleInput) {
    btnSaveDJRole.addEventListener('click', () => {
      const val = customDJRoleInput.value.trim().replace(/^@/, '');
      if (val) {
        activeDJRole = val;
        localStorage.setItem('xonmusic_dj_role', activeDJRole);
        roleStatusText.innerHTML = `✅ Active DJ Role: <strong>@${activeDJRole}</strong> (Saved & Active)`;
        showToast(`Server DJ Role set to @${activeDJRole}!`, 'fa-user-shield text-success');
        appendConsoleLog(`Server DJ permission updated to role: <b>@${activeDJRole}</b>`);
      }
    });
  }

  // Render Queue List
  function renderQueue() {
    if (!queueListContainer) return;
    queueListContainer.innerHTML = '';

    queue.forEach((track, index) => {
      const isCurrent = index === 0;
      const item = document.createElement('div');
      item.className = `queue-item ${isCurrent ? 'active-track' : ''}`;
      item.innerHTML = `
        <div class="q-num">${isCurrent ? '<i class="fa-solid fa-volume-high fa-beat"></i>' : index}</div>
        <img src="${track.image}" alt="track" class="q-thumb">
        <div class="q-details">
          <span class="q-title">${track.title}</span>
          <span class="q-meta">${track.artist} • ${track.duration} • By ${track.requester}</span>
        </div>
        ${isCurrent ? '<span class="badge-playing">PLAYING</span>' : `<button class="q-action-btn remove-track-btn" data-index="${index}" title="Remove"><i class="fa-solid fa-xmark"></i></button>`}
      `;
      queueListContainer.appendChild(item);
    });

    if (queueCountBadge) {
      queueCountBadge.textContent = `${queue.length} Songs In Queue`;
    }

    document.querySelectorAll('.remove-track-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const idx = parseInt(e.currentTarget.dataset.index);
        const removed = queue.splice(idx, 1)[0];
        renderQueue();
        showToast(`Removed "${removed.title}" from queue.`, 'fa-trash text-danger');
        appendConsoleLog(`Track <code>${removed.title}</code> removed by DJ.`);
      });
    });
  }

  // Play / Pause Toggle
  function togglePlayPause() {
    isPlaying = !isPlaying;
    if (isPlaying) {
      mockupPlayBtn.innerHTML = '<i class="fa-solid fa-pause"></i>';
      equalizerBars.forEach(b => b.style.animationPlayState = 'running');
      showToast('Music playback resumed.');
      appendConsoleLog('Voice Channel Playback: <b>Resumed</b>', true);
    } else {
      mockupPlayBtn.innerHTML = '<i class="fa-solid fa-play"></i>';
      equalizerBars.forEach(b => b.style.animationPlayState = 'paused');
      showToast('Music playback paused.');
      appendConsoleLog('Voice Channel Playback: <b>Paused</b>');
    }
  }

  // Skip Track
  function skipTrack() {
    if (queue.length > 1) {
      const skipped = queue.shift();
      const next = queue[0];
      mockupTitle.textContent = next.title;
      mockupArtist.textContent = next.artist;
      mockupImg.src = next.image;
      renderQueue();
      showToast(`Skipped to "${next.title}"`, 'fa-forward-step text-purple');
      appendConsoleLog(`DJ skipped track <code>${skipped.title}</code> -> Now playing <code>${next.title}</code>`);
    } else {
      showToast('No more tracks in queue!', 'fa-circle-exclamation');
    }
  }

  if (mockupPlayBtn) mockupPlayBtn.addEventListener('click', togglePlayPause);
  if (mockupSkipBtn) mockupSkipBtn.addEventListener('click', skipTrack);

  if (mockupLoopBtn) {
    mockupLoopBtn.addEventListener('click', () => {
      isLooping = !isLooping;
      mockupLoopBtn.style.color = isLooping ? 'var(--neon-green)' : 'var(--text-primary)';
      mockupLoopBtn.style.borderColor = isLooping ? 'var(--neon-green)' : 'var(--border-glass)';
      showToast(`Loop mode: ${isLooping ? 'ENABLED (Repeat 🔁)' : 'DISABLED'}`);
      appendConsoleLog(`Loop mode toggled: <b>${isLooping ? 'ON' : 'OFF'}</b>`);
    });
  }

  // Search Bar / Play Track directly from Web Controller
  function handleWebSearch(query) {
    if (!query || !query.trim()) return;
    const cleanQuery = query.trim();

    const newTrack = {
      title: cleanQuery.length > 40 ? cleanQuery.slice(0, 40) + '...' : cleanQuery,
      artist: "YouTube / Direct Stream • 48kHz",
      duration: "03:45",
      image: "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=600&auto=format&fit=crop&q=80",
      requester: currentUser ? `@${currentUser.username} (${activeDJRole})` : "@DJUser"
    };

    queue.push(newTrack);
    renderQueue();
    showToast(`Added "${newTrack.title}" to server queue!`, 'fa-music text-purple');
    appendConsoleLog(`Track queued: <code>${newTrack.title}</code> by DJ Role permission.`);
    if (webSearchInput) webSearchInput.value = '';
  }

  if (webSearchBtn && webSearchInput) {
    webSearchBtn.addEventListener('click', () => handleWebSearch(webSearchInput.value));
    webSearchInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') handleWebSearch(webSearchInput.value);
    });
  }

  tagPills.forEach(pill => {
    pill.addEventListener('click', () => {
      const q = pill.getAttribute('data-query');
      handleWebSearch(q);
    });
  });

  if (webVolumeRange) {
    webVolumeRange.addEventListener('input', (e) => {
      currentVolume = e.target.value;
      if (volValueDisplay) volValueDisplay.textContent = `${currentVolume}%`;
      appendConsoleLog(`DJ adjusted volume to <b>${currentVolume}%</b>`);
    });
  }

  document.querySelectorAll('.fx-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      btn.classList.toggle('active');
      const fxName = btn.textContent.trim();
      const isActive = btn.classList.contains('active');
      showToast(`${fxName} filter: ${isActive ? 'ENABLED' : 'DISABLED'}`);
      appendConsoleLog(`Audio DSP filter <b>${fxName}</b> ${isActive ? 'applied' : 'removed'}.`);
    });
  });

  if (clearQueueBtn) {
    clearQueueBtn.addEventListener('click', () => {
      if (queue.length > 1) {
        queue = [queue[0]];
        renderQueue();
        showToast('Upcoming queue cleared by DJ.', 'fa-trash');
        appendConsoleLog('Queue cleared.');
      } else {
        showToast('Queue is already empty.');
      }
    });
  }

  if (shuffleQueueBtn) {
    shuffleQueueBtn.addEventListener('click', () => {
      if (queue.length > 2) {
        const current = queue[0];
        const rest = queue.slice(1).sort(() => Math.random() - 0.5);
        queue = [current, ...rest];
        renderQueue();
        showToast('Queue shuffled randomly! 🔀');
        appendConsoleLog('Queue items shuffled.');
      }
    });
  }

  cmdFilterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      cmdFilterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const category = btn.getAttribute('data-category');
      commandsTableRows.forEach(row => {
        const rowCat = row.getAttribute('data-cat');
        if (category === 'all' || rowCat === category) {
          row.style.display = '';
        } else {
          row.style.display = 'none';
        }
      });
    });
  });

  copyCmdBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const cmd = btn.getAttribute('data-cmd');
      navigator.clipboard.writeText(cmd).then(() => {
        showToast(`Copied "${cmd}" to clipboard!`, 'fa-copy');
      });
    });
  });

  function updateAuthUI() {
    if (currentUser) {
      loginBtnText.textContent = currentUser.username;
      discordLoginBtn.innerHTML = `
        <img src="${currentUser.avatar}" style="width: 22px; height: 22px; border-radius: 50%;">
        <span>${currentUser.username}</span>
      `;
    } else {
      loginBtnText.textContent = "Login with Discord";
      discordLoginBtn.innerHTML = `<i class="fa-brands fa-discord"></i> <span>Login with Discord</span>`;
    }
  }

  if (discordLoginBtn) {
    discordLoginBtn.addEventListener('click', () => {
      if (currentUser) {
        if (confirm(`Logged in as @${currentUser.username}. Do you want to logout?`)) {
          currentUser = null;
          userGuilds = [];
          localStorage.removeItem('xonmusic_user');
          localStorage.removeItem('xonmusic_guilds');
          updateAuthUI();
          renderServersDashboard();
          showToast('Logged out successfully.');
        }
      } else {
        authModal.classList.add('active');
      }
    });
  }

  if (btnPromptDiscordLogin) {
    btnPromptDiscordLogin.addEventListener('click', () => {
      redirectToDiscordOAuth();
    });
  }

  if (btnProceedDiscordAuth) {
    btnProceedDiscordAuth.addEventListener('click', () => {
      redirectToDiscordOAuth();
    });
  }

  if (modalCloseBtn) {
    modalCloseBtn.addEventListener('click', () => authModal.classList.remove('active'));
  }

  window.addEventListener('click', (e) => {
    if (e.target === authModal) authModal.classList.remove('active');
  });

  // Initialize
  checkDiscordOAuthRedirect();
  renderServersDashboard();
  renderQueue();
  updateAuthUI();
});
