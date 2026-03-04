"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter, usePathname } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { Send, RefreshCw, Trash2, LogOut, CheckSquare, MessageSquare, Settings, FileSearch, User as UserIcon } from "lucide-react";
import { agentApi, ChatEvent } from "@/lib/api";
import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import { cn } from "@/lib/utils";

interface Message {
  role: "user" | "assistant";
  content: string;
  toolCalls?: ToolCall[];
  timestamp: Date;
}

interface ToolCall {
  tool: string;
  args: string;
  result?: string;
}

export default function AgentPage() {
  const router = useRouter();
  const pathname = usePathname();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [token, setToken] = useState<string>("");
  const [streamContent, setStreamContent] = useState("");
  const [currentToolCalls, setCurrentToolCalls] = useState<ToolCall[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const getToken = async () => {
      const response = await fetch("/api/auth/get-token");
      if (response.ok) {
        const data = await response.json();
        setToken(data.token);
      } else {
        router.push("/login");
      }
    };
    getToken();
  }, [router]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamContent, currentToolCalls]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading || !token) return;

    const userMessage = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMessage, timestamp: new Date() }]);
    setLoading(true);
    setStreamContent("");
    setCurrentToolCalls([]);

    try {
      let assistantContent = "";
      const toolCalls: ToolCall[] = [];

      for await (const event of agentApi.chatStream(token, userMessage)) {
        if (event.type === "content" && event.content) {
          assistantContent += event.content;
          setStreamContent(assistantContent);
        } else if (event.type === "tool_call") {
          const toolCall: ToolCall = {
            tool: event.tool || "unknown",
            args: event.args || "{}",
          };
          toolCalls.push(toolCall);
          setCurrentToolCalls([...toolCalls]);
        } else if (event.type === "tool_result") {
          if (toolCalls.length > 0) {
            toolCalls[toolCalls.length - 1].result = event.result;
            setCurrentToolCalls([...toolCalls]);
          }
        } else if (event.type === "error") {
          assistantContent += `\n\n**Error:** ${event.content}`;
          setStreamContent(assistantContent);
        } else if (event.type === "done") {
          break;
        }
      }

      // Save the message
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: assistantContent,
          toolCalls: toolCalls.length > 0 ? toolCalls : undefined,
          timestamp: new Date(),
        },
      ]);
      setStreamContent("");
      setCurrentToolCalls([]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `**Error:** ${error instanceof Error ? error.message : "Failed to get response"}`,
          timestamp: new Date(),
        },
      ]);
    } finally {
      setLoading(false);
      setStreamContent("");
      setCurrentToolCalls([]);
    }
  };

  const handleReset = async () => {
    if (!token) return;
    await agentApi.resetChat(token);
    setMessages([]);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const examplePrompts = [
    "What are my pending todos?",
    "Create a todo for reviewing PRs",
    "Help me write a Python function to sort a list",
    "Mark my high priority todos as complete",
    "How do I fix a SQL injection vulnerability?",
    "Explain the difference between REST and GraphQL",
    "Help me optimize this database query",
  ];

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <aside className="w-64 border-r bg-muted/30 p-4 flex flex-col">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-primary">Todo Agent</h1>
          <p className="text-sm text-muted-foreground">AI-Powered Tasks</p>
        </div>

        <nav className="space-y-2 flex-1">
          <Button
            variant="ghost"
            className="w-full justify-start"
            onClick={() => router.push("/dashboard")}
          >
            <CheckSquare className="mr-2 h-4 w-4" />
            Dashboard
          </Button>
          <Button
            variant={pathname === "/agent" ? "default" : "ghost"}
            className="w-full justify-start"
            onClick={() => router.push("/agent")}
          >
            <MessageSquare className="mr-2 h-4 w-4" />
            AI Chat
          </Button>
          <Button
            variant={pathname === "/review" ? "default" : "ghost"}
            className="w-full justify-start"
            onClick={() => router.push("/review")}
          >
            <FileSearch className="mr-2 h-4 w-4" />
            Code Review
          </Button>
        </nav>

        <div className="space-y-2 pt-4 border-t">
          <Button
            variant="ghost"
            className="w-full justify-start"
            onClick={() => router.push("/profile")}
          >
            <UserIcon className="mr-2 h-4 w-4" />
            Profile
          </Button>
          <Button
            variant="outline"
            className="w-full justify-start"
            onClick={handleReset}
            disabled={messages.length === 0}
          >
            <Trash2 className="mr-2 h-4 w-4" />
            Clear Chat
          </Button>
        </div>
      </aside>

      {/* Main chat area */}
      <main className="flex-1 flex flex-col bg-background">
        {/* Chat header */}
        <header className="border-b bg-background/95 backdrop-blur p-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold">Todo Agent</h2>
              <p className="text-sm text-muted-foreground">
                Manage todos and ask IT/coding questions
              </p>
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={handleReset}
              disabled={messages.length === 0}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </header>

        {/* Messages area */}
        <div className="flex-1 overflow-y-auto p-6">
          <div className="max-w-3xl mx-auto space-y-6">
            {messages.length === 0 ? (
              <div className="text-center py-12">
                <div className="text-6xl mb-4">📋</div>
                <h3 className="text-xl font-semibold mb-2">Hello! I'm your Todo Agent</h3>
                <p className="text-muted-foreground mb-8 max-w-md mx-auto">
                  I can help you manage todos and answer IT/coding questions.
                </p>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-2xl mx-auto">
                  {examplePrompts.map((prompt, i) => (
                    <button
                      key={i}
                      onClick={() => setInput(prompt)}
                      className="text-left p-4 rounded-lg border bg-card hover:bg-accent transition-colors"
                    >
                      <p className="text-sm">{prompt}</p>
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <>
                {messages.map((msg, i) => (
                  <div
                    key={i}
                    className={cn(
                      "flex gap-4",
                      msg.role === "user" ? "justify-end" : "justify-start"
                    )}
                  >
                    {msg.role === "assistant" && (
                      <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center shrink-0">
                        <MessageSquare className="h-4 w-4 text-primary-foreground" />
                      </div>
                    )}
                    <Card
                      className={cn(
                        "max-w-[80%] p-4",
                        msg.role === "user"
                          ? "bg-primary text-primary-foreground"
                          : "bg-card"
                      )}
                    >
                      <div className={cn("prose prose-sm max-w-none", msg.role === "user" && "prose-invert")}>
                        <MarkdownContent content={msg.content} />
                      </div>

                      {msg.toolCalls && msg.toolCalls.length > 0 && (
                        <div className="mt-4 space-y-2">
                          {msg.toolCalls.map((call, j) => (
                            <div
                              key={j}
                              className="text-xs bg-muted p-2 rounded font-mono"
                            >
                              <div className="flex items-center gap-2 text-muted-foreground">
                                <Settings className="h-3 w-3" />
                                <span>Called: {call.tool}</span>
                              </div>
                              {call.result && (
                                <div className="mt-1 text-green-600 dark:text-green-400">
                                  ✓ {call.result.slice(0, 100)}
                                  {call.result.length > 100 && "..."}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </Card>
                  </div>
                ))}

                {/* Loading indicator - shows before any content is received */}
                {loading && !streamContent && currentToolCalls.length === 0 && (
                  <div className="flex gap-4 justify-start">
                    <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center shrink-0">
                      <MessageSquare className="h-4 w-4 text-primary-foreground animate-pulse" />
                    </div>
                    <Card className="max-w-[80%] p-4 bg-card">
                      <div className="flex items-center gap-2">
                        <RefreshCw className="h-4 w-4 animate-spin" />
                        <span className="text-sm text-muted-foreground">Thinking...</span>
                      </div>
                    </Card>
                  </div>
                )}

                {/* Streaming content */}
                {loading && streamContent && (
                  <div className="flex gap-4 justify-start">
                    <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center shrink-0">
                      <MessageSquare className="h-4 w-4 text-primary-foreground animate-pulse" />
                    </div>
                    <Card className="max-w-[80%] p-4 bg-card">
                      <div className="prose prose-sm max-w-none">
                        <MarkdownContent content={streamContent} />
                      </div>
                      <span className="inline-block w-2 h-4 bg-current animate-pulse ml-1" />
                    </Card>
                  </div>
                )}

                {/* Active tool calls */}
                {currentToolCalls.length > 0 && (
                  <div className="flex gap-4 justify-start">
                    <div className="w-8" />
                    <div className="space-y-2">
                      {currentToolCalls.map((call, i) => (
                        <div
                          key={i}
                          className="text-sm bg-muted p-3 rounded-lg flex items-center gap-2 animate-pulse"
                        >
                          <Settings className="h-4 w-4 animate-spin" />
                          <span>
                            {call.result ? "Completed" : "Running"}: {call.tool}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </>
            )}
          </div>
        </div>

        {/* Input area */}
        <div className="border-t bg-background p-4">
          <form onSubmit={handleSubmit} className="max-w-3xl mx-auto">
            <div className="flex gap-2">
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about todos, IT, or coding..."
                disabled={loading || !token}
                className="flex-1"
              />
              <Button type="submit" disabled={loading || !input.trim() || !token}>
                {loading ? (
                  <RefreshCw className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </Button>
            </div>
            <p className="text-xs text-muted-foreground mt-2 text-center">
              Press Enter to send, Shift+Enter for new line
            </p>
          </form>
        </div>
      </main>
    </div>
  );
}

function MarkdownContent({ content }: { content: string }) {
  return (
    <ReactMarkdown
      components={{
        code({ className, children, ...props }) {
          const match = /language-(\w+)/.exec(className || "");
          const hasLanguage = match && match[1];
          const isInline = !hasLanguage && String(children).indexOf('\n') === -1;

          return !isInline && hasLanguage ? (
            <SyntaxHighlighter
              // @ts-ignore - style type mismatch with newer react-syntax-highlighter
              style={vscDarkPlus}
              language={match[1]}
              PreTag="div"
            >
              {String(children).replace(/\n$/, "")}
            </SyntaxHighlighter>
          ) : (
            <code className={className} {...props}>
              {children}
            </code>
          );
        },
      }}
    >
      {content}
    </ReactMarkdown>
  );
}
