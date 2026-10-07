/**
 * Remotion Manga Studio - Pure HTML5 Animation Engine
 * Deterministic frame-based timeline for 16:9 1920x1080 video generation.
 */

// Math Easing & Remotion-like Interpolation
const Easing = {
  easeOutCubic: (t) => 1 - Math.pow(1 - t, 3),
  easeOutBack: (t) => {
    const c1 = 1.70158;
    const c3 = c1 + 1;
    return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2);
  },
  easeInOutQuad: (t) => t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2,
  easeOutExpo: (t) => (t === 1) ? 1 : 1 - Math.pow(2, -10 * t)
};

function clamp(val, min, max) {
  return Math.min(Math.max(val, min), max);
}

function interpolate(frame, inputRange, outputRange, options = {}) {
  const [inMin, inMax] = inputRange;
  const [outMin, outMax] = outputRange;
  let t = (frame - inMin) / (inMax - inMin);

  if (options.extrapolateLeft === 'clamp' || !options.extrapolateLeft) {
    if (frame < inMin) t = 0;
  }
  if (options.extrapolateRight === 'clamp' || !options.extrapolateRight) {
    if (frame > inMax) t = 1;
  }

  const easing = options.easing || ((x) => x);
  return outMin + (outMax - outMin) * easing(clamp(t, 0, 1));
}

// Global Timeline State
class RemotionEngine {
  constructor() {
    this.config = null;
    this.configLoadedExternally = false;
    this.currentFrame = 0;
    this.totalFrames = 0;
    this.fps = 30;
    this.isPlaying = false;
    this.animationTimer = null;
    this.scenes = []; // [{ id, enabled, duration, startFrame, endFrame }]
    this.lastDiskConfigStr = null;

    this.init();
  }

  async init() {
    // Check if in render mode via URL param ?render=1
    const params = new URLSearchParams(window.location.search);
    if (params.get('render') === '1') {
      document.body.classList.add('render-mode');
    }

    // If config was already loaded externally (e.g. via window.loadConfig), do not fetch
    if (!this.configLoadedExternally) {
      try {
        const res = await fetch(`config.json?t=${Date.now()}`, { cache: 'no-store' });
        if (!this.configLoadedExternally) {
          const text = await res.text();
          this.lastDiskConfigStr = text;
          this.config = JSON.parse(text);
        }
      } catch (e) {
        if (!this.configLoadedExternally) {
          console.warn('Could not load config.json, using default template', e);
          this.config = this.getDefaultConfig();
          this.lastDiskConfigStr = JSON.stringify(this.config);
        }
      }
    }

    if (!this.config) {
      this.config = this.getDefaultConfig();
    }

    this.fps = (this.config.general && this.config.general.fps) || 30;
    this.applyConfigToDOM();
    this.rebuildTimeline();
    this.setupEventListeners();
    this.handleResize();
    window.remotionReady = true;

    if (document.fonts) {
      document.fonts.ready.then(() => {
        this.adjustComicTitleFit();
        this.adjustCommentsFit();
      });
    }

    // Auto-sync config from disk when previewing in browser
    if (!document.body.classList.contains('render-mode')) {
      this.startConfigWatcher();
    }

    // Check if autoplay requested
    if (params.get('autoplay') === '1') {
      this.play();
    } else {
      this.seekToFrame(0);
    }
  }

  startConfigWatcher() {
    setInterval(async () => {
      if (this.isPlaying) return;
      try {
        const res = await fetch(`config.json?t=${Date.now()}`, { cache: 'no-store' });
        if (!res.ok) return;
        const text = await res.text();
        // Chỉ reload khi nội dung file config.json trên ổ đĩa thực sự thay đổi từ bên ngoài (ví dụ sửa qua VSCode/Notepad)
        if (this.lastDiskConfigStr !== null && text !== this.lastDiskConfigStr) {
          this.lastDiskConfigStr = text;
          const newCfg = JSON.parse(text);
          this.loadConfig(newCfg);
        }
      } catch (e) { }
    }, 1000);
  }

  getDefaultConfig() {
    return {
      general: { fps: 30, width: 1920, height: 1080, themeColor: "#ffffff", accentColor: "#ffffff", goldColor: "#ffffff", bgColor: "#000000" },
      scene1: {
        enabled: true,
        duration: 5.0,
        channel: { name: "GÀ VÀNG", handle: "@yellowchickenaudio" },
        comic: {
          title: "CHUYỂN SINH THÀNH GOBLIN",
          subTitle: "Phát Minh Từ Kiếm Đến Súng",
          chapter: "TẬP 1",
          badge: "CHUYỂN SINH / DỊ THẾ GIỚI",
          synopsis: "Sau một ngàn năm bị phong ấn dưới vực sâu U Minh, Huyết Ma Vương Kenjiro tỉnh giấc với sức mạnh bóng tối vô song. Đối mặt với sự phản bội của tam đại gia tộc hoàng gia, hắn đơn thương độc mã tiến về vương đô để đoạt lại những gì đã mất..."
        }
      },
      scene2: {
        enabled: true,
        duration: 4.5,
        title: "BÌNH LUẬN NỔI BẬT CỦA KHÁN GIẢ",
        comments: [
          { user: "Minh Tuấn Manga", time: "05/10/2026", text: "Bộ này nét vẽ đỉnh chóp, cốt truyện cuốn dã man! Mong ad ra tập mới nhanh nhanh nhé!", likes: "1.4k" },
          { user: "Huyền Trang Anime", time: "04/10/2026", text: "Pha combat cuối chap 44 quá mãn nhãn, Kenjiro ngầu đét. Nhóm dịch làm việc siêu có tâm!", likes: "980" },
          { user: "Hoàng Nam Comic", time: "02/10/2026", text: "Xem xong phải donate ngay cho ad một ly cà phê. Chúc kênh ngày càng phát triển!", likes: "750" }
        ]
      },
      scene3: {
        enabled: true,
        duration: 5.0,
        title: "ỦNG HỘ DUY TRÌ KÊNH",
        subTitle: "",
        message: "Sự đồng hành và ủng hộ từ các bạn là nguồn động lực to lớn giúp kênh tiếp tục đầu tư sản xuất những video giới thiệu truyện chất lượng cao nhất mỗi ngày. Xin chân thành cảm ơn!",
        qrImage: "assets/qr_code.png",
        bank: { bankName: "MB BANK (Ngân Hàng Quân Đội)", accountNumber: "9999 8888 6666", accountHolder: "NGUYEN VAN ADMIN", branch: "Chi nhánh Hà Nội", memo: "Ủng hộ kênh Manga Studio" },
        momo: { phone: "0988 888 888", name: "NGUYEN VAN ADMIN" }
      },
      scene4: {
        enabled: true,
        duration: 4.0,
        title: "LƯU Ý QUAN TRỌNG",
        subTitle: "NOTICE & DISCLAIMER TỪ KÊNH",
        items: [
          { badge: "LỊCH RA TẬP", title: "Lịch Chiếu Cố Định", desc: "Tập mới lên sóng vào lúc 19:30 mỗi tối thứ 2, 4, 6 và Chủ Nhật. Đừng quên bật chuông thông báo!" },
          { badge: "BẢN QUYỀN", title: "Tôn Trọng Tác Giả & Họa Sĩ", desc: "Video phục vụ mục đích giới thiệu truyện và phi thương mại. Mọi bản quyền hình ảnh thuộc về tác giả gốc." },
          { badge: "TƯƠNG TÁC", title: "Cộng Đồng Giao Lưu", desc: "Bấm Like, Share và Subscribe kênh để tham gia vào cộng đồng những người đam mê Manga cùng chúng mình nhé!" }
        ]
      }
    };
  }

  rebuildTimeline() {
    this.scenes = [];
    let curFrame = 0;

    const list = [
      { id: 'scene-1', key: 'scene1' },
      { id: 'scene-2', key: 'scene2' },
      { id: 'scene-3', key: 'scene3' },
      { id: 'scene-4', key: 'scene4' }
    ];

    list.forEach(item => {
      const data = this.config[item.key];
      if (data && data.enabled !== false) {
        const durSec = data.duration || 4.5;
        const durFrames = Math.round(durSec * this.fps);
        this.scenes.push({
          id: item.id,
          key: item.key,
          duration: durSec,
          startFrame: curFrame,
          endFrame: curFrame + durFrames
        });
        curFrame += durFrames;
      }
    });

    this.totalFrames = Math.max(curFrame, 1);

    // Update timeline slider bounds
    const slider = document.getElementById('timeline-slider');
    if (slider) {
      slider.max = this.totalFrames - 1;
    }

    this.renderTimelineMarkers();
  }

  renderTimelineMarkers() {
    const container = document.getElementById('timeline-scene-markers');
    if (!container) return;
    container.innerHTML = '';

    this.scenes.forEach((sc, i) => {
      const seg = document.createElement('div');
      seg.className = 'scene-marker';
      const pct = ((sc.endFrame - sc.startFrame) / this.totalFrames) * 100;
      seg.style.width = `${pct}%`;
      seg.textContent = `CẢNH ${sc.id.split('-')[1]} (${sc.duration}s)`;
      seg.title = `Click để chuyển tới Cảnh ${sc.id.split('-')[1]}`;
      seg.addEventListener('click', () => {
        this.seekToFrame(sc.startFrame);
      });
      container.appendChild(seg);
    });
  }

  applyConfigToDOM() {
    if (!this.config) return;

    // Scene 1
    const s1 = this.config.scene1;
    if (s1) {
      if (s1.channel) {
        const chName = s1.channel.name || 'M';
        document.getElementById('s1-channel-name').textContent = chName;
        const handleEl = document.getElementById('s1-channel-handle');
        if (handleEl) handleEl.textContent = s1.channel.handle || '';
        const badgeEl = document.getElementById('s1-channel-badge');
        if (badgeEl) badgeEl.textContent = s1.channel.badge || '';

        // Pure CSS First-Letter Avatar
        const firstLetter = chName.trim().charAt(0).toUpperCase() || 'M';
        const avatarEl = document.getElementById('s1-channel-avatar-css');
        if (avatarEl) avatarEl.textContent = firstLetter;
      }
      if (s1.comic) {
        document.getElementById('s1-comic-title').textContent = s1.comic.title || '';
        document.getElementById('s1-comic-subtitle').textContent = s1.comic.subTitle || '';
        document.getElementById('s1-comic-chapter').textContent = s1.comic.chapter || '';
        document.getElementById('s1-comic-badge').textContent = s1.comic.badge || 'HOT';
        document.getElementById('s1-comic-synopsis').textContent = s1.comic.synopsis || '';
        this.adjustComicTitleFit();
      }
    }

    // Scene 2 Comments
    const s2 = this.config.scene2;
    if (s2) {
      document.getElementById('s2-title').textContent = s2.title || 'BÌNH LUẬN NỔI BẬT';
      const commentContainer = document.getElementById('s2-comments-container');
      commentContainer.innerHTML = '';
      const comments = s2.comments || [];
      comments.forEach((c) => {
        const userFirstLetter = (c.user || 'U').trim().charAt(0).toUpperCase() || 'U';
        const card = document.createElement('div');
        card.className = 'comment-card';
        card.innerHTML = `
          <div class="comment-user-avatar-css">${userFirstLetter}</div>
          <div class="comment-content">
            <div class="comment-header-row">
              <span class="comment-username">${c.user}</span>
              <span class="comment-time">${c.time || ''}</span>
            </div>
            <p class="comment-body-text">${c.text}</p>
          </div>
        `;
        commentContainer.appendChild(card);
      });
      this.adjustCommentsFit();
    }

    // Scene 3 Donate
    const s3 = this.config.scene3;
    if (s3) {
      const s3TitleEl = document.getElementById('s3-title');
      if (s3TitleEl) s3TitleEl.textContent = s3.title || 'DONATE DUY TRÌ KÊNH';
      const s3MsgEl = document.getElementById('s3-message');
      if (s3MsgEl && s3.message) s3MsgEl.textContent = s3.message;
      if (s3.qrImage) document.getElementById('s3-qr-image').src = s3.qrImage;
      if (s3.bank) {
        const bName = document.getElementById('s3-bank-name');
        if (bName) bName.textContent = s3.bank.bankName || 'NGÂN HÀNG';
        const bBranch = document.getElementById('s3-bank-branch');
        if (bBranch) bBranch.textContent = s3.bank.branch || '';
        const bAcc = document.getElementById('s3-bank-account');
        if (bAcc) bAcc.textContent = s3.bank.accountNumber || '';
        const bHolder = document.getElementById('s3-bank-holder');
        if (bHolder) bHolder.textContent = s3.bank.accountHolder || '';
        const bMemo = document.getElementById('s3-bank-memo');
        if (bMemo) bMemo.textContent = s3.bank.memo || 'Ung ho kenh';
      }
      if (s3.momo) {
        const mPhone = document.getElementById('s3-momo-phone');
        if (mPhone) mPhone.textContent = s3.momo.phone || '';
        const mName = document.getElementById('s3-momo-name');
        if (mName) mName.textContent = s3.momo.name || '';
      }
    }

    // Scene 4 Notices
    const s4 = this.config.scene4;
    if (s4) {
      document.getElementById('s4-title').textContent = s4.title || 'LƯU Ý QUAN TRỌNG';
      const container = document.getElementById('s4-cards-container');
      container.innerHTML = '';
      const items = s4.items || [];
      items.forEach(it => {
        const c = document.createElement('div');
        c.className = 'notice-card';
        c.innerHTML = `
          <div class="notice-badge">${it.badge}</div>
          <div class="notice-title">${it.title}</div>
          <div class="notice-desc">${it.desc}</div>
        `;
        container.appendChild(c);
      });
    }

    this.populateDrawerInputs();
    this.adjustComicTitleFit();
  }

  /**
   * Auto-fit comic title horizontally to fit on a single line within screen
   */
  adjustComicTitleFit() {
    const titleEl = document.getElementById('s1-comic-title');
    if (!titleEl) return;

    titleEl.style.whiteSpace = 'nowrap';
    titleEl.style.display = 'inline-block';

    const maxAllowedWidth = 1680; // Safe width within 1920x1080 stage
    let baseFontSize = 140;

    titleEl.style.fontSize = `${baseFontSize}px`;

    let currentW = titleEl.scrollWidth || titleEl.offsetWidth;
    if (currentW > maxAllowedWidth) {
      const scale = maxAllowedWidth / currentW;
      let newFontSize = Math.floor(baseFontSize * scale * 0.95);
      titleEl.style.fontSize = `${newFontSize}px`;

      currentW = titleEl.scrollWidth || titleEl.offsetWidth;
      while (currentW > maxAllowedWidth && newFontSize > 24) {
        newFontSize -= 2;
        titleEl.style.fontSize = `${newFontSize}px`;
        currentW = titleEl.scrollWidth || titleEl.offsetWidth;
      }
    }
  }

  /**
   * Auto-fit comments vertically so all comments fit comfortably on screen
   */
  adjustCommentsFit() {
    const grid = document.getElementById('s2-comments-container');
    if (!grid) return;

    const cards = grid.querySelectorAll('.comment-card');
    if (cards.length === 0) return;

    // Available max height for comments grid inside 1080p stage
    const maxAllowedHeight = 840;

    let fontSize = 21;
    let lineHeight = 1.48;
    let padV = 16;
    let gap = 16;

    const apply = () => {
      grid.style.gap = `${gap}px`;
      cards.forEach(card => {
        card.style.padding = `${padV}px 32px`;
        const body = card.querySelector('.comment-body-text');
        if (body) {
          body.style.fontSize = `${fontSize}px`;
          body.style.lineHeight = `${lineHeight}`;
        }
      });
    };

    apply();

    // Measure total rendered height of the comments grid
    let currentHeight = grid.scrollHeight;
    while (currentHeight > maxAllowedHeight && fontSize > 12) {
      if (fontSize > 16) {
        fontSize -= 1;
        lineHeight = 1.42;
        padV = Math.max(10, padV - 1);
        gap = Math.max(10, gap - 1);
      } else {
        fontSize -= 0.5;
        lineHeight = 1.35;
        padV = Math.max(8, padV - 1);
        gap = Math.max(8, gap - 1);
      }
      apply();
      currentHeight = grid.scrollHeight;
    }
  }

  populateDrawerInputs() {
    if (!this.config) return;
    const s1 = this.config.scene1 || {};
    const ch = s1.channel || {};
    const cm = s1.comic || {};

    const setVal = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.value = val !== undefined ? val : '';
    };

    setVal('edit-channel-name', ch.name);
    setVal('edit-comic-title', cm.title);
    setVal('edit-comic-subtitle', cm.subTitle);
    setVal('edit-comic-chapter', cm.chapter);
    setVal('edit-comic-badge', cm.badge);
    setVal('edit-comic-synopsis', cm.synopsis);
    setVal('edit-s1-duration', s1.duration || 5.0);

    const s2 = this.config.scene2 || {};
    const chkS2 = document.getElementById('edit-s2-enabled');
    if (chkS2) chkS2.checked = s2.enabled !== false;
    setVal('edit-s2-duration', s2.duration || 4.5);

    const comments = s2.comments || [];
    for (let i = 0; i < 3; i++) {
      const c = comments[i] || {};
      setVal(`edit-comment-${i + 1}-user`, c.user);
      setVal(`edit-comment-${i + 1}-time`, c.time);
      setVal(`edit-comment-${i + 1}-text`, c.text);
    }

    const s3 = this.config.scene3 || {};
    const bk = s3.bank || {};
    const mo = s3.momo || {};
    setVal('edit-bank-name', bk.bankName);
    setVal('edit-bank-account', bk.accountNumber);
    setVal('edit-bank-holder', bk.accountHolder);
    setVal('edit-momo-phone', mo.phone);
    setVal('edit-s3-duration', s3.duration || 5.0);

    const s4 = this.config.scene4 || {};
    const chkS4 = document.getElementById('edit-s4-enabled');
    if (chkS4) chkS4.checked = s4.enabled !== false;
    setVal('edit-s4-duration', s4.duration || 4.0);
  }

  saveDrawerInputs() {
    if (!this.config) return;

    this.config.scene1 = this.config.scene1 || {};
    this.config.scene1.channel = this.config.scene1.channel || {};
    this.config.scene1.comic = this.config.scene1.comic || {};

    const elChName = document.getElementById('edit-channel-name');
    if (elChName) this.config.scene1.channel.name = elChName.value;

    const elCmTitle = document.getElementById('edit-comic-title');
    if (elCmTitle) this.config.scene1.comic.title = elCmTitle.value;

    const elCmSub = document.getElementById('edit-comic-subtitle');
    if (elCmSub) this.config.scene1.comic.subTitle = elCmSub.value;

    const elCmChap = document.getElementById('edit-comic-chapter');
    if (elCmChap) this.config.scene1.comic.chapter = elCmChap.value;

    const elCmBadge = document.getElementById('edit-comic-badge');
    if (elCmBadge) this.config.scene1.comic.badge = elCmBadge.value;

    const elCmSyn = document.getElementById('edit-comic-synopsis');
    if (elCmSyn) this.config.scene1.comic.synopsis = elCmSyn.value;

    const elS1Dur = document.getElementById('edit-s1-duration');
    if (elS1Dur) this.config.scene1.duration = parseFloat(elS1Dur.value) || 5.0;

    this.config.scene2 = this.config.scene2 || {};
    const elS2En = document.getElementById('edit-s2-enabled');
    if (elS2En) this.config.scene2.enabled = elS2En.checked;

    const elS2Dur = document.getElementById('edit-s2-duration');
    if (elS2Dur) this.config.scene2.duration = parseFloat(elS2Dur.value) || 4.5;

    this.config.scene2.comments = this.config.scene2.comments || [];
    for (let i = 0; i < 3; i++) {
      const uEl = document.getElementById(`edit-comment-${i + 1}-user`);
      const tEl = document.getElementById(`edit-comment-${i + 1}-time`);
      const txtEl = document.getElementById(`edit-comment-${i + 1}-text`);

      this.config.scene2.comments[i] = {
        user: uEl ? uEl.value : (this.config.scene2.comments[i]?.user || ''),
        time: tEl ? tEl.value : (this.config.scene2.comments[i]?.time || ''),
        text: txtEl ? txtEl.value : (this.config.scene2.comments[i]?.text || '')
      };
    }

    this.config.scene3 = this.config.scene3 || {};
    this.config.scene3.bank = this.config.scene3.bank || {};
    this.config.scene3.momo = this.config.scene3.momo || {};

    const elBkName = document.getElementById('edit-bank-name');
    if (elBkName) this.config.scene3.bank.bankName = elBkName.value;

    const elBkAcc = document.getElementById('edit-bank-account');
    if (elBkAcc) this.config.scene3.bank.accountNumber = elBkAcc.value;

    const elBkHolder = document.getElementById('edit-bank-holder');
    if (elBkHolder) this.config.scene3.bank.accountHolder = elBkHolder.value;

    const elMoPhone = document.getElementById('edit-momo-phone');
    if (elMoPhone) this.config.scene3.momo.phone = elMoPhone.value;

    const elS3Dur = document.getElementById('edit-s3-duration');
    if (elS3Dur) this.config.scene3.duration = parseFloat(elS3Dur.value) || 5.0;

    this.config.scene4 = this.config.scene4 || {};
    const elS4En = document.getElementById('edit-s4-enabled');
    if (elS4En) this.config.scene4.enabled = elS4En.checked;

    const elS4Dur = document.getElementById('edit-s4-duration');
    if (elS4Dur) this.config.scene4.duration = parseFloat(elS4Dur.value) || 4.0;

    this.applyConfigToDOM();
    this.rebuildTimeline();
    this.seekToFrame(0);
  }

  /**
   * Deterministic Frame Render
   * Maps currentFrame mathematically to all visual properties.
   */
  seekToFrame(frame) {
    this.currentFrame = clamp(Math.round(frame), 0, this.totalFrames - 1);

    // Find active scene
    let activeScene = this.scenes[0];
    for (const sc of this.scenes) {
      if (this.currentFrame >= sc.startFrame && this.currentFrame < sc.endFrame) {
        activeScene = sc;
        break;
      }
    }
    if (!activeScene && this.scenes.length > 0) {
      activeScene = this.scenes[this.scenes.length - 1];
    }

    // Toggle active scene visibility
    ['scene-1', 'scene-2', 'scene-3', 'scene-4'].forEach(id => {
      const el = document.getElementById(id);
      if (!el) return;
      if (activeScene && el.id === activeScene.id) {
        el.classList.add('active');
      } else {
        el.classList.remove('active');
      }
    });

    if (activeScene) {
      const localFrame = this.currentFrame - activeScene.startFrame;
      const sceneLen = activeScene.endFrame - activeScene.startFrame;
      this.animateScene(activeScene.id, localFrame, sceneLen);
    }

    // Update Player UI
    this.updatePlayerUI();
  }

  seekToTime(seconds) {
    this.seekToFrame(Math.round(seconds * this.fps));
  }

  animateScene(sceneId, frame, totalSceneFrames) {
    // Slower, smoother transitions: Intro (35 frames ~ 1.2s), Outro (22 frames ~ 0.7s)
    const introLen = Math.min(36, Math.floor(totalSceneFrames * 0.35));
    const outroLen = Math.min(22, Math.floor(totalSceneFrames * 0.25));

    const introProgress = interpolate(frame, [0, introLen], [0, 1], {
      easing: Easing.easeOutCubic,
      extrapolateRight: 'clamp'
    });

    const outroProgress = interpolate(frame, [totalSceneFrames - outroLen, totalSceneFrames], [1, 0], {
      easing: Easing.easeInOutQuad,
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp'
    });

    const opacity = (frame < introLen ? introProgress : outroProgress);

    if (sceneId === 'scene-1') {
      const pillEl = document.getElementById('s1-channel-pill');
      const titleEl = document.getElementById('s1-title-box');
      const badgeEl = document.getElementById('s1-badge-strip');
      const synEl = document.getElementById('s1-synopsis-box');

      // Slower, graceful slide in from top-left for channel pill
      const pillX = interpolate(frame, [0, 30], [-40, 0], { easing: Easing.easeOutCubic });
      const pillOp = interpolate(frame, [0, 24], [0, 1], { easing: Easing.easeInOutQuad });

      // Comic title zooms in smoothly over 38 frames
      const titleScale = interpolate(frame, [6, 38], [0.88, 1], { easing: Easing.easeOutBack });
      const titleY = interpolate(frame, [6, 38], [25, 0], { easing: Easing.easeOutCubic });

      // Chapter badge & hot badge slide in
      const badgeScale = interpolate(frame, [2, 32], [0.82, 1], { easing: Easing.easeOutBack });

      // Synopsis slides up softly
      const synY = interpolate(frame, [14, 42], [40, 0], { easing: Easing.easeOutCubic });
      const synOp = interpolate(frame, [14, 38], [0, 1], { easing: Easing.easeInOutQuad });

      if (pillEl) {
        pillEl.style.transform = `translateX(${pillX}px)`;
        pillEl.style.opacity = Math.min(pillOp, opacity);
      }
      if (titleEl) {
        titleEl.style.transform = `translateY(${titleY}px) scale(${titleScale})`;
        titleEl.style.opacity = opacity;
      }
      if (badgeEl) {
        badgeEl.style.transform = `scale(${badgeScale})`;
        badgeEl.style.opacity = opacity;
      }
      if (synEl) {
        synEl.style.transform = `translateY(${synY}px)`;
        synEl.style.opacity = Math.min(synOp, opacity);
      }
    }

    else if (sceneId === 'scene-2') {
      const header = document.querySelector('#scene-2 .scene-header');
      if (header) {
        const hY = interpolate(frame, [0, 28], [-30, 0], { easing: Easing.easeOutCubic });
        header.style.transform = `translateY(${hY}px)`;
        header.style.opacity = opacity;
      }

      const cards = document.querySelectorAll('.comment-card');
      cards.forEach((card, idx) => {
        const delay = 8 + idx * 12; // Slower stagger delay
        const cardY = interpolate(frame, [delay, delay + 30], [50, 0], { easing: Easing.easeOutCubic });
        const cardOp = interpolate(frame, [delay, delay + 24], [0, 1], { easing: Easing.easeInOutQuad });
        card.style.transform = `translateY(${cardY}px)`;
        card.style.opacity = Math.min(cardOp, opacity);
      });
    }

    else if (sceneId === 'scene-3') {
      const header = document.querySelector('#scene-3 .scene-header');
      if (header) {
        const hY = interpolate(frame, [0, 28], [-30, 0], { easing: Easing.easeOutCubic });
        header.style.transform = `translateY(${hY}px)`;
        header.style.opacity = opacity;
      }

      const qrBox = document.getElementById('s3-qr-box');
      const detailsBox = document.getElementById('s3-details-box');

      // Slower entrance for QR and details
      const qrScale = interpolate(frame, [4, 38], [0.86, 1], { easing: Easing.easeOutBack });
      const qrOp = interpolate(frame, [4, 30], [0, 1], { easing: Easing.easeInOutQuad });
      const detailsX = interpolate(frame, [10, 42], [50, 0], { easing: Easing.easeOutCubic });

      if (qrBox) {
        qrBox.style.transform = `scale(${qrScale})`;
        qrBox.style.opacity = Math.min(qrOp, opacity);
      }
      if (detailsBox) {
        detailsBox.style.transform = `translateX(${detailsX}px)`;
        detailsBox.style.opacity = opacity;
      }
    }

    else if (sceneId === 'scene-4') {
      const header = document.querySelector('#scene-4 .scene-header');
      if (header) {
        const hY = interpolate(frame, [0, 28], [-30, 0], { easing: Easing.easeOutCubic });
        header.style.transform = `translateY(${hY}px)`;
        header.style.opacity = opacity;
      }

      const cards = document.querySelectorAll('.notice-card');
      cards.forEach((card, idx) => {
        const delay = 8 + idx * 12; // Slower stagger delay
        const cardY = interpolate(frame, [delay, delay + 30], [50, 0], { easing: Easing.easeOutCubic });
        const cardOp = interpolate(frame, [delay, delay + 22], [0, 1]);
        card.style.transform = `translateY(${cardY}px)`;
        card.style.opacity = Math.min(cardOp, opacity);
      });
    }
  }

  updatePlayerUI() {
    const slider = document.getElementById('timeline-slider');
    if (slider && !this.isDraggingSlider) {
      slider.value = this.currentFrame;
    }

    const curSec = (this.currentFrame / this.fps).toFixed(2);
    const totSec = (this.totalFrames / this.fps).toFixed(2);

    const tc = document.getElementById('display-timecode');
    if (tc) {
      tc.textContent = `${this.formatTime(curSec)} / ${this.formatTime(totSec)}`;
    }

    const fc = document.getElementById('display-framecount');
    if (fc) {
      fc.textContent = `Frame: ${this.currentFrame} / ${this.totalFrames} (${this.fps} FPS)`;
    }
  }

  formatTime(totalSecStr) {
    const totalSec = parseFloat(totalSecStr);
    const m = Math.floor(totalSec / 60);
    const s = Math.floor(totalSec % 60);
    const ms = Math.floor((totalSec % 1) * 100);
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}.${String(ms).padStart(2, '0')}`;
  }

  play() {
    if (this.isPlaying) return;
    this.isPlaying = true;
    const playIcon = document.getElementById('play-icon');
    if (playIcon) playIcon.textContent = '⏸';

    let lastTime = performance.now();
    const frameInterval = 1000 / this.fps;

    const loop = (currentTime) => {
      if (!this.isPlaying) return;
      const delta = currentTime - lastTime;

      if (delta >= frameInterval) {
        lastTime = currentTime - (delta % frameInterval);
        if (this.currentFrame >= this.totalFrames - 1) {
          this.seekToFrame(0);
        } else {
          this.seekToFrame(this.currentFrame + 1);
        }
      }
      this.animationTimer = requestAnimationFrame(loop);
    };

    this.animationTimer = requestAnimationFrame(loop);
  }

  pause() {
    this.isPlaying = false;
    if (this.animationTimer) {
      cancelAnimationFrame(this.animationTimer);
    }
    const playIcon = document.getElementById('play-icon');
    if (playIcon) playIcon.textContent = '▶';
  }

  togglePlay() {
    if (this.isPlaying) this.pause();
    else this.play();
  }

  setupEventListeners() {
    const btnPlay = document.getElementById('btn-play-pause');
    if (btnPlay) btnPlay.addEventListener('click', () => this.togglePlay());

    const btnRestart = document.getElementById('btn-restart');
    if (btnRestart) btnRestart.addEventListener('click', () => {
      this.pause();
      this.seekToFrame(0);
    });

    const slider = document.getElementById('timeline-slider');
    if (slider) {
      slider.addEventListener('mousedown', () => { this.isDraggingSlider = true; });
      window.addEventListener('mouseup', () => { this.isDraggingSlider = false; });
      slider.addEventListener('input', (e) => {
        this.pause();
        this.seekToFrame(parseInt(e.target.value));
      });
    }

    // Toggle Config Drawer
    const btnToggleEditor = document.getElementById('btn-toggle-editor');
    const drawer = document.getElementById('editor-drawer');
    const btnCloseDrawer = document.getElementById('btn-close-drawer');
    if (btnToggleEditor && drawer) {
      btnToggleEditor.addEventListener('click', () => drawer.classList.toggle('open'));
    }
    if (btnCloseDrawer && drawer) {
      btnCloseDrawer.addEventListener('click', () => drawer.classList.remove('open'));
    }

    // Apply config changes from Drawer
    const btnApply = document.getElementById('btn-apply-config');
    if (btnApply) {
      btnApply.addEventListener('click', () => {
        this.saveDrawerInputs();
        if (drawer) drawer.classList.remove('open');
      });
    }

    // Download updated config.json
    const btnDownload = document.getElementById('btn-download-config');
    if (btnDownload) {
      btnDownload.addEventListener('click', () => {
        this.saveDrawerInputs();
        const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(this.config, null, 2));
        const dlAnchor = document.createElement('a');
        dlAnchor.setAttribute("href", dataStr);
        dlAnchor.setAttribute("download", "config.json");
        dlAnchor.click();
      });
    }

    // Export WebM via in-browser MediaRecorder
    const btnExport = document.getElementById('btn-export-browser');
    if (btnExport) {
      btnExport.addEventListener('click', () => this.exportWebMInBrowser());
    }

    // Responsive Canvas Resizing
    window.addEventListener('resize', () => this.handleResize());
  }

  handleResize() {
    if (document.body.classList.contains('render-mode')) return;

    const viewport = document.getElementById('viewport');
    const stage = document.getElementById('stage-container');
    if (!viewport || !stage) return;

    const vw = viewport.clientWidth - 40;
    const vh = viewport.clientHeight - 40;

    const scale = Math.min(vw / 1920, vh / 1080);
    stage.style.transform = `scale(${scale})`;
  }

  /**
   * Optional In-Browser WebM Recorder
   * Users can record WebM directly with zero server or python setup!
   */
  async exportWebMInBrowser() {
    const btn = document.getElementById('btn-export-browser');
    if (!btn) return;
    btn.textContent = 'Đang chuẩn bị render...';
    btn.disabled = true;

    try {
      this.pause();
      this.seekToFrame(0);

      // Create high-res offscreen canvas
      const canvas = document.createElement('canvas');
      canvas.width = 1920;
      canvas.height = 1080;
      const ctx = canvas.getContext('2d');

      const stream = canvas.captureStream(this.fps);
      const recorder = new MediaRecorder(stream, {
        mimeType: 'video/webm;codecs=vp9',
        videoBitsPerSecond: 6000000
      });

      const chunks = [];
      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) chunks.push(e.data);
      };

      recorder.onstop = () => {
        const blob = new Blob(chunks, { type: 'video/webm' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `manga_intro_${Date.now()}.webm`;
        a.click();
        btn.textContent = 'Xuất WebM (Trình Duyệt)';
        btn.disabled = false;
      };

      recorder.start();

      // Render frames sequentially
      for (let f = 0; f < this.totalFrames; f++) {
        this.seekToFrame(f);
        btn.textContent = `Đang xuất WebM: Frame ${f}/${this.totalFrames}...`;
        await new Promise(r => setTimeout(r, 1000 / this.fps));
      }

      recorder.stop();
    } catch (err) {
      console.error(err);
      alert('Lỗi xuất video trên trình duyệt: ' + err.message + '\nBạn hãy dùng script python render.py để xuất chất lượng cao nhất.');
      btn.textContent = 'Xuất WebM (Trình Duyệt)';
      btn.disabled = false;
    }
  }

  // APIs exposed for headless python rendering
  getVideoConfig() {
    return {
      width: 1920,
      height: 1080,
      fps: this.fps,
      totalFrames: this.totalFrames,
      durationInSeconds: this.totalFrames / this.fps,
      scenes: this.scenes
    };
  }

  loadConfig(cfg) {
    this.configLoadedExternally = true;
    this.config = cfg;
    this.fps = (this.config.general && this.config.general.fps) || 30;
    this.applyConfigToDOM();
    this.populateDrawerInputs();
    this.rebuildTimeline();
    this.seekToFrame(0);
    window.remotionReady = true;
  }
}

// Global hook
window.addEventListener('DOMContentLoaded', () => {
  window.remotionEngine = new RemotionEngine();

  // Expose global methods for Python
  window.seekToFrame = (f) => window.remotionEngine.seekToFrame(f);
  window.seekToTime = (s) => window.remotionEngine.seekToTime(s);
  window.getVideoConfig = () => window.remotionEngine.getVideoConfig();
  window.loadConfig = (cfg) => window.remotionEngine.loadConfig(cfg);
  window.playFromStart = () => {
    window.remotionEngine.seekToFrame(0);
    window.remotionEngine.play();
  };
});
