import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Send, Bot, User, Loader2, ExternalLink } from "lucide-react";
import { cn } from "@/lib/utils";

interface Message {
  role: "user" | "agent";
  content: string;
}

export function Chat() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "agent",
      content: `Welcome! I'm Trade Copilot — your AI assistant for the Indian stock market (NSE).

Ask me things like:
• "What is the current market regime?"
• "Scan for breakout stocks"
• "Analyze RELIANCE"
• "Show my portfolio"
• "Execute a full scan-to-trade flow"

All trades are paper trades. No real money involved.`,
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const sendMessage = async (overrideMessage?: string) => {
    const userMessage = (overrideMessage ?? input.trim()).trim();
    if (!userMessage || isLoading) return;

    if (!overrideMessage) setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setIsLoading(true);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMessage }),
      });
      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        { role: "agent", content: data.reply || "No response." },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "agent", content: `Error: ${err instanceof Error ? err.message : "Unknown error"}` },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <Card className="flex flex-col h-full">
      <CardHeader className="pb-3 flex flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2">
          <Bot className="h-5 w-5" />
          Trade Copilot
        </CardTitle>
        <a
          href={import.meta.env.VITE_ADK_WEB_URL ?? "http://127.0.0.1:8000"}
          target="_blank"
          rel="noopener noreferrer"
        >
          <Button size="sm" className="gap-1.5 h-8 bg-black text-white hover:bg-black/90 dark:bg-white dark:text-black dark:hover:bg-white/90">
            <ExternalLink className="h-3.5 w-3.5" />
            Agentic mode
          </Button>
        </a>
      </CardHeader>
      <CardContent className="flex-1 flex flex-col gap-3 p-4 pt-0">
        <ScrollArea className="flex-1 pr-4" ref={scrollRef}>
          <div className="space-y-4">
            {messages.map((msg, i) => (
              <div
                key={i}
                className={cn(
                  "flex gap-3",
                  msg.role === "user" ? "justify-end" : "justify-start"
                )}
              >
                {msg.role === "agent" && (
                  <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center shrink-0">
                    <Bot className="h-4 w-4 text-primary-foreground" />
                  </div>
                )}
                <div
                  className={cn(
                    "rounded-lg px-4 py-2 max-w-[80%]",
                    msg.role === "user"
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted"
                  )}
                >
                  {msg.role === "agent" ? (
                    <div className="text-sm [&_p]:my-1.5 [&_p:last-child]:mb-0 [&_ul]:list-disc [&_ul]:pl-4 [&_ul]:my-1.5 [&_ol]:list-decimal [&_ol]:pl-4 [&_ol]:my-1.5 [&_li]:my-0.5 [&_strong]:font-semibold [&_h1]:text-base [&_h1]:font-bold [&_h2]:text-sm [&_h2]:font-bold [&_h3]:text-sm [&_h3]:font-semibold">
                      <ReactMarkdown
                        components={{
                          p: ({ children }) => <p className="mb-1.5 last:mb-0">{children}</p>,
                          ul: ({ children }) => <ul className="list-disc pl-4 space-y-0.5 my-1.5">{children}</ul>,
                          ol: ({ children }) => <ol className="list-decimal pl-4 space-y-0.5 my-1.5">{children}</ol>,
                          li: ({ children }) => <li className="leading-snug">{children}</li>,
                          strong: ({ children }) => <strong className="font-semibold text-foreground">{children}</strong>,
                          h1: ({ children }) => <h1 className="text-base font-bold mt-2 mb-1">{children}</h1>,
                          h2: ({ children }) => <h2 className="text-sm font-bold mt-2 mb-1">{children}</h2>,
                          h3: ({ children }) => <h3 className="text-sm font-semibold mt-1.5 mb-0.5">{children}</h3>,
                        }}
                      >
                        {msg.content}
                      </ReactMarkdown>
                    </div>
                  ) : (
                    <span className="whitespace-pre-wrap">{msg.content}</span>
                  )}
                </div>
                {msg.role === "user" && (
                  <div className="h-8 w-8 rounded-full bg-secondary flex items-center justify-center shrink-0">
                    <User className="h-4 w-4" />
                  </div>
                )}
              </div>
            ))}
            {isLoading && (
              <div className="flex gap-3 justify-start">
                <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center shrink-0">
                  <Bot className="h-4 w-4 text-primary-foreground" />
                </div>
                <div className="rounded-lg px-4 py-2 bg-muted flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Thinking...
                </div>
              </div>
            )}
          </div>
        </ScrollArea>
        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <span>Quick:</span>
          {[
            { label: "Market + get into stocks", prompt: "Understand the market and I want to get into stocks" },
            { label: "Best oversold stocks", prompt: "Give me the best oversold stocks from Nifty 50" },
            { label: "Dividend opportunities", prompt: "Give me good dividend stocks with buy and sell points" },
            { label: "My portfolio", prompt: "Show my portfolio and performance" },
          ].map(({ label, prompt }) => (
            <Button
              key={prompt}
              variant="outline"
              size="sm"
              className="h-7 rounded-full text-xs font-normal"
              disabled={isLoading}
              onClick={() => sendMessage(prompt)}
            >
              {label}
            </Button>
          ))}
        </div>
        <div className="flex gap-2">
          <Input
            placeholder="Ask about the market, scan stocks, or trade..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
          />
          <Button onClick={() => sendMessage()} disabled={isLoading || !input.trim()}>
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
