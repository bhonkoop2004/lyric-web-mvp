let currentJobId = null
let fakeProgress = 0
let progressTimer = null
let selectedFormat = "youtube"
let selectedStyle = "classic"
let selectedPosition = "center"
let renderStartedAt = null

const API_BASE = window.location.origin

const audioInput = document.getElementById("audio")
const bgInput = document.getElementById("bg")

function updateEta() {
    const etaText = document.getElementById("etaText")

    if (selectedFormat === "youtube") {
        etaText.innerText = "1–3 minutes"
    }

    else if (selectedFormat === "square") {
        etaText.innerText = "2–4 minutes"
    }

    else if (selectedFormat === "tiktok") {
        etaText.innerText = "3–6 minutes"
    }
}

function selectStyle(style) {
    selectedStyle = style

    document.getElementById("style-minimal").classList.remove("active")
    document.getElementById("style-classic").classList.remove("active")
    document.getElementById("style-neon").classList.remove("active")
    document.getElementById("style-cinematic").classList.remove("active")
    document.getElementById("style-fire").classList.remove("active")
    document.getElementById("style-emerald").classList.remove("active")

    document.getElementById("style-" + style).classList.add("active")
}

function selectPosition(position) {
    selectedPosition = position

    document.getElementById("position-center").classList.remove("active")
    document.getElementById("position-bottom").classList.remove("active")

    document.getElementById("position-" + position).classList.add("active")
}

function getStyleValues() {
    if (selectedStyle === "minimal") {
        return {
            lyricColor: "white",
            fontStyle: "clean"
        }
    }

    if (selectedStyle === "neon") {
        return {
            lyricColor: "blue",
            fontStyle: "bold"
        }
    }

    if (selectedStyle === "cinematic") {
        return {
            lyricColor: "yellow",
            fontStyle: "cinematic"
        }
    }

    if (selectedStyle === "fire") {
        return {
            lyricColor: "yellow",
            fontStyle: "bold"
        }
    }

    if (selectedStyle === "emerald") {
        return {
            lyricColor: "green",
            fontStyle: "bold"
        }
    }

    return {
        lyricColor: "pink",
        fontStyle: "bold"
    }
}

function getEstimatedSeconds() {
    if (selectedFormat === "youtube") {
        return 150
    }

    if (selectedFormat === "square") {
        return 210
    }

    if (selectedFormat === "tiktok") {
        return 300
    }

    return 180
}

function formatTime(seconds) {
    seconds = Math.max(0, Math.ceil(seconds))

    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60

    if (minutes <= 0) {
        return remainingSeconds + "s left"
    }

    return minutes + "m " + remainingSeconds + "s left"
}

function getTimeLeftText() {
    if (!renderStartedAt) {
        return " · calculating..."
    }

    const elapsed = (Date.now() - renderStartedAt) / 1000
    const estimated = getEstimatedSeconds()
    const remaining = estimated - elapsed

    return " · " + formatTime(remaining)
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

    document.getElementById("progressBar").style.width =
        fakeProgress + "%"

    document.getElementById("progressText").innerText =
        Math.floor(fakeProgress) + "%" + getTimeLeftText()
}

function startFakeProgress() {
    clearInterval(progressTimer)

    renderStartedAt = Date.now()

    progressTimer = setInterval(() => {
        if (fakeProgress < 90) {
            fakeProgress += 0.5
        }

        else if (fakeProgress < 96) {
            fakeProgress += 0.1
        }

        setProgress(fakeProgress)
    }, 1000)
}

function stopProgressDone() {
    clearInterval(progressTimer)

    renderStartedAt = null
    fakeProgress = 100

    document.getElementById("progressBar").style.width = "100%"
    document.getElementById("progressText").innerText = "100% · ready"
}

async function generate() {
    try {
        const audio = audioInput.files[0]
        const bg = bgInput.files[0]

        if (!audio || !bg) {
            alert("Please upload both an MP3 and a background image first.")
            return
        }

        const styleValues = getStyleValues()

        const lyricsText =
            document.getElementById("lyricsInput").value

        document.getElementById("status").innerText =
            "Uploading files... Estimated time: " +
            document.getElementById("etaText").innerText

        document.getElementById("download").innerHTML = ""

        renderStartedAt = null

        setProgress(5)

        const form = new FormData()

        form.append("audio", audio)
        form.append("background", bg)
        form.append("video_format", selectedFormat)
        form.append("lyric_color", styleValues.lyricColor)
        form.append("font_style", styleValues.fontStyle)
        form.append("style", selectedStyle)
        form.append("text_position", selectedPosition)

        form.append(
            "lyrics_text",
            lyricsText
        )

        const response = await fetch(
            API_BASE + "/generate",
            {
                method: "POST",
                body: form
            }
        )

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
    }

    catch (error) {
        clearInterval(progressTimer)

        renderStartedAt = null

        document.getElementById("status").innerText =
            "Frontend/backend error: " + error.message

        console.error(error)
    }
}

async function checkStatus() {
    try {
        if (!currentJobId) return

        const response = await fetch(
            API_BASE + `/status/${currentJobId}`
        )

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
                "Preparing synced lyric video..."

            setTimeout(checkStatus, 2000)
        }

        else if (data.status === "rendering") {
            document.getElementById("status").innerText =
                "Rendering Spotify-style lyric video..."

            setTimeout(checkStatus, 2000)
        }

        else if (data.status === "done") {
            stopProgressDone()

            document.getElementById("status").innerText =
                "Your video is ready!"

            document.getElementById("download").innerHTML =
                `<a
                    href="${data.video_url}"
                    target="_blank"
                    download
                    onclick="fetch('/track-download')"
                >
                    Download Video
                </a>`
        }

        else if (data.status === "error") {
            clearInterval(progressTimer)

            renderStartedAt = null

            document.getElementById("status").innerText =
                "Render error: " + data.error
        }

        else {
            clearInterval(progressTimer)

            renderStartedAt = null

            document.getElementById("status").innerText =
                "Unknown status: " + data.status
        }
    }

    catch (error) {
        clearInterval(progressTimer)

        renderStartedAt = null

        document.getElementById("status").innerText =
            "Status check error: " + error.message

        console.error(error)
    }
}

updateEta()