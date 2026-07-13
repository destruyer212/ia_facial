/**
 * Escaneo facial en vivo para registro.
 * Requiere window.__mpVision (cargado desde index.html).
 */
(function registerScannerBootstrap() {
  const REGISTER_SCAN_STEPS = [
    {
      id: "front",
      field: "front",
      label: "Frontal",
      prompt: "Mira de frente al centro del circulo",
      speech: "Mira de frente al centro del circulo.",
      matchYaw: (yaw) => Math.abs(yaw) <= 0.14,
    },
    {
      id: "left",
      field: "left",
      label: "Giro izquierda",
      prompt: "Gira la cabeza hacia tu izquierda",
      speech: "Gira la cabeza hacia tu izquierda.",
      matchYaw: (yaw) => yaw <= -0.08,
    },
    {
      id: "right",
      field: "right",
      label: "Giro derecha",
      prompt: "Gira la cabeza hacia tu derecha",
      speech: "Gira la cabeza hacia tu derecha.",
      matchYaw: (yaw) => yaw >= 0.08,
    },
  ];

  const SCAN_TUNING = {
    requiredStableFrames: 4,
    centerToleranceRatio: 0.17,
    minFaceSizeRatio: 0.18,
    maxFaceSizeRatio: 0.72,
    mirrorWebcam: true,
  };

  const MESH_POINT_COLOR = "#38bdf8";
  const MESH_GLOW_COLOR = "rgba(56, 189, 248, 0.45)";

  const LEFT_EYE_INDICES = [33, 160, 158, 133, 153, 144];
  const RIGHT_EYE_INDICES = [362, 385, 387, 263, 373, 380];

  const BLINK_LIVE_TUNING = {
    earOpenMin: 0.19,
    earClosedMax: 0.24,
    earDropMin: 0.035,
    openFramesRequired: 5,
    timeoutMs: 14000,
  };

  let sharedLandmarker = null;
  let sharedLandmarkerPromise = null;

  async function loadSharedLandmarker() {
    if (sharedLandmarker) return sharedLandmarker;
    if (!sharedLandmarkerPromise) {
      sharedLandmarkerPromise = (async () => {
        const mp = await import(
          "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/+esm",
        );
        const vision = await mp.FilesetResolver.forVisionTasks(
          "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm",
        );
        sharedLandmarker = await mp.FaceLandmarker.createFromOptions(vision, {
          baseOptions: {
            modelAssetPath:
              "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task",
            delegate: "CPU",
          },
          runningMode: "VIDEO",
          numFaces: 1,
        });
        return sharedLandmarker;
      })();
    }
    return sharedLandmarkerPromise;
  }

  function drawFaceMesh(ctx, landmarks, width, height) {
    for (const point of landmarks) {
      const x = point.x * width;
      const y = point.y * height;
      ctx.beginPath();
      ctx.fillStyle = MESH_GLOW_COLOR;
      ctx.arc(x, y, 3.2, 0, Math.PI * 2);
      ctx.fill();
      ctx.beginPath();
      ctx.fillStyle = MESH_POINT_COLOR;
      ctx.arc(x, y, 1.6, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  function eyeAspectRatio(landmarks, eyeIndices) {
    const pt = (idx) => landmarks[idx];
    const dist = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);
    const verticalA = dist(pt(eyeIndices[1]), pt(eyeIndices[5]));
    const verticalB = dist(pt(eyeIndices[2]), pt(eyeIndices[4]));
    const horizontal = dist(pt(eyeIndices[0]), pt(eyeIndices[3]));
    if (horizontal <= 0) return 0;
    return (verticalA + verticalB) / (2 * horizontal);
  }

  function computeEarAvg(landmarks) {
    const left = eyeAspectRatio(landmarks, LEFT_EYE_INDICES);
    const right = eyeAspectRatio(landmarks, RIGHT_EYE_INDICES);
    return (left + right) / 2;
  }

  /**
   * Espera un parpadeo real (ojos cerrados) con MediaPipe y captura en ese instante.
   */
  async function captureBlinkOnLiveClose({ video, captureFrame, onStatus }) {
    const landmarker = await loadSharedLandmarker();
    if (!video?.videoWidth) {
      throw new Error("La camara no esta lista para detectar parpadeo.");
    }
    if (typeof captureFrame !== "function") {
      throw new Error("No hay funcion de captura para el paso de parpadeo.");
    }

    let baselineEar = 0;
    let openFrames = 0;
    const started = performance.now();

    return new Promise((resolve, reject) => {
      let settled = false;

      const finish = (fn) => {
        if (settled) return;
        settled = true;
        fn();
      };

      const tick = () => {
        if (settled) return;

        if (performance.now() - started > BLINK_LIVE_TUNING.timeoutMs) {
          finish(() => {
            reject(
              new Error(
                "No se detecto parpadeo a tiempo. Mira de frente y parpadea de forma natural.",
              ),
            );
          });
          return;
        }

        let landmarks;
        try {
          landmarks = landmarker.detectForVideo(video, performance.now()).faceLandmarks?.[0];
        } catch {
          requestAnimationFrame(tick);
          return;
        }

        if (!landmarks?.length) {
          onStatus?.("Centra tu rostro en la camara...");
          openFrames = 0;
          baselineEar = 0;
          requestAnimationFrame(tick);
          return;
        }

        const ear = computeEarAvg(landmarks);

        if (openFrames < BLINK_LIVE_TUNING.openFramesRequired) {
          if (ear >= BLINK_LIVE_TUNING.earOpenMin) {
            openFrames += 1;
            baselineEar =
              baselineEar === 0 ? ear : Math.max(baselineEar, ear * 0.35 + baselineEar * 0.65);
            onStatus?.("Listo — parpadea de forma natural");
          } else {
            openFrames = Math.max(0, openFrames - 1);
            onStatus?.("Abre los ojos y mira a la camara");
          }
          requestAnimationFrame(tick);
          return;
        }

        const earDrop = baselineEar - ear;
        const eyesClosed =
          ear <= BLINK_LIVE_TUNING.earClosedMax || earDrop >= BLINK_LIVE_TUNING.earDropMin;

        if (!eyesClosed) {
          onStatus?.("Te estamos mirando — parpadea cuando quieras");
          if (ear > baselineEar * 0.92) {
            baselineEar = ear * 0.25 + baselineEar * 0.75;
          }
          requestAnimationFrame(tick);
          return;
        }

        onStatus?.("Parpadeo detectado — capturando...");
        captureFrame()
          .then((blob) => {
            if (!blob) {
              finish(() => reject(new Error("No se pudo capturar el parpadeo.")));
              return;
            }
            finish(() => resolve(blob));
          })
          .catch((error) => {
            finish(() => reject(error));
          });
      };

      onStatus?.("Detectando parpadeo en vivo...");
      requestAnimationFrame(tick);
    });
  }

  class FaceMeshOverlay {
    constructor(video, canvas) {
      this.video = video;
      this.canvas = canvas;
      this.landmarker = null;
      this.running = false;
      this.rafId = null;
      this.ready = false;
    }

    async start() {
      if (this.running) return true;
      try {
        this.landmarker = await loadSharedLandmarker();
        this.ready = true;
      } catch (error) {
        console.warn("MediaPipe no disponible en escaneo de asistencia:", error);
        this.ready = false;
        return false;
      }
      this.running = true;
      this.loop();
      return true;
    }

    stop() {
      this.running = false;
      this.ready = false;
      if (this.rafId) {
        cancelAnimationFrame(this.rafId);
        this.rafId = null;
      }
      const ctx = this.canvas?.getContext("2d");
      if (ctx && this.canvas) {
        ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
      }
    }

    loop() {
      if (!this.running) return;
      this.rafId = requestAnimationFrame(() => this.tick());
    }

    tick() {
      if (!this.running || !this.landmarker || !this.video?.videoWidth) {
        this.loop();
        return;
      }
      const width = this.video.videoWidth;
      const height = this.video.videoHeight;
      this.canvas.width = width;
      this.canvas.height = height;
      const results = this.landmarker.detectForVideo(this.video, performance.now());
      const ctx = this.canvas.getContext("2d");
      ctx.clearRect(0, 0, width, height);
      const landmarks = results.faceLandmarks?.[0];
      if (landmarks?.length) {
        drawFaceMesh(ctx, landmarks, width, height);
      }
      this.loop();
    }
  }

  function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  class RegisterFaceScanner {
    constructor(options = {}) {
      this.video = options.video;
      this.canvas = options.canvas;
      this.circleEl = options.circleEl;
      this.stepLabelEl = options.stepLabelEl;
      this.hintEl = options.hintEl;
      this.progressEl = options.progressEl;
      this.onSpeak = options.onSpeak || (() => {});
      this.onStepCaptured = options.onStepCaptured || (() => {});
      this.onComplete = options.onComplete || (() => {});
      this.onStatus = options.onStatus || (() => {});

      this.stream = null;
      this.landmarker = null;
      this.running = false;
      this.rafId = null;
      this.captures = {};
      this.stepIndex = 0;
      this.stableFrames = 0;
      this.requiredStableFrames = SCAN_TUNING.requiredStableFrames;
      this.capturing = false;
      this.fallbackMode = false;
      this.apiBase = options.apiBase || "";
      this.orgCode = options.orgCode || "";
      this.authToken = options.authToken || "";
    }

    get isComplete() {
      return REGISTER_SCAN_STEPS.every((step) => this.captures[step.field]);
    }

    async start() {
      if (this.running) return;
      this.captures = {};
      this.stepIndex = 0;
      this.stableFrames = 0;
      this.onStatus("loading", "Preparando escaneo...", "Solicitando camara y modelos de IA");

      await this.startCamera();
      await this.beginPoseScan();
    }

    async beginPoseScan() {
      if (this.running) return;

      try {
        this.onStatus("loading", "Cargando IA...", "Descargando MediaPipe (primera vez tarda unos segundos)");
        await this.ensureLandmarker();
      } catch (error) {
        console.warn("MediaPipe no disponible, usando modo compatible:", error);
        this.fallbackMode = true;
        this.onStatus(
          "scanning",
          "Modo compatible",
          "Sin puntos azules: usando deteccion del servidor. Centra tu rostro en el circulo.",
        );
      }

      this.running = true;
      this.renderProgress();
      const step = this.currentStep();
      this.onStatus("scanning", "Escaneo iniciado", step.prompt);
      this.onSpeak(step.speech);

      if (this.fallbackMode) {
        this.fallbackLoop();
        return;
      }
      this.loop();
    }

    stop() {
      this.running = false;
      if (this.rafId) {
        cancelAnimationFrame(this.rafId);
        this.rafId = null;
      }
      if (this.stream) {
        this.stream.getTracks().forEach((track) => track.stop());
        this.stream = null;
      }
      if (this.video) {
        this.video.srcObject = null;
      }
      const ctx = this.canvas?.getContext("2d");
      if (ctx && this.canvas) {
        ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
      }
      this.circleEl?.classList.remove("aligned", "scanning");
    }

    currentStep() {
      return REGISTER_SCAN_STEPS[this.stepIndex] || REGISTER_SCAN_STEPS[0];
    }

    async ensureLandmarker() {
      if (this.landmarker) return;
      this.landmarker = await loadSharedLandmarker();
    }

    async startCamera() {
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error("Este navegador no permite acceso a la camara.");
      }
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: "user",
          width: { ideal: 1280, min: 640 },
          height: { ideal: 720, min: 480 },
        },
        audio: false,
      });
      this.stream = stream;
      this.video.srcObject = stream;
      await new Promise((resolve) => {
        if (this.video.readyState >= 2 && this.video.videoWidth > 0) {
          resolve();
          return;
        }
        this.video.addEventListener("loadeddata", resolve, { once: true });
        window.setTimeout(resolve, 3000);
      });
      await sleep(400);
      if (!this.video.videoWidth) {
        throw new Error("La camara no respondio. Revisa permisos del navegador.");
      }
    }

    loop() {
      if (!this.running) return;
      this.rafId = requestAnimationFrame(() => this.tick());
    }

    tick() {
      if (!this.running || !this.landmarker || !this.video?.videoWidth) {
        this.loop();
        return;
      }

      const width = this.video.videoWidth;
      const height = this.video.videoHeight;
      this.canvas.width = width;
      this.canvas.height = height;

      const results = this.landmarker.detectForVideo(this.video, performance.now());
      const ctx = this.canvas.getContext("2d");
      ctx.clearRect(0, 0, width, height);

      const landmarks = results.faceLandmarks?.[0];
      if (!landmarks?.length) {
        this.stableFrames = 0;
        this.circleEl?.classList.remove("aligned");
        this.updateHint("Coloca tu rostro dentro del circulo");
        this.loop();
        return;
      }

      const metrics = this.computeMetrics(landmarks, width, height);
      this.drawMesh(ctx, landmarks, width, height);
      this.evaluatePose(metrics);
      this.loop();
    }

    async fallbackLoop() {
      while (this.running) {
        const width = this.video.videoWidth;
        const height = this.video.videoHeight;
        if (!width || !height) {
          await sleep(200);
          continue;
        }
        this.canvas.width = width;
        this.canvas.height = height;
        const ctx = this.canvas.getContext("2d");
        ctx.clearRect(0, 0, width, height);
        ctx.drawImage(this.video, 0, 0, width, height);

        const metrics = await this.detectFaceViaApi(width, height);
        if (!metrics) {
          this.stableFrames = 0;
          this.circleEl?.classList.remove("aligned");
          this.updateHint("Coloca tu rostro dentro del circulo");
          await sleep(350);
          continue;
        }

        this.drawFallbackBox(ctx, metrics);
        this.evaluatePose(metrics);
        await sleep(350);
      }
    }

    async detectFaceViaApi(width, height) {
      if (!this.apiBase) return null;
      const blob = await this.grabFrameBlob();
      if (!blob) return null;
      const form = new FormData();
      form.append("file", blob, "detect.jpg");
      try {
        const headers = {};
        if (this.orgCode) headers["X-Org-Code"] = this.orgCode;
        if (this.authToken) headers.Authorization = `Bearer ${this.authToken}`;
        const response = await fetch(`${this.apiBase}/api/v1/faces/detect`, {
          method: "POST",
          headers,
          body: form,
        });
        if (!response.ok) return null;
        const data = await response.json();
        if (!data.face_count || !data.faces?.length) return null;
        const face = data.faces[0];
        let centerX = face.x + face.width / 2;
        const centerY = face.y + face.height / 2;
        centerX = this.mirrorX(centerX, width);
        return {
          centerX,
          centerY,
          faceWidth: face.width,
          faceHeight: face.height,
          yaw: 0,
          frameCenterX: width / 2,
          frameCenterY: height / 2,
          frameSize: Math.min(width, height),
        };
      } catch {
        return null;
      }
    }

    drawFallbackBox(ctx, metrics) {
      const x = metrics.centerX - metrics.faceWidth / 2;
      const y = metrics.centerY - metrics.faceHeight / 2;
      ctx.strokeStyle = MESH_POINT_COLOR;
      ctx.lineWidth = 2;
      ctx.strokeRect(x, y, metrics.faceWidth, metrics.faceHeight);
    }

    evaluatePose(metrics) {
      const step = this.currentStep();
      const aligned = this.isFaceAligned(metrics);
      const poseOk = this.fallbackMode || step.matchYaw(metrics.yaw);

      this.circleEl?.classList.toggle("aligned", aligned && poseOk);
      this.circleEl?.classList.add("scanning");

      if (aligned && poseOk) {
        this.stableFrames += 1;
        if (this.stableFrames >= this.requiredStableFrames && !this.capturing) {
          this.updateHint("Capturando...");
          this.captureCurrentStep().catch((error) => {
            this.capturing = false;
            this.onStatus("error", "Error al capturar", error.message);
          });
        }
      } else {
        this.stableFrames = 0;
        this.updateHint(aligned ? step.prompt : "Centra tu rostro en el circulo");
      }

      if (this.stepLabelEl) {
        this.stepLabelEl.textContent = `Paso ${this.stepIndex + 1}/${REGISTER_SCAN_STEPS.length}: ${step.label}`;
      }
    }

    computeMetrics(landmarks, width, height) {
      const xs = landmarks.map((p) => p.x * width);
      const ys = landmarks.map((p) => p.y * height);
      const minX = Math.min(...xs);
      const maxX = Math.max(...xs);
      const minY = Math.min(...ys);
      const maxY = Math.max(...ys);
      const centerX = this.mirrorX((minX + maxX) / 2, width);
      const centerY = (minY + maxY) / 2;
      const faceWidth = maxX - minX;

      const leftCheek = landmarks[234];
      const rightCheek = landmarks[454];
      const nose = landmarks[1];
      const leftDist = Math.abs(nose.x - leftCheek.x);
      const rightDist = Math.abs(rightCheek.x - nose.x);
      const yaw = (rightDist - leftDist) / Math.max(leftDist + rightDist, 0.0001);

      return {
        centerX,
        centerY,
        faceWidth,
        faceHeight: maxY - minY,
        yaw,
        frameCenterX: width / 2,
        frameCenterY: height / 2,
        frameSize: Math.min(width, height),
      };
    }

    isFaceAligned(metrics) {
      const dx = Math.abs(metrics.centerX - metrics.frameCenterX);
      const dy = Math.abs(metrics.centerY - metrics.frameCenterY);
      const centerTolerance = metrics.frameSize * SCAN_TUNING.centerToleranceRatio;
      const sizeRatio = metrics.faceWidth / metrics.frameSize;
      return (
        dx <= centerTolerance &&
        dy <= centerTolerance &&
        sizeRatio >= SCAN_TUNING.minFaceSizeRatio &&
        sizeRatio <= SCAN_TUNING.maxFaceSizeRatio
      );
    }

    mirrorX(x, width) {
      return SCAN_TUNING.mirrorWebcam ? width - x : x;
    }

    drawMesh(ctx, landmarks, width, height) {
      drawFaceMesh(ctx, landmarks, width, height);
    }

    async captureCurrentStep() {
      if (this.capturing) return;
      this.capturing = true;
      const step = this.currentStep();
      const blob = await this.grabFrameBlob();
      if (!blob) {
        this.capturing = false;
        throw new Error("No se pudo capturar la imagen de la camara.");
      }
      this.captures[step.field] = blob;
      this.stableFrames = 0;
      this.onStepCaptured(step, blob);
      this.renderProgress();

      if (this.stepIndex < REGISTER_SCAN_STEPS.length - 1) {
        this.stepIndex += 1;
        this.capturing = false;
        const next = this.currentStep();
        this.onStatus("scanning", `Captura ${step.label} lista`, next.prompt);
        this.onSpeak(`${step.label} capturado. ${next.speech}`);
        return;
      }

      this.running = false;
      this.capturing = false;
      this.circleEl?.classList.remove("scanning");
      this.onStatus("success", "Escaneo completo", "Las 3 poses fueron capturadas. Guardando perfil...");
      this.onSpeak("Escaneo completo. Guardando tu perfil facial.");
      Promise.resolve(this.onComplete(this.captures)).catch((error) => {
        const message = error?.message || "No se pudo guardar el perfil.";
        this.onStatus("error", "Error al guardar", message);
      });
    }

    async grabFrameBlob() {
      const temp = document.createElement("canvas");
      temp.width = this.video.videoWidth;
      temp.height = this.video.videoHeight;
      const ctx = temp.getContext("2d");
      if (SCAN_TUNING.mirrorWebcam) {
        ctx.translate(temp.width, 0);
        ctx.scale(-1, 1);
      }
      ctx.drawImage(this.video, 0, 0, temp.width, temp.height);
      return new Promise((resolve) => {
        temp.toBlob((blob) => resolve(blob), "image/jpeg", 0.92);
      });
    }

    renderProgress() {
      if (!this.progressEl) return;
      this.progressEl.innerHTML = REGISTER_SCAN_STEPS.map((step) => {
        const done = Boolean(this.captures[step.field]);
        const active = this.currentStep().id === step.id && this.running;
        return `<span class="register-scan-chip${done ? " done" : ""}${active ? " active" : ""}">${step.label}</span>`;
      }).join("");
    }

    updateHint(text) {
      if (this.hintEl) this.hintEl.textContent = text;
    }

    applyCapturesToForm(formEl) {
      for (const step of REGISTER_SCAN_STEPS) {
        const blob = this.captures[step.field];
        const input = formEl.querySelector(`input[name="${step.field}"]`);
        if (!blob || !input) continue;
        const file = new File([blob], `${step.field}.jpg`, { type: "image/jpeg" });
        const transfer = new DataTransfer();
        transfer.items.add(file);
        input.files = transfer.files;
      }
    }
  }

  async function captureBlinkBurstPickClosed(video, captureFrame, count = 8, intervalMs = 110) {
    const landmarker = await loadSharedLandmarker();
    let bestBlob = null;
    let lowestEar = Infinity;

    for (let index = 0; index < count; index += 1) {
      let ear = 1;
      try {
        const landmarks = landmarker.detectForVideo(video, performance.now()).faceLandmarks?.[0];
        if (landmarks?.length) {
          ear = computeEarAvg(landmarks);
        }
      } catch {
        // continuar
      }
      const blob = await captureFrame();
      if (blob && ear <= lowestEar) {
        lowestEar = ear;
        bestBlob = blob;
      }
      if (index < count - 1) {
        await sleep(intervalMs);
      }
    }

    return bestBlob || captureFrame();
  }

  window.RegisterFaceScanner = RegisterFaceScanner;
  window.FaceMeshOverlay = FaceMeshOverlay;
  window.captureBlinkOnLiveClose = captureBlinkOnLiveClose;
  window.captureBlinkBurstPickClosed = captureBlinkBurstPickClosed;
  window.REGISTER_SCAN_STEPS = REGISTER_SCAN_STEPS;
  window.registerScannerLoadError = null;

  window.isRegisterScannerReady = function isRegisterScannerReady() {
    return Boolean(window.RegisterFaceScanner);
  };

  // Si app.js esta en cache, el boton no debe fallar en silencio.
  window.startRegisterFaceScan = function startRegisterFaceScanBootstrap() {
    if (typeof window.__startRegisterFaceScanReady === "function") {
      return window.__startRegisterFaceScanReady();
    }
    const msg =
      "JavaScript desactualizado (cache del navegador). Pulsa Ctrl+Shift+R o cierra la pestaña y vuelve a abrir http://127.0.0.1:5500/";
    console.error("[IA Facial]", msg);
    window.alert(msg);
  };
})();
