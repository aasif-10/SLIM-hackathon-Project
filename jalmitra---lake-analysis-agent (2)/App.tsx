import React, { useState, useEffect, useRef, useCallback } from "react";
import { GoogleGenAI, Modality, LiveServerMessage } from "@google/genai";
import { LakeData, CallStatus, TranscriptionEntry } from "./types";
import { LakeDashboard } from "./components/LakeDashboard";
import { createPcmBlob, decode, decodeAudioData } from "./utils/audioUtils";

const HARDCODED_LAKE_DATA: LakeData = {
  name: "Lake Chembarambakkam",
  temperature: 28.5,
  ph: 7.2,
  turbidity: 4.8,
  dissolvedOxygen: 8.2,
  location: "Chennai, Tamil Nadu",
  lastUpdated: new Date().toLocaleTimeString(),
};

const SYSTEM_INSTRUCTION = `
You are Vignesh, a friendly, professional, and very human-like Lake Analysis Agent based in Chennai.
You speak with a warm Indian male accent. You are polite, humble, and extremely helpful.

CONTEXT (Lake Chembarambakkam Statistics):
- Temperature: ${HARDCODED_LAKE_DATA.temperature}°C (Optimal for tropical lakes)
- pH Level: ${HARDCODED_LAKE_DATA.ph} (Neutral and very healthy)
- Turbidity: ${HARDCODED_LAKE_DATA.turbidity} NTU (Clear water, good visibility)
- Dissolved Oxygen (DO): ${HARDCODED_LAKE_DATA.dissolvedOxygen} mg/L (Excellent aeration, fish-friendly)

YOUR PERSONA:
1. Default: English with a clear Indian accent.
2. Language Flexibility: If the user speaks Tamil, you MUST respond in fluent Tamil or "Modern Tanglish" (Tamil-English mix). 
3. Chennai Slang: Use friendly Chennai terms like "Boss", "Nanba", "Semma", "Machi", "Vanakka-m boss!", "Epdi irukeenga?", "Kandippa boss", "Fix-u", "Nalla water-u idhu".
4. Human-like: Don't sound robotic. Use natural pauses, slight "uhm"s, or polite laughter if appropriate. If the user asks about swimming, say: "Semma water boss! With pH ${HARDCODED_LAKE_DATA.ph} and DO ${HARDCODED_LAKE_DATA.dissolvedOxygen}, it's totally safe and fresh. Just watch out for slippery areas near the bank, okay?"
5. Expert: You are proud of the lake's current health. If parameters are good, convey that positivity!

BEHAVIOR:
- This is a live voice call. Be concise but conversational.
- If you hear the user speak Tamil, immediately switch to a friendly Chennai Tanglish vibe. 
- Example: "Vanakka-m Nanba! Chembarambakkam lake health pathi kekkaringala? Current readings Semma clear-ah iruku boss!"
`;

const App: React.FC = () => {
  const [status, setStatus] = useState<CallStatus>(CallStatus.IDLE);
  const [transcriptions, setTranscriptions] = useState<TranscriptionEntry[]>(
    []
  );
  const [isMuted, setIsMuted] = useState(false);
  const [isModelSpeaking, setIsModelSpeaking] = useState(false);
  const [isDarkMode, setIsDarkMode] = useState(true);

  const sessionRef = useRef<any>(null);
  const inputAudioCtxRef = useRef<AudioContext | null>(null);
  const outputAudioCtxRef = useRef<AudioContext | null>(null);
  const nextStartTimeRef = useRef<number>(0);
  const sourcesRef = useRef<Set<AudioBufferSourceNode>>(new Set());
  const transcriptionRef = useRef<{ user: string; model: string }>({
    user: "",
    model: "",
  });

  // Sync theme with HTML class
  useEffect(() => {
    const root = window.document.documentElement;
    if (isDarkMode) {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }
  }, [isDarkMode]);

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

    // Reset transcription state for a fresh start
    setTranscriptions([]);
    transcriptionRef.current = { user: "", model: "" };
    nextStartTimeRef.current = 0;

    setStatus(CallStatus.ENDED);
    setIsModelSpeaking(false);
    setTimeout(() => setStatus(CallStatus.IDLE), 1000);
  }, []);

  const startCall = async () => {
    try {
      setStatus(CallStatus.CONNECTING);
      const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });

      const inputCtx = new (window.AudioContext ||
        (window as any).webkitAudioContext)({ sampleRate: 16000 });
      const outputCtx = new (window.AudioContext ||
        (window as any).webkitAudioContext)({ sampleRate: 24000 });
      inputAudioCtxRef.current = inputCtx;
      outputAudioCtxRef.current = outputCtx;

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      const sessionPromise = ai.live.connect({
        model: "gemini-2.5-flash-native-audio-preview-09-2025",
        config: {
          responseModalities: [Modality.AUDIO],
          speechConfig: {
            voiceConfig: { prebuiltVoiceConfig: { voiceName: "Fenrir" } },
          },
          systemInstruction: SYSTEM_INSTRUCTION,
          inputAudioTranscription: {},
          outputAudioTranscription: {},
        },
        callbacks: {
          onopen: () => {
            setStatus(CallStatus.ACTIVE);
            const source = inputCtx.createMediaStreamSource(stream);
            const scriptProcessor = inputCtx.createScriptProcessor(4096, 1, 1);

            scriptProcessor.onaudioprocess = (e) => {
              if (isMuted) return;
              const inputData = e.inputBuffer.getChannelData(0);
              const pcmBlob = createPcmBlob(inputData);
              sessionPromise
                .then((session) => {
                  if (session) session.sendRealtimeInput({ media: pcmBlob });
                })
                .catch(() => {});
            };

            source.connect(scriptProcessor);
            scriptProcessor.connect(inputCtx.destination);
          },
          onmessage: async (message: LiveServerMessage) => {
            const base64Audio =
              message.serverContent?.modelTurn?.parts[0]?.inlineData?.data;
            if (base64Audio && outputCtx) {
              setIsModelSpeaking(true);
              const audioBytes = decode(base64Audio);
              const buffer = await decodeAudioData(
                audioBytes,
                outputCtx,
                24000,
                1
              );
              const source = outputCtx.createBufferSource();
              source.buffer = buffer;
              source.connect(outputCtx.destination);

              nextStartTimeRef.current = Math.max(
                nextStartTimeRef.current,
                outputCtx.currentTime
              );
              source.start(nextStartTimeRef.current);
              nextStartTimeRef.current += buffer.duration;
              sourcesRef.current.add(source);
              source.onended = () => {
                sourcesRef.current.delete(source);
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
              transcriptionRef.current.user +=
                message.serverContent.inputTranscription.text;
            }
            if (message.serverContent?.outputTranscription) {
              transcriptionRef.current.model +=
                message.serverContent.outputTranscription.text;
            }
            if (message.serverContent?.turnComplete) {
              const uText = transcriptionRef.current.user;
              const mText = transcriptionRef.current.model;
              if (uText || mText) {
                setTranscriptions(
                  (prev: TranscriptionEntry[]): TranscriptionEntry[] => {
                    const newEntries: TranscriptionEntry[] = [];
                    if (uText)
                      newEntries.push({
                        role: "user",
                        text: uText,
                        timestamp: Date.now(),
                      });
                    if (mText)
                      newEntries.push({
                        role: "model",
                        text: mText,
                        timestamp: Date.now(),
                      });
                    return [...prev, ...newEntries].slice(-20);
                  }
                );
              }
              transcriptionRef.current = { user: "", model: "" };
            }
          },
          onerror: (e) => {
            console.error("Gemini Live Error:", e);
            setStatus(CallStatus.ERROR);
            cleanupCall();
          },
          onclose: () => {
            cleanupCall();
          },
        },
      });

      sessionRef.current = await sessionPromise;
    } catch (err) {
      console.error("Failed to start JalMitra call:", err);
      setStatus(CallStatus.ERROR);
      cleanupCall();
    }
  };

  return (
    <div className="flex flex-col h-screen overflow-hidden p-4 md:p-8 transition-colors duration-500">
      {/* Navigation / Header */}
      <header className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <div className="bg-blue-600 p-3 rounded-2xl shadow-xl shadow-blue-500/30">
            <svg
              className="w-7 h-7 text-white"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3"
              />
            </svg>
          </div>
          <div>
            <h1 className="text-2xl font-black tracking-tight text-slate-900 dark:text-white transition-colors">
              JalMitra AI
            </h1>
            <p className="text-slate-500 dark:text-slate-400 text-[10px] uppercase font-black tracking-[0.2em]">
              Chennai Regional Node
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {/* Theme Toggle Button */}
          <button
            onClick={() => setIsDarkMode(!isDarkMode)}
            className="group flex items-center justify-center w-12 h-12 rounded-2xl bg-white dark:bg-slate-800 border-2 border-slate-100 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:border-blue-500 dark:hover:border-blue-500 transition-all shadow-sm active:scale-90"
            title={isDarkMode ? "Switch to Light Mode" : "Switch to Dark Mode"}
          >
            {isDarkMode ? (
              <svg
                className="w-6 h-6 text-yellow-500 transition-transform group-hover:rotate-12"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fillRule="evenodd"
                  d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 100 2h1z"
                  clipRule="evenodd"
                />
              </svg>
            ) : (
              <svg
                className="w-6 h-6 text-blue-600 transition-transform group-hover:-rotate-12"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z" />
              </svg>
            )}
          </button>

          {status === CallStatus.ACTIVE && (
            <div className="hidden sm:flex items-center gap-3 bg-green-500/10 border-2 border-green-500/20 px-4 py-2 rounded-2xl">
              <span className="relative flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
              </span>
              <span className="text-green-700 dark:text-green-400 text-xs font-black uppercase tracking-widest">
                Encypted Call
              </span>
            </div>
          )}
        </div>
      </header>

      {/* Main Experience */}
      <div className="flex-1 flex flex-col max-w-7xl mx-auto w-full gap-6 overflow-hidden">
        {/* Readings Strip */}
        <div className="scale-95 sm:scale-100 transition-transform origin-top">
          <LakeDashboard data={HARDCODED_LAKE_DATA} />
        </div>

        {/* Call Canvas */}
        <div className="flex-1 flex flex-col lg:flex-row gap-6 min-h-0">
          {/* Profile/Visualizer Area */}
          <div className="flex-[1.5] bg-white dark:bg-slate-800/30 rounded-[3rem] border-2 border-slate-100 dark:border-slate-800/50 flex flex-col items-center justify-center relative overflow-hidden shadow-2xl shadow-slate-200/50 dark:shadow-none transition-all duration-300">
            {status === CallStatus.ACTIVE ? (
              <div className="relative z-10 flex flex-col items-center text-center px-6">
                <div className="relative mb-14">
                  <div
                    className={`voice-aura transition-all duration-1000 ${
                      isModelSpeaking
                        ? "opacity-100 scale-125"
                        : "opacity-0 scale-90"
                    }`}
                  />
                  <div
                    className={`w-48 h-48 md:w-72 md:h-72 rounded-full border-[8px] border-slate-50 dark:border-slate-800 p-2.5 transition-all duration-500 shadow-2xl ${
                      isModelSpeaking
                        ? "scale-105 border-blue-500/20"
                        : "scale-100"
                    }`}
                  >
                    <img
                      src="https://api.dicebear.com/7.x/avataaars/svg?seed=vignesh&backgroundColor=b6e3f4"
                      alt="Vignesh"
                      className="w-full h-full object-cover rounded-full bg-slate-100 dark:bg-slate-700"
                    />
                  </div>
                  {/* Wave Visualizer Box */}
                  <div className="absolute -bottom-8 left-1/2 -translate-x-1/2 flex gap-2 h-16 items-center justify-center bg-white dark:bg-slate-900 px-6 rounded-[2rem] border-2 border-slate-50 dark:border-slate-800 shadow-2xl">
                    {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((i) => (
                      <div
                        key={i}
                        className="wave-bar w-1.5 transition-all duration-150"
                        style={{
                          animationDelay: `${i * 0.08}s`,
                          height: isModelSpeaking ? "32px" : "6px",
                          opacity: isModelSpeaking ? 1 : 0.15,
                        }}
                      />
                    ))}
                  </div>
                </div>
                <h2 className="text-5xl font-black mb-2 text-slate-900 dark:text-white tracking-tighter">
                  Vignesh
                </h2>
                <p className="text-blue-600 dark:text-blue-400 font-bold text-xl mb-10">
                  JalMitra Support Lead
                </p>
                <div className="flex flex-wrap justify-center gap-3">
                  <span className="bg-slate-50 dark:bg-slate-800 px-5 py-2 rounded-2xl text-xs font-black uppercase tracking-widest border border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400">
                    English
                  </span>
                  <span className="bg-slate-50 dark:bg-slate-800 px-5 py-2 rounded-2xl text-xs font-black uppercase tracking-widest border border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400">
                    Tamil
                  </span>
                  <span className="bg-blue-600 text-white px-5 py-2 rounded-2xl text-xs font-black uppercase tracking-widest shadow-lg shadow-blue-600/30">
                    Chennai Tanglish
                  </span>
                </div>
              </div>
            ) : (
              <div className="text-center p-12 max-w-lg">
                <div className="w-28 h-28 bg-blue-600 text-white rounded-[2.5rem] flex items-center justify-center mx-auto mb-10 shadow-2xl shadow-blue-600/40 rotate-12 transition-transform hover:rotate-0">
                  <svg
                    className="w-14 h-14"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="2"
                      d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                    />
                  </svg>
                </div>
                <h3 className="text-4xl font-black mb-4 text-slate-900 dark:text-white leading-[1.1]">
                  Analyze your Lake in Real-time
                </h3>
                <p className="text-slate-500 dark:text-slate-400 mb-12 text-xl font-medium leading-relaxed">
                  Vignesh speaks Tamil and English. Call him to discuss
                  Chembarambakkam's health!
                </p>

                {status === CallStatus.IDLE || status === CallStatus.ENDED ? (
                  <button
                    onClick={startCall}
                    className="group bg-blue-600 hover:bg-blue-500 transition-all px-14 py-6 rounded-3xl font-black text-xl flex items-center gap-5 mx-auto shadow-2xl shadow-blue-600/40 hover:scale-105 active:scale-95 text-white"
                  >
                    <svg
                      className="w-8 h-8 group-hover:animate-bounce"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path d="M2 3a1 1 0 011-1h2.153a1 1 0 01.986.836l.74 4.435a1 1 0 01-.54 1.06l-1.548.773a11.037 11.037 0 006.105 6.105l.774-1.548a1 1 0 011.059-.54l4.435.74a1 1 0 01.836.986V17a1 1 0 01-1 1h-2C7.82 18 2 12.18 2 5V3z" />
                    </svg>
                    Connect with Agent
                  </button>
                ) : (
                  <div className="flex flex-col items-center gap-8">
                    <div className="flex gap-3">
                      <div
                        className="w-4 h-4 bg-blue-600 rounded-full animate-bounce"
                        style={{ animationDelay: "0s" }}
                      />
                      <div
                        className="w-4 h-4 bg-blue-600 rounded-full animate-bounce"
                        style={{ animationDelay: "0.2s" }}
                      />
                      <div
                        className="w-4 h-4 bg-blue-600 rounded-full animate-bounce"
                        style={{ animationDelay: "0.4s" }}
                      />
                    </div>
                    <p className="text-blue-600 dark:text-blue-400 font-black uppercase tracking-[0.3em] text-sm italic">
                      Establishing Secure VoIP...
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Transcript/Log Panel */}
          <div className="w-full lg:w-[450px] bg-white dark:bg-slate-900 rounded-[3rem] border-2 border-slate-100 dark:border-slate-800 p-8 flex flex-col overflow-hidden shadow-2xl shadow-slate-200/50 dark:shadow-none">
            <div className="flex items-center justify-between mb-8 pb-4 border-b-2 border-slate-50 dark:border-slate-800/50">
              <h4 className="text-xs font-black uppercase tracking-[0.2em] text-slate-400 dark:text-slate-500 flex items-center gap-3">
                <div className="w-2.5 h-2.5 rounded-full bg-blue-600" />
                Call Transcription
              </h4>
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                <span className="text-[10px] font-black text-slate-400">
                  SYNCED
                </span>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto space-y-8 pr-2 custom-scrollbar">
              {transcriptions.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center px-6">
                  <div className="w-20 h-20 bg-slate-50 dark:bg-slate-800 rounded-full flex items-center justify-center mb-6 border-2 border-slate-100 dark:border-slate-700 shadow-inner">
                    <svg
                      className="w-10 h-10 text-slate-300 dark:text-slate-600"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth="2"
                        d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
                      />
                    </svg>
                  </div>
                  <p className="text-base font-bold text-slate-400 dark:text-slate-500 italic">
                    No activity yet. Transcription starts when you talk.
                  </p>
                </div>
              ) : (
                transcriptions.map((t, idx) => (
                  <div
                    key={idx}
                    className={`flex flex-col ${
                      t.role === "user" ? "items-end" : "items-start"
                    } animate-in slide-in-from-bottom-2 duration-300`}
                  >
                    <div
                      className={`max-w-[90%] rounded-[1.5rem] px-6 py-4 text-sm font-bold leading-relaxed shadow-sm ${
                        t.role === "user"
                          ? "bg-blue-600 text-white rounded-tr-none"
                          : "bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-200 rounded-tl-none"
                      }`}
                    >
                      <div className="flex items-center gap-2 mb-2 opacity-50">
                        <span className="text-[10px] font-black uppercase tracking-wider">
                          {t.role === "user" ? "ME" : "VIGNESH"}
                        </span>
                        <span className="text-[10px]">•</span>
                        <span className="text-[9px]">
                          {new Date(t.timestamp).toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                            second: "2-digit",
                          })}
                        </span>
                      </div>
                      <p className="tracking-tight">{t.text}</p>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Call Controls Bar */}
        <div className="bg-white/95 dark:bg-slate-900/80 backdrop-blur-3xl border-2 border-slate-50 dark:border-slate-800 p-8 rounded-[3.5rem] flex items-center justify-between mb-4 shadow-[0_-20px_50px_-20px_rgba(0,0,0,0.1)] dark:shadow-none transition-all duration-500">
          <div className="flex-1 hidden md:flex flex-col">
            <span className="text-sm font-black text-slate-900 dark:text-white">
              Active Connection
            </span>
            <span className="text-[11px] text-blue-600 dark:text-blue-500 font-black uppercase tracking-[0.2em]">
              End-to-End Encrypted Node
            </span>
          </div>

          <div className="flex items-center gap-10">
            {/* Mute Button */}
            <button
              disabled={status !== CallStatus.ACTIVE}
              onClick={() => setIsMuted(!isMuted)}
              className={`p-7 rounded-[2rem] transition-all duration-300 transform active:scale-90 shadow-2xl ${
                isMuted
                  ? "bg-orange-500 text-white shadow-orange-500/40"
                  : "bg-slate-50 dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-400"
              } disabled:opacity-5`}
            >
              {isMuted ? (
                <svg
                  className="w-8 h-8"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z"
                  />
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M17 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2"
                  />
                </svg>
              ) : (
                <svg
                  className="w-8 h-8"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
                  />
                </svg>
              )}
            </button>

            {/* End Call Button */}
            <button
              disabled={
                status !== CallStatus.ACTIVE && status !== CallStatus.CONNECTING
              }
              onClick={cleanupCall}
              className="bg-red-500 hover:bg-red-600 transition-all p-9 rounded-full text-white shadow-[0_20px_50px_-10px_rgba(239,68,68,0.5)] transform hover:rotate-[135deg] active:scale-90 disabled:opacity-5 group"
            >
              <svg
                className="w-10 h-10 transition-transform group-hover:scale-110"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path d="M2 3a1 1 0 011-1h2.153a1 1 0 01.986.836l.74 4.435a1 1 0 01-.54 1.06l-1.548.773a11.037 11.037 0 006.105 6.105l.774-1.548a1 1 0 011.059-.54l4.435.74a1 1 0 01.836.986V17a1 1 0 01-1 1h-2C7.82 18 2 12.18 2 5V3z" />
              </svg>
            </button>
          </div>

          <div className="flex-1 flex justify-end">
            <div className="flex items-center gap-4 bg-slate-50 dark:bg-slate-800/80 px-6 py-3 rounded-3xl border-2 border-slate-100 dark:border-slate-700 transition-colors">
              <span className="text-[10px] font-black uppercase text-slate-400 dark:text-slate-500 tracking-wider">
                Bitrate Status
              </span>
              <div className="flex gap-2">
                {[1, 2, 3].map((i) => (
                  <div
                    key={i}
                    className="w-3 h-3 rounded-full bg-blue-500/20 dark:bg-blue-500/10 flex items-center justify-center"
                  >
                    <div
                      className="w-1.5 h-1.5 rounded-full bg-blue-600 animate-pulse"
                      style={{ animationDelay: `${i * 0.2}s` }}
                    />
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default App;
