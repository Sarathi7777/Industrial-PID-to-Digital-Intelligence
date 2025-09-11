import React, { useState, useRef, useEffect } from "react";
import {
  MessageCircle,
  Send,
  X,
  Bot,
  User,
  Loader2,
  AlertCircle,
  RefreshCw,
} from "lucide-react";
import { useChat } from "../contexts/ChatContext";

interface Message {
  id: string;
  sender: "user" | "bot";
  text: string;
  timestamp: Date;
}

const GlobalChatWidget: React.FC = () => {
  const { isChatOpen, toggleChat, pidData } = useChat();
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Focus input when chat opens
  useEffect(() => {
    if (isChatOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isChatOpen]);

  // Add welcome message when chat first opens
  useEffect(() => {
    if (isChatOpen && messages.length === 0) {
      const welcomeMessage: Message = {
        id: "welcome",
        sender: "bot",
        text: "Hello! I'm APX CoPilot, your comprehensive P&ID Digital Intelligence assistant. I can help you with:\n\n• Understanding P&ID analysis results\n• Explaining component types and functions\n• Troubleshooting analysis issues\n• Platform capabilities and features\n• P&ID standards and conventions\n\nWhat would you like to know about the platform or your P&ID data?",
        timestamp: new Date(),
      };
      setMessages([welcomeMessage]);
    }
  }, [isChatOpen, messages.length]);

  const sendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      sender: "user",
      text: inputValue.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue("");
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch("http://localhost:8000/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question: userMessage.text,
          context_json: pidData || {},
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      const botMessage: Message = {
        id: (Date.now() + 1).toString(),
        sender: "bot",
        text: data.response,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, botMessage]);
    } catch (err) {
      console.error("Error sending message:", err);
      setError(err instanceof Error ? err.message : "Failed to send message");
      
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        sender: "bot",
        text: "Sorry, I encountered an error while processing your request. Please try again.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const clearChat = () => {
    setMessages([]);
    setError(null);
  };

  if (!isChatOpen) {
    return (
      <div className="fixed bottom-6 right-6 z-50">
        <button
          onClick={toggleChat}
          className="w-14 h-14 bg-gradient-to-r from-yellow-400 to-yellow-500 hover:from-yellow-500 hover:to-yellow-600 text-black rounded-full shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-110 flex items-center justify-center group border-2 border-white"
        >
          <MessageCircle className="w-6 h-6 group-hover:scale-110 transition-transform" />
        </button>
      </div>
    );
  }

  return (
    <div className="fixed bottom-6 right-6 z-50 w-96 h-[600px] bg-black rounded-2xl shadow-2xl border-2 border-yellow-400 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-yellow-400 to-yellow-500 p-4 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 bg-black/20 rounded-full flex items-center justify-center border border-black">
            <Bot className="w-5 h-5 text-black" />
          </div>
          <div>
            <h3 className="text-black font-bold text-lg">APX CoPilot</h3>
            <p className="text-black/70 text-xs font-medium">
              {pidData ? "P&ID Data Available" : "General Help"}
            </p>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={clearChat}
            className="p-1.5 text-black/70 hover:text-black hover:bg-black/20 rounded-lg transition-colors"
            title="Clear chat"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={toggleChat}
            className="p-1.5 text-black/70 hover:text-black hover:bg-black/20 rounded-lg transition-colors"
            title="Close chat"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-800">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.sender === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                message.sender === "user"
                  ? "bg-gradient-to-r from-yellow-400 to-yellow-500 text-black border border-yellow-300"
                  : "bg-white text-black border border-yellow-400"
              }`}
            >
              <div className="flex items-start space-x-2">
                {message.sender === "bot" && (
                  <Bot className="w-4 h-4 text-yellow-600 flex-shrink-0 mt-0.5" />
                )}
                {message.sender === "user" && (
                  <User className="w-4 h-4 text-black/70 flex-shrink-0 mt-0.5" />
                )}
                <div className="flex-1">
                  <p className="text-sm leading-relaxed whitespace-pre-wrap font-medium">
                    {message.text}
                  </p>
                  <p className="text-xs opacity-70 mt-1">
                    {message.timestamp.toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </p>
                </div>
              </div>
            </div>
          </div>
        ))}
        
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-white text-black rounded-2xl px-4 py-3 max-w-[80%] border border-yellow-400">
              <div className="flex items-center space-x-2">
                <Bot className="w-4 h-4 text-yellow-600 flex-shrink-0" />
                <div className="flex items-center space-x-1">
                  <Loader2 className="w-4 h-4 animate-spin text-yellow-600" />
                  <span className="text-sm font-medium">Thinking...</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="flex justify-start">
            <div className="bg-red-500/20 border border-red-500 text-red-300 rounded-2xl px-4 py-3 max-w-[80%]">
              <div className="flex items-center space-x-2">
                <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
                <div>
                  <p className="text-sm font-medium">Error</p>
                  <p className="text-xs opacity-80">{error}</p>
                </div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-yellow-400 bg-gray-800">
        <div className="flex space-x-2">
          <input
            ref={inputRef}
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={
              pidData 
                ? "Ask about your P&ID data or the platform..." 
                : "Ask APX CoPilot..."
            }
            disabled={isLoading}
            className="flex-1 bg-white border-2 border-yellow-400 text-black rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-yellow-400 focus:border-yellow-500 disabled:opacity-50 disabled:cursor-not-allowed placeholder-black/50 font-medium"
          />
          <button
            onClick={sendMessage}
            disabled={!inputValue.trim() || isLoading}
            className="bg-gradient-to-r from-yellow-400 to-yellow-500 hover:from-yellow-500 hover:to-yellow-600 disabled:from-gray-400 disabled:to-gray-500 text-black p-3 rounded-xl transition-all duration-200 disabled:cursor-not-allowed disabled:opacity-50 border-2 border-yellow-300 font-bold"
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>
        <p className="text-xs text-yellow-400 mt-2 text-center font-medium">
          • Press Enter to send
        </p>
      </div>
    </div>
  );
};

export default GlobalChatWidget;
