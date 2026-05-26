let currentJobId = null
let fakeProgress = 0
let progressTimer = null
let selectedFormat = "youtube"

const API_BASE =
    window.location.protocol === "file:"
        ? "https://lyricgenerator.net"
        : ""

const audioInput = document.getElementById("audio")
const bgInput = document.getElementById("bg")

function updateEta() {
    const etaText = document.getElementById("etaText")

    if (selectedFormat === "youtube") {
        etaText.innerText = "1–3 minutes"
    } else if (selectedFormat === "square") {
        etaText.innerText = "2–4 minutes"
    } else if (selectedFormat === "tiktok") {
        etaText.innerText = "3–6 minutes"
    }
}

function selectFormat(format) {
    selectedFormat = format

    document.getElementById("format-youtube").classList.remove("active")
    document.getElementById("format-tiktok").classList.remove("active")
    document.getElementById("format-square").classList.remove("active")

    document.getElementById("format-" + format).classList.add("active")

    updateEta()
}

audioInput.addEventListener("change", () => {
    if (audioInput.files[0]) {
        document.getElementById("audioName").innerText =
            "✅ " + audioInput.files[0].name
    }
})

bgInput.addEventListener("change", () => {
    if (bgInput.files[0]) {
        document.getElementById("bgName").innerText =
            "✅ " + bgInput.files[0].name

        const reader = new FileReader()

        reader.onload = function(e) {
            const preview = document.getElementById("preview")
            preview.style.display = "block"
            preview.innerHTML = `<img src="${e.target.result}">`
        }

        reader.readAsDataURL(bgInput.files[0])
    }
})

function setupDrag(boxId, inputId) {
    const box = document.getElementById(boxId)
    const input = document.getElementById(inputId)

    box.addEventListener("dragover", (e) => {
        e.preventDefault()
        box.classList.add("dragover")
    })

    box.addEventListener("dragleave", () => {
        box.classList.remove("dragover")
    })

    box.addEventListener("drop", (e) => {
        e.preventDefault()
        box.classList.remove("dragover")
        input.files = e.dataTransfer.files
        input.dispatchEvent(new Event("change"))
    })
}

setupDrag("audioBox", "audio")
setupDrag("bgBox", "bg")

function setProgress(value) {
    fakeProgress = Math.min(value, 100)
    document.getElementById("progressBar").style.width = fakeProgress + "%"
    document.getElementById("progressText").innerText =
        Math.floor(fakeProgress) + "%"
}

function startFakeProgress() {
    clearInterval(progressTimer)

    progressTimer = setInterval(() => {
        if (fakeProgress < 90) {
            fakeProgress += 0.5
        } else if (fakeProgress < 96) {
            fakeProgress += 0.1
        }

        setProgress(fakeProgress)
    }, 1000)
}

function stopProgressDone() {
    clearInterval(progressTimer)
    setProgress(100)
}

async function generate() {
    try {
        const audio = audioInput.files[0]
        const bg = bgInput.files[0]

        if (!audio || !bg) {
            alert("Please upload both an MP3 and a background image first.")
            return
        }

        document.getElementById("status").innerText =
            "Uploading files... Estimated time: " +
            document.getElementById("etaText").innerText

        document.getElementById("download").innerHTML = ""

        setProgress(5)

        const form = new FormData()
        form.append("audio", audio)
        form.append("background", bg)
        form.append("video_format", selectedFormat)

        const response = await fetch(API_BASE + "/generate", {
            method: "POST",
            body: form
        })

        if (!response.ok) {
            const text = await response.text()
            throw new Error(text)
        }

        const data = await response.json()

        currentJobId = data.job_id

        document.getElementById("status").innerText =
            "Queued... Estimated time: " +
            document.getElementById("etaText").innerText

        setProgress(10)

        startFakeProgress()
        checkStatus()

    } catch (error) {
        clearInterval(progressTimer)

        document.getElementById("status").innerText =
            "Frontend/backend error: " + error.message

        console.error(error)
    }
}

async function checkStatus() {
    try {
        if (!currentJobId) return

        const response = await fetch(API_BASE + `/status/${currentJobId}`)

        if (!response.ok) {
            const text = await response.text()
            throw new Error(text)
        }

        const data = await response.json()

        if (data.status === "queued") {
            document.getElementById("status").innerText =
                "Queued... Estimated time: " +
                document.getElementById("etaText").innerText

            setTimeout(checkStatus, 2000)
        }

        else if (data.status === "transcribing") {
            document.getElementById("status").innerText =
                "AI is reading lyrics automatically..."

            setTimeout(checkStatus, 2000)
        }

        else if (data.status === "rendering") {
            document.getElementById("status").innerText =
                "Rendering cinematic lyric video..."

            setTimeout(checkStatus, 2000)
        }

        else if (data.status === "done") {
            stopProgressDone()

            document.getElementById("status").innerText =
                "Your video is ready!"

            document.getElementById("download").innerHTML =
                `<a href="${data.video_url}" target="_blank" download>
                    Download Video
                </a>`
        }

        else if (data.status === "error") {
            clearInterval(progressTimer)

            document.getElementById("status").innerText =
                "Render error: " + data.error
        }

        else {
            clearInterval(progressTimer)

            document.getElementById("status").innerText =
                "Unknown status: " + data.status
        }

    } catch (error) {
        clearInterval(progressTimer)

        document.getElementById("status").innerText =
            "Status check error: " + error.message

        console.error(error)
    }
}

updateEta()