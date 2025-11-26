const apiBase = (window.__API_BASE__ || '') || '' // empty -> same origin

const $messages = document.getElementById('messages')
const $prompt = document.getElementById('prompt')
const $sendBtn = document.getElementById('sendBtn')
const $clearBtn = document.getElementById('clearBtn')
const $fileInput = document.getElementById('fileInput')

let isLoading = false

function appendMessage(role, text){
  const div = document.createElement('div')
  div.className = 'msg ' + (role === 'user' ? 'user' : 'assistant')
  div.textContent = text
  $messages.appendChild(div)
  $messages.scrollTop = $messages.scrollHeight
}

function setLoading(flag){
  isLoading = flag
  $sendBtn.disabled = flag
  $sendBtn.textContent = flag ? 'Sending...' : 'Send'
}

async function sendPrompt(){
  if (isLoading) return
  const text = $prompt.value.trim()
  if (!text && !$fileInput.files.length) return

  // If file selected include filename in the prompt for now
  let fileNote = ''
  if ($fileInput.files.length){
    const f = $fileInput.files[0]
    fileNote = `\n\n[Attached file: ${f.name} - size ${f.size} bytes]`
  }

  const prompt = text + fileNote

  appendMessage('user', text || `[Uploaded ${$fileInput.files[0].name}]`)
  setLoading(true)
  try{
    const url = apiBase + '/chat'
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt })
    })
    const data = await res.json()
    const reply = data && data.model_response ? data.model_response : JSON.stringify(data)
    appendMessage('assistant', reply)
  }catch(e){
    appendMessage('assistant', 'Request failed: ' + e)
  }finally{
    setLoading(false)
  }
}

function clearChat(){
  $messages.innerHTML = ''
  $prompt.value = ''
  $fileInput.value = ''
}

function init(){
  $sendBtn.addEventListener('click', sendPrompt)
  $clearBtn.addEventListener('click', clearChat)
  $prompt.addEventListener('keydown', (e)=>{
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) sendPrompt()
  })
  // simple preview when file selected
  $fileInput.addEventListener('change', ()=>{
    if ($fileInput.files.length){
      const f = $fileInput.files[0]
      appendMessage('user', `[Selected file: ${f.name}]`)
    }
  })
}

init()
