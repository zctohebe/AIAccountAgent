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

async function uploadFileWithPresign(file){
  // request presign
  const presignUrl = apiBase + '/presign'
  const res = await fetch(presignUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filename: file.name, content_type: file.type })
  })
  const data = await res.json()
  if (!data || !data.presigned) throw new Error('Failed to get presigned info')

  const { url, fields, key } = data.presigned

  // build form data
  const form = new FormData()
  Object.keys(fields || {}).forEach(k => form.append(k, fields[k]))
  form.append('file', file)

  const uploadRes = await fetch(url, {
    method: 'POST',
    body: form
  })
  if (!uploadRes.ok) throw new Error('Upload failed')

  return key
}

async function sendPrompt(){
  if (isLoading) return
  const text = $prompt.value.trim()
  if (!text && !$fileInput.files.length) return

  setLoading(true)
  try{
    let promptText = text
    if ($fileInput.files.length){
      const f = $fileInput.files[0]
      appendMessage('user', `[Uploading ${f.name}...]`)
      try{
        const s3key = await uploadFileWithPresign(f)
        appendMessage('user', `[Uploaded ${f.name} -> s3://${s3key}]`)
        promptText += `\n\n[Attached S3 object: s3://${s3key}]`
      }catch(uerr){
        appendMessage('assistant', 'File upload failed: ' + uerr)
      }
    } else {
      appendMessage('user', text)
    }

    // send chat request
    const url = apiBase + '/chat'
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt: promptText })
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
