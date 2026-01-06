import React, { useState, useRef, useCallback } from "react";
import { AppLayout } from "../components/layout/AppLayout";
import { Card, Button } from "../components/ui";

// Lake data for display
const LAKE_DATA = {
  name: "Lake Chembarambakkam",
  temperature: 28.5,
  ph: 7.2,
  turbidity: 4.8,
  dissolvedOxygen: 8.2,
  location: "Chennai, Tamil Nadu",
};

const CallStatus = {
  IDLE: "idle",
  CONNECTING: "connecting",
  ACTIVE: "active",
  ENDED: "ended",
  ERROR: "error",
};

// Audio utility functions
function decode(base64) {
  const binaryString = atob(base64);
  const len = binaryString.length;
  const bytes = new Uint8Array(len);
  for (let i = 0; i < len; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }
  return bytes;
}

function encode(bytes) {
  let binary = "";
  const len = bytes.byteLength;
  for (let i = 0; i < len; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

function decodeAudioData(data, ctx, sampleRate, numChannels) {
  const dataInt16 = new Int16Array(data.buffer);
  const frameCount = dataInt16.length / numChannels;
  const buffer = ctx.createBuffer(numChannels, frameCount, sampleRate);

  for (let channel = 0; channel < numChannels; channel++) {
    const channelData = buffer.getChannelData(channel);
    for (let i = 0; i < frameCount; i++) {
      channelData[i] = dataInt16[i * numChannels + channel] / 32768.0;
    }
  }
  return buffer;
}

function createPcmBlob(data) {
  const l = data.length;
  const int16 = new Int16Array(l);
  for (let i = 0; i < l; i++) {
    int16[i] = data[i] * 32768;
  }
  return {
    data: encode(new Uint8Array(int16.buffer)),
    mimeType: "audio/pcm;rate=16000",
  };
}

export const VoiceAgent = () => {
  const [status, setStatus] = useState(CallStatus.IDLE);
  const [transcriptions, setTranscriptions] = useState([]);
  const [isMuted, setIsMuted] = useState(false);
  const [isModelSpeaking, setIsModelSpeaking] = useState(false);
  const [error, setError] = useState("");

  const sessionRef = useRef(null);
  const inputAudioCtxRef = useRef(null);
  const outputAudioCtxRef = useRef(null);
  const nextStartTimeRef = useRef(0);
  const sourcesRef = useRef(new Set());
  const isMutedRef = useRef(false);

  // Keep isMutedRef in sync
  isMutedRef.current = isMuted;

  const cleanupCall = useCallback(() => {
    if (sessionRef.current) {
      sessionRef.current.close();
      sessionRef.current = null;
    }
    sourcesRef.current.forEach((source) => {
      try {
        source.stop();
      } catch (e) {}
    });
    sourcesRef.current.clear();

    if (inputAudioCtxRef.current) {
      inputAudioCtxRef.current.close().catch(() => {});
      inputAudioCtxRef.current = null;
    }
    if (outputAudioCtxRef.current) {
      outputAudioCtxRef.current.close().catch(() => {});
      outputAudioCtxRef.current = null;
    }

    setTranscriptions([]);
    nextStartTimeRef.current = 0;
    setStatus(CallStatus.ENDED);
    setIsModelSpeaking(false);
    setTimeout(() => setStatus(CallStatus.IDLE), 1000);
  }, []);

  const startCall = async () => {
    try {
      setStatus(CallStatus.CONNECTING);
      setError("");

      // Dynamic import of Google GenAI
      const { GoogleGenAI, Modality } = await import("@google/genai");
      const apiKey = import.meta.env.VITE_GEMINI_API_KEY;

      if (!apiKey) {
        setError(
          "VITE_GEMINI_API_KEY not configured. Add it to frontend-react/.env"
        );
        setStatus(CallStatus.ERROR);
        return;
      }

      const ai = new GoogleGenAI({ apiKey });

      const inputCtx = new AudioContext({ sampleRate: 16000 });
      const outputCtx = new AudioContext({ sampleRate: 24000 });
      inputAudioCtxRef.current = inputCtx;
      outputAudioCtxRef.current = outputCtx;

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      const systemInstruction = `
You are Vignesh, a friendly, professional Lake Analysis Agent based in Chennai.
You speak with a warm Indian accent. You are polite, humble, and helpful.

CONTEXT (Lake Chembarambakkam Statistics):
- Temperature: ${LAKE_DATA.temperature}°C (Optimal for tropical lakes)
- pH Level: ${LAKE_DATA.ph} (Neutral and very healthy)
- Turbidity: ${LAKE_DATA.turbidity} NTU (Clear water, good visibility)
- Dissolved Oxygen (DO): ${LAKE_DATA.dissolvedOxygen} mg/L (Excellent aeration)

YOUR PERSONA:
1. Default: English with a clear Indian accent.
2. If the user speaks Tamil, respond in Tamil or Chennai Tanglish.
3. Use friendly Chennai terms like "Boss", "Nanba", "Semma".
4. Be human-like with natural pauses.
5. Be proud of the lake's current health!

BEHAVIOR:
- This is a live voice call. Be concise but conversational.
- Respond warmly and helpfully to questions about the lake.
`;

      const session = await ai.live.connect({
        model: "gemini-2.5-flash-native-audio-preview-09-2025",
        config: {
          responseModalities: [Modality.AUDIO],
          speechConfig: {
            voiceConfig: { prebuiltVoiceConfig: { voiceName: "Fenrir" } },
          },
          systemInstruction,
          inputAudioTranscription: {},
          outputAudioTranscription: {},
        },
        callbacks: {
          onopen: () => {
            setStatus(CallStatus.ACTIVE);
            const source = inputCtx.createMediaStreamSource(stream);
            const scriptProcessor = inputCtx.createScriptProcessor(4096, 1, 1);

            scriptProcessor.onaudioprocess = (e) => {
              if (isMutedRef.current) return;
              const inputData = e.inputBuffer.getChannelData(0);
              const pcmBlob = createPcmBlob(inputData);
              if (sessionRef.current) {
                sessionRef.current.sendRealtimeInput({ media: pcmBlob });
              }
            };

            source.connect(scriptProcessor);
            scriptProcessor.connect(inputCtx.destination);
          },
          onmessage: async (message) => {
            const base64Audio =
              message.serverContent?.modelTurn?.parts[0]?.inlineData?.data;
            if (base64Audio && outputCtx) {
              setIsModelSpeaking(true);
              const audioBytes = decode(base64Audio);
              const buffer = decodeAudioData(audioBytes, outputCtx, 24000, 1);
              const audioSource = outputCtx.createBufferSource();
              audioSource.buffer = buffer;
              audioSource.connect(outputCtx.destination);

              nextStartTimeRef.current = Math.max(
                nextStartTimeRef.current,
                outputCtx.currentTime
              );
              audioSource.start(nextStartTimeRef.current);
              nextStartTimeRef.current += buffer.duration;
              sourcesRef.current.add(audioSource);
              audioSource.onended = () => {
                sourcesRef.current.delete(audioSource);
                if (sourcesRef.current.size === 0) setIsModelSpeaking(false);
              };
            }

            if (message.serverContent?.interrupted) {
              sourcesRef.current.forEach((s) => {
                try {
                  s.stop();
                } catch (e) {}
              });
              sourcesRef.current.clear();
              nextStartTimeRef.current = 0;
              setIsModelSpeaking(false);
            }

            if (message.serverContent?.inputTranscription) {
              const text = message.serverContent.inputTranscription.text;
              if (text) {
                setTranscriptions((prev) => [
                  ...prev.slice(-19),
                  { role: "user", text, time: Date.now() },
                ]);
              }
            }
            if (message.serverContent?.outputTranscription) {
              const text = message.serverContent.outputTranscription.text;
              if (text) {
                setTranscriptions((prev) => [
                  ...prev.slice(-19),
                  { role: "model", text, time: Date.now() },
                ]);
              }
            }
          },
          onerror: (e) => {
            console.error("Gemini Live Error:", e);
            setError("Connection error. Please try again.");
            setStatus(CallStatus.ERROR);
            cleanupCall();
          },
          onclose: () => {
            cleanupCall();
          },
        },
      });

      sessionRef.current = session;
    } catch (err) {
      console.error("Failed to start call:", err);
      setError(err.message || "Failed to connect");
      setStatus(CallStatus.ERROR);
    }
  };

  return (
    <AppLayout title="Voice Agent">
      <div
        style={{
          display: "flex",
          gap: "var(--space-lg)",
          height: "calc(100vh - 160px)",
        }}
      >
        {/* Main Call Area */}
        <Card
          style={{
            flex: 2,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            textAlign: "center",
            padding: "var(--space-xl)",
          }}
        >
          {status === CallStatus.ACTIVE ? (
            <>
              <div
                style={{
                  width: 160,
                  height: 160,
                  borderRadius: "50%",
                  background: isModelSpeaking
                    ? "linear-gradient(135deg, var(--primary), #60a5fa)"
                    : "var(--bg-surface)",
                  border: "4px solid var(--border-color)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  marginBottom: 24,
                  transition: "all 0.3s",
                  boxShadow: isModelSpeaking
                    ? "0 0 60px rgba(59, 130, 246, 0.5)"
                    : "none",
                }}
              >
                <span style={{ fontSize: 56 }}>🎙️</span>
              </div>
              <h2
                style={{
                  fontSize: "1.75rem",
                  fontWeight: 700,
                  marginBottom: 8,
                  color: "var(--text-main)",
                }}
              >
                Agent
              </h2>
              <p style={{ color: "var(--text-muted)", marginBottom: 32 }}>
                SLIM Support Lead •{" "}
                {isModelSpeaking ? "🔊 Speaking..." : "🎧 Listening..."}
              </p>

              <div style={{ display: "flex", gap: 16 }}>
                <Button
                  variant={isMuted ? "primary" : "secondary"}
                  onClick={() => setIsMuted(!isMuted)}
                >
                  {isMuted ? "🔇 Unmute" : "🎤 Mute"}
                </Button>
                <Button
                  variant="ghost"
                  onClick={cleanupCall}
                  style={{ background: "#ef4444", color: "#fff" }}
                >
                  📞 End Call
                </Button>
              </div>
            </>
          ) : (
            <>
              <div
                style={{
                  width: 100,
                  height: 100,
                  borderRadius: 24,
                  background: "var(--primary)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  marginBottom: 24,
                }}
              >
                <span style={{ fontSize: 48 }}>💧</span>
              </div>
              <h2
                style={{
                  fontSize: "1.75rem",
                  fontWeight: 700,
                  marginBottom: 8,
                  color: "var(--text-main)",
                }}
              >
                SLIM Voice Agent
              </h2>
              <p
                style={{
                  color: "var(--text-muted)",
                  maxWidth: 400,
                  marginBottom: 32,
                }}
              >
                Speak with our agent, our AI lake analyst. Ask questions about
                Lake Chembarambakkam's health in English or Tamil!
              </p>

              {error && (
                <p style={{ color: "#ef4444", marginBottom: 16 }}>{error}</p>
              )}

              {status === CallStatus.IDLE || status === CallStatus.ENDED ? (
                <Button
                  variant="primary"
                  onClick={startCall}
                  style={{ padding: "16px 32px", fontSize: "1.1rem" }}
                >
                  📞 Start Call with Agent
                </Button>
              ) : status === CallStatus.CONNECTING ? (
                <p style={{ color: "var(--primary)" }}>🔄 Connecting...</p>
              ) : (
                <Button
                  variant="primary"
                  onClick={startCall}
                  style={{ padding: "16px 32px" }}
                >
                  🔄 Try Again
                </Button>
              )}
            </>
          )}
        </Card>

        {/* Stats & Transcript */}
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            gap: "var(--space-lg)",
            minWidth: 300,
          }}
        >
          {/* Lake Stats */}
          <Card style={{ padding: "var(--space-lg)" }}>
            <h3
              style={{
                fontSize: "1rem",
                fontWeight: 600,
                marginBottom: 16,
                color: "var(--text-main)",
              }}
            >
              Lake Chembarambakkam
            </h3>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: 12,
              }}
            >
              <div
                style={{
                  padding: 12,
                  borderRadius: 8,
                  background: "var(--bg-surface)",
                  border: "1px solid var(--border-color)",
                }}
              >
                <div
                  style={{
                    fontSize: "0.7rem",
                    color: "var(--text-muted)",
                    marginBottom: 4,
                  }}
                >
                  Temperature
                </div>
                <div style={{ fontWeight: 600, color: "#f59e0b" }}>
                  {LAKE_DATA.temperature}°C
                </div>
              </div>
              <div
                style={{
                  padding: 12,
                  borderRadius: 8,
                  background: "var(--bg-surface)",
                  border: "1px solid var(--border-color)",
                }}
              >
                <div
                  style={{
                    fontSize: "0.7rem",
                    color: "var(--text-muted)",
                    marginBottom: 4,
                  }}
                >
                  pH Level
                </div>
                <div style={{ fontWeight: 600, color: "#22c55e" }}>
                  {LAKE_DATA.ph}
                </div>
              </div>
              <div
                style={{
                  padding: 12,
                  borderRadius: 8,
                  background: "var(--bg-surface)",
                  border: "1px solid var(--border-color)",
                }}
              >
                <div
                  style={{
                    fontSize: "0.7rem",
                    color: "var(--text-muted)",
                    marginBottom: 4,
                  }}
                >
                  Turbidity
                </div>
                <div style={{ fontWeight: 600, color: "var(--primary)" }}>
                  {LAKE_DATA.turbidity} NTU
                </div>
              </div>
              <div
                style={{
                  padding: 12,
                  borderRadius: 8,
                  background: "var(--bg-surface)",
                  border: "1px solid var(--border-color)",
                }}
              >
                <div
                  style={{
                    fontSize: "0.7rem",
                    color: "var(--text-muted)",
                    marginBottom: 4,
                  }}
                >
                  Dissolved O₂
                </div>
                <div style={{ fontWeight: 600, color: "#22c55e" }}>
                  {LAKE_DATA.dissolvedOxygen} mg/L
                </div>
              </div>
            </div>
          </Card>

          {/* Transcript */}
          <Card
            style={{
              flex: 1,
              overflow: "hidden",
              display: "flex",
              flexDirection: "column",
              padding: "var(--space-lg)",
              maxHeight: "400px",
            }}
          >
            <h3
              style={{
                fontSize: "1rem",
                fontWeight: 600,
                marginBottom: 16,
                color: "var(--text-main)",
              }}
            >
              📝 Transcript
            </h3>
            <div style={{ flex: 1, overflowY: "auto", paddingRight: 8 }}>
              {transcriptions.length === 0 ? (
                <p
                  style={{
                    color: "var(--text-muted)",
                    textAlign: "center",
                    padding: 24,
                    fontSize: "0.9rem",
                  }}
                >
                  Start a call to see the conversation here.
                </p>
              ) : (
                transcriptions.map((t, i) => (
                  <div
                    key={i}
                    style={{
                      padding: "10px 14px",
                      marginBottom: 8,
                      borderRadius: 12,
                      background:
                        t.role === "user"
                          ? "var(--primary-light)"
                          : "var(--bg-surface)",
                      border: "1px solid var(--border-color)",
                    }}
                  >
                    <div
                      style={{
                        fontSize: "0.65rem",
                        color: "var(--text-muted)",
                        marginBottom: 4,
                        fontWeight: 600,
                      }}
                    >
                      {t.role === "user" ? "👤 You" : "🤖 Vignesh"}
                    </div>
                    <div style={{ fontSize: "0.85rem" }}>{t.text}</div>
                  </div>
                ))
              )}
            </div>
          </Card>
        </div>
      </div>
    </AppLayout>
  );
};
