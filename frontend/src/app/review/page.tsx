"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Code,
  FileCode,
  GitBranch,
  Send,
  Trash2,
  CheckSquare,
  FileSearch,
  Loader2,
  User as UserIcon,
} from "lucide-react";
import { reviewApi, ReviewEvent } from "@/lib/api";
import { ReviewResults } from "@/components/review/ReviewResults";

const FOCUS_AREAS = [
  { id: "security", label: "Security" },
  { id: "bugs", label: "Bugs" },
  { id: "style", label: "Style" },
  { id: "architecture", label: "Architecture" },
  { id: "performance", label: "Performance" },
  { id: "best_practices", label: "Best Practices" },
];

const LANGUAGES = [
  "python",
  "javascript",
  "typescript",
  "java",
  "c",
  "cpp",
  "csharp",
  "go",
  "rust",
  "ruby",
  "php",
  "swift",
  "kotlin",
  "sql",
  "bash",
  "yaml",
  "json",
  "html",
  "css",
];

export default function ReviewPage() {
  const router = useRouter();
  const [token, setToken] = useState<string>("");
  const [inputMethod, setInputMethod] = useState<"snippet" | "file" | "git">("snippet");
  const [code, setCode] = useState("");
  const [language, setLanguage] = useState("python");
  const [filePath, setFilePath] = useState("");
  const [stagedOnly, setStagedOnly] = useState(false);
  const [focusAreas, setFocusAreas] = useState<string[]>(["security", "bugs", "style", "best_practices"]);
  const [results, setResults] = useState("");
  const [loading, setLoading] = useState(false);
  const [streamContent, setStreamContent] = useState("");

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

  const handleFocusAreaChange = (area: string, checked: boolean) => {
    if (checked) {
      setFocusAreas([...focusAreas, area]);
    } else {
      setFocusAreas(focusAreas.filter((a) => a !== area));
    }
  };

  const handleSelectAll = () => {
    if (focusAreas.length === FOCUS_AREAS.length) {
      setFocusAreas([]);
    } else {
      setFocusAreas(FOCUS_AREAS.map((a) => a.id));
    }
  };

  const getFocusAreasString = () => {
    return focusAreas.length > 0 ? focusAreas.join(",") : "security,bugs,style,best_practices";
  };

  const handleReview = async () => {
    if (!token) return;

    setLoading(true);
    setResults("");
    setStreamContent("");

    try {
      if (inputMethod === "snippet") {
        if (!code.trim()) {
          setResults("Please enter some code to review.");
          setLoading(false);
          return;
        }

        // Use streaming for snippet reviews
        const message = `Please review this ${language} code focusing on: ${getFocusAreasString()}\n\n\`\`\`${language}\n${code}\n\`\`\``;

        let fullContent = "";
        for await (const event of reviewApi.chatStream(token, message)) {
          if (event.type === "content" && event.content) {
            fullContent += event.content;
            setStreamContent(fullContent);
          } else if (event.type === "error") {
            fullContent += `\n\n**Error:** ${event.content}`;
            setStreamContent(fullContent);
          } else if (event.type === "done") {
            break;
          }
        }

        setResults(fullContent);
      } else if (inputMethod === "file") {
        if (!filePath.trim()) {
          setResults("Please enter a file path.");
          setLoading(false);
          return;
        }

        const response = await reviewApi.reviewFile(token, filePath, getFocusAreasString());
        setResults(response.response);
      } else if (inputMethod === "git") {
        const response = await reviewApi.reviewGitDiff(token, stagedOnly, getFocusAreasString());
        setResults(response.response);
      }
    } catch (error) {
      setResults(`**Error:** ${error instanceof Error ? error.message : "Failed to review code"}`);
    } finally {
      setLoading(false);
      setStreamContent("");
    }
  };

  const handleClear = () => {
    setResults("");
    setStreamContent("");
    setCode("");
    setFilePath("");
  };

  const exampleSnippets = [
    { name: "SQL Injection Risk", lang: "python", code: 'def get_user(user_id):\n    query = f"SELECT * FROM users WHERE id = {user_id}"\n    return db.execute(query)' },
    { name: "Missing Error Handling", lang: "javascript", code: 'function fetchUserData(userId) {\n  const response = fetch(`/api/users/${userId}`);\n  return response.json();\n}' },
    { name: "Race Condition", lang: "python", code: 'if user.balance >= amount:\n    time.sleep(0.1)  # Simulate processing\n    user.balance -= amount\n    save(user)' },
  ];

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <aside className="w-64 border-r bg-muted/30 p-4 flex flex-col">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-primary">Todo Agent</h1>
          <p className="text-sm text-muted-foreground">Code Review</p>
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
            variant="ghost"
            className="w-full justify-start"
            onClick={() => router.push("/agent")}
          >
            <Code className="mr-2 h-4 w-4" />
            AI Chat
          </Button>
          <Button
            variant="default"
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
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 flex flex-col bg-background overflow-hidden">
        {/* Header */}
        <header className="border-b bg-background/95 backdrop-blur p-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold">Code Review</h2>
              <p className="text-sm text-muted-foreground">
                Analyze your code for security, bugs, and best practices
              </p>
            </div>
            <Button variant="outline" size="sm" onClick={handleClear} disabled={!results && !loading}>
              <Trash2 className="h-4 w-4 mr-2" />
              Clear
            </Button>
          </div>
        </header>

        {/* Scrollable content */}
        <div className="flex-1 overflow-y-auto p-6">
          <div className="max-w-5xl mx-auto space-y-6">
            {/* Input Methods */}
            <Card className="p-6">
              <Tabs value={inputMethod} onValueChange={(v) => setInputMethod(v as any)}>
                <TabsList className="grid w-full grid-cols-3">
                  <TabsTrigger value="snippet">
                    <Code className="h-4 w-4 mr-2" />
                    Paste Code
                  </TabsTrigger>
                  <TabsTrigger value="file">
                    <FileCode className="h-4 w-4 mr-2" />
                    Select File
                  </TabsTrigger>
                  <TabsTrigger value="git">
                    <GitBranch className="h-4 w-4 mr-2" />
                    Git Diff
                  </TabsTrigger>
                </TabsList>

                {/* Paste Code Tab */}
                <TabsContent value="snippet" className="space-y-4 mt-4">
                  <div className="space-y-2">
                    <Label htmlFor="language">Programming Language</Label>
                    <Select value={language} onValueChange={setLanguage}>
                      <SelectTrigger id="language">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {LANGUAGES.map((lang) => (
                          <SelectItem key={lang} value={lang}>
                            {lang.charAt(0).toUpperCase() + lang.slice(1)}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="code">Code Snippet</Label>
                    <Textarea
                      id="code"
                      value={code}
                      onChange={(e) => setCode(e.target.value)}
                      placeholder="Paste your code here..."
                      className="min-h-[200px] font-mono text-sm"
                      disabled={loading}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label className="text-sm text-muted-foreground">Or try an example:</Label>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                      {exampleSnippets.map((snippet) => (
                        <Button
                          key={snippet.name}
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            setLanguage(snippet.lang);
                            setCode(snippet.code);
                          }}
                          disabled={loading}
                          className="text-left justify-start"
                        >
                          {snippet.name}
                        </Button>
                      ))}
                    </div>
                  </div>
                </TabsContent>

                {/* Select File Tab */}
                <TabsContent value="file" className="space-y-4 mt-4">
                  <div className="space-y-2">
                    <Label htmlFor="filePath">File Path (relative to project root)</Label>
                    <Input
                      id="filePath"
                      value={filePath}
                      onChange={(e) => setFilePath(e.target.value)}
                      placeholder="backend/app/main.py"
                      disabled={loading}
                    />
                    <p className="text-xs text-muted-foreground">
                      Enter the path to a file in your project
                    </p>
                  </div>

                  <div className="bg-muted/50 p-4 rounded-lg">
                    <p className="text-sm font-medium mb-2">Common files to review:</p>
                    <div className="flex flex-wrap gap-2">
                      {["app/main.py", "app/agent/agent.py", "app/api/todos.py", "src/app/page.tsx"].map((path) => (
                        <Button
                          key={path}
                          variant="secondary"
                          size="sm"
                          onClick={() => setFilePath(path)}
                          disabled={loading}
                        >
                          {path}
                        </Button>
                      ))}
                    </div>
                  </div>
                </TabsContent>

                {/* Git Diff Tab */}
                <TabsContent value="git" className="space-y-4 mt-4">
                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="staged"
                      checked={stagedOnly}
                      onCheckedChange={(checked) => setStagedOnly(checked as boolean)}
                      disabled={loading}
                    />
                    <Label htmlFor="staged">Review staged changes (git diff --staged)</Label>
                  </div>

                  {!stagedOnly && (
                    <p className="text-sm text-muted-foreground">
                      Will review unstaged changes (git diff)
                    </p>
                  )}

                  <div className="bg-muted/50 p-4 rounded-lg">
                    <p className="text-sm font-medium mb-2">Quick test:</p>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        // Just to show the feature works
                        setResults("Run `git diff` or `git add` some changes first to review.");
                      }}
                      disabled={loading}
                    >
                      Check git status
                    </Button>
                  </div>
                </TabsContent>
              </Tabs>
            </Card>

            {/* Focus Areas */}
            <Card className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold">Focus Areas</h3>
                <Button variant="ghost" size="sm" onClick={handleSelectAll} disabled={loading}>
                  {focusAreas.length === FOCUS_AREAS.length ? "Deselect All" : "Select All"}
                </Button>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {FOCUS_AREAS.map((area) => (
                  <div key={area.id} className="flex items-center space-x-2">
                    <Checkbox
                      id={area.id}
                      checked={focusAreas.includes(area.id)}
                      onCheckedChange={(checked) => handleFocusAreaChange(area.id, checked as boolean)}
                      disabled={loading}
                    />
                    <Label htmlFor={area.id} className="text-sm cursor-pointer">
                      {area.label}
                    </Label>
                  </div>
                ))}
              </div>
            </Card>

            {/* Submit Button */}
            <Button
              onClick={handleReview}
              disabled={loading || !token}
              className="w-full"
              size="lg"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Reviewing...
                </>
              ) : (
                <>
                  <Send className="h-4 w-4 mr-2" />
                  Review Code
                </>
              )}
            </Button>

            {/* Results */}
            <ReviewResults content={streamContent || results} loading={loading} />
          </div>
        </div>
      </main>
    </div>
  );
}
