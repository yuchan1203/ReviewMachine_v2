const form = document.getElementById('analyzeForm');
const status = document.getElementById('status');
const result = document.getElementById('result');
const spinner = document.getElementById('spinner');
const submitBtn = document.getElementById('submitBtn');
const downloadBtn = document.getElementById('downloadBtn');
const uploadForm = document.getElementById('uploadForm');
const fileInput = document.getElementById('fileInput');
const uploadStatus = document.getElementById('uploadStatus');

function setLoading(isLoading){
  if(isLoading){
    spinner.hidden = false;
    spinner.setAttribute('aria-hidden','false');
    submitBtn.disabled = true;
  } else {
    spinner.hidden = true;
    spinner.setAttribute('aria-hidden','true');
    submitBtn.disabled = false;
  }
}

async function fetchAndRenderStats(appId){
  try{
    const resp = await fetch(`/stats/${encodeURIComponent(appId)}`);
    if(!resp.ok) return;
    const payload = await resp.json();
    renderPieChart(payload.counts);
    renderLineChart(payload.timeline);
  }catch(e){
    console.warn('stats fetch failed', e);
  }
}

function renderPieChart(counts){
  const labels = Object.keys(counts);
  const values = labels.map(k => counts[k] || 0);
  const data = [{ labels, values, type: 'pie', hole: 0.3 }];
  const layout = { title: '감성 분포' };
  Plotly.newPlot('pieChart', data, layout, {responsive:true});
}

function renderLineChart(timeline){
  if(!Array.isArray(timeline)) return;
  const dates = timeline.map(r => r.date);
  const scores = timeline.map(r => r.sentiment_score || 0);
  const data = [{ x: dates, y: scores, type: 'scatter', mode:'lines+markers', marker:{color:'#2563eb'} }];
  const layout = { title: '감성 점수 타임라인', xaxis:{title:'날짜'}, yaxis:{title:'감성 점수'} };
  Plotly.newPlot('lineChart', data, layout, {responsive:true});
}

document.addEventListener('DOMContentLoaded', () => {
  const exampleButtons = document.querySelectorAll('.example-btn');
  exampleButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const appIdInput = document.getElementById('appId');
      appIdInput.value = btn.dataset.appid || '';
      appIdInput.focus();
      status.textContent = `예시 앱 선택: ${btn.dataset.appid}`;
      exampleButtons.forEach(b => b.setAttribute('aria-pressed','false'));
      btn.setAttribute('aria-pressed','true');
    });
  });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const appId = document.getElementById('appId').value.trim();
    const count = parseInt(document.getElementById('count').value) || 100;
    if (!appId) { status.textContent = 'App ID를 입력하세요.'; return; }
    setLoading(true);
    status.textContent = '요청 중...';
    result.textContent = '';
    try {
      const hfToken = document.getElementById('hfToken')?.value?.trim() || null;
      if(hfToken){
        try{ localStorage.setItem('hf_token', hfToken); }catch(e){}
      }
      const resp = await fetch('/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ app_id: appId, count, hf_token: hfToken })
      });
      const data = await resp.json();
      if (!resp.ok) {
        status.textContent = `Error ${resp.status}`;
        result.textContent = JSON.stringify(data, null, 2);
      } else {
        status.textContent = '완료';
        result.textContent = JSON.stringify(data, null, 2);
        result.focus();
        // render charts using stats endpoint
        fetchAndRenderStats(appId);
        downloadBtn.disabled = false;
        downloadBtn.dataset.appid = appId;
      }
    } catch (err) {
      status.textContent = '요청 실패';
      result.textContent = err.toString();
    } finally {
      setLoading(false);
    }
  });

  // download button
  downloadBtn.addEventListener('click', () => {
    const appId = downloadBtn.dataset.appid || document.getElementById('appId').value.trim();
    if(!appId) return alert('다운로드할 app_id를 먼저 분석하거나 업로드하세요.');
    window.location = `/download/analyzed/${encodeURIComponent(appId)}`;
  });

  // restore hf token from localStorage if available
  try{
    const stored = localStorage.getItem('hf_token');
    if(stored){ document.getElementById('hfToken').value = stored; }
  }catch(e){}

  // upload handler
  uploadForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const file = fileInput.files[0];
    if(!file) { uploadStatus.textContent = 'CSV 파일을 선택하세요.'; return; }
    uploadStatus.textContent = '업로드 중...';
    const fd = new FormData();
    fd.append('file', file, file.name);
    try{
      const resp = await fetch('/upload', { method: 'POST', body: fd });
      const data = await resp.json();
      if(!resp.ok){ uploadStatus.textContent = `업로드 실패: ${data.detail || resp.status}`; return; }
      uploadStatus.textContent = `업로드 완료: app_id=${data.app_id}, rows=${data.rows}`;
      // populate appId and fetch stats
      document.getElementById('appId').value = data.app_id;
      downloadBtn.dataset.appid = data.app_id;
      fetchAndRenderStats(data.app_id);
    }catch(err){
      uploadStatus.textContent = '업로드 실패';
    }
  });
});
