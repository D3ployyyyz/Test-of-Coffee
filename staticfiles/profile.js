const mural = document.getElementById('mural');
const form = document.getElementById('form-recado');
let draggingRecado = null;
let offsetX = 0;
let offsetY = 0;
let maxZ = 10; // z-index inicial para recados

// Função para criar recado HTML dinamicamente
function criarRecado(autor, texto, reacoes, posX = 20, posY = 80) {
  const recado = document.createElement('article');
  recado.classList.add('recado');

  recado.style.left = posX + 'px';
  recado.style.top = posY + 'px';

  // Avatar aleatório baseado no nome
  const avatarNum = Math.floor(Math.abs(hashCode(autor)) % 70) + 1;
  const avatarUrl = `https://i.pravatar.cc/44?img=${avatarNum}`;

  recado.innerHTML = `
    <div class="autor">
      <img class="avatar" src="${avatarUrl}" alt="avatar ${autor}" />
      <strong>${escapeHtml(autor)}</strong>
    </div>
    <p class="texto">${escapeHtml(texto)}</p>
    <div class="footer">
      <span class="data">${new Date().toLocaleDateString('pt-BR')}</span>
      <span class="reacoes">${escapeHtml(reacoes)}</span>
    </div>
  `;

  // Eventos para arrastar
  recado.addEventListener('mousedown', (e) => {
    draggingRecado = recado;
    offsetX = e.clientX - recado.offsetLeft;
    offsetY = e.clientY - recado.offsetTop;
    subirZIndex(recado);
    e.preventDefault();
  });

  // Ao clicar, sobe na frente
  recado.addEventListener('click', (e) => {
    subirZIndex(recado);
    e.stopPropagation();
  });

  return recado;
}

// Z-index maior para recado ativo
function subirZIndex(element) {
  maxZ++;
  element.style.zIndex = maxZ;
}

// Escape simples para texto
function escapeHtml(text) {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// Função hash para avatar consistente
function hashCode(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = ((hash << 5) - hash) + str.charCodeAt(i);
    hash |= 0;
  }
  return hash;
}

// Form submit para adicionar recado novo
form.addEventListener('submit', (e) => {
  e.preventDefault();
  const autor = form.autor.value.trim();
  const texto = form.texto.value.trim();
  const reacoes = form.reacoes.value.trim();

  if (!autor || !texto) return;

  // Posição inicial no canto inferior esquerdo do mural, ajustada para não sair do mural
  const posX = 10 + Math.random() * (mural.clientWidth - 140);
  const posY = 150 + Math.random() * (mural.clientHeight - 170);

  const novoRecado = criarRecado(autor, texto, reacoes, posX, posY);
  mural.appendChild(novoRecado);

  form.reset();
});

// Movimentação do recado
document.addEventListener('mousemove', (e) => {
  if (!draggingRecado) return;

  let x = e.clientX - offsetX;
  let y = e.clientY - offsetY;

  // Limitar dentro do mural
  const rect = mural.getBoundingClientRect();
  const recadoRect = draggingRecado.getBoundingClientRect();

  if (x < 0) x = 0;
  if (y < 0) y = 0;
  if (x + recadoRect.width > rect.width) x = rect.width - recadoRect.width;
  if (y + recadoRect.height > rect.height) y = rect.height - recadoRect.height;

  draggingRecado.style.left = x + 'px';
  draggingRecado.style.top = y + 'px';
});

// Soltar o recado
document.addEventListener('mouseup', () => {
  if (draggingRecado) {
    draggingRecado = null;
  }
});

// Se clicar fora dos recados, nada acontece
mural.addEventListener('click', () => {
  // Pode implementar deselecionar recado, se quiser
});

// Inicial: definir z-index dos recados iniciais e posicionar fixo (já no style inline)
document.querySelectorAll('#mural .recado').forEach((recado, i) => {
  recado.style.zIndex = i + 1;
  subirZIndex(recado);
  recado.style.position = 'absolute';

  // Também habilitar drag para os recados já existentes
  recado.addEventListener('mousedown', (e) => {
    draggingRecado = recado;
    offsetX = e.clientX - recado.offsetLeft;
    offsetY = e.clientY - recado.offsetTop;
    subirZIndex(recado);
    e.preventDefault();
  });

  recado.addEventListener('click', (e) => {
    subirZIndex(recado);
    e.stopPropagation();
  });
});

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
      const hostname = new URL(url).hostname.replace('www.','').toLowerCase();
      for(const s of socialIconsMap) {
        if(hostname.includes(s.domain)) return s.icon;
      }
    } catch {
      return null;
    }
    return 'https://cdn-icons-png.flaticon.com/128/565/565547.png'; // ícone genérico
  }

  // Busca a capa da playlist do Spotify sem usar API oficial
  async function fetchSpotifyCover(playlistUrl) {
    const match = playlistUrl.match(/playlist\/([a-zA-Z0-9]+)/);
    if (!match) return null;

    const finalUrl = `https://open.spotify.com/playlist/${match[1]}`;
    try {
      // Proxy para evitar CORS
      const resposta = await fetch(`https://api.allorigins.win/raw?url=${encodeURIComponent(finalUrl)}`);
      const html = await resposta.text();
      const ogImageMatch = html.match(/property="og:image" content="(.*?)"/);
      return ogImageMatch?.[1] || null;
    } catch {
      return null;
    }
  }

  async function loadPlaylistCover(playlistUrl) {
  const capaContainer = document.getElementById("playlist-image-container");
  capaContainer.innerHTML = "";

  const imgUrl = await fetchSpotifyCover(playlistUrl);

  if (imgUrl) {
    // Criar imagem da capa
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
// Função auxiliar para gerar url embed do Spotify player da playlist
function getSpotifyEmbedUrl(playlistUrl) {
  const match = playlistUrl.match(/playlist\/([a-zA-Z0-9]+)/);
  if (!match) return "";
  return `https://open.spotify.com/embed/playlist/${match[1]}`;
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
    if(data.playlistUrl){
      await loadPlaylistCover(data.playlistUrl);
    }
  }

  window.onload = loadProfile;