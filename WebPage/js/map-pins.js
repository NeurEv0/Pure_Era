/**
 * 地图标记点动画效果
 * 支持标记点的动画显示和交互功能
 */

// 抗菌肽研究机构数据
const researchCenters = [
  { 
    id: 1, 
    lat: 40, 
    lng: -74, 
    title: "美国抗菌肽研究中心", 
    description: "专注于抗菌肽设计和筛选的研究机构，拥有先进的高通量筛选平台。",
    image: "location1.jpg"
  },
  { 
    id: 2, 
    lat: 51, 
    lng: -0.1, 
    title: "欧洲生物技术研究所", 
    description: "致力于抗菌肽结构与功能研究的国际合作机构，拥有丰富的肽库资源。",
    image: "location2.jpg"
  },
  { 
    id: 3, 
    lat: 35, 
    lng: 139, 
    title: "亚洲抗生素研究中心", 
    description: "专注于从传统药物中发现新型抗菌肽的研究机构，已发现多种有效成分。",
    image: "location3.jpg"
  },
  { 
    id: 4, 
    lat: -33.9, 
    lng: 151.2, 
    title: "澳大利亚生物技术中心", 
    description: "研究海洋生物来源抗菌肽的专业机构，在抗菌肽应用领域取得显著成果。",
    image: "location4.jpg"
  },
  { 
    id: 5, 
    lat: 30, 
    lng: 31, 
    title: "非洲传统医学研究所", 
    description: "结合传统医学知识研究抗菌肽的机构，探索自然界中的抗菌肽资源。",
    image: "location5.jpg"
  },
  { 
    id: 6, 
    lat: -23.5, 
    lng: -46.6, 
    title: "南美药物研发中心", 
    description: "专注于热带植物抗菌肽研究的机构，已开发多种临床应用产品。",
    image: "location6.jpg"
  },
  { 
    id: 7, 
    lat: 39.9, 
    lng: 116.4, 
    title: "中国抗菌肽数据中心", 
    description: "致力于抗菌肽数据收集与分析的研究机构，建立了全面的抗菌肽数据库。",
    image: "location7.jpg"
  },
  { 
    id: 8, 
    lat: 55.8, 
    lng: 37.6, 
    title: "北欧肽类药物研究所", 
    description: "专注于耐寒微生物抗菌肽研究的机构，发现了多种特殊环境下的活性肽。",
    image: "location8.jpg"
  }
];

// 初始化地图和标记点
function initMap() {
  // 获取地图容器
  const mapContainer = document.querySelector('.map-container');
  if (!mapContainer) return;
  
  // 清空现有标记点
  const existingMarkers = mapContainer.querySelectorAll('.map-marker');
  existingMarkers.forEach(marker => marker.remove());
  
  // 创建标记点元素
  researchCenters.forEach(center => {
    const markerElement = document.createElement('div');
    markerElement.className = 'map-marker';
    markerElement.setAttribute('data-id', center.id);
    
    // 计算位置（需要根据实际地图尺寸调整）
    const mapWidth = mapContainer.offsetWidth;
    const mapHeight = mapContainer.offsetHeight;
    
    // 简单的经纬度转换为像素位置（仅作示例，实际应用需要更精确的计算）
    // 假设地图范围是经度-180到180，纬度-90到90
    const left = ((center.lng + 180) / 360) * mapWidth;
    const top = ((90 - center.lat) / 180) * mapHeight;
    
    markerElement.style.left = `${left}px`;
    markerElement.style.top = `${top}px`;
    
    // 创建标记点详情
    const detailsElement = document.createElement('div');
    detailsElement.className = 'marker-details';
    detailsElement.innerHTML = `
      <span class="close-btn">&times;</span>
      <h3>${center.title}</h3>
      <p>${center.description}</p>
      <img src="images/locations/${center.image}" alt="${center.title}" onerror="this.src='images/locations/placeholder.jpg'">
    `;
    
    markerElement.appendChild(detailsElement);
    mapContainer.appendChild(markerElement);
    
    // 添加点击事件
    markerElement.addEventListener('click', function(e) {
      // 如果点击的是关闭按钮，则只关闭详情不触发其他操作
      if (e.target.classList.contains('close-btn')) {
        closeAllDetails();
        return;
      }
      
      // 关闭其他打开的标记点
      closeAllDetails();
      
      // 切换当前标记点
      this.classList.add('active');
      const details = this.querySelector('.marker-details');
      details.classList.add('visible');
      
      // 阻止事件冒泡
      e.stopPropagation();
    });
    
    // 为关闭按钮添加事件
    const closeBtn = detailsElement.querySelector('.close-btn');
    closeBtn.addEventListener('click', function(e) {
      closeAllDetails();
      e.stopPropagation();
    });
  });
  
  // 点击地图外部关闭所有详情
  document.addEventListener('click', function(e) {
    if (!e.target.closest('.map-marker')) {
      closeAllDetails();
    }
  });
  
  // 执行初始显示动画
  setTimeout(() => {
    showMarkersAnimation();
  }, 500);
}

// 关闭所有详情面板
function closeAllDetails() {
  document.querySelectorAll('.map-marker').forEach(marker => {
    marker.classList.remove('active');
    const details = marker.querySelector('.marker-details');
    if (details) {
      details.classList.remove('visible');
    }
  });
}

// 显示标记点动画
function showMarkersAnimation() {
  const markers = document.querySelectorAll('.map-marker:not(.visible)');
  
  markers.forEach((marker, index) => {
    setTimeout(() => {
      marker.classList.add('visible');
    }, index * 150); // 每个标记点延迟150ms显示
  });
}

// 根据滚动位置显示标记点
function showMarkersOnScroll() {
  const mapContainer = document.querySelector('.map-container');
  if (!mapContainer) return;
  
  const containerRect = mapContainer.getBoundingClientRect();
  
  // 如果地图容器在视图中
  if (containerRect.top < window.innerHeight && containerRect.bottom > 0) {
    showMarkersAnimation();
  }
}

// 创建默认的占位图片
function createPlaceholderImage() {
  const img = new Image();
  img.src = 'data:image/svg+xml;charset=UTF-8,%3Csvg xmlns="http://www.w3.org/2000/svg" width="200" height="150" viewBox="0 0 200 150"%3E%3Crect fill="%23CCCCCC" width="200" height="150"/%3E%3Ctext fill="%23FFFFFF" font-family="sans-serif" font-size="30" dy="10.5" font-weight="bold" x="50%" y="50%" text-anchor="middle"%3E图片%3C/text%3E%3C/svg%3E';
  img.onload = function() {
    const canvas = document.createElement('canvas');
    canvas.width = 200;
    canvas.height = 150;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(img, 0, 0);
    
    // 保存为文件
    try {
      const dataURL = canvas.toDataURL('image/jpeg');
      const link = document.createElement('a');
      link.href = dataURL;
      link.download = 'placeholder.jpg';
      link.style.display = 'none';
      document.body.appendChild(link);
      // 自动下载文件（实际应用中可能需要手动触发）
      // link.click();
      document.body.removeChild(link);
    } catch (e) {
      console.error('无法生成占位图:', e);
    }
  };
}

// 调整地图标记点位置
function adjustMarkerPositions() {
  const mapContainer = document.querySelector('.map-container');
  if (!mapContainer) return;
  
  const mapWidth = mapContainer.offsetWidth;
  const mapHeight = mapContainer.offsetHeight;
  
  document.querySelectorAll('.map-marker').forEach((marker, index) => {
    const center = researchCenters[index];
    if (!center) return;
    
    const left = ((center.lng + 180) / 360) * mapWidth;
    const top = ((90 - center.lat) / 180) * mapHeight;
    
    marker.style.left = `${left}px`;
    marker.style.top = `${top}px`;
  });
}

// 窗口大小改变时调整标记点位置
window.addEventListener('resize', adjustMarkerPositions);

// 滚动时检查是否显示标记点
window.addEventListener('scroll', showMarkersOnScroll);

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
  // 尝试创建占位图片
  createPlaceholderImage();
  
  // 等待地图图片加载完成后初始化标记点
  const mapImg = document.querySelector('.map-background');
  if (mapImg) {
    if (mapImg.complete) {
      initMap();
    } else {
      mapImg.onload = initMap;
    }
  } else {
    // 如果没有找到地图图片，仍然初始化
    initMap();
  }
  
  // 初始检查是否显示标记点
  showMarkersOnScroll();
}); 