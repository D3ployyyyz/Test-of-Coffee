
// Função hash para avatar consistente
function hashCode(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = ((hash << 5) - hash) + str.charCodeAt(i);
    hash |= 0;
  }
  return hash;
}

  // Mapeamento de domínios para ícones de redes sociais
  const socialIconsMap = [
    {name: 'YouTube', domain: 'youtube.com', icon: 'https://cdn-icons-png.flaticon.com/128/1384/1384028.png'},
    {name: 'Instagram', domain: 'instagram.com', icon: 'https://cdn-icons-png.flaticon.com/128/1384/1384031.png'},
    {name: 'Twitter', domain: 'x.com', icon: 'https://cdn-icons-png.flaticon.com/128/5968/5968958.png'},
    {name: 'LinkedIn', domain: 'linkedin.com', icon: 'https://cdn-icons-png.flaticon.com/128/1384/1384014.png'},
    {name: 'Facebook', domain: 'facebook.com', icon: 'https://cdn-icons-png.flaticon.com/128/1384/1384028.png'},
    {name: 'TikTok', domain: 'tiktok.com', icon: 'https://cdn-icons-png.flaticon.com/128/3046/3046120.png'},
  ];

  function getSocialIcon(url) {
    try {
      const hostname = new URL(url).hostname.replace('www.', '').toLowerCase();
      for (const s of socialIconsMap) {
        if (hostname.includes(s.domain)) return s.icon;
      }
    } catch (e) {
      console.warn("URL inválida para ícone:", url);
    }
    // Ícone genérico de link
    return 'https://cdn-icons-png.flaticon.com/128/709/709722.png';
  }  

  async function fetchSpotifyCover(playlistUrl) {
    const match = playlistUrl.match(/playlist\/([a-zA-Z0-9]+)/);
    if (!match) return null;
  
    const playlistId = match[1];
    const finalUrl = `https://open.spotify.com/playlist/${playlistId}`;
  
    try {
      const resposta = await fetch(`https://api.allorigins.win/raw?url=${encodeURIComponent(finalUrl)}`);
      const html = await resposta.text();
      const ogImageMatch = html.match(/property="og:image" content="(.*?)"/);
      return ogImageMatch?.[1] || null;
    } catch {
      return null;
    }
  }
  
  function getSpotifyEmbedUrl(playlistUrl) {
    const match = playlistUrl.match(/playlist\/([a-zA-Z0-9]+)/);
    if (!match) return "";
    return `https://open.spotify.com/embed/playlist/${match[1]}`;
  }
  
  async function loadPlaylistCover(playlistUrl) {
    const capaContainer = document.getElementById("playlist-image-container");
    capaContainer.innerHTML = "";
  
    const imgUrl = await fetchSpotifyCover(playlistUrl);
  
    // Atualiza a capa do vinil (imagem dentro do vinil)
    const vinylImg = document.getElementById('vinyl-label-img');
    if (vinylImg && imgUrl) {
      vinylImg.src = imgUrl;
      vinylImg.alt = "Capa da playlist";
    }
  
    if (imgUrl) {
      // Criar imagem da capa (quadrada)
      const img = document.createElement("img");
      img.src = imgUrl;
      img.alt = "Capa da playlist";
      img.className = "playlist-cover-img";
      capaContainer.appendChild(img);
  
      // Criar iframe mini player, oculto inicialmente via classes
      let iframe = document.createElement("iframe");
      iframe.id = "mini-player";
      iframe.src = getSpotifyEmbedUrl(playlistUrl);
      iframe.allow = "autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture";
      capaContainer.appendChild(iframe);
  
      let hideTimeout;
  
      // Mostrar player com animação ao entrar no container
      capaContainer.addEventListener("mouseenter", () => {
        clearTimeout(hideTimeout);
        iframe.classList.remove("hide");
        iframe.classList.add("show");
      });
  
      // Iniciar animação de saída ao sair do container
      capaContainer.addEventListener("mouseleave", () => {
        hideTimeout = setTimeout(() => {
          iframe.classList.remove("show");
          iframe.classList.add("hide");
        }, 100);
      });
  
      // Se entrar no iframe (player), cancela esconder e garante mostrar
      iframe.addEventListener("mouseenter", () => {
        clearTimeout(hideTimeout);
        iframe.classList.remove("hide");
        iframe.classList.add("show");
      });
  
      // Ao sair do iframe, inicia animação de saída
      iframe.addEventListener("mouseleave", () => {
        hideTimeout = setTimeout(() => {
          iframe.classList.remove("show");
          iframe.classList.add("hide");
        }, 100);
      });
  
      // Remover classe hide após animação acabar para resetar estado
      iframe.addEventListener("animationend", () => {
        if (iframe.classList.contains("hide")) {
          iframe.classList.remove("hide");
        }
      });
  
    } else {
      capaContainer.innerHTML = `<p style="color: white;">Não foi possível carregar a capa da playlist.</p>`;
    }
  }
  
  
  async function loadProfile() {
    const data = JSON.parse(localStorage.getItem('profileData'));
    if (!data) return;

    // Foto
    const picEl = document.querySelector('#profile .left-profile .pic');
    picEl.src = data.pic || "https://media.tenor.com/ipuTozw3PXsAAAAj/pixel-cat.gif";

    // Emotion
    document.querySelector('#profile .content .emotion').textContent = data.emotion || "😊";

    // Name
    document.querySelector('#profile .content .name').textContent = data.name || "coelho";

    // Description
    document.querySelector('#profile .content .description').textContent = data.description || "";

    // Location
    document.querySelector('#profile .content .location').textContent = data.location || "";

    // Likes
    const likesDiv = document.querySelector('#profile .content .likes');
    likesDiv.innerHTML = "";
    if(Array.isArray(data.likes)){
      data.likes.forEach(like => {
        const span = document.createElement('span');
        span.className = 'like-item';
        span.textContent = like;
        likesDiv.appendChild(span);
      });
    }

    // Redes sociais
    const socialsDiv = document.querySelector('#profile .content .socials');
    socialsDiv.innerHTML = "";
    if(Array.isArray(data.socials)){
      data.socials.forEach(social => {
        if(!social.url) return;
        const a = document.createElement('a');
        a.href = social.url;
        a.target = "_blank";
        a.rel = "noopener noreferrer";

        const iconUrl = getSocialIcon(social.url);

        const img = document.createElement('img');
        img.src = iconUrl;
        img.alt = social.url;
        a.appendChild(img);
        socialsDiv.appendChild(a);
      });
    }

    // Playlist Spotify: buscar capa e mostrar imagem clicável que abre o player oficial numa nova aba
    if (data.playlistUrl) {
      await loadVinylCover(data.playlistUrl);     // capa do vinil
      await loadPlaylistCover(data.playlistUrl);  // capa quadrada + mini player
    }
    
  }

  window.onload = loadProfile;

  const sidebar = document.getElementById('sidebar');
  const toggleBtn = document.getElementById('toggle-sidebar');

  toggleBtn.addEventListener('click', () => {
    sidebar.classList.toggle('hidden');
  });