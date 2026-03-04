"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter, usePathname } from "next/navigation";
import { Button } from "@/components/ui/button";
import { TodoCard } from "@/components/dashboard/TodoCard";
import { AddTodoModal } from "@/components/dashboard/AddTodoModal";
import { Plus, LogOut, RefreshCw, MessageSquare, CheckSquare, FileSearch, User as UserIcon } from "lucide-react";
import { todosApi, Todo } from "@/lib/api";
import { cn } from "@/lib/utils";

export default function DashboardPage() {
  const router = useRouter();
  const pathname = usePathname();
  const [todos, setTodos] = useState<Todo[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editTodo, setEditTodo] = useState<Todo | null>(null);
  const [filter, setFilter] = useState<"all" | "pending" | "completed">("all");
  const [token, setToken] = useState<string>("");

  // Get token from cookie
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

  const fetchTodos = useCallback(async () => {
    if (!token) return;

    setLoading(true);
    try {
      const data = await todosApi.getTodos(token, {
        completed_only: filter === "completed" ? true : filter === "pending" ? false : undefined,
      });
      setTodos(data.items);
    } catch (error) {
      console.error("Failed to fetch todos:", error);
    } finally {
      setLoading(false);
    }
  }, [token, filter]);

  useEffect(() => {
    fetchTodos();
  }, [fetchTodos]);

  const handleCreateTodo = async (data: {
    title: string;
    description?: string;
    due_date?: string;
    priority: "low" | "medium" | "high";
  }) => {
    await todosApi.createTodo(token, data);
    fetchTodos();
  };

  const handleUpdateTodo = async (data: {
    title: string;
    description?: string;
    due_date?: string;
    priority: "low" | "medium" | "high";
  }) => {
    if (editTodo) {
      await todosApi.updateTodo(token, editTodo.id, data);
      fetchTodos();
    }
  };

  const handleToggleComplete = async (id: number) => {
    await todosApi.toggleComplete(token, id);
    fetchTodos();
  };

  const handleDeleteTodo = async (id: number) => {
    if (confirm("Are you sure you want to delete this todo?")) {
      await todosApi.deleteTodo(token, id);
      fetchTodos();
    }
  };

  const handleEdit = (todo: Todo) => {
    setEditTodo(todo);
    setModalOpen(true);
  };

  const handleLogout = async () => {
    await fetch("/api/auth/logout", { method: "POST" });
    router.push("/login");
  };

  // Group todos by completion and date
  const pendingTodos = todos.filter((t) => !t.is_completed);
  const completedTodos = todos.filter((t) => t.is_completed);

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
            variant={pathname === "/dashboard" ? "default" : "ghost"}
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
            variant="ghost"
            className="w-full justify-start text-muted-foreground"
            onClick={handleLogout}
          >
            <LogOut className="mr-2 h-4 w-4" />
            Logout
          </Button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <header className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 p-4 sticky top-0 z-10">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold">My Todos</h2>
              <p className="text-sm text-muted-foreground">
                {pendingTodos.length} pending, {completedTodos.length} completed
              </p>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="icon"
                onClick={fetchTodos}
                disabled={loading}
              >
                <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
              </Button>
              <Button onClick={() => { setEditTodo(null); setModalOpen(true); }}>
                <Plus className="mr-2 h-4 w-4" />
                New Todo
              </Button>
            </div>
          </div>

          {/* Filter tabs */}
          <div className="flex gap-2 mt-4">
            <Button
              variant={filter === "all" ? "default" : "ghost"}
              size="sm"
              onClick={() => setFilter("all")}
            >
              All
            </Button>
            <Button
              variant={filter === "pending" ? "default" : "ghost"}
              size="sm"
              onClick={() => setFilter("pending")}
            >
              Pending
            </Button>
            <Button
              variant={filter === "completed" ? "default" : "ghost"}
              size="sm"
              onClick={() => setFilter("completed")}
            >
              Completed
            </Button>
          </div>
        </header>

        <div className="p-6 max-w-4xl mx-auto">
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : todos.length === 0 ? (
            <div className="text-center py-16">
              <div className="text-6xl mb-4">📝</div>
              <h3 className="text-lg font-semibold mb-2">No todos yet</h3>
              <p className="text-muted-foreground mb-6">
                Create your first todo or ask the AI agent to help you get started.
              </p>
              <Button onClick={() => router.push("/agent")}>
                <MessageSquare className="mr-2 h-4 w-4" />
                Chat with AI
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              {pendingTodos.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-muted-foreground mb-3">
                    PENDING
                  </h3>
                  <div className="space-y-3">
                    {pendingTodos.map((todo) => (
                      <TodoCard
                        key={todo.id}
                        todo={todo}
                        onToggle={handleToggleComplete}
                        onDelete={handleDeleteTodo}
                        onEdit={handleEdit}
                      />
                    ))}
                  </div>
                </div>
              )}

              {completedTodos.length > 0 && filter !== "pending" && (
                <div>
                  <h3 className="text-sm font-semibold text-muted-foreground mb-3 mt-8">
                    COMPLETED
                  </h3>
                  <div className="space-y-3">
                    {completedTodos.map((todo) => (
                      <TodoCard
                        key={todo.id}
                        todo={todo}
                        onToggle={handleToggleComplete}
                        onDelete={handleDeleteTodo}
                        onEdit={handleEdit}
                      />
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </main>

      <AddTodoModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onSave={editTodo ? handleUpdateTodo : handleCreateTodo}
        editTodo={editTodo}
      />
    </div>
  );
}
