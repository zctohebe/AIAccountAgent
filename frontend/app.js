const apiBase = (window.__API_BASE__ || 'http://localhost:8000'); // Backward compatible with localhost dev

const $messages = document.getElementById('messages')
const $prompt = document.getElementById('prompt')
const $sendBtn = document.getElementById('sendBtn')
const $clearBtn = document.getElementById('clearBtn')
const $fileInput = document.getElementById('fileInput')
const $btnUpload = document.getElementById('btnUpload')
const $uploadResult = document.getElementById('uploadResult')

// Fill quick demo buttons
document.querySelectorAll('.pill[data-fill]').forEach(btn=>{
  btn.addEventListener('click', ()=>{ $prompt.value = btn.getAttribute('data-fill')||''; $prompt.focus(); })
})
const fillRunReport = document.getElementById('fill-run-report')
if (fillRunReport){
  fillRunReport.addEventListener('click', ()=>{
    $prompt.value = `运行示例摘要报表 { "prompt": "[Run Report]", "reportType": "sample-summary", "input": { "source": "local", "format": "jsonl", "path": "resources/sample-data.jsonl" }, "output": { "target": "local", "path": "results/sample-summary-output.json" }, "params": {} }`
    $prompt.focus()
  })
}

function appendMessage(role, text, isMarkdown=false){
  const wrap = document.createElement('div')
  wrap.className = 'message'
  const r = document.createElement('div'); r.className='role'; r.textContent = role
  const bubble = document.createElement('div'); bubble.className='bubble'
  if (isMarkdown && window.marked){ bubble.innerHTML = window.marked.parse(text) }
  else { bubble.textContent = text }
  wrap.appendChild(r); wrap.appendChild(bubble)
  $messages.appendChild(wrap)
  $messages.scrollTop = $messages.scrollHeight
}

async function sendPrompt(){
  const text = ($prompt.value||'').trim()
  if (!text) return
  appendMessage('You', text)
  $prompt.value=''
  try{
    const res = await fetch(apiBase+'/', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ prompt: text }) })
    const data = await res.json()
    const md = data.markdown || (data.model_response ? '``' + data.model_response + '``' : '``' + JSON.stringify(data) + '``')
    appendMessage('Agent', md, true)
  }catch(e){ appendMessage('Agent', '请求失败: '+ e) }
}

// Enter to send (Shift+Enter newline); handle IME & modifiers
function handleEnterToSend(e){
  const isEnter = (e.key === 'Enter' || e.keyCode === 13)
  if (isEnter && !e.shiftKey && !e.ctrlKey && !e.metaKey && !e.altKey && !e.isComposing){
    e.preventDefault()
    sendPrompt()
  }
}
$prompt.addEventListener('keydown', handleEnterToSend)
$prompt.addEventListener('keypress', handleEnterToSend)
if ($sendBtn) $sendBtn.addEventListener('click', sendPrompt)
if ($clearBtn) $clearBtn.addEventListener('click', ()=>{ $messages.innerHTML='' })

// Upload via backend /upload
async function upload(){
  const f = $fileInput && $fileInput.files && $fileInput.files[0]
  if (!f){ if($uploadResult) $uploadResult.textContent='请选择文件'; return }
  const buf = await f.arrayBuffer()
  const b64 = btoa(String.fromCharCode(...new Uint8Array(buf)))
  try{
    const res = await fetch(apiBase+'/upload', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ filename: f.name, contentBase64: b64 }) })
    const data = await res.json()
    const md = data.markdown || ('上传成功: '+ (data.path||''))
    if ($uploadResult){
      $uploadResult.innerHTML = window.marked ? window.marked.parse(md) : md
    } else {
      appendMessage('Agent', md, true)
    }
  }catch(e){ if ($uploadResult) $uploadResult.textContent='上传失败: '+e }
}
if ($btnUpload) $btnUpload.addEventListener('click', upload)
