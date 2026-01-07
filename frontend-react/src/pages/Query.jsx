import React, { useState, useRef, useEffect } from "react";
import { AppLayout } from "../components/layout/AppLayout";
import { Card, Button, Input, Badge } from "../components/ui";
import { motion, AnimatePresence } from "framer-motion";
import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

const QUICK_QUERIES = [
  { label: "Current pH", q: "What is the current pH level?" },
  { label: "Turbidity Status", q: "Show the latest turbidity reading." },
  { label: "Temp Delta", q: "How does temp compare to yesterday?" },
  { label: "Safety Check", q: "Is the water safe for swimming?" },
  { label: "Do Analysis", q: "Analyze Dissolved Oxygen trends." },
];

import { useAuth } from "../context/AuthContext";

export const Query = () => {
  const { token } = useAuth();
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: "ai",
      text: "Hello! I am the SLIM AI Ecology Agent. I can help you analyze lake sensor data, identify anomalies, and forecast trends. Ask me anything.",
    },
  ]);
  const [inputValue, setInputValue] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const chatEndRef = useRef(null);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  const handleSendMessage = async (text = inputValue) => {
    if (!text.trim()) return;

    const q = text;
    setMessages((prev) => [...prev, { id: Date.now(), type: "user", text: q }]);
    setInputValue("");
    setIsTyping(true);

    try {
      // Dynamic API URL
      const API_BASE_URL = import.meta.env.VITE_API_URL || "";

      const response = await fetch(`${API_BASE_URL}/api/expert-analysis`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ question: q }),
      });

      if (!response.ok) {
        throw new Error(`API returned ${response.status}`);
      }

      const data = await response.json();

      // Format the response with markdown-style bold
      const formattedAnswer = data.answer
        ? data.answer
            .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
            .replace(/\n/g, "<br/>")
        : "Unable to generate analysis.";

      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          type: "ai",
          text: formattedAnswer,
        },
      ]);
    } catch (error) {
      console.error("Query error:", error);
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          type: "ai",
          text: `<strong>Error:</strong> Unable to connect to the analysis engine. Please ensure the backend server is running.`,
        },
      ]);
    } finally {
      setIsTyping(false);
    }
  };

  // Chat Bubble Component
  const ChatBubble = ({ msg }) => (
    <motion.div
      initial={{ opacity: 0, scale: 0.95, y: 10 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      className={`flex ${
        msg.type === "user" ? "justify-end" : "justify-start"
      } mb-4`}
    >
      <div
        style={{
          maxWidth: "80%",
          padding: "12px 16px",
          borderRadius:
            msg.type === "user" ? "16px 16px 4px 16px" : "16px 16px 16px 4px",
          fontSize: "0.95rem",
          lineHeight: 1.5,
          background:
            msg.type === "user" ? "var(--primary-color)" : "var(--bg-surface)",
          color: msg.type === "user" ? "#fff" : "var(--text-main)",
          border:
            msg.type === "user" ? "none" : "1px solid var(--border-color)",
          boxShadow: "0 2px 4px rgba(0,0,0,0.02)",
        }}
      >
        <div dangerouslySetInnerHTML={{ __html: msg.text }} />
        <div
          style={{
            fontSize: "0.7rem",
            opacity: 0.7,
            marginTop: 4,
            textAlign: msg.type === "user" ? "right" : "left",
          }}
        >
          {new Date().toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </div>
      </div>
    </motion.div>
  );

  return (
    <AppLayout title="Query Intelligence">
      <div
        className="grid-3"
        style={{ height: "calc(100vh - 140px)", gap: "var(--space-lg)" }}
      >
        {/* LEFT COLUMN: CHAT INTERFACE (Spans 2 columns) */}
        <Card
          className="col-span-2"
          style={{
            gridColumn: "span 2",
            display: "flex",
            flexDirection: "column",
            height: "100%",
            padding: 0,
            overflow: "hidden",
          }}
        >
          {/* Header */}
          <div
            style={{
              padding: "var(--space-md) var(--space-lg)",
              borderBottom: "1px solid var(--border-color)",
              background: "var(--bg-surface)",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <div className="flex items-center gap-3">
              <div
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: "50%",
                  background: "var(--success)",
                }}
              ></div>
              <div>
                <div style={{ fontWeight: 600 }}>Ecology Specialist Agent</div>
                <div className="text-muted" style={{ fontSize: "0.75rem" }}>
                  Powered by Gemini Pro • Live Connection
                </div>
              </div>
            </div>
            <Button variant="ghost" size="sm">
              Clear Chat
            </Button>
          </div>

          {/* Chat Area */}
          <div
            className="flex-1 overflow-y-auto"
            style={{ padding: "var(--space-lg)", background: "var(--bg-body)" }}
          >
            {messages.map((msg) => (
              <ChatBubble key={msg.id} msg={msg} />
            ))}
            {isTyping && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex justify-start mb-4"
              >
                <div
                  style={{
                    padding: "12px 16px",
                    background: "var(--bg-surface)",
                    borderRadius: 16,
                    border: "1px solid var(--border-color)",
                  }}
                >
                  <span className="typing-dot">●</span>{" "}
                  <span className="typing-dot">●</span>{" "}
                  <span className="typing-dot">●</span>
                </div>
              </motion.div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Input Area */}
          <div
            style={{
              padding: "var(--space-lg)",
              background: "var(--bg-surface)",
              borderTop: "1px solid var(--border-color)",
            }}
          >
            <div className="flex gap-2">
              <Input
                placeholder="Ask a question about lake health..."
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSendMessage()}
                style={{ flex: 1 }}
              />
              <Button
                variant="primary"
                onClick={() => handleSendMessage()}
                disabled={!inputValue.trim()}
              >
                Send
              </Button>
            </div>
            <div
              className="flex gap-2 mt-3 overflow-x-auto pb-2"
              style={{ scrollbarWidth: "none" }}
            >
              {QUICK_QUERIES.map((q, i) => (
                <button
                  key={i}
                  onClick={() => handleSendMessage(q.q)}
                  className="badge badge-neutral hover:bg-slate-200 cursor-pointer transition-colors"
                  style={{
                    border: "1px solid var(--border-color)",
                    background: "transparent",
                  }}
                >
                  {q.label}
                </button>
              ))}
            </div>
          </div>
        </Card>

        {/* RIGHT COLUMN: CONTEXT & HISTORY */}
        <div
          className="flex flex-col"
          style={{ height: "100%", gap: "var(--space-lg)" }}
        >
          <Card style={{ flex: 1 }}>
            <div className="card-title mb-4">Context Awareness</div>
            <div
              className="text-muted"
              style={{ fontSize: "0.9rem", marginBottom: 16 }}
            >
              The agent has access to real-time data from 6 sensors in the
              Ulsoor Lake sector.
            </div>
            <div className="flex flex-col gap-3">
              <div className="p-3 border rounded bg-surface">
                <div className="text-xs text-muted uppercase">
                  Active Session
                </div>
                <div className="font-semibold">Session ID: #88229</div>
              </div>
              <div className="p-3 border rounded bg-surface">
                <div className="text-xs text-muted uppercase">Last Update</div>
                <div className="font-semibold">Just now</div>
              </div>
            </div>
          </Card>

          <Card style={{ flex: 1.5 }}>
            <div className="card-title mb-4">Metric Trends</div>
            <div style={{ height: 200, position: "relative" }}>
              {/* Mini Chart Mockup */}
              <Line
                data={{
                  labels: [
                    "10:00",
                    "11:00",
                    "12:00",
                    "13:00",
                    "14:00",
                    "15:00",
                  ],
                  datasets: [
                    {
                      label: "pH",
                      data: [7.1, 7.2, 7.1, 7.3, 7.2, 7.2],
                      borderColor: "#10b981",
                      tension: 0.4,
                      pointRadius: 2,
                    },
                  ],
                }}
                options={{
                  responsive: true,
                  maintainAspectRatio: false,
                  plugins: { legend: { display: false } },
                  scales: { x: { display: false }, y: { display: false } },
                }}
              />
            </div>
            <div className="mt-4 text-center text-sm text-success font-medium">
              Parameters Stable
            </div>
          </Card>
        </div>
      </div>

      <style>{`
                .typing-dot {
                    animation: blink 1.4s infinite both;
                    font-size: 0.8rem;
                    color: var(--text-muted);
                }
                .typing-dot:nth-child(2) { animation-delay: 0.2s; }
                .typing-dot:nth-child(3) { animation-delay: 0.4s; }
                @keyframes blink { 0% { opacity: 0.2; } 20% { opacity: 1; } 100% { opacity: 0.2; } }
            `}</style>
    </AppLayout>
  );
};
